"""Unit tests for the QA Visual API router."""

import io
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.infrastructure.qa_visual.analyzer import QAVisualAnalysisError, QAVisualAnalyzer
from src.infrastructure.qa_visual.config import QAVisualConfig
from src.infrastructure.qa_visual.endpoint import create_qa_visual_router
from src.infrastructure.qa_visual.models import AnalyzeResponse, QAAnalysis
from src.infrastructure.qa_visual.storage import QAVisualReportStore

PNG_BYTES = b"\x89PNG\r\n\x1a\nfakepngdata"


def make_response(**overrides) -> AnalyzeResponse:
    fields = dict(
        report_id="rep-001",
        target="amc",
        analysis=QAAnalysis(overall_score=95, summary="clean"),
        passed=True,
        score=95,
        threshold=80,
        cost_usd=0.000428,
        latency_s=4.37,
        model="deepseek-v4-flash-vision-exp",
        regression_detected=False,
    )
    fields.update(overrides)
    return AnalyzeResponse(**fields)


@pytest.fixture
def store(tmp_path: Path) -> QAVisualReportStore:
    store = QAVisualReportStore(reports_dir=str(tmp_path / "qa-visual"))
    store.save(make_response())
    store.save(make_response(report_id="rep-002", target="landing", score=60, passed=False))
    return store


@pytest.fixture
def analyzer(store) -> QAVisualAnalyzer:
    analyzer = QAVisualAnalyzer.__new__(QAVisualAnalyzer)
    analyzer._config = QAVisualConfig()
    analyzer._store = store
    analyzer.analyze = AsyncMock(return_value=make_response())
    return analyzer


@pytest.fixture
def client(analyzer) -> TestClient:
    app = FastAPI()
    app.include_router(create_qa_visual_router(analyzer=analyzer))
    return TestClient(app)


