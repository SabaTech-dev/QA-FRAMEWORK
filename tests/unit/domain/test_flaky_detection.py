"""
Unit Tests for Flaky Test Detection
"""

from datetime import UTC, datetime, timedelta

import pytest

from src.domain.flaky_detection.entities import (
    FlakyDetectionSession,
    FlakyTest,
    QuarantineEntry,
    TestRun,
)
from src.domain.flaky_detection.value_objects import (
    DetectionMethod,
    FailurePattern,
    FlakinessScore,
    FlakyStatus,
    QuarantineReason,
    TestIdentifier,
)


class TestTestIdentifier:
    """Tests for TestIdentifier value object."""

    def test_create_identifier(self):
        """Test creating test identifier."""
        identifier = TestIdentifier(
            test_id="suite::class::method",
            suite_id="suite",
            class_name="class",
            method_name="method",
        )

        assert identifier.suite_id == "suite"
        assert identifier.class_name == "class"
        assert identifier.method_name == "method"

    def test_str_representation(self):
        """Test string representation."""
        identifier = TestIdentifier(
            test_id="suite::class::method",
            suite_id="suite",
            class_name="class",
            method_name="method",
        )

        assert str(identifier) == "suite::class::method"

    def test_from_string_with_class(self):
        """Test parsing identifier with class."""
        identifier = TestIdentifier.from_string("suite::class::method")

        assert identifier.suite_id == "suite"
        assert identifier.class_name == "class"
        assert identifier.method_name == "method"

    def test_from_string_without_class(self):
        """Test parsing identifier without class."""
        identifier = TestIdentifier.from_string("suite::method")

        assert identifier.suite_id == "suite"
        assert identifier.class_name is None
        assert identifier.method_name == "method"

    def test_from_string_invalid(self):
        """Test parsing invalid identifier."""
        with pytest.raises(ValueError):
            TestIdentifier.from_string("invalid")


class TestFlakinessScore:
    """Tests for FlakinessScore value object."""

    def test_create_score(self):
        """Test creating flakiness score."""
        score = FlakinessScore(
            score=0.7,
            confidence=0.8,
            method=DetectionMethod.STATISTICAL,
        )

        assert score.score == 0.7
        assert score.confidence == 0.8
        assert score.is_flaky is True

    def test_is_flaky(self):
        """Test is_flaky property."""
        assert FlakinessScore(0.5, 1.0, DetectionMethod.STATISTICAL).is_flaky is True
        assert FlakinessScore(0.7, 1.0, DetectionMethod.STATISTICAL).is_flaky is True
        assert FlakinessScore(0.4, 1.0, DetectionMethod.STATISTICAL).is_flaky is False

    def test_is_suspect(self):
        """Test is_suspect property."""
        assert FlakinessScore(0.3, 1.0, DetectionMethod.STATISTICAL).is_suspect is True
        assert FlakinessScore(0.4, 1.0, DetectionMethod.STATISTICAL).is_suspect is True
        assert FlakinessScore(0.5, 1.0, DetectionMethod.STATISTICAL).is_suspect is False
        assert FlakinessScore(0.2, 1.0, DetectionMethod.STATISTICAL).is_suspect is False

    def test_invalid_score(self):
        """Test validation of score range."""
        with pytest.raises(ValueError):
            FlakinessScore(1.5, 0.8, DetectionMethod.STATISTICAL)

        with pytest.raises(ValueError):
            FlakinessScore(-0.1, 0.8, DetectionMethod.STATISTICAL)


class TestFailurePattern:
    """Tests for FailurePattern value object."""

    def test_no_pattern(self):
        """Test when no pattern exists."""
        pattern = FailurePattern(
            consecutive_failures=1,
            max_consecutive_failures=1,
            failure_positions=[0],
            alternating_pattern=False,
            cluster_positions=[],
        )

        assert pattern.has_pattern is False

    def test_alternating_pattern(self):
        """Test alternating pattern detection."""
        pattern = FailurePattern(
            consecutive_failures=1,
            max_consecutive_failures=1,
            failure_positions=[0, 2, 4],
            alternating_pattern=True,
            cluster_positions=[],
        )

        assert pattern.has_pattern is True

    def test_cluster_pattern(self):
        """Test cluster pattern detection."""
        pattern = FailurePattern(
            consecutive_failures=2,
            max_consecutive_failures=2,
            failure_positions=[0, 1, 2],
            alternating_pattern=False,
            cluster_positions=[(0, 2)],
        )

        assert pattern.has_pattern is True


