"""
Unit Tests for Flaky Detection Infrastructure
"""

from datetime import datetime, timezone

import pytest

from src.domain.flaky_detection.entities import TestRun
from src.domain.flaky_detection.value_objects import QuarantineReason, TestIdentifier
from src.infrastructure.flaky_detection.flaky_detector import FlakyDetector
from src.infrastructure.flaky_detection.quarantine_manager import InMemoryQuarantineManager
from src.infrastructure.flaky_detection.root_cause_analyzer import RootCauseAnalyzer


class TestFlakyDetector:
    """Tests for FlakyDetector."""

    @pytest.fixture
    def detector(self):
        """Create a detector instance."""
        return FlakyDetector(min_runs=5)

    @pytest.fixture
    def test_identifier(self):
        """Create a test identifier."""
        return TestIdentifier.from_string("suite::TestClass::test_method")

    def test_detect_healthy_test(self, detector, test_identifier):
        """Test detection of healthy test."""
        runs = [TestRun(passed=True, duration_ms=100) for _ in range(20)]

        score = detector.detect(test_identifier, runs)

        assert score.score < 0.3
        assert score.is_flaky is False

    def test_detect_flaky_test(self, detector, test_identifier):
        """Test detection of flaky test."""
        # Create alternating pass/fail pattern
        runs = [TestRun(passed=i % 2 == 0, duration_ms=100) for i in range(20)]

        score = detector.detect(test_identifier, runs)

        assert score.score > 0.4
        assert score.is_flaky is True

    def test_detect_with_insufficient_runs(self, detector, test_identifier):
        """Test detection with insufficient data."""
        runs = [TestRun(passed=True, duration_ms=100) for _ in range(3)]

        score = detector.detect(test_identifier, runs)

        assert score.confidence == 0.0

    def test_detect_consistently_failing(self, detector, test_identifier):
        """Test that consistently failing tests are not flaky."""
        runs = [TestRun(passed=False, duration_ms=100) for _ in range(20)]

        score = detector.detect(test_identifier, runs)

        # Consistent failure is not flakiness
        assert score.score < 0.3

    def test_batch_detect(self, detector):
        """Test batch detection."""
        test1 = TestIdentifier.from_string("suite::test1")
        test2 = TestIdentifier.from_string("suite::test2")

        healthy_runs = [TestRun(passed=True, duration_ms=100) for _ in range(15)]
        flaky_runs = [TestRun(passed=i % 2 == 0, duration_ms=100) for i in range(15)]

        tests = [
            (test1, healthy_runs),
            (test2, flaky_runs),
        ]

        results = detector.batch_detect(tests)

        assert len(results) == 2
        # Should be sorted by score descending
        assert results[0][1].score >= results[1][1].score

    def test_analyze_test(self, detector, test_identifier):
        """Test full test analysis."""
        runs = [TestRun(passed=i % 2 == 0, duration_ms=100 + i * 10) for i in range(20)]

        flaky = detector.analyze_test(test_identifier, runs)

        assert flaky.total_runs == 20
        assert flaky.total_passes == 10
        assert flaky.total_failures == 10
        assert flaky.pass_rate == 0.5

    def test_duration_variance_detection(self):
        """Test detection based on duration variance."""
        detector = FlakyDetector(min_runs=5, duration_variance_threshold=0.3)
        test_id = TestIdentifier.from_string("suite::test")

        # High variance in duration
        runs = [
            TestRun(passed=True, duration_ms=100),
            TestRun(passed=True, duration_ms=500),
            TestRun(passed=True, duration_ms=150),
            TestRun(passed=True, duration_ms=800),
            TestRun(passed=True, duration_ms=200),
            TestRun(passed=True, duration_ms=600),
            TestRun(passed=True, duration_ms=120),
            TestRun(passed=True, duration_ms=700),
            TestRun(passed=True, duration_ms=180),
            TestRun(passed=True, duration_ms=550),
        ]

        flaky = detector.analyze_test(test_id, runs)

        # High duration variance should contribute to flakiness
        assert flaky.duration_variance > 0.5


