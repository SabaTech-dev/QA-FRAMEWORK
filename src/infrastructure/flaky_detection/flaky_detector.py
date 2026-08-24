"""
Flaky Test Detector Implementation

Statistical and pattern-based detection of flaky tests.
"""

import statistics
from collections import Counter
from typing import List, Tuple

from src.domain.flaky_detection.entities import FlakyTest, TestRun
from src.domain.flaky_detection.value_objects import (
    DetectionMethod,
    FailurePattern,
    FlakinessScore,
    FlakyStatus,
    TestIdentifier,
)


class FlakyDetector:
    """
    Multi-method flaky test detector.

    Uses several approaches:
    - Statistical analysis of pass/fail rates
    - Sequence pattern analysis
    - Duration variance analysis
    - Failure clustering detection
    """

    def __init__(
        self,
        min_runs: int = 10,
        flaky_threshold: float = 0.5,
        suspect_threshold: float = 0.3,
        duration_variance_threshold: float = 0.5,
        consecutive_failure_threshold: int = 3,
    ):
        self.min_runs = min_runs
        self.flaky_threshold = flaky_threshold
        self.suspect_threshold = suspect_threshold
        self.duration_variance_threshold = duration_variance_threshold
        self.consecutive_failure_threshold = consecutive_failure_threshold

    def detect(
        self,
        test_identifier: TestIdentifier,
        runs: List[TestRun],
    ) -> FlakinessScore:
        """
        Detect if a test is flaky based on its run history.
        """
        if len(runs) < self.min_runs:
            # Not enough data for reliable detection
            return FlakinessScore(
                score=0.0,
                confidence=0.0,
                method=DetectionMethod.STATISTICAL,
            )

        # Calculate multiple scores
        scores = []

        # 1. Statistical score (pass rate variance)
        stat_score = self._statistical_analysis(runs)
        scores.append((stat_score, DetectionMethod.STATISTICAL))

        # 2. Sequence pattern score
        seq_score = self._sequence_analysis(runs)
        scores.append((seq_score, DetectionMethod.SEQUENCE_ANALYSIS))

        # 3. Duration variance score
        dur_score = self._duration_analysis(runs)
        scores.append((dur_score, DetectionMethod.TIMING_ANALYSIS))

        # Combine scores with weighted average
        # Statistical analysis is most reliable
        weights = [0.5, 0.3, 0.2]

        final_score = sum(s * w for (s, _), w in zip(scores, weights))

        # Confidence increases with more runs
        confidence = min(1.0, len(runs) / 50)

        return FlakinessScore(
            score=final_score,
            confidence=confidence,
            method=DetectionMethod.STATISTICAL,
        )

    def batch_detect(
        self,
        tests: List[Tuple[TestIdentifier, List[TestRun]]],
    ) -> List[Tuple[TestIdentifier, FlakinessScore]]:
        """Detect flakiness for multiple tests."""
        results = []

        for test_identifier, runs in tests:
            score = self.detect(test_identifier, runs)
            results.append((test_identifier, score))

        # Sort by flakiness score descending
        results.sort(key=lambda x: x[1].score, reverse=True)

        return results

    def analyze_test(
        self,
        test_identifier: TestIdentifier,
        runs: List[TestRun],
    ) -> FlakyTest:
        """
        Perform full analysis of a test.
        """
        score = self.detect(test_identifier, runs)

        # Determine status
        if score.is_flaky:
            status = FlakyStatus.FLAKY
        elif score.is_suspect:
            status = FlakyStatus.SUSPECT
        else:
            status = FlakyStatus.HEALTHY

        # Calculate failure pattern
        failure_pattern = self._detect_failure_pattern(runs)

        # Extract common errors
        common_errors = self._extract_common_errors(runs)

        # Calculate statistics
        total_runs = len(runs)
        total_passes = sum(1 for r in runs if r.passed)
        durations = [r.duration_ms for r in runs]

        avg_duration = int(statistics.mean(durations)) if durations else 0
        std_dev = statistics.stdev(durations) if len(durations) > 1 else 0

        return FlakyTest(
            test_identifier=test_identifier,
            status=status,
            flakiness_score=score,
            total_runs=total_runs,
            total_passes=total_passes,
            total_failures=total_runs - total_passes,
            pass_rate=total_passes / total_runs if total_runs > 0 else 1.0,
            avg_duration_ms=avg_duration,
            duration_std_dev=std_dev,
            min_duration_ms=int(min(durations)) if durations else 0,
            max_duration_ms=int(max(durations)) if durations else 0,
            failure_pattern=failure_pattern,
            common_errors=common_errors[:5],
            detection_method=DetectionMethod.STATISTICAL,
            first_detected=None,
            last_flaky_at=None,
        )

    def _statistical_analysis(self, runs: List[TestRun]) -> float:
        """
        Statistical analysis of pass/fail rates.

        A truly flaky test will have inconsistent results.
        """
        if not runs:
            return 0.0

        total = len(runs)
        failures = sum(1 for r in runs if not r.passed)
        failure_rate = failures / total

        # Perfect pass or fail rate is not flaky
        if failure_rate == 0 or failure_rate == 1:
            return 0.0

        # The closer to 50% failure rate, the more likely to be flaky
        # But we also consider the variance in results

        # Check for runs that flip-flop
        flips = 0
        for i in range(1, len(runs)):
            if runs[i].passed != runs[i - 1].passed:
                flips += 1

        flip_rate = flips / (total - 1) if total > 1 else 0

        # High flip rate indicates flakiness
        # Combine failure rate deviation from 0/1 and flip rate
        deviation = min(failure_rate, 1 - failure_rate)  # How far from extremes
        score = deviation * 0.6 + flip_rate * 0.4

        return min(1.0, score)

    def _sequence_analysis(self, runs: List[TestRun]) -> float:
        """
        Analyze failure sequences.

        Alternating patterns or clustered failures indicate flakiness.
        """
        if len(runs) < 3:
            return 0.0

        # Check for alternating pattern (F-P-F-P)
        alternations = 0
        for i in range(1, len(runs)):
            if runs[i].passed != runs[i - 1].passed:
                alternations += 1

        alternation_rate = alternations / (len(runs) - 1)

        # Check for consecutive failures
        max_consecutive = 0
        current_consecutive = 0
        for run in runs:
            if not run.passed:
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_consecutive = 0

        # Score based on patterns
        # High alternation rate suggests flakiness
        # But too many consecutive failures suggests real failure
        if max_consecutive >= len(runs) * 0.8:
            # Likely a real failure, not flaky
            return 0.0

        score = alternation_rate

        # Bonus for perfect alternation in certain ranges
        if 0.4 <= alternation_rate <= 0.6:
            score += 0.2

        return min(1.0, score)

    def _duration_analysis(self, runs: List[TestRun]) -> float:
        """
        Analyze duration variance.

        High variance in test duration can indicate flakiness
        (race conditions, resource contention).
        """
        durations = [r.duration_ms for r in runs if r.duration_ms > 0]

        if len(durations) < 3:
            return 0.0

        avg = statistics.mean(durations)
        if avg == 0:
            return 0.0

        std_dev = statistics.stdev(durations)
        coefficient_of_variation = std_dev / avg

        # High CV indicates inconsistency
        if coefficient_of_variation > self.duration_variance_threshold:
            return min(1.0, coefficient_of_variation)

        return coefficient_of_variation * 0.5

    def _detect_failure_pattern(self, runs: List[TestRun]) -> FailurePattern:
        """Detect failure patterns in test runs."""
        consecutive_failures = 0
        max_consecutive = 0
        failure_positions = []
        last_was_failure = False

        for i, run in enumerate(runs):
            if not run.passed:
                failure_positions.append(i)
                if last_was_failure:
                    consecutive_failures += 1
                else:
                    consecutive_failures = 1
                max_consecutive = max(max_consecutive, consecutive_failures)
                last_was_failure = True
            else:
                last_was_failure = False

        # Detect alternating pattern
        alternating = False
        if len(runs) >= 4:
            alternations = sum(
                1 for i in range(1, len(runs)) if runs[i].passed != runs[i - 1].passed
            )
            alternating = alternations / (len(runs) - 1) > 0.6

        # Detect clustering
        clusters = []
        if failure_positions:
            cluster_start = failure_positions[0]
            last_pos = failure_positions[0]

            for pos in failure_positions[1:]:
                if pos - last_pos <= 2:
                    last_pos = pos
                else:
                    if last_pos - cluster_start >= 2:
                        clusters.append((cluster_start, last_pos))
                    cluster_start = pos
                    last_pos = pos

            if last_pos - cluster_start >= 2:
                clusters.append((cluster_start, last_pos))

        return FailurePattern(
            consecutive_failures=max_consecutive,
            max_consecutive_failures=max_consecutive,
            failure_positions=failure_positions,
            alternating_pattern=alternating,
            cluster_positions=clusters,
        )

    def _extract_common_errors(self, runs: List[TestRun]) -> List[str]:
        """Extract common error messages from failed runs."""
        errors = []
        for run in runs:
            if not run.passed and run.error_type:
                errors.append(run.error_type)

        # Count occurrences
        counter = Counter(errors)

        # Return most common errors
        return [error for error, _ in counter.most_common(5)]