class TestAnalyzeEndpoint:
    def test_post_analyze_multipart(self, client, analyzer):
        analyzer.analyze.return_value = make_response(report_id="new-rep", target="amc")
        response = client.post(
            "/api/v1/qa-visual/analyze",
            files={"screenshot": ("page.png", io.BytesIO(PNG_BYTES), "image/png")},
            data={"target": "amc"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["report_id"] == "new-rep"
        assert body["target"] == "amc"
        assert body["passed"] is True
        assert body["score"] == 95
        analyzer.analyze.assert_awaited_once()

    def test_post_analyze_passes_screenshot_bytes(self, client, analyzer):
        client.post(
            "/api/v1/qa-visual/analyze",
            files={"screenshot": ("page.png", io.BytesIO(PNG_BYTES), "image/png")},
            data={"target": "amc"},
        )
        call = analyzer.analyze.call_args
        sent_bytes = call.args[0] if call.args else call.kwargs.get("image_bytes")
        sent_target = call.args[1] if len(call.args) > 1 else call.kwargs.get("target")
        assert sent_bytes == PNG_BYTES
        assert sent_target == "amc"

    def test_post_analyze_requires_screenshot(self, client):
        response = client.post("/api/v1/qa-visual/analyze", data={"target": "amc"})
        assert response.status_code == 422

    def test_post_analyze_empty_screenshot_rejected(self, client):
        response = client.post(
            "/api/v1/qa-visual/analyze",
            files={"screenshot": ("page.png", io.BytesIO(b""), "image/png")},
            data={"target": "amc"},
        )
        assert response.status_code == 422

    def test_post_analyze_oversized_screenshot_rejected(self, client):
        from src.infrastructure.qa_visual.endpoint import MAX_SCREENSHOT_BYTES

        huge = b"x" * (MAX_SCREENSHOT_BYTES + 1)
        response = client.post(
            "/api/v1/qa-visual/analyze",
            files={"screenshot": ("page.png", io.BytesIO(huge), "image/png")},
            data={"target": "amc"},
        )
        assert response.status_code == 413

    def test_post_analyze_content_length_precheck_rejects_early(self, client):
        """S-2a: Content-Length far above the cap is rejected before reading."""
        from src.infrastructure.qa_visual.endpoint import MAX_SCREENSHOT_BYTES

        huge = b"x" * (MAX_SCREENSHOT_BYTES + 2 * 1024 * 1024)
        response = client.post(
            "/api/v1/qa-visual/analyze",
            files={"screenshot": ("page.png", io.BytesIO(huge), "image/png")},
            data={"target": "amc"},
        )
        assert response.status_code == 413
        assert "exceeds" in response.json()["detail"].lower()

    def test_post_analyze_rejects_non_png_content_type(self, client, analyzer):
        """S-2c: uploads that are not image/png get 415, no paid API call."""
        response = client.post(
            "/api/v1/qa-visual/analyze",
            files={"screenshot": ("page.jpg", io.BytesIO(PNG_BYTES), "image/jpeg")},
            data={"target": "amc"},
        )
        assert response.status_code == 415
        analyzer.analyze.assert_not_awaited()

    def test_post_analyze_rejects_non_png_magic_bytes(self, client, analyzer):
        """S-2c: image/png content-type but no PNG signature is rejected."""
        response = client.post(
            "/api/v1/qa-visual/analyze",
            files={"screenshot": ("page.png", io.BytesIO(b"JFIFnotapng"), "image/png")},
            data={"target": "amc"},
        )
        assert response.status_code == 415
        analyzer.analyze.assert_not_awaited()

    def test_post_analyze_target_too_long_rejected(self, client):
        """S-5: target longer than 255 chars is rejected (422), no 500."""
        response = client.post(
            "/api/v1/qa-visual/analyze",
            files={"screenshot": ("page.png", io.BytesIO(PNG_BYTES), "image/png")},
            data={"target": "x" * 256},
        )
        assert response.status_code == 422

    def test_post_analyze_requires_target(self, client):
        response = client.post(
            "/api/v1/qa-visual/analyze",
            files={"screenshot": ("page.png", io.BytesIO(PNG_BYTES), "image/png")},
        )
        assert response.status_code == 422

    def test_post_analyze_analysis_error_returns_generic_502(self, client, analyzer):
        """S-3: upstream gateway detail must NOT reach the HTTP client."""
        analyzer.analyze.side_effect = QAVisualAnalysisError(
            "Vision gateway failed: Gateway HTTP 503: down"
        )
        response = client.post(
            "/api/v1/qa-visual/analyze",
            files={"screenshot": ("page.png", io.BytesIO(PNG_BYTES), "image/png")},
            data={"target": "amc"},
        )
        assert response.status_code == 502
        detail = response.json()["detail"]
        assert "503" not in detail
        assert "down" not in detail

    def test_post_analyze_parse_error_does_not_leak_raw_output(self, client, analyzer):
        """S-3: raw model output excerpt must NOT reach the HTTP client."""
        analyzer.analyze.side_effect = QAVisualAnalysisError(
            "Model output could not be parsed into the QA contract",
            raw_content="garbage output",
        )
        response = client.post(
            "/api/v1/qa-visual/analyze",
            files={"screenshot": ("page.png", io.BytesIO(PNG_BYTES), "image/png")},
            data={"target": "amc"},
        )
        assert response.status_code == 502
        assert "garbage" not in response.json()["detail"]

    def test_post_analyze_error_detail_logged_server_side(self, client, analyzer, caplog):
        """S-3: full detail goes to server logs, not to the client."""
        analyzer.analyze.side_effect = QAVisualAnalysisError(
            "Vision gateway failed: Gateway HTTP 503: down",
            raw_content="secret model output",
        )
        with caplog.at_level("ERROR", logger="src.infrastructure.qa_visual.endpoint"):
            client.post(
                "/api/v1/qa-visual/analyze",
                files={"screenshot": ("page.png", io.BytesIO(PNG_BYTES), "image/png")},
                data={"target": "amc"},
            )
        assert any("503" in r.message for r in caplog.records)
        assert any("secret model output" in r.message for r in caplog.records)


class TestReportsEndpoints:
    def test_get_reports_lists_all(self, client):
        response = client.get("/api/v1/qa-visual/reports")
        assert response.status_code == 200
        reports = response.json()
        assert len(reports) == 2

    def test_get_reports_filter_by_target(self, client):
        response = client.get("/api/v1/qa-visual/reports", params={"target": "landing"})
        assert response.status_code == 200
        reports = response.json()
        assert len(reports) == 1
        assert reports[0]["target"] == "landing"

    def test_get_reports_limit(self, client):
        response = client.get("/api/v1/qa-visual/reports", params={"limit": 1})
        assert response.status_code == 200
        assert len(response.json()) == 1

    def test_get_report_by_id(self, client):
        response = client.get("/api/v1/qa-visual/reports/rep-001")
        assert response.status_code == 200
        assert response.json()["report_id"] == "rep-001"

    def test_get_report_not_found(self, client):
        response = client.get("/api/v1/qa-visual/reports/missing")
        assert response.status_code == 404


class TestTrendsEndpoint:
    def test_get_trends(self, client):
        response = client.get("/api/v1/qa-visual/trends", params={"target": "amc"})
        assert response.status_code == 200
        body = response.json()
        assert "points" in body
        assert "alerts" in body
        assert len(body["points"]) == 1
        assert body["points"][0]["target"] == "amc"

    def test_get_trends_all_targets_when_no_target(self, client):
        response = client.get("/api/v1/qa-visual/trends")
        assert response.status_code == 200
        assert len(response.json()["points"]) == 2


class TestBaselinesEndpoint:
    def test_get_baseline_exists(self, client):
        response = client.get("/api/v1/qa-visual/baselines/amc")
        assert response.status_code == 200
        assert response.json()["target"] == "amc"

    def test_get_baseline_not_found(self, client):
        response = client.get("/api/v1/qa-visual/baselines/nope")
        assert response.status_code == 404


class TestRouterDependencies:
    """S-1 (Fase C): the factory must accept injectable router dependencies."""

    def _protected_client(self, analyzer):
        from fastapi import Depends, HTTPException

        def deny_all() -> None:
            raise HTTPException(status_code=401, detail="Not authenticated")

        app = FastAPI()
        app.include_router(
            create_qa_visual_router(analyzer=analyzer, dependencies=[Depends(deny_all)])
        )
        return TestClient(app)

    def test_dependencies_apply_to_all_five_endpoints(self, analyzer):
        client = self._protected_client(analyzer)
        get_paths = [
            "/api/v1/qa-visual/reports",
            "/api/v1/qa-visual/reports/rep-001",
            "/api/v1/qa-visual/trends",
            "/api/v1/qa-visual/baselines/amc",
        ]
        for path in get_paths:
            assert client.get(path).status_code == 401, path
        response = client.post(
            "/api/v1/qa-visual/analyze",
            files={"screenshot": ("page.png", io.BytesIO(PNG_BYTES), "image/png")},
            data={"target": "amc"},
        )
        assert response.status_code == 401

    def test_dependencies_run_before_analyzer(self, analyzer):
        client = self._protected_client(analyzer)
        client.post(
            "/api/v1/qa-visual/analyze",
            files={"screenshot": ("page.png", io.BytesIO(PNG_BYTES), "image/png")},
            data={"target": "amc"},
        )
        analyzer.analyze.assert_not_awaited()

    def test_no_dependencies_backward_compatible(self, analyzer):
        app = FastAPI()
        app.include_router(create_qa_visual_router(analyzer=analyzer))
        client = TestClient(app)
        assert client.get("/api/v1/qa-visual/reports").status_code == 200
