"""Owner-scoping tests for the QA Visual module (S-1R — card 9b67f430).

Security finding S-1R: the report store was global, so any authenticated
user could read, trend-analyse and baseline-compare reports belonging to
other users — a cross-tenant BOLA (CVSS 5.4). The router factory now
accepts a ``get_current_principal`` dependency returning a
``QAVisualPrincipal`` (``owner`` + ``is_admin``), and every endpoint
enforces:

- ``analyze`` stamps the calling principal as the report owner
- reports / trends / baselines are scoped to the owner
- admins bypass the scoping (see everything)
- an authenticated non-owner reading someone else's report gets 403
- reports persisted before owner-scoping (``owner`` absent) are
  admin-only: regular users never see them

Without ``get_current_principal`` the router keeps its legacy
unscoped behaviour for standalone mounts (backward compatibility).
"""

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.infrastructure.qa_visual.analyzer import QAVisualAnalyzer
from src.infrastructure.qa_visual.config import QAVisualConfig
from src.infrastructure.qa_visual.endpoint import create_qa_visual_router
from src.infrastructure.qa_visual.gateway_client import VisionResult
from src.infrastructure.qa_visual.models import (
    AnalyzeResponse,
    QAAnalysis,
    QAVisualPrincipal,
)
from src.infrastructure.qa_visual.storage import QAVisualReportStore

PNG_BYTES = b"\x89PNG\r\n\x1a\nfakepngdata"

ALICE = QAVisualPrincipal(owner="alice")
BOB = QAVisualPrincipal(owner="bob")
ADMIN = QAVisualPrincipal(owner="root", is_admin=True)


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
        timestamp=datetime(2026, 8, 24, 12, 0, 0, tzinfo=timezone.utc),
    )
    fields.update(overrides)
    return AnalyzeResponse(**fields)


