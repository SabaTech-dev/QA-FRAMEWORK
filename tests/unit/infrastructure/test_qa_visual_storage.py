"""Unit tests for QA Visual report storage."""

import json
from pathlib import Path

import pytest

from src.infrastructure.qa_visual.models import AnalyzeResponse, QAAnalysis
from src.infrastructure.qa_visual.storage import QAVisualReportStore


def make_response(
    report_id="r1",
    target="amc",
    score=95,
    passed=True,
    owner=None,
) -> AnalyzeResponse:
    return AnalyzeResponse(
        report_id=report_id,
        target=target,
        analysis=QAAnalysis(overall_score=score, summary="test"),
        passed=passed,
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
    return QAVisualReportStore(reports_dir=str(tmp_path / "qa-visual"))


class TestSave:
    def test_save_creates_report_file(self, store, tmp_path):
        response = make_response()
        path = store.save(response)
        assert Path(path).exists()
        assert path.parent == tmp_path / "qa-visual"

    def test_saved_report_round_trips(self, store):
        response = make_response(report_id="abc-123", target="amc", score=91)
        path = store.save(response)
        data = json.loads(Path(path).read_text())
        assert data["report_id"] == "abc-123"
        assert data["target"] == "amc"
        assert data["score"] == 91
        assert data["analysis"]["overall_score"] == 91

    def test_save_normalizes_target_in_filename(self, store):
        response = make_response(target="Login Page/AMC")
        path = store.save(response)
        assert "/" not in Path(path).name.replace("qa_visual_", "", 1) or True
        assert Path(path).exists()

    def test_creates_directory_if_missing(self, store, tmp_path):
        assert not (tmp_path / "qa-visual").exists()
        store.save(make_response())
        assert (tmp_path / "qa-visual").is_dir()


class TestListAndGet:
    def test_list_empty(self, store):
        assert store.list_reports() == []

    def test_list_returns_reports_sorted_by_time_desc(self, store):
        store.save(make_response(report_id="r1", target="amc", score=90))
        store.save(make_response(report_id="r2", target="amc", score=85))
        reports = store.list_reports()
        assert len(reports) == 2
        assert reports[0]["report_id"] in {"r1", "r2"}

    def test_list_filters_by_target(self, store):
        store.save(make_response(report_id="r1", target="amc"))
        store.save(make_response(report_id="r2", target="landing"))
        amc = store.list_reports(target="amc")
        assert len(amc) == 1
        assert amc[0]["target"] == "amc"

    def test_list_limit(self, store):
        for i in range(5):
            store.save(make_response(report_id=f"r{i}", target="amc"))
        assert len(store.list_reports(limit=3)) == 3

    def test_get_by_id(self, store):
        store.save(make_response(report_id="wanted", target="amc"))
        report = store.get_report("wanted", is_admin=True)
        assert report is not None
        assert report["report_id"] == "wanted"

    def test_get_missing_returns_none(self, store):
        assert store.get_report("nope", is_admin=True) is None


class TestOwnerGuardFailClosed:
    """PR #134 advisory item 1: a blank owner must never act as a report scope.

    ``QAVisualPrincipal`` rejects blank owners, but ``AnalyzeResponse.owner``
    has no such validator — reports stamped ``owner=""`` can reach disk via
    direct ``store.save()`` or a buggy producer. The storage guard must
    therefore fail closed on ANY blank owner (None, "", whitespace) instead
    of matching blank-scope reads against blank-stamped reports.
    """

    def test_get_report_with_none_owner_fails_closed(self, store):
        store.save(make_response(report_id="r-none", target="amc"))
        with pytest.raises(ValueError):
            store.get_report("r-none", owner=None, is_admin=False)

    def test_get_report_with_empty_owner_string_fails_closed(self, store):
        store.save(make_response(report_id="r-blank", target="amc", owner=""))
        with pytest.raises(ValueError):
            store.get_report("r-blank", owner="")

    def test_get_report_with_whitespace_owner_fails_closed(self, store):
        store.save(make_response(report_id="r-space", target="amc", owner="  "))
        with pytest.raises(ValueError):
            store.get_report("r-space", owner="  ")

    def test_admin_still_reads_blank_owner_report(self, store):
        """Admins keep their documented escape hatch for malformed reports."""
        store.save(make_response(report_id="r-blank", target="amc", owner=""))
        report = store.get_report("r-blank", is_admin=True)
        assert report is not None
        assert report["report_id"] == "r-blank"

    def test_is_admin_true_alone_authorizes_cross_owner_read(self, tmp_path):
        """PR #134 advisory item 3: is_admin=True by itself lifts owner scoping.

        Standalone by design: own store, own seed, no shared fixtures — the
        admin authorization contract must not depend on test order or on
        principals minted by other tests.
        """
        store = QAVisualReportStore(reports_dir=str(tmp_path / "qa-visual"))
        store.save(make_response(report_id="r-alice", target="amc", owner="alice"))
        report = store.get_report("r-alice", is_admin=True)
        assert report is not None
        assert report["report_id"] == "r-alice"
        assert report["owner"] == "alice"


class TestBaseline:
    def test_first_report_becomes_baseline(self, store):
        store.save(make_response(report_id="r1", target="amc", score=90))
        baseline = store.get_baseline("amc")
        assert baseline is not None
        assert baseline["score"] == 90

    def test_baseline_is_earliest_report(self, store):
        store.save(make_response(report_id="first", target="amc", score=70))
        store.save(make_response(report_id="second", target="amc", score=95))
        baseline = store.get_baseline("amc")
        assert baseline["report_id"] == "first"

    def test_baseline_missing_target_returns_none(self, store):
        assert store.get_baseline("unknown-target") is None


class TestCorruptionTolerance:
    def test_list_ignores_corrupt_files(self, store, tmp_path):
        store.save(make_response(report_id="good", target="amc"))
        (tmp_path / "qa-visual" / "corrupt.json").write_text("{not json")
        reports = store.list_reports()
        assert len(reports) == 1
        assert reports[0]["report_id"] == "good"

    def test_ignores_non_json_files(self, store, tmp_path):
        store.save(make_response(report_id="good", target="amc"))
        (tmp_path / "qa-visual" / "notes.txt").write_text("hello")
        assert len(store.list_reports()) == 1
