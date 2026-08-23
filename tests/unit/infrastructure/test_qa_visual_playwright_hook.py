"""Unit tests for the Playwright E2E post-test QA Visual hook."""

import json
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from src.infrastructure.qa_visual.analyzer import QAVisualAnalysisError, QAVisualAnalyzer
from src.infrastructure.qa_visual.config import QAVisualConfig
from src.infrastructure.qa_visual.models import AnalyzeResponse, QAAnalysis
from src.infrastructure.qa_visual.playwright_hook import QAVisualHook
from src.infrastructure.qa_visual.storage import QAVisualReportStore

PNG_BYTES = b"\x89PNG\r\n\x1a\nfakepng"


class FakePage:
    """Duck-typed stand-in for a Playwright page."""

    def __init__(self, screenshot_bytes: bytes = PNG_BYTES):
        self._bytes = screenshot_bytes
        self.screenshot_calls = []

    async def screenshot(self, path: str) -> None:
        self.screenshot_calls.append(path)
        Path(path).write_bytes(self._bytes)


def make_response(**overrides) -> AnalyzeResponse:
    fields = dict(
        report_id="rep-1",
        target="test_login",
        analysis=QAAnalysis(overall_score=95, summary="clean"),
        passed=True,
        score=95,
        threshold=80,
        cost_usd=0.0004,
        latency_s=4.0,
        model="deepseek-v4-flash-vision-exp",
        regression_detected=False,
    )
    fields.update(overrides)
    return AnalyzeResponse(**fields)


@pytest.fixture
def analyzer(tmp_path):
    analyzer = QAVisualAnalyzer.__new__(QAVisualAnalyzer)
    analyzer._config = QAVisualConfig()
    analyzer._store = QAVisualReportStore(reports_dir=str(tmp_path / "reports"))
    analyzer.analyze = AsyncMock(return_value=make_response())
    return analyzer


@pytest.fixture
def hook(analyzer, tmp_path) -> QAVisualHook:
    return QAVisualHook(
        analyzer=analyzer,
        screenshots_dir=str(tmp_path / "screenshots"),
    )


class TestScreenshotCapture:
    @pytest.mark.asyncio
    async def test_screenshot_taken_to_hook_dir(self, hook, analyzer):
        page = FakePage()
        await hook.on_test_end(page, test_name="test_login")
        assert len(page.screenshot_calls) == 1
        assert Path(page.screenshot_calls[0]).parent.name == "screenshots"
        assert "test_login" in Path(page.screenshot_calls[0]).name

    @pytest.mark.asyncio
    async def test_screenshots_dir_created_if_missing(self, hook, tmp_path):
        screenshots_dir = tmp_path / "screenshots"
        assert not screenshots_dir.exists()
        await hook.on_test_end(FakePage(), test_name="test_login")
        assert screenshots_dir.is_dir()

    @pytest.mark.asyncio
    async def test_screenshot_bytes_analyzed(self, hook, analyzer):
        await hook.on_test_end(FakePage(), test_name="test_login")
        call = analyzer.analyze.call_args
        sent = call.args[0] if call.args else call.kwargs.get("image_bytes")
        assert sent == PNG_BYTES

    @pytest.mark.asyncio
    async def test_target_is_test_name(self, hook, analyzer):
        await hook.on_test_end(FakePage(), test_name="test_checkout_flow")
        call = analyzer.analyze.call_args
        sent_target = call.args[1] if len(call.args) > 1 else call.kwargs.get("target")
        assert sent_target == "test_checkout_flow"


class TestTestReportAppend:
    @pytest.mark.asyncio
    async def test_appends_qa_visual_section_to_existing_report(self, hook, tmp_path):
        report_path = tmp_path / "report.json"
        report_path.write_text(json.dumps({"test": "test_login", "status": "passed"}))

        response = await hook.on_test_end(
            FakePage(), test_name="test_login", report_path=str(report_path)
        )

        data = json.loads(report_path.read_text())
        assert data["status"] == "passed"  # original content preserved
        assert data["qa_visual"]["report_id"] == "rep-1"
        assert data["qa_visual"]["score"] == 95
        assert response.score == 95

    @pytest.mark.asyncio
    async def test_creates_report_file_when_missing(self, hook, tmp_path):
        report_path = tmp_path / "new_report.json"
        await hook.on_test_end(FakePage(), test_name="test_login", report_path=str(report_path))
        data = json.loads(report_path.read_text())
        assert data["qa_visual"]["report_id"] == "rep-1"

    @pytest.mark.asyncio
    async def test_replaces_previous_qa_visual_section(self, hook, tmp_path):
        report_path = tmp_path / "report.json"
        report_path.write_text(
            json.dumps({"test": "t", "qa_visual": {"report_id": "old", "score": 1}})
        )
        await hook.on_test_end(FakePage(), test_name="t", report_path=str(report_path))
        data = json.loads(report_path.read_text())
        assert data["qa_visual"]["report_id"] == "rep-1"


class TestFailSoftBehaviour:
    """A QA hook must never break the E2E suite it observes."""

    @pytest.mark.asyncio
    async def test_analysis_failure_returns_none(self, hook, analyzer):
        analyzer.analyze.side_effect = QAVisualAnalysisError("gateway down")
        result = await hook.on_test_end(FakePage(), test_name="test_login")
        assert result is None

    @pytest.mark.asyncio
    async def test_screenshot_failure_returns_none(self, hook):
        class BrokenPage:
            async def screenshot(self, path: str) -> None:
                raise RuntimeError("browser crashed")

        result = await hook.on_test_end(BrokenPage(), test_name="test_login")
        assert result is None

    @pytest.mark.asyncio
    async def test_failure_does_not_touch_report_file(self, hook, analyzer, tmp_path):
        report_path = tmp_path / "report.json"
        report_path.write_text(json.dumps({"status": "passed"}))
        analyzer.analyze.side_effect = QAVisualAnalysisError("gateway down")
        await hook.on_test_end(FakePage(), test_name="t", report_path=str(report_path))
        assert json.loads(report_path.read_text()) == {"status": "passed"}


class TestEndToEndWithRealAnalyzer:
    """Full hook flow against a real analyzer with a stub gateway."""

    @pytest.mark.asyncio
    async def test_full_flow(self, tmp_path):
        from src.infrastructure.qa_visual.gateway_client import VisionResult

        content = json.dumps({"overall_score": 88, "summary": "fine"})
        gateway = AsyncMock()
        gateway.analyze_image = AsyncMock(
            return_value=VisionResult(
                content=content,
                latency_s=3.0,
                usage={"prompt_tokens": 100, "completion_tokens": 50},
                cost_usd=0.00006,
                model_reported="deepseek-v4-flash-vision-exp",
                finish_reason="stop",
            )
        )
        analyzer = QAVisualAnalyzer(
            config=QAVisualConfig(),
            gateway_client=gateway,
            store=QAVisualReportStore(reports_dir=str(tmp_path / "reports")),
        )
        hook = QAVisualHook(analyzer=analyzer, screenshots_dir=str(tmp_path / "shots"))

        report_path = tmp_path / "e2e_report.json"
        response = await hook.on_test_end(
            FakePage(), test_name="test_home", report_path=str(report_path)
        )

        assert response.score == 88
        assert response.passed is True
        data = json.loads(report_path.read_text())
        assert data["qa_visual"]["score"] == 88
        # report also persisted in the module store
        stored = analyzer.store.list_reports(target="test_home")
        assert len(stored) == 1
