"""Browser-Use Service - AI-Powered Test Automation."""

import asyncio
from typing import Optional, Dict, Any
from uuid import uuid4
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.browser_use_task import BrowserUseTask, TaskStatus
from config import settings
from core.logging_config import get_logger

logger = get_logger(__name__)


class BrowserUseService:
    """Service for executing browser-use tasks."""

    def __init__(self):
        self.active_tasks: Dict[str, asyncio.Task] = {}
        self._llm = None

    def _get_llm(self):
        """Get LLM instance based on configuration."""
        if self._llm is None:
            if settings.BROWSER_USE_LLM_PROVIDER == "groq":
                # browser-use 0.13 ships its own LLM wrappers (BaseChatModel protocol);
                # langchain models are no longer accepted by Agent.
                from browser_use import ChatGroq

                self._llm = ChatGroq(
                    model=settings.BROWSER_USE_MODEL,
                    api_key=(
                        settings.GROQ_API_KEY.get_secret_value() if settings.GROQ_API_KEY else None
                    ),
                )
            else:
                raise ValueError(f"Unsupported LLM provider: {settings.BROWSER_USE_LLM_PROVIDER}")
        return self._llm

    @staticmethod
    def _compose_task(prompt: str, url: str) -> str:
        """Embed the start URL in the task text.

        browser-use 0.13 removed ``run(url)``: with ``directly_open_url=True``
        (the default) the agent extracts a single URL from the task and opens
        it as its initial action.
        """
        return f"{prompt}\n\nStart by navigating to: {url}"

    def _build_agent(self, prompt: str, url: str, options: Optional[Dict[str, Any]] = None):
        """Construct a browser-use 0.13 Agent (no network, no browser launch).

        ``browser_config=`` was removed in 0.13; the headless flag now lives on
        a ``BrowserProfile`` passed as ``browser_profile=``.
        """
        from browser_use import Agent, BrowserProfile

        return Agent(
            task=self._compose_task(prompt, url),
            llm=self._get_llm(),
            browser_profile=BrowserProfile(headless=(options or {}).get("headless", True)),
        )

    async def execute_task(
        self,
        prompt: str,
        url: str,
        user_id: int,
        db: AsyncSession,
        options: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Execute a browser-use task asynchronously.

        Args:
            prompt: Natural language task description
            url: Target URL
            user_id: User ID executing the task
            db: Database session
            options: Optional execution options

        Returns:
            Task ID
        """
        task_id = f"bu_{uuid4().hex[:8]}"

        # Create task record
        db_task = BrowserUseTask(
            task_id=task_id,
            user_id=user_id,
            prompt=prompt,
            url=url,
            status=TaskStatus.PENDING,
            options=options or {},
        )
        db.add(db_task)
        await db.commit()

        logger.info("Created browser-use task", task_id=task_id, prompt=prompt, url=url)

        # Start background execution
        async_task = asyncio.create_task(
            self._execute_browser_agent(task_id, prompt, url, db, options)
        )
        self.active_tasks[task_id] = async_task

        return task_id

    async def _execute_browser_agent(
        self,
        task_id: str,
        prompt: str,
        url: str,
        db: AsyncSession,
        options: Optional[Dict[str, Any]] = None,
    ):
        """Execute browser-use agent in background."""
        try:
            # Update status to running
            await self._update_task_status(db, task_id, TaskStatus.RUNNING)

            options = options or {}
            # browser-use 0.13: Agent construction uses browser_profile= (browser_config
            # was removed) and the start URL travels inside the task text.
            agent = self._build_agent(prompt, url, options)

            start_time = datetime.utcnow()

            # Cap at 100 steps (the 0.1.x default) to bound task cost; 0.13 defaults to 500.
            result = await agent.run(max_steps=options.get("max_steps", 100))

            duration = (datetime.utcnow() - start_time).total_seconds()

            # Update task with results
            await self._update_task_result(
                db,
                task_id,
                TaskStatus.COMPLETED,
                result=self._parse_result(result),
                duration_seconds=int(duration),
            )

            logger.info("Browser-use task completed", task_id=task_id, duration=duration)

        except Exception as e:
            logger.error("Browser-use task failed", task_id=task_id, error=str(e))
            await self._update_task_result(db, task_id, TaskStatus.FAILED, error_message=str(e))

    def _parse_result(self, result: Any) -> Dict:
        """Parse browser-use result into dict."""
        if isinstance(result, dict):
            return result
        if hasattr(result, "model_dump"):
            return result.model_dump()
        return {"raw_result": str(result)}

    async def _update_task_status(self, db: AsyncSession, task_id: str, status: TaskStatus):
        """Update task status in database."""
        result = await db.execute(select(BrowserUseTask).where(BrowserUseTask.task_id == task_id))
        task = result.scalar_one_or_none()
        if task:
            task.status = status
            await db.commit()

    async def _update_task_result(
        self,
        db: AsyncSession,
        task_id: str,
        status: TaskStatus,
        result: Optional[Dict] = None,
        error_message: Optional[str] = None,
        duration_seconds: Optional[int] = None,
    ):
        """Update task with final results."""
        result_obj = await db.execute(
            select(BrowserUseTask).where(BrowserUseTask.task_id == task_id)
        )
        task = result_obj.scalar_one_or_none()
        if task:
            task.status = status
            if result:
                task.result = result
            if error_message:
                task.error_message = error_message
            if duration_seconds:
                task.duration_seconds = duration_seconds
            task.completed_at = datetime.utcnow()
            await db.commit()

    async def get_status(self, task_id: str, db: AsyncSession) -> Optional[Dict[str, Any]]:
        """Get task status."""
        result = await db.execute(select(BrowserUseTask).where(BrowserUseTask.task_id == task_id))
        task = result.scalar_one_or_none()
        if not task:
            return None

        return {
            "task_id": task.task_id,
            "status": task.status.value,
            "progress": 100 if task.status == TaskStatus.COMPLETED else 0,
            "current_step": None,
            "error": task.error_message,
        }

    async def get_results(self, task_id: str, db: AsyncSession) -> Optional[Dict[str, Any]]:
        """Get full task results."""
        result = await db.execute(select(BrowserUseTask).where(BrowserUseTask.task_id == task_id))
        task = result.scalar_one_or_none()
        if not task:
            return None

        return {
            "task_id": task.task_id,
            "status": task.status.value,
            "success": task.status == TaskStatus.COMPLETED,
            "steps": task.result.get("steps", []) if task.result else [],
            "screenshots": task.screenshots or [],
            "video": task.video_path,
            "duration_seconds": float(task.duration_seconds) if task.duration_seconds else None,
            "error": task.error_message,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        }
