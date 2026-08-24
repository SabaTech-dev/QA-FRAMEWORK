"""Fail-closed storage access tests for the QA Visual module (adv-1, JWT edge b).

Security finding adv-1: ``QAVisualReportStore.get_report`` took only a
report id, so authorization lived solely in the endpoint layer — any new
caller (task, script, future endpoint) could read any tenant's report
(BOLA). The store now requires the caller's identity up front:

- a bare ``get_report(report_id)`` call raises ``ValueError`` (no open
  default: state who is asking or pass ``is_admin=True``)
- an owner-scoped read only returns the owner's own reports
- a report that exists but belongs to someone else raises
  ``ReportAccessDenied`` so routers can answer 403 without leaking
  existence through a second lookup
- ``is_admin=True`` lifts the scoping explicitly

JWT edge (b): ``QAVisualPrincipal(owner="")`` must never become a report
scope — the model rejects an empty owner and the router answers 4xx for
principals that bypass model validation.
"""

from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from src.infrastructure.qa_visual.config import QAVisualConfig
from src.infrastructure.qa_visual.endpoint import create_qa_visual_router
from src.infrastructure.qa_visual.models import AnalyzeResponse, QAAnalysis, QAVisualPrincipal
from src.infrastructure.qa_visual.storage import QAVisualReportStore

PNG_BYTES = b"\x89PNG\r\n\x1a\nfakepngdata"


def make_response(report_id: str, owner: str | None, score: int = 95) -> AnalyzeResponse:
    return AnalyzeResponse(
        report_id=report_id,
        target="amc",
        analysis=QAAnalysis(overall_score=score, summary="seeded"),
        passed=True,
        score=score,
        threshold=80,
        cost_usd=0.000428,
        latency_s=4.37,
        model="deepseek-v4-flash-vision-exp",
        regression_detected=False,
        owner=owner,
    )


@pytest.fixture
def store(tmp_path: Path) -> QAVisualReportStore:
    store = QAVisualReportStore(reports_dir=str(tmp_path / "qa-visual"))
    store.save(make_response("rep-alice", owner="alice"))
    store.save(make_response("rep-bob", owner="bob"))
    store.save(make_response("rep-legacy", owner=None))
    return store


class TestGetReportFailClosed:
    """adv-1: the store itself enforces who may read a report."""

    def test_bare_call_raises_value_error(self, store):
        with pytest.raises(ValueError, match="owner"):
            store.get_report("rep-alice")

    def test_unscoped_call_without_admin_raises_value_error(self, store):
        with pytest.raises(ValueError, match="is_admin"):
            store.get_report("rep-alice", owner=None, is_admin=False)

    def test_owner_reads_own_report(self, store):
        report = store.get_report("rep-alice", owner="alice")
        assert report is not None
        assert report["report_id"] == "rep-alice"

    def test_owner_cannot_read_others_report(self, store):
        from src.infrastructure.qa_visual.storage import ReportAccessDenied

        with pytest.raises(ReportAccessDenied):
            store.get_report("rep-alice", owner="bob")

    def test_legacy_report_denied_for_regular_owner(self, store):
        from src.infrastructure.qa_visual.storage import ReportAccessDenied

        with pytest.raises(ReportAccessDenied):
            store.get_report("rep-legacy", owner="alice")

    def test_admin_reads_any_report(self, store):
        report = store.get_report("rep-bob", is_admin=True)
        assert report is not None
        assert report["owner"] == "bob"

    def test_admin_with_owner_scope_still_reads_any_report(self, store):
        report = store.get_report("rep-bob", owner="root", is_admin=True)
        assert report is not None

    def test_missing_report_returns_none_for_owner(self, store):
        assert store.get_report("missing", owner="alice") is None

    def test_missing_report_returns_none_for_admin(self, store):
        assert store.get_report("missing", is_admin=True) is None

    def test_bola_guard_still_rejects_after_reseed(self, store, tmp_path):
        """A second save/lookup round trip keeps the owner scoping."""
        store.save(make_response("rep-carol", owner="carol"))
        from src.infrastructure.qa_visual.storage import ReportAccessDenied

        with pytest.raises(ReportAccessDenied):
            store.get_report("rep-carol", owner="alice")


class TestPrincipalOwnerValidation:
    """JWT edge (b): an empty owner identity is invalid at the model."""

    def test_empty_owner_rejected_by_model(self):
        with pytest.raises(ValidationError):
            QAVisualPrincipal(owner="")

    def test_whitespace_owner_rejected_by_model(self):
        with pytest.raises(ValidationError):
            QAVisualPrincipal(owner="   ")

    def test_valid_owner_accepted_by_model(self):
        assert QAVisualPrincipal(owner="alice").owner == "alice"


class TestRouterEmptyOwnerGuard:
    """JWT edge (b): principals bypassing model validation get 4xx."""

    @pytest.fixture
    def client(self, store):
        principal_holder = {"principal": None}

        def get_principal():
            return principal_holder["principal"]

        app = FastAPI()
        app.include_router(
            create_qa_visual_router(
                analyzer=_store_only_analyzer(store), get_current_principal=get_principal
            )
        )
        app.state.principal_holder = principal_holder
        return TestClient(app)

    def test_empty_owner_principal_gets_4xx_on_reports(self, client, store):
        client.app.state.principal_holder["principal"] = QAVisualPrincipal.model_construct(owner="")
        response = client.get("/api/v1/qa-visual/reports")
        assert 400 <= response.status_code < 500

    def test_empty_owner_principal_gets_4xx_on_single_report(self, client, store):
        client.app.state.principal_holder["principal"] = QAVisualPrincipal.model_construct(owner="")
        response = client.get("/api/v1/qa-visual/reports/rep-alice")
        assert 400 <= response.status_code < 500

    def test_empty_owner_principal_gets_4xx_on_analyze(self, client, store):
        client.app.state.principal_holder["principal"] = QAVisualPrincipal.model_construct(owner="")
        response = client.post(
            "/api/v1/qa-visual/analyze",
            files={"screenshot": ("page.png", PNG_BYTES, "image/png")},
            data={"target": "amc"},
        )
        assert 400 <= response.status_code < 500

    def test_empty_owner_admin_bypasses_guard_on_reads(self, client, store):
        """An admin principal does not need a usable owner for reads."""
        client.app.state.principal_holder["principal"] = QAVisualPrincipal.model_construct(
            owner="", is_admin=True
        )
        response = client.get("/api/v1/qa-visual/reports")
        assert response.status_code == 200


def _store_only_analyzer(store: QAVisualReportStore):
    """Analyzer stub whose only job is serving the seeded store."""
    from src.infrastructure.qa_visual.analyzer import QAVisualAnalyzer

    analyzer = QAVisualAnalyzer.__new__(QAVisualAnalyzer)
    analyzer._config = QAVisualConfig()
    analyzer._store = store
    return analyzer
