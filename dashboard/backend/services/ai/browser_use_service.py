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

try:
    from src.infrastructure.observability import get_langfuse_tracer, get_langfuse_handler
except ImportError:
    get_langfuse_tracer = None  # type: ignore[assignment]
    get_langfuse_handler = None  # type: ignore[assignment]

logger = get_logger(__name__)


class _null_context:
    """No-op context manager for when Langfuse is disabled."""
    def __enter__(self):
        return None
    def __exit__(self, *args):
        pass


class BrowserUseService:
    """Service for executing browser-use tasks."""

    def __init__(self):
        self.active_tasks: Dict[str, asyncio.Task] = {}
        self._llm = None

    def _get_llm(self):
        """Get LLM instance based on configuration."""
        if self._llm is None:
            if settings.BROWSER_USE_LLM_PROVIDER == "groq":
                from langchain_groq import ChatGroq

                callbacks = []
                if get_langfuse_handler is not None:
                    try:
                        handler = get_langfuse_handler()
                        callbacks.append(handler)
                    except Exception as exc:
                        logger.warning("Langfuse handler not available: %s", exc)

                self._llm = ChatGroq(
                    model=settings.BROWSER_USE_MODEL,
                    api_key=settings.GROQ_API_KEY,
                    callbacks=callbacks if callbacks else None,
                )
            else:
                raise ValueError(f"Unsupported LLM provider: {settings.BROWSER_USE_LLM_PROVIDER}")
        return self._llm

    async def execute_task(
        self,
        prompt: str,
        url: str,
        user_id: int,
        db: AsyncSession,
        options: Optional[Dict[str, Any]] = None
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
            options=options or {}
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
        options: Optional[Dict[str, Any]] = None
    ):
        """Execute browser-use agent in background."""
        tracer = get_langfuse_tracer() if get_langfuse_tracer is not None else None

        with (
            tracer.span(
                name="browser-use-agent",
                input={"prompt": prompt, "url": url, "task_id": task_id},
                metadata={"service": "browser_use", "task_id": task_id},
            )
            if tracer and tracer.is_active
            else _null_context()
        ) as span:
            try:
                # Update status to running
                await self._update_task_status(db, task_id, TaskStatus.RUNNING)

                # Import browser-use here to avoid import errors if not installed
                from browser_use import Agent

                llm = self._get_llm()
                options = options or {}

                agent = Agent(
                    task=prompt,
                    llm=llm,
                    browser_config={
                        "headless": options.get("headless", True),
                    }
                )

                start_time = datetime.utcnow()

                # Run the agent
                result = await agent.run(url)

                duration = (datetime.utcnow() - start_time).total_seconds()

                parsed = self._parse_result(result)

                # Update task with results
                await self._update_task_result(
                    db, task_id, TaskStatus.COMPLETED,
                    result=parsed,
                    duration_seconds=int(duration),
                )

                if span is not None:
                    span.update(
                        output=parsed,
                        metadata={"duration_seconds": duration, "status": "completed"},
                    )

                logger.info("Browser-use task completed", task_id=task_id, duration=duration)

            except Exception as e:
                logger.error("Browser-use task failed", task_id=task_id, error=str(e))
                await self._update_task_result(
                    db, task_id, TaskStatus.FAILED,
                    error_message=str(e),
                )
                if span is not None:
                    span.update(output={"error": str(e)}, level="ERROR")

    def _parse_result(self, result: Any) -> Dict:
        """Parse browser-use result into dict."""
        if isinstance(result, dict):
            return result
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        return {"raw_result": str(result)}

    async def _update_task_status(
        self,
        db: AsyncSession,
        task_id: str,
        status: TaskStatus
    ):
        """Update task status in database."""
        result = await db.execute(
            select(BrowserUseTask).where(BrowserUseTask.task_id == task_id)
        )
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
        duration_seconds: Optional[int] = None
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

    async def get_status(
        self,
        task_id: str,
        db: AsyncSession
    ) -> Optional[Dict[str, Any]]:
        """Get task status."""
        result = await db.execute(
            select(BrowserUseTask).where(BrowserUseTask.task_id == task_id)
        )
        task = result.scalar_one_or_none()
        if not task:
            return None

        return {
            "task_id": task.task_id,
            "status": task.status.value,
            "progress": 100 if task.status == TaskStatus.COMPLETED else 0,
            "current_step": None,
            "error": task.error_message
        }

    async def get_results(
        self,
        task_id: str,
        db: AsyncSession
    ) -> Optional[Dict[str, Any]]:
        """Get full task results."""
        result = await db.execute(
            select(BrowserUseTask).where(BrowserUseTask.task_id == task_id)
        )
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
            "completed_at": task.completed_at.isoformat() if task.completed_at else None
        }
