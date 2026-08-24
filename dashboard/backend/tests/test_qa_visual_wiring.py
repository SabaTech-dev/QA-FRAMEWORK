"""Wiring tests for the QA Visual router in the dashboard (Fase C — card 0ddedd75).

S-1/S-1R: dashboard/backend/main.py mounts the vendored qa_visual router —
gated behind QA_VISUAL_ENABLED=1 — with ``dependencies=[Depends(get_current_user)]``.
Every endpoint must reject unauthenticated requests on the REAL app.
Without credentials the response is 401 or 403 depending on the stack's
HTTPBearer handling (this one answers 401 "Not authenticated"); with a
malformed bearer token get_current_user answers 401.

The flag must be set BEFORE main is imported because the app (and the
conditional router mount) is built at import time; the fixture reloads
main under the flag so ordering vs. test_qa_visual_feature_flag.py is
irrelevant.

A hand-built app with an injected fake analyzer proves the authenticated
happy path, so no paid gateway call or real report dir is touched.
"""

import importlib
import io
from unittest.mock import AsyncMock

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from src.infrastructure.qa_visual import (
    QAVisualAnalyzer,
    create_qa_visual_router,
)
from src.infrastructure.qa_visual.config import QAVisualConfig
from src.infrastructure.qa_visual.models import AnalyzeResponse, QAAnalysis
from src.infrastructure.qa_visual.storage import QAVisualReportStore

PNG_BYTES = b"\x89PNG\r\n\x1a\nfakepngdata"

GET_PATHS = [
    "/api/v1/qa-visual/reports",
    "/api/v1/qa-visual/reports/rep-001",
    "/api/v1/qa-visual/trends",
    "/api/v1/qa-visual/baselines/amc",
]


@pytest.fixture(scope="module")
def main_app():
    # S-1R: build the app with the router actually mounted.
    mp = pytest.MonkeyPatch()
    mp.setenv("QA_VISUAL_ENABLED", "1")
    import main as dashboard_main

    app = importlib.reload(dashboard_main).app
    yield app
    mp.undo()


@pytest.fixture(scope="module")
def main_client(main_app):
    return TestClient(main_app)


class TestMainAppAuthEnforcement:
    """The real dashboard app must enforce auth on all five endpoints."""

    def test_no_credentials_rejected_all_get_endpoints(self, main_client):
        for path in GET_PATHS:
            assert main_client.get(path).status_code in (401, 403), path

    def test_no_credentials_rejected_analyze(self, main_client):
        response = main_client.post(
            "/api/v1/qa-visual/analyze",
            files={"screenshot": ("page.png", PNG_BYTES, "image/png")},
            data={"target": "amc"},
        )
        assert response.status_code in (401, 403)

    def test_malformed_token_401_all_endpoints(self, main_client):
        headers = {"Authorization": "Bearer not.a.jwt"}
        for path in GET_PATHS:
            response = main_client.get(path, headers=headers)
            assert response.status_code == 401, path
        response = main_client.post(
            "/api/v1/qa-visual/analyze",
            files={"screenshot": ("page.png", PNG_BYTES, "image/png")},
            data={"target": "amc"},
            headers=headers,
        )
        assert response.status_code == 401


class TestAuthenticatedHappyPath:
    """With auth bypassed and a fake analyzer, the mounted router serves."""

    @pytest.fixture()
    def authed_client(self, tmp_path):
        store = QAVisualReportStore(reports_dir=str(tmp_path / "qa-visual"))
        sample = AnalyzeResponse(
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
        store.save(sample)
        analyzer = QAVisualAnalyzer.__new__(QAVisualAnalyzer)
        analyzer._config = QAVisualConfig()
        analyzer._store = store
        analyzer.analyze = AsyncMock(return_value=sample)

        app = FastAPI()
        app.include_router(
            create_qa_visual_router(analyzer=analyzer, dependencies=[Depends(lambda: "fake-user")])
        )
        return TestClient(app)

    def test_authed_reports_list(self, authed_client):
        response = authed_client.get("/api/v1/qa-visual/reports")
        assert response.status_code == 200
        assert response.json()[0]["report_id"] == "rep-001"

    def test_authed_report_by_id(self, authed_client):
        response = authed_client.get("/api/v1/qa-visual/reports/rep-001")
        assert response.status_code == 200
        assert response.json()["report_id"] == "rep-001"

    def test_authed_report_by_id_not_found(self, authed_client):
        assert authed_client.get("/api/v1/qa-visual/reports/missing").status_code == 404

    def test_authed_trends(self, authed_client):
        response = authed_client.get("/api/v1/qa-visual/trends")
        assert response.status_code == 200
        body = response.json()
        assert body["points"][0]["target"] == "amc"

    def test_authed_baseline(self, authed_client):
        response = authed_client.get("/api/v1/qa-visual/baselines/amc")
        assert response.status_code == 200
        assert response.json()["target"] == "amc"

    def test_authed_baseline_not_found(self, authed_client):
        assert authed_client.get("/api/v1/qa-visual/baselines/nope").status_code == 404

    def test_authed_analyze_reaches_analyzer(self, authed_client):
        response = authed_client.post(
            "/api/v1/qa-visual/analyze",
            files={"screenshot": ("page.png", io.BytesIO(PNG_BYTES), "image/png")},
            data={"target": "amc"},
        )
        assert response.status_code == 200
        assert response.json()["report_id"] == "rep-001"
