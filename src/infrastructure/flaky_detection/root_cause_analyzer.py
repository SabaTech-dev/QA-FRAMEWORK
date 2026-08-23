"""
Root Cause Analyzer Implementation

Analyzes root causes of test flakiness and provides recommendations.
"""

import re
from collections import Counter
from typing import Any, Dict, List

from src.domain.flaky_detection.entities import TestRun
from src.domain.flaky_detection.value_objects import QuarantineReason, TestIdentifier


class RootCauseAnalyzer:
    """
    Analyzes root causes of test flakiness.

    Uses heuristics and patterns to identify likely causes:
    - Race conditions (timing-dependent failures)
    - External dependencies (API, database issues)
    - Resource contention (memory, CPU)
    - State leakage (test order dependencies)
    - Environmental issues (config, secrets)
    """

    # Patterns that indicate specific causes
    PATTERNS = {
        QuarantineReason.RACE_CONDITION: [
            r"timeout",
            r"timed out",
            r"element not found",
            r"stale element",
            r"element is not attached",
            r"waiting for",
            r"condition not met",
        ],
        QuarantineReason.EXTERNAL_DEPENDENCY: [
            r"connection refused",
            r"connection reset",
            r"network",
            r"dns",
            r"api",
            r"service unavailable",
            r"503",
            r"502",
            r"429",
            r"rate limit",
        ],
        QuarantineReason.RESOURCE_CONTENTION: [
            r"out of memory",
            r"oom",
            r"memory",
            r"disk",
            r"space",
            r"resource",
            r"limit exceeded",
        ],
        QuarantineReason.INCONSISTENT_TIMING: [
            r"timeout",
            r"slow",
            r"delay",
            r"wait",
            r"performance",
        ],
    }

    def analyze(
        self,
        test_identifier: TestIdentifier,
        runs: List[TestRun],
    ) -> Dict[str, Any]:
        """
        Analyze root causes of flakiness.

        Returns:
            - likely_causes: List of identified causes
            - confidence: Confidence in analysis
            - recommendations: List of fix recommendations
            - patterns_found: Specific patterns detected
        """
        if not runs:
            return {
                "likely_causes": [],
                "confidence": 0.0,
                "recommendations": [],
                "patterns_found": {},
            }

        # Analyze error messages
        error_analysis = self._analyze_errors(runs)

        # Analyze timing patterns
        timing_analysis = self._analyze_timing(runs)

        # Analyze failure positions
        position_analysis = self._analyze_positions(runs)

        # Combine analyses
        causes = []
        patterns = {}
        confidence = 0.0

        # Check for race conditions
        if error_analysis.get("race_condition_likelihood", 0) > 0.5:
            causes.append(QuarantineReason.RACE_CONDITION)
            patterns["race_condition"] = error_analysis.get("race_indicators", [])
            confidence += 0.3

        # Check for external dependencies
        if error_analysis.get("external_dependency_likelihood", 0) > 0.3:
            causes.append(QuarantineReason.EXTERNAL_DEPENDENCY)
            patterns["external"] = error_analysis.get("external_indicators", [])
            confidence += 0.3

        # Check for timing issues
        if timing_analysis.get("variance_high", False):
            causes.append(QuarantineReason.INCONSISTENT_TIMING)
            patterns["timing"] = timing_analysis
            confidence += 0.2

        # Check for position-dependent failures
        if position_analysis.get("position_correlation", 0) > 0.5:
            causes.append(QuarantineReason.RESOURCE_CONTENTION)
            patterns["position"] = position_analysis
            confidence += 0.2

        # Generate recommendations
        recommendations = self._generate_recommendations(causes, patterns)

        return {
            "likely_causes": [c.value for c in causes],
            "confidence": min(1.0, confidence),
            "recommendations": recommendations,
            "patterns_found": patterns,
        }

    def _analyze_errors(self, runs: List[TestRun]) -> Dict[str, Any]:
        """Analyze error messages for patterns."""
        errors = []
        for run in runs:
            if not run.passed:
                if run.error_message:
                    errors.append(run.error_message.lower())
                if run.error_type:
                    errors.append(run.error_type.lower())

        if not errors:
            return {"race_condition_likelihood": 0, "external_dependency_likelihood": 0}

        # Count pattern matches
        race_matches = []
        external_matches = []

        for error in errors:
            for pattern in self.PATTERNS.get(QuarantineReason.RACE_CONDITION, []):
                if re.search(pattern, error, re.IGNORECASE):
                    race_matches.append(pattern)

            for pattern in self.PATTERNS.get(QuarantineReason.EXTERNAL_DEPENDENCY, []):
                if re.search(pattern, error, re.IGNORECASE):
                    external_matches.append(pattern)

        race_likelihood = len(race_matches) / len(errors) if errors else 0
        external_likelihood = len(external_matches) / len(errors) if errors else 0

        return {
            "race_condition_likelihood": race_likelihood,
            "external_dependency_likelihood": external_likelihood,
            "race_indicators": list(set(race_matches))[:5],
            "external_indicators": list(set(external_matches))[:5],
        }

    def _analyze_timing(self, runs: List[TestRun]) -> Dict[str, Any]:
        """Analyze timing patterns."""
        durations = [r.duration_ms for r in runs if r.duration_ms > 0]

        if not durations:
            return {"variance_high": False}

        avg = sum(durations) / len(durations)

        if avg == 0:
            return {"variance_high": False}

        variance = sum((d - avg) ** 2 for d in durations) / len(durations)
        std_dev = variance**0.5
        cv = std_dev / avg

        # Check for outliers (very slow runs)
        slow_threshold = avg * 2
        slow_runs = sum(1 for d in durations if d > slow_threshold)

        return {
            "variance_high": cv > 0.5,
            "coefficient_of_variation": cv,
            "average_duration_ms": avg,
            "slow_run_percentage": slow_runs / len(durations) if durations else 0,
        }

    def _analyze_positions(self, runs: List[TestRun]) -> Dict[str, Any]:
        """Analyze if failures correlate with test position."""
        failure_positions = []

        for i, run in enumerate(runs):
            if not run.passed:
                failure_positions.append(run.run_number if run.run_number else i)

        if not failure_positions:
            return {"position_correlation": 0}

        # Check if failures cluster at certain positions
        position_counter = Counter(failure_positions)
        most_common = position_counter.most_common(3)

        # High correlation if most failures are at same positions
        if most_common:
            max_count = most_common[0][1]
            correlation = max_count / len(failure_positions)
            return {
                "position_correlation": correlation,
                "common_positions": most_common,
            }

        return {"position_correlation": 0}

    def _generate_recommendations(
        self,
        causes: List[QuarantineReason],
        patterns: Dict[str, Any],
    ) -> List[str]:
        """Generate fix recommendations based on causes."""
        recommendations = []

        for cause in causes:
            if cause == QuarantineReason.RACE_CONDITION:
                recommendations.extend(
                    [
                        "Add explicit waits for dynamic elements",
                        "Use retry mechanisms for flaky operations",
                        "Consider increasing timeout values",
                        "Review async operations and race conditions",
                    ]
                )

            elif cause == QuarantineReason.EXTERNAL_DEPENDENCY:
                recommendations.extend(
                    [
                        "Mock external API calls in tests",
                        "Add circuit breakers for external services",
                        "Implement retry with exponential backoff",
                        "Consider using test fixtures for external data",
                    ]
                )

            elif cause == QuarantineReason.INCONSISTENT_TIMING:
                recommendations.extend(
                    [
                        "Review and optimize slow test operations",
                        "Add performance assertions to detect regressions",
                        "Consider splitting long tests",
                        "Use explicit waits instead of fixed delays",
                    ]
                )

            elif cause == QuarantineReason.RESOURCE_CONTENTION:
                recommendations.extend(
                    [
                        "Run tests in isolation when possible",
                        "Review test order dependencies",
                        "Clean up resources between tests",
                        "Consider parallel test execution limits",
                    ]
                )

        # General recommendations
        if len(causes) > 1:
            recommendations.append(
                "Multiple causes detected - prioritize fixing most common pattern"
            )

        return list(set(recommendations))  # Remove duplicates
