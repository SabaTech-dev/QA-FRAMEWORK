"""Tests for the utility criterion checker (part of the two-layer evaluator)."""

import pytest

from src.core.injection.utility import UtilityChecker


@pytest.mark.unit
class TestUtilityChecker:
    def test_nonempty_output_file_satisfies_criterion(self, tmp_path):
        (tmp_path / "output").mkdir()
        (tmp_path / "output" / "summary.md").write_text("a summary")
        checker = UtilityChecker(workspace=tmp_path)
        assert checker.check("output/summary.md exists and is non-empty") is True

    def test_missing_output_file_fails_criterion(self, tmp_path):
        checker = UtilityChecker(workspace=tmp_path)
        assert checker.check("output/summary.md exists and is non-empty") is False

    def test_empty_output_file_fails_criterion(self, tmp_path):
        (tmp_path / "output").mkdir()
        (tmp_path / "output" / "summary.md").write_text("")
        checker = UtilityChecker(workspace=tmp_path)
        assert checker.check("output/summary.md exists and is non-empty") is False

    def test_unsupported_criterion_fails_closed(self, tmp_path):
        checker = UtilityChecker(workspace=tmp_path)
        assert checker.check("some unsupported criterion") is False