class TestTestRun:
    """Tests for TestRun entity."""

    def test_create_test_run(self):
        """Test creating a test run."""
        run = TestRun(
            passed=True,
            duration_ms=150,
        )

        assert run.passed is True
        assert run.duration_ms == 150
        assert run.id is not None

    def test_to_dict(self):
        """Test serialization."""
        identifier = TestIdentifier.from_string("suite::test")
        run = TestRun(
            test_identifier=identifier,
            passed=False,
            duration_ms=200,
            error_message="Assertion failed",
        )

        data = run.to_dict()

        assert data["passed"] is False
        assert data["duration_ms"] == 200
        assert "test_identifier" in data


class TestFlakyTest:
    """Tests for FlakyTest entity."""

    def test_create_flaky_test(self):
        """Test creating a flaky test."""
        identifier = TestIdentifier.from_string("suite::test")
        flaky = FlakyTest(
            test_identifier=identifier,
            status=FlakyStatus.FLAKY,
            total_runs=20,
            total_passes=15,
            total_failures=5,
            pass_rate=0.75,
        )

        assert flaky.status == FlakyStatus.FLAKY
        assert flaky.total_runs == 20
        assert flaky.pass_rate == 0.75

    def test_failure_rate(self):
        """Test failure rate calculation."""
        flaky = FlakyTest(
            total_runs=100,
            total_passes=80,
            total_failures=20,
            pass_rate=0.8,
        )

        assert flaky.failure_rate == pytest.approx(0.2, rel=0.01)

    def test_is_quarantined(self):
        """Test is_quarantined property."""
        healthy = FlakyTest(status=FlakyStatus.HEALTHY)
        quarantined = FlakyTest(status=FlakyStatus.QUARANTINED)

        assert healthy.is_quarantined is False
        assert quarantined.is_quarantined is True

    def test_update_stats(self):
        """Test updating statistics."""
        flaky = FlakyTest(total_runs=0, total_passes=0, total_failures=0)

        runs = [
            TestRun(passed=True, duration_ms=100),
            TestRun(passed=True, duration_ms=120),
            TestRun(passed=False, duration_ms=80),
        ]

        updated = flaky.update_stats(runs)

        assert updated.total_runs == 3
        assert updated.total_passes == 2
        assert updated.total_failures == 1
        assert updated.pass_rate == pytest.approx(2 / 3, rel=0.01)


class TestQuarantineEntry:
    """Tests for QuarantineEntry entity."""

    def test_create_entry(self):
        """Test creating a quarantine entry."""
        identifier = TestIdentifier.from_string("suite::test")
        entry = QuarantineEntry(
            test_identifier=identifier,
            reason=QuarantineReason.HIGH_FAILURE_RATE,
            description="Test fails 50% of the time",
        )

        assert entry.reason == QuarantineReason.HIGH_FAILURE_RATE
        assert entry.is_resolved is False

    def test_is_expired(self):
        """Test expiry check."""
        # Not expired
        entry = QuarantineEntry(
            expires_at=datetime.now(UTC) + timedelta(days=10),
        )
        assert entry.is_expired is False

        # Expired
        expired = QuarantineEntry(
            expires_at=datetime.now(UTC) - timedelta(days=1),
        )
        assert expired.is_expired is True

    def test_add_evaluation(self):
        """Test adding evaluation result."""
        entry = QuarantineEntry()

        updated = entry.add_evaluation(True, "10 consecutive passes")

        assert len(updated.evaluation_results) == 1
        assert updated.last_evaluation is not None

    def test_resolve(self):
        """Test resolving quarantine."""
        entry = QuarantineEntry()

        resolved = entry.resolve("Test is now stable")

        assert resolved.is_resolved is True
        assert resolved.resolution_notes == "Test is now stable"


class TestFlakyDetectionSession:
    """Tests for FlakyDetectionSession entity."""

    def test_create_session(self):
        """Test creating a detection session."""
        session = FlakyDetectionSession()

        assert session.status == "pending"
        assert session.tests_analyzed == 0

    def test_total_issues(self):
        """Test total issues calculation."""
        session = FlakyDetectionSession(
            suspect_tests=5,
            flaky_tests=3,
            quarantined_tests=2,
        )

        assert session.total_issues == 10

    def test_health_rate(self):
        """Test health rate calculation."""
        session = FlakyDetectionSession(
            tests_analyzed=100,
            healthy_tests=85,
            suspect_tests=10,
            flaky_tests=5,
        )

        assert session.health_rate == 0.85

    def test_complete(self):
        """Test completing session."""
        session = FlakyDetectionSession()

        completed = session.complete()

        assert completed.status == "completed"
        assert completed.completed_at is not None

    def test_to_dict(self):
        """Test serialization."""
        session = FlakyDetectionSession(
            tests_analyzed=50,
            healthy_tests=40,
            flaky_tests=5,
            suspect_tests=5,
        )

        data = session.to_dict()

        assert data["tests_analyzed"] == 50
        assert data["total_issues"] == 10
        assert data["health_rate"] == 0.8
