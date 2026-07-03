"""
Tests for None input handling and input validation in compliance exporters.

Covers:
- None test_session crashes
- Empty evaluations crashes
- None system_description crashes
- None methodology crashes
- None evaluation.hallucinations crashes
- XSS/injection in system_id and provider_name
- SARIF message sanitization
"""

import pytest
from datetime import datetime, timezone

from src.domain.accuracy_testing.entities import (
    AccuracyTestSession,
    AccuracyEvaluation,
)
from src.domain.accuracy_testing.value_objects import (
    EvaluationCriterion,
    AccuracyLevel,
    EvaluationStatus,
    ResponseVerdict,
    CriterionScore,
)
from src.domain.compliance.entities import (
    SystemDescription,
    TestingMethodology,
    SARIFReport,
)
from src.infrastructure.compliance.sarif_exporter import SARIFExporter
from src.infrastructure.compliance.annex_iv_exporter import AnnexIVExporter
from src.infrastructure.compliance.sarif_sanitizer import (
    sanitize_message_text,
    sanitize_dict_strings,
)


# ========================================================================
# Fixtures
# ========================================================================

@pytest.fixture
def valid_session():
    return AccuracyTestSession(
        name="test-session",
        total_benchmarks=1,
        evaluations_completed=1,
        evaluations_passed=1,
        status=EvaluationStatus.COMPLETED,
        evaluations=[
            AccuracyEvaluation(
                benchmark_id="bench-1",
                overall_score=0.8,
                verdict=ResponseVerdict.ACCURATE,
                passed=True,
                criterion_scores=[
                    CriterionScore(
                        criterion=EvaluationCriterion.FACTUAL_ACCURACY,
                        score=0.8,
                        explanation="Good",
                    ),
                ],
            ),
        ],
    )


@pytest.fixture
def valid_system():
    return SystemDescription(
        system_id="test-system-001",
        name="Test AI",
        provider_name="SabaTech",
    )


@pytest.fixture
def valid_methodology():
    return TestingMethodology(
        methodology_name="Accuracy Testing",
        description="Standard accuracy evaluation",
    )


@pytest.fixture
def sarif_exporter():
    return SARIFExporter()


@pytest.fixture
def annex_exporter():
    return AnnexIVExporter()


# ========================================================================
# SARIF Exporter — None Guards
# ========================================================================

class TestSARIFNoneGuards:
    def test_none_session_raises(self, sarif_exporter):
        with pytest.raises(ValueError, match="test_session is required"):
            sarif_exporter.export(None)

    def test_empty_evaluations_raises(self, sarif_exporter):
        session = AccuracyTestSession(name="empty")
        with pytest.raises(ValueError, match="at least one evaluation"):
            sarif_exporter.export(session)

    def test_none_evaluations_list_raises(self, sarif_exporter):
        session = AccuracyTestSession(name="none-evals")
        session.evaluations = None
        with pytest.raises(ValueError, match="at least one evaluation"):
            sarif_exporter.export(session)

    def test_none_evaluation_in_list_skipped(self, sarif_exporter, valid_session):
        """None evaluations in list should be skipped, not crash."""
        valid_session.evaluations.append(None)
        report = sarif_exporter.export(valid_session)
        assert isinstance(report, SARIFReport)
        # Only the valid evaluation should produce results
        assert len(report.runs) == 1

    def test_none_system_description_allowed(self, sarif_exporter, valid_session):
        """None system_description is allowed (optional field)."""
        report = sarif_exporter.export(valid_session, system_description=None)
        assert isinstance(report, SARIFReport)


# ========================================================================
# Annex IV Exporter — None Guards
# ========================================================================

class TestAnnexIVNoneGuards:
    def test_none_system_description_raises(self, annex_exporter, valid_session, valid_methodology):
        with pytest.raises(ValueError, match="system_description is required"):
            annex_exporter.export(None, valid_methodology, valid_session)

    def test_none_methodology_raises(self, annex_exporter, valid_session, valid_system):
        with pytest.raises(ValueError, match="testing_methodology is required"):
            annex_exporter.export(valid_system, None, valid_session)

    def test_none_session_raises(self, annex_exporter, valid_system, valid_methodology):
        with pytest.raises(ValueError, match="test_session is required"):
            annex_exporter.export(valid_system, valid_methodology, None)

    def test_empty_evaluations_raises(self, annex_exporter, valid_system, valid_methodology):
        session = AccuracyTestSession(name="empty")
        with pytest.raises(ValueError, match="at least one evaluation"):
            annex_exporter.export(valid_system, valid_methodology, session)

    def test_none_evaluation_in_list_skipped(
        self, annex_exporter, valid_system, valid_methodology, valid_session
    ):
        """None evaluations in list should be skipped, not crash."""
        valid_session.evaluations.append(None)
        report = annex_exporter.export(valid_system, valid_methodology, valid_session)
        assert report.total_evaluations == 1