class TestInMemoryQuarantineManager:
    """Tests for InMemoryQuarantineManager."""

    @pytest.fixture
    def manager(self):
        """Create a manager instance."""
        return InMemoryQuarantineManager()

    @pytest.fixture
    def test_identifier(self):
        """Create a test identifier."""
        return TestIdentifier.from_string("suite::TestClass::test_method")

    @pytest.mark.asyncio
    async def test_quarantine(self, manager, test_identifier):
        """Test quarantining a test."""
        entry = await manager.quarantine(
            test_identifier,
            QuarantineReason.HIGH_FAILURE_RATE,
            description="Fails 50% of the time",
        )

        assert entry.test_identifier == test_identifier
        assert entry.reason == QuarantineReason.HIGH_FAILURE_RATE
        assert entry.is_resolved is False

    @pytest.mark.asyncio
    async def test_quarantine_duplicate(self, manager, test_identifier):
        """Test quarantining already quarantined test."""
        await manager.quarantine(test_identifier, QuarantineReason.HIGH_FAILURE_RATE)
        entry2 = await manager.quarantine(test_identifier, QuarantineReason.RACE_CONDITION)

        # Should return existing entry
        assert entry2.reason == QuarantineReason.HIGH_FAILURE_RATE

    @pytest.mark.asyncio
    async def test_release(self, manager, test_identifier):
        """Test releasing from quarantine."""
        await manager.quarantine(test_identifier, QuarantineReason.HIGH_FAILURE_RATE)

        released = await manager.release(test_identifier, notes="Test is now stable")

        assert released.is_resolved is True
        assert released.resolution_notes == "Test is now stable"

    @pytest.mark.asyncio
    async def test_release_non_quarantined(self, manager, test_identifier):
        """Test releasing non-quarantined test."""
        released = await manager.release(test_identifier)

        assert released is None

    @pytest.mark.asyncio
    async def test_get_quarantined(self, manager, test_identifier):
        """Test getting quarantined tests."""
        test2 = TestIdentifier.from_string("suite::test2")

        await manager.quarantine(test_identifier, QuarantineReason.HIGH_FAILURE_RATE)
        await manager.quarantine(test2, QuarantineReason.RACE_CONDITION)

        # Release one
        await manager.release(test_identifier)

        quarantined = await manager.get_quarantined(None)

        assert len(quarantined) == 1
        assert quarantined[0].test_identifier == test2

    @pytest.mark.asyncio
    async def test_evaluate_for_release(self, manager, test_identifier):
        """Test evaluating quarantined test for release."""
        await manager.quarantine(test_identifier, QuarantineReason.HIGH_FAILURE_RATE)

        # 10 consecutive passes
        runs = [TestRun(passed=True, duration_ms=100) for _ in range(10)]

        entry = await manager.evaluate(test_identifier, runs)

        assert entry.evaluation_results[-1]["passed"] is True

    @pytest.mark.asyncio
    async def test_evaluate_not_ready(self, manager, test_identifier):
        """Test evaluation when not enough passes."""
        await manager.quarantine(test_identifier, QuarantineReason.HIGH_FAILURE_RATE)

        # Only 5 consecutive passes
        runs = [TestRun(passed=True, duration_ms=100) for _ in range(5)]

        entry = await manager.evaluate(test_identifier, runs)

        assert entry.evaluation_results[-1]["passed"] is False

    @pytest.mark.asyncio
    async def test_get_expired(self, manager, test_identifier):
        """Test getting expired quarantines."""
        from datetime import timedelta

        # Create expired entry
        entry = await manager.quarantine(test_identifier, QuarantineReason.HIGH_FAILURE_RATE)
        # Manually set expired
        manager._quarantines[entry.id] = entry.__class__(
            id=entry.id,
            test_identifier=entry.test_identifier,
            reason=entry.reason,
            quarantined_at=entry.quarantined_at,
            expires_at=datetime.now(timezone.utc) - timedelta(days=1),
        )

        expired = await manager.get_expired()

        assert len(expired) == 1


class TestRootCauseAnalyzer:
    """Tests for RootCauseAnalyzer."""

    @pytest.fixture
    def analyzer(self):
        """Create an analyzer instance."""
        return RootCauseAnalyzer()

    @pytest.fixture
    def test_identifier(self):
        """Create a test identifier."""
        return TestIdentifier.from_string("suite::test")

    def test_analyze_empty_runs(self, analyzer, test_identifier):
        """Test analysis with no runs."""
        result = analyzer.analyze(test_identifier, [])

        assert result["likely_causes"] == []
        assert result["confidence"] == 0.0

    def test_analyze_race_condition(self, analyzer, test_identifier):
        """Test detection of race condition."""
        runs = [
            TestRun(passed=False, error_message="Element not found: timeout waiting for element"),
            TestRun(passed=False, error_message="Stale element reference"),
            TestRun(passed=True, duration_ms=100),
            TestRun(passed=False, error_message="Timed out waiting for condition"),
        ]

        result = analyzer.analyze(test_identifier, runs)

        assert "race_condition" in result["likely_causes"]
        assert len(result["recommendations"]) > 0

    def test_analyze_external_dependency(self, analyzer, test_identifier):
        """Test detection of external dependency issues."""
        runs = [
            TestRun(passed=False, error_message="Connection refused to API server"),
            TestRun(passed=False, error_message="503 Service Unavailable"),
            TestRun(passed=True, duration_ms=100),
            TestRun(passed=False, error_message="Network error: DNS resolution failed"),
        ]

        result = analyzer.analyze(test_identifier, runs)

        assert "external_dependency" in result["likely_causes"]

    def test_analyze_timing_issues(self, analyzer, test_identifier):
        """Test detection of timing issues."""
        # High variance in duration
        runs = [
            TestRun(passed=True, duration_ms=100),
            TestRun(passed=True, duration_ms=500),
            TestRun(passed=True, duration_ms=150),
            TestRun(passed=True, duration_ms=800),
            TestRun(passed=True, duration_ms=200),
        ]

        result = analyzer.analyze(test_identifier, runs)

        # Should detect timing variance
        assert "timing" in result["patterns_found"]

    def test_generate_recommendations(self, analyzer, test_identifier):
        """Test recommendation generation."""
        runs = [
            TestRun(passed=False, error_message="Timeout waiting for element"),
        ]

        result = analyzer.analyze(test_identifier, runs)

        assert len(result["recommendations"]) > 0
        # Should include race condition recommendations
        assert any("wait" in r.lower() for r in result["recommendations"])