@pytest.fixture
def store(tmp_path: Path) -> QAVisualReportStore:
    store = QAVisualReportStore(reports_dir=str(tmp_path / "qa-visual"))
    store.save(make_response(owner="alice"))
    store.save(
        make_response(
            report_id="rep-002",
            target="landing",
            score=60,
            passed=False,
            owner="bob",
        )
    )
    # Report persisted before owner-scoping existed.
    store.save(
        make_response(
            report_id="rep-legacy",
            target="amc",
            owner=None,
            timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
    )
    return store


class TestStorageOwnerScoping:
    def test_list_reports_filters_by_owner(self, store):
        reports = store.list_reports(owner="alice")
        assert [r["report_id"] for r in reports] == ["rep-001"]

    def test_list_reports_without_owner_returns_all(self, store):
        assert len(store.list_reports()) == 3

    def test_list_reports_excludes_legacy_reports_for_owner(self, store):
        ids = [r["report_id"] for r in store.list_reports(owner="bob")]
        assert ids == ["rep-002"]

    def test_get_baseline_scoped_by_owner(self, store):
        store.save(
            make_response(
                report_id="rep-alice-early",
                target="amc",
                owner="alice",
                timestamp=datetime(2026, 1, 2, tzinfo=timezone.utc),
            )
        )
        baseline = store.get_baseline("amc", owner="alice")
        assert baseline["report_id"] == "rep-alice-early"

    def test_get_baseline_without_owner_returns_earliest_overall(self, store):
        baseline = store.get_baseline("amc")
        assert baseline["report_id"] == "rep-legacy"


def gateway_result(score: int) -> VisionResult:
    content = '{"overall_score": %d, "summary": "generated"}' % score
    return VisionResult(
        content=content,
        latency_s=4.0,
        usage={"prompt_tokens": 1000, "completion_tokens": 500},
        cost_usd=0.0004,
        model_reported="deepseek-v4-flash-vision-exp",
        finish_reason="stop",
    )


def real_analyzer(store: QAVisualReportStore, score: int) -> QAVisualAnalyzer:
    analyzer = QAVisualAnalyzer.__new__(QAVisualAnalyzer)
    analyzer._config = QAVisualConfig()
    analyzer._store = store
    analyzer._gateway = AsyncMock()
    analyzer._gateway.analyze_image = AsyncMock(return_value=gateway_result(score))
    return analyzer


class TestAnalyzerOwnerStamping:
    @pytest.mark.asyncio
    async def test_analyze_stamps_owner_on_report(self, tmp_path):
        store = QAVisualReportStore(reports_dir=str(tmp_path / "qa-visual"))
        analyzer = real_analyzer(store, score=95)

        response = await analyzer.analyze(PNG_BYTES, target="amc", owner="alice")

        assert response.owner == "alice"
        persisted = store.get_report(response.report_id)
        assert persisted["owner"] == "alice"

    @pytest.mark.asyncio
    async def test_analyze_without_owner_keeps_report_unowned(self, tmp_path):
        store = QAVisualReportStore(reports_dir=str(tmp_path / "qa-visual"))
        analyzer = real_analyzer(store, score=95)

        response = await analyzer.analyze(PNG_BYTES, target="amc")

        assert response.owner is None

    @pytest.mark.asyncio
    async def test_regression_ignores_other_owners_baseline(self, tmp_path):
        """bob's high-score baseline must not flag alice's low run.

        Without owner scoping alice's score-60 run would compare against
        bob's score-95 baseline and be marked as a regression, leaking
        bob's data into alice's result.
        """
        store = QAVisualReportStore(reports_dir=str(tmp_path / "qa-visual"))
        store.save(make_response(report_id="rep-bob-base", target="amc", owner="bob"))
        analyzer = real_analyzer(store, score=60)

        response = await analyzer.analyze(PNG_BYTES, target="amc", owner="alice")

        assert response.score == 60
        assert response.regression_detected is False

    @pytest.mark.asyncio
    async def test_regression_uses_own_owners_baseline(self, tmp_path):
        store = QAVisualReportStore(reports_dir=str(tmp_path / "qa-visual"))
        store.save(make_response(report_id="rep-alice-base", target="amc", owner="alice"))
        analyzer = real_analyzer(store, score=60)

        response = await analyzer.analyze(PNG_BYTES, target="amc", owner="alice")

        assert response.regression_detected is True


class EndpointBuilder:
    """Hand-built app with a switchable principal (no real auth service)."""

    def __init__(self, analyzer):
        self.holder = {"principal": None}
        self.analyzer = analyzer

    def client(self, principal: QAVisualPrincipal) -> TestClient:
        self.holder["principal"] = principal

        def get_principal():
            return self.holder["principal"]

        app = FastAPI()
        app.include_router(
            create_qa_visual_router(
                analyzer=self.analyzer,
                get_current_principal=get_principal,
            )
        )
        return TestClient(app)


@pytest.fixture
def endpoint(store):
    # analyze is mocked so POST /analyze never writes to the store;
    # the GET endpoints use the real store seeded by the fixture.
    analyzer = QAVisualAnalyzer.__new__(QAVisualAnalyzer)
    analyzer._config = QAVisualConfig()
    analyzer._store = store
    analyzer.analyze = AsyncMock(return_value=make_response(owner="alice"))
    return EndpointBuilder(analyzer)


class TestEndpointOwnerEnforcement:
    def test_analyze_passes_owner_to_analyzer(self, endpoint):
        client = endpoint.client(ALICE)
        response = client.post(
            "/api/v1/qa-visual/analyze",
            files={"screenshot": ("page.png", PNG_BYTES, "image/png")},
            data={"target": "amc"},
        )
        assert response.status_code == 200
        kwargs = endpoint.analyzer.analyze.call_args.kwargs
        # The endpoint forwards the principal owner so the analyzer can
        # stamp it before persisting.
        assert kwargs.get("owner") == "alice"

    def test_owner_reads_own_report_200(self, endpoint):
        assert endpoint.client(ALICE).get("/api/v1/qa-visual/reports/rep-001").status_code == 200

    def test_non_owner_gets_403(self, endpoint):
        assert endpoint.client(BOB).get("/api/v1/qa-visual/reports/rep-001").status_code == 403

    def test_admin_reads_others_report_200(self, endpoint):
        assert endpoint.client(ADMIN).get("/api/v1/qa-visual/reports/rep-001").status_code == 200

    def test_missing_report_404_for_owner(self, endpoint):
        assert endpoint.client(ALICE).get("/api/v1/qa-visual/reports/missing").status_code == 404

    def test_legacy_report_403_for_regular_user(self, endpoint):
        assert endpoint.client(ALICE).get("/api/v1/qa-visual/reports/rep-legacy").status_code == 403

    def test_legacy_report_200_for_admin(self, endpoint):
        assert endpoint.client(ADMIN).get("/api/v1/qa-visual/reports/rep-legacy").status_code == 200

    def test_reports_listing_scoped_to_owner(self, endpoint):
        body = endpoint.client(ALICE).get("/api/v1/qa-visual/reports").json()
        assert [r["report_id"] for r in body] == ["rep-001"]

    def test_reports_listing_admin_sees_all(self, endpoint):
        body = endpoint.client(ADMIN).get("/api/v1/qa-visual/reports").json()
        assert len(body) == 3

    def test_trends_scoped_to_owner(self, endpoint):
        body = endpoint.client(BOB).get("/api/v1/qa-visual/trends").json()
        targets = {p["target"] for p in body["points"]}
        assert targets == {"landing"}

    def test_baseline_404_for_non_owner(self, endpoint):
        assert endpoint.client(BOB).get("/api/v1/qa-visual/baselines/amc").status_code == 404

    def test_baseline_200_for_owner(self, endpoint):
        assert endpoint.client(ALICE).get("/api/v1/qa-visual/baselines/amc").status_code == 200

    def test_baseline_200_for_admin(self, endpoint):
        assert endpoint.client(ADMIN).get("/api/v1/qa-visual/baselines/amc").status_code == 200


class TestBackwardCompatibility:
    def test_router_without_principal_keeps_legacy_behaviour(self, tmp_path):
        store = QAVisualReportStore(reports_dir=str(tmp_path / "qa-visual"))
        store.save(make_response())
        analyzer = real_analyzer(store, score=95)

        app = FastAPI()
        app.include_router(create_qa_visual_router(analyzer=analyzer))
        client = TestClient(app)

        assert client.get("/api/v1/qa-visual/reports").status_code == 200
        assert len(client.get("/api/v1/qa-visual/reports").json()) == 1
