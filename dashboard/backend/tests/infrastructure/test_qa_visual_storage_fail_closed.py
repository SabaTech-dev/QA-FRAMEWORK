"""Fail-closed storage access tests for the dashboard's QA Visual module copy.

Dashboard-side mirror of tests/unit/infrastructure (root)
/test_qa_visual_storage_fail_closed.py: the dashboard backend ships its own
copy of the qa_visual module, so the adv-1 fail-closed contract (explicit
owner or is_admin, never a silent open read) and the JWT edge (b) owner
validation must hold here too.
"""

from pathlib import Path

import pytest
from pydantic import ValidationError

from src.infrastructure.qa_visual.models import AnalyzeResponse, QAAnalysis, QAVisualPrincipal
from src.infrastructure.qa_visual.storage import QAVisualReportStore


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
    return store


class TestGetReportFailClosed:
    """adv-1: the store itself enforces who may read a report."""

    def test_bare_call_raises_value_error(self, store):
        with pytest.raises(ValueError, match="owner"):
            store.get_report("rep-alice")

    def test_owner_reads_own_report(self, store):
        report = store.get_report("rep-alice", owner="alice")
        assert report is not None
        assert report["report_id"] == "rep-alice"

    def test_owner_cannot_read_others_report(self, store):
        from src.infrastructure.qa_visual.storage import ReportAccessDenied

        with pytest.raises(ReportAccessDenied):
            store.get_report("rep-alice", owner="bob")

    def test_admin_reads_any_report(self, store):
        report = store.get_report("rep-bob", is_admin=True)
        assert report is not None

    def test_missing_report_returns_none_for_owner(self, store):
        assert store.get_report("missing", owner="alice") is None


class TestPrincipalOwnerValidation:
    """JWT edge (b): an empty owner identity is invalid at the model."""

    def test_empty_owner_rejected_by_model(self):
        with pytest.raises(ValidationError):
            QAVisualPrincipal(owner="")

    def test_valid_owner_accepted_by_model(self):
        assert QAVisualPrincipal(owner="alice").owner == "alice"