# ========================================================================
# Input Validation — XSS/injection in system_id / provider_name
# ========================================================================

class TestInputValidationXSS:
    def test_script_tag_in_system_id_rejected(self):
        with pytest.raises(ValueError):
            SystemDescription(system_id="<script>alert(1)</script>")

    def test_angle_brackets_in_provider_rejected(self):
        with pytest.raises(ValueError):
            SystemDescription(provider_name="<b>XSS</b>")

    def test_control_chars_in_system_id_rejected(self):
        with pytest.raises(ValueError):
            SystemDescription(system_id="test\x00system")

    def test_backslash_in_provider_rejected(self):
        with pytest.raises(ValueError):
            SystemDescription(provider_name="test\\provider")

    def test_pipe_in_provider_rejected(self):
        with pytest.raises(ValueError):
            SystemDescription(provider_name="test|provider")

    def test_backtick_in_provider_rejected(self):
        with pytest.raises(ValueError):
            SystemDescription(provider_name="test`provider")

    def test_long_system_id_rejected(self):
        with pytest.raises(ValueError, match="max length"):
            SystemDescription(system_id="a" * 201)

    def test_long_provider_name_rejected(self):
        with pytest.raises(ValueError, match="max length"):
            SystemDescription(provider_name="a" * 501)

    def test_empty_system_id_skips_validation(self):
        """Empty system_id (default) should not raise."""
        s = SystemDescription(system_id="")
        assert s.system_id == ""

    def test_valid_system_id_accepted(self):
        s = SystemDescription(system_id="my-system_01:v2.0")
        assert s.system_id == "my-system_01:v2.0"

    def test_valid_provider_name_accepted(self):
        s = SystemDescription(provider_name="SabaTech GmbH & Co.")
        assert s.provider_name == "SabaTech GmbH & Co."

    def test_unicode_provider_accepted(self):
        s = SystemDescription(provider_name="SabaTech España")
        assert s.provider_name == "SabaTech España"


# ========================================================================
# SARIF Message Sanitization
# ========================================================================

class TestSARIFSanitization:
    def test_null_char_removed(self):
        result = sanitize_message_text("hello\x00world")
        assert result == "helloworld"

    def test_control_chars_removed(self):
        result = sanitize_message_text("test\x01\x02\x03data")
        assert result == "testdata"

    def test_newline_preserved(self):
        result = sanitize_message_text("line1\nline2")
        assert result == "line1\nline2"

    def test_tab_preserved(self):
        result = sanitize_message_text("col1\tcol2")
        assert result == "col1\tcol2"

    def test_carriage_return_preserved(self):
        result = sanitize_message_text("line1\rline2")
        assert result == "line1\rline2"

    def test_none_passthrough(self):
        assert sanitize_message_text(None) is None

    def test_non_string_coerced(self):
        result = sanitize_message_text(12345)
        assert result == "12345"

    def test_dict_strings_sanitized(self):
        data = {"msg": "hello\x00world", "count": 42}
        result = sanitize_dict_strings(data)
        assert result["msg"] == "helloworld"
        assert result["count"] == 42

    def test_nested_dict_sanitized(self):
        data = {"outer": {"inner": "test\x00val"}}
        result = sanitize_dict_strings(data)
        assert result["outer"]["inner"] == "testval"

    def test_list_strings_sanitized(self):
        data = {"items": ["a\x00b", "c\x01d"]}
        result = sanitize_dict_strings(data)
        assert result["items"] == ["ab", "cd"]

    def test_sarif_export_uses_sanitizer(self, sarif_exporter, valid_session):
        """SARIF output should not contain raw control characters."""
        report = sarif_exporter.export(valid_session)
        json_str = report.to_json()
        # Null bytes should not appear in JSON output
        assert "\x00" not in json_str
        # Other control chars (except \n \r \t) should not appear
        for i in range(0x01, 0x20):
            if i in (0x0A, 0x0D, 0x09):  # \n \r \t
                continue
            assert chr(i) not in json_str, f"Control char 0x{i:02x} found in SARIF JSON"
