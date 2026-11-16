"""Browser Automation Service - AI-Powered Test Automation (playwright port).

Port of the former browser-use 0.13 integration (card c478c23a, decision
Joker 11-nov). Same public interface as before (execute_task / get_status),
but the agent loop now runs on Playwright (already in the stack) and the
LLM is reached through the LiteLLM gateway (:4000 -> :8009), removing the
old agent-library and vendor LLM SDK dependencies.
"""

import asyncio
import json
import re
from typing import Optional, Dict, Any, List
from uuid import uuid4
from datetime import datetime

import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.browser_use_task import BrowserUseTask, TaskStatus
from config import settings
from core.logging_config import get_logger

logger = get_logger(__name__)

_MAX_SNIPPET_CHARS = 4000

_SYSTEM_PROMPT = (
    "You drive a browser to complete the user's task. Each turn you receive "
    "the current page state. Reply ONLY with a JSON object choosing one action:\n"
    '{"action": "click"|"type"|"scroll"|"navigate"|"done", '
    '"selector": "<css selector>", "text": "<text to type or final answer>"}\n'
    'Use "done" with "text" set to a short summary when the task is complete.'
)


class BrowserAutomationError(RuntimeError):
    """Raised when the automation loop cannot proceed."""


class BrowserUseService:
    """Service for executing browser automation tasks (playwright backend)."""

    def __init__(self):
        self.active_tasks: Dict[str, asyncio.Task] = {}

    # ------------------------------------------------------------------ LLM
    def _get_llm_config(self) -> Dict[str, str]:
        """Resolve LiteLLM/OpenAI-compatible endpoint config.

        The old Groq path is gone: the LiteLLM gateway (:4000 -> :8009) is the
        single remote door. Existing deployments that only set the groq vars
        keep working because we route them through LiteLLM too.
        """
        base_url = getattr(settings, "LITELLM_BASE_URL", None) or "http://127.0.0.1:4000/v1"
        api_key = None
        if getattr(settings, "LITELLM_API_KEY", None):
            api_key = settings.LITELLM_API_KEY.get_secret_value()
        elif getattr(settings, "GROQ_API_KEY", None):
            api_key = settings.GROQ_API_KEY.get_secret_value()
        return {"base_url": base_url, "api_key": api_key or "sk-noop", "model": settings.BROWSER_USE_MODEL}

    async def _ask_llm(self, messages) -> str:
        """One chat completion through the LiteLLM gateway."""
        cfg = self._get_llm_config()
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                cfg["base_url"] + "/chat/completions",
                headers={"Authorization": "Bearer " + cfg["api_key"]},
                json={"model": cfg["model"], "messages": messages, "temperature": 0},
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]

    async def _plan_step(self, prompt: str, page_state: str, history) -> Dict[str, Any]:
        """Ask the LLM for the next action given the current page state."""
        messages = [{"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": "Task: " + prompt}]
        messages.extend(history)
        messages.append({"role": "user", "content": "Current page state:\n" + page_state})
        raw = await self._ask_llm(messages)
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not match:
            raise BrowserAutomationError("LLM returned non-JSON action: " + raw[:200])
        return json.loads(match.group(0))

    # ------------------------------------------------------------ page state
    @staticmethod
    async def _page_state(page) -> str:
        """Compact textual snapshot of the page for the LLM."""
        title = await page.title()
        current = page.url
        body = await page.evaluate(
            "() => {"
            "const els = Array.from(document.querySelectorAll("
            "'a[href], button, input, textarea, select, [role=button], [onclick]'));"
            "return els.slice(0, 60).map((e, i) => {"
            "const label = (e.innerText || e.placeholder || e.value || e.getAttribute('aria-label') || '').trim().slice(0, 80);"
            "const sel = e.id ? '#' + e.id : (e.name ? '[name=' + e.name + ']' : e.tagName.toLowerCase() + ':' + i);"
            "return sel + ' -> ' + label;"
            "}).join('\n');"
            "}"
        )
        return "URL: " + current + "\nTitle: " + title + "\nInteractive elements:\n" + body[:_MAX_SNIPPET_CHARS]

    @staticmethod
    async def _apply_action(page, action: Dict[str, Any]) -> None:
        """Execute one LLM-chosen action on the page."""
        kind = action.get("action", "")
        if kind == "click":
            await page.click(action["selector"], timeout=10000)
        elif kind == "type":
            await page.fill(action["selector"], action.get("text", ""), timeout=10000)
        elif kind == "scroll":
            await page.mouse.wheel(0, 600)
        elif kind == "navigate":
            await page.goto(action.get("text") or action.get("selector"), timeout=30000)
        elif kind == "done":
            return
        else:
            raise BrowserAutomationError("Unsupported action from LLM: " + str(kind))
        await page.wait_for_load_state("domcontentloaded", timeout=15000)

    # ----------------------------------------------------------------- task
    @staticmethod
    def _compose_task(prompt: str, url: str) -> str:
        """Embed the start URL in the task text (kept for interface compat)."""
        return prompt + " (start URL: " + url + ")"

    async def execute_task(
        self,
        prompt: str,
        url: str,
        user_id: int,
        db: AsyncSession,
        options: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Execute a browser automation task asynchronously. Returns task ID."""
        task_id = "bu_" + uuid4().hex[:8]

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

        background_task = asyncio.create_task(
            self._execute_browser_agent(task_id, prompt, url, db, options)
        )
        self.active_tasks[task_id] = background_task
        background_task.add_done_callback(lambda _: self.active_tasks.pop(task_id, None))
        return task_id

    async def _execute_browser_agent(
        self,
        task_id: str,
        prompt: str,
        url: str,
        db: AsyncSession,
        options: Optional[Dict[str, Any]] = None,
    ):
        """Run the playwright automation loop in background."""
        try:
            await self._update_task_status(db, task_id, TaskStatus.RUNNING)
            options = options or {}
            max_steps = options.get("max_steps", 100)
            headless = options.get("headless", True)

            from playwright.async_api import async_playwright

            start_time = datetime.utcnow()
            history = []
            final_answer = None

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=headless)
                context = await browser.new_context()
                page = await context.new_page()
                await page.goto(url, timeout=30000, wait_until="domcontentloaded")

                for _ in range(max_steps):
                    state = await self._page_state(page)
                    action = await self._plan_step(prompt, state, history)
                    history.append({"role": "assistant", "content": json.dumps(action)})
                    if action.get("action") == "done":
                        final_answer = action.get("text", "")
                        break
                    await self._apply_action(page, action)

                result = {
                    "url": page.url,
                    "title": await page.title(),
                    "final_answer": final_answer,
                    "steps_used": len(history),
                }
                if options.get("screenshot"):
                    result["screenshot"] = await page.screenshot(
                        path=options.get("screenshot_path") or "/tmp/" + task_id + ".png"
                    )
                await browser.close()

            duration = (datetime.utcnow() - start_time).total_seconds()
            await self._update_task_result(
                db,
                task_id,
                TaskStatus.COMPLETED,
                result=self._parse_result(result),
                duration_seconds=int(duration),
            )
            logger.info("Browser automation task completed", task_id=task_id, duration=duration)

        except Exception as e:
            logger.error("Browser automation task failed", task_id=task_id, error=str(e))
            await self._update_task_result(db, task_id, TaskStatus.FAILED, error_message=str(e))

    def _parse_result(self, result: Any) -> Dict:
        """Parse automation result into dict."""
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
        if not task:
            return
        task.status = status
        if result is not None:
            task.result = result
        if error_message is not None:
            task.error_message = error_message
        if duration_seconds is not None:
            task.duration_seconds = duration_seconds
        if status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
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
            "status": task.status.value if hasattr(task.status, "value") else task.status,
            "prompt": task.prompt,
            "url": task.url,
            "result": task.result,
            "screenshots": task.screenshots or [],
            "video": task.video_path,
            "duration_seconds": float(task.duration_seconds) if task.duration_seconds else None,
            "error": task.error_message,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        }
