"""Playwright E2E post-test hook for QA Visual analysis.

After a test finishes, the hook captures a screenshot of the page, sends it
through the QA Visual analyzer and appends the resulting report to the test's
JSON report file under a ``qa_visual`` key.

Design rules:
- Duck typing: any object with ``await screenshot(path=...)`` works, so both
  Playwright pages and test doubles can be passed in.
- Fail-soft: a QA hook must never break the E2E suite it observes. All errors
  are logged and swallowed, returning None.
"""

import json
import logging
import re
from pathlib import Path

from src.infrastructure.qa_visual.analyzer import QAVisualAnalyzer
from src.infrastructure.qa_visual.models import AnalyzeResponse

logger = logging.getLogger(__name__)


def _sanitize_test_name(test_name: str) -> str:
    sanitized = re.sub(r"[^a-zA-Z0-9_-]+", "-", test_name).strip("-")
    return sanitized or "unnamed-test"


class QAVisualHook:
    """Post-test hook: screenshot -> vision analysis -> test report append."""

    def __init__(
        self, analyzer: QAVisualAnalyzer, screenshots_dir: str = "reports/qa-visual/screenshots"
    ):
        self._analyzer = analyzer
        self._screenshots_dir = Path(screenshots_dir)

    async def on_test_end(
        self,
        page,
        test_name: str,
        report_path: str | Path | None = None,
    ) -> AnalyzeResponse | None:
        """Capture, analyze and record. Never raises.

        Args:
            page: object exposing ``await page.screenshot(path=...)``
            test_name: test (or page) identifier used as analysis target
            report_path: optional JSON test report to append the result to

        Returns:
            The AnalyzeResponse, or None when the hook failed softly.
        """
        safe_name = _sanitize_test_name(test_name)
        try:
            screenshot_path = await self._capture(page, safe_name)
            image_bytes = screenshot_path.read_bytes()
            response = await self._analyzer.analyze(image_bytes, target=test_name)
        except Exception:
            logger.exception("qa-visual hook failed for %s (ignored)", safe_name)
            return None

        if report_path:
            try:
                self._append_to_report(Path(report_path), response)
            except Exception:
                logger.exception(
                    "qa-visual hook could not update test report %s (ignored)", report_path
                )
        return response

    async def _capture(self, page, safe_name: str) -> Path:
        self._screenshots_dir.mkdir(parents=True, exist_ok=True)
        path = self._screenshots_dir / f"{safe_name}.png"
        # Duck-typed call: works with playwright Page and PlaywrightPage alike.
        await page.screenshot(path=str(path))
        return path

    def _append_to_report(self, report_path: Path, response: AnalyzeResponse) -> None:
        data = {}
        if report_path.exists():
            try:
                data = json.loads(report_path.read_text())
            except json.JSONDecodeError:
                logger.warning(
                    "qa-visual: test report %s is not valid JSON, recreating", report_path
                )
                data = {}
        data["qa_visual"] = response.model_dump(mode="json")
        report_path.write_text(json.dumps(data, indent=2))
