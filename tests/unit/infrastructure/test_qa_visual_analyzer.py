"""Unit tests for the QA Visual analyzer (threshold + baseline regression)."""

import json
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from src.infrastructure.qa_visual.analyzer import (
    QAVisualAnalysisError,
    QAVisualAnalyzer,
    build_trend_report,
)
from src.infrastructure.qa_visual.config import QAVisualConfig
from src.infrastructure.qa_visual.gateway_client import VisionGatewayError, VisionResult
from src.infrastructure.qa_visual.storage import QAVisualReportStore

GOOD_CONTENT = json.dumps(
    {
        "page_title": "AMC",
        "visible_texts": ["Login"],
        "qa_issues": [],
        "overall_score": 95,
        "summary": "clean",
        "visual_regression": {
            "unexpected_whitespace": False,
            "overlapping_elements": False,
            "cut_off_content": False,
            "misaligned": False,
        },
    }
)


def make_vision_result(content: str = GOOD_CONTENT, cost: float = 0.000428) -> VisionResult:
    return VisionResult(
        content=content,
        latency_s=4.37,
        usage={"prompt_tokens": 1000, "completion_tokens": 800},
        cost_usd=cost,
        model_reported="deepseek-v4-flash-vision-exp",
        finish_reason="stop",
    )


@pytest.fixture
def store(tmp_path: Path) -> QAVisualReportStore:
    return QAVisualReportStore(reports_dir=str(tmp_path / "qa-visual"))


@pytest.fixture
def gateway():
    gw = AsyncMock()
    gw.analyze_image = AsyncMock(return_value=make_vision_result())
    gw.close = AsyncMock()
    return gw


@pytest.fixture
def analyzer(store, gateway) -> QAVisualAnalyzer:
    return QAVisualAnalyzer(config=QAVisualConfig(), gateway_client=gateway, store=store)


class TestAnalyze:
    @pytest.mark.asyncio
    async def test_happy_path_passes_threshold(self, analyzer, store):
        response = await analyzer.analyze(b"png", target="amc")
        assert response.passed is True
        assert response.score == 95
        assert response.threshold == 80
        assert response.cost_usd == pytest.approx(0.000428)
        assert response.latency_s == 4.37
        assert response.model == "deepseek-v4-flash-vision-exp"
        assert response.target == "amc"

    @pytest.mark.asyncio
    async def test_report_persisted(self, analyzer, store):
        response = await analyzer.analyze(b"png", target="amc")
        # analyze() ran without an owner, so the persisted report is
        # unowned (legacy shape): only an explicit admin read sees it.
        saved = store.get_report(response.report_id, is_admin=True)
        assert saved is not None
        assert saved["score"] == 95

    @pytest.mark.asyncio
    async def test_low_score_fails_threshold(self, analyzer, gateway):
        low = json.loads(GOOD_CONTENT)
        low["overall_score"] = 65
        gateway.analyze_image.return_value = make_vision_result(json.dumps(low))
        response = await analyzer.analyze(b"png", target="amc")
        assert response.passed is False
        assert response.score == 65

    @pytest.mark.asyncio
    async def test_gateway_error_wrapped(self, analyzer, gateway):
        gateway.analyze_image.side_effect = VisionGatewayError("Gateway HTTP 503: down")
        with pytest.raises(QAVisualAnalysisError, match="503"):
            await analyzer.analyze(b"png", target="amc")

    @pytest.mark.asyncio
    async def test_parse_error_raises_with_raw_content(self, analyzer, gateway):
        gateway.analyze_image.return_value = make_vision_result("utter garbage")
        with pytest.raises(QAVisualAnalysisError) as exc_info:
            await analyzer.analyze(b"png", target="amc")
        assert exc_info.value.raw_content == "utter garbage"


class TestRegressionDetection:
    @pytest.mark.asyncio
    async def test_first_run_is_never_regression(self, analyzer):
        response = await analyzer.analyze(b"png", target="amc")
        assert response.regression_detected is False

    @pytest.mark.asyncio
    async def test_score_drop_triggers_regression(self, analyzer, gateway):
        await analyzer.analyze(b"png", target="amc")  # baseline score 95
        dropped = json.loads(GOOD_CONTENT)
        dropped["overall_score"] = 80  # drop of 15 >= alert threshold (10)
        gateway.analyze_image.return_value = make_vision_result(json.dumps(dropped))
        response = await analyzer.analyze(b"png", target="amc")
        assert response.regression_detected is True

    @pytest.mark.asyncio
    async def test_small_drop_no_regression(self, analyzer, gateway):
        await analyzer.analyze(b"png", target="amc")  # baseline score 95
        slight = json.loads(GOOD_CONTENT)
        slight["overall_score"] = 90  # drop of 5 < 10
        gateway.analyze_image.return_value = make_vision_result(json.dumps(slight))
        response = await analyzer.analyze(b"png", target="amc")
        assert response.regression_detected is False

    @pytest.mark.asyncio
    async def test_regression_flags_trigger_regression(self, analyzer, gateway):
        await analyzer.analyze(b"png", target="amc")
        flagged = json.loads(GOOD_CONTENT)
        flagged["visual_regression"]["overlapping_elements"] = True
        gateway.analyze_image.return_value = make_vision_result(json.dumps(flagged))
        response = await analyzer.analyze(b"png", target="amc")
        assert response.regression_detected is True

    @pytest.mark.asyncio
    async def test_targets_are_independent(self, analyzer, gateway):
        await analyzer.analyze(b"png", target="amc")  # baseline 95
        other = json.loads(GOOD_CONTENT)
        other["overall_score"] = 40
        gateway.analyze_image.return_value = make_vision_result(json.dumps(other))
        response = await analyzer.analyze(b"png", target="landing")
        assert response.regression_detected is False  # no baseline for landing


class TestTrendReport:
    @pytest.mark.asyncio
    async def test_trend_report_empty(self, store):
        points, alerts = build_trend_report(store, "amc")
        assert points == []
        assert alerts == []

    @pytest.mark.asyncio
    async def test_trend_report_points(self, analyzer, store, gateway):
        await analyzer.analyze(b"png", target="amc")
        scores = [90, 85, 60]
        for score in scores:
            content = json.loads(GOOD_CONTENT)
            content["overall_score"] = score
            gateway.analyze_image.return_value = make_vision_result(json.dumps(content))
            await analyzer.analyze(b"png", target="amc")

        points, alerts = build_trend_report(store, "amc")
        assert len(points) >= 4
        assert points[0].score in scores + [95]

    @pytest.mark.asyncio
    async def test_trend_alert_on_degradation(self, analyzer, store, gateway):
        await analyzer.analyze(b"png", target="amc")  # 95
        for score in (94, 93, 70):  # last one drops 23 points
            content = json.loads(GOOD_CONTENT)
            content["overall_score"] = score
            gateway.analyze_image.return_value = make_vision_result(json.dumps(content))
            await analyzer.analyze(b"png", target="amc")

        points, alerts = build_trend_report(store, "amc")
        degradation = [a for a in alerts if a.type == "degradation"]
        assert degradation
        assert degradation[0].current_score == 70
        assert degradation[0].previous_score == 93

    @pytest.mark.asyncio
    async def test_no_alert_on_stable_scores(self, analyzer, store, gateway):
        for score in (95, 94, 93, 92):
            content = json.loads(GOOD_CONTENT)
            content["overall_score"] = score
            gateway.analyze_image.return_value = make_vision_result(json.dumps(content))
            await analyzer.analyze(b"png", target="amc")

        points, alerts = build_trend_report(store, "amc")
        assert alerts == []
