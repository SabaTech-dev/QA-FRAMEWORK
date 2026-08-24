"""
Value Objects for Flaky Test Detection Domain
"""

from dataclasses import dataclass
from enum import Enum


class FlakyStatus(str, Enum):
    """Status of a flaky test."""

    HEALTHY = "healthy"  # No flakiness detected
    SUSPECT = "suspect"  # Some signs of flakiness
    FLAKY = "flaky"  # Confirmed flaky
    QUARANTINED = "quarantined"  # Removed from regular runs
    FIXED = "fixed"  # Previously flaky, now stable


class QuarantineReason(str, Enum):
    """Reasons for quarantining a test."""

    HIGH_FAILURE_RATE = "high_failure_rate"
    INCONSISTENT_TIMING = "inconsistent_timing"
    EXTERNAL_DEPENDENCY = "external_dependency"
    RESOURCE_CONTENTION = "resource_contention"
    RACE_CONDITION = "race_condition"
    UNKNOWN = "unknown"


class DetectionMethod(str, Enum):
    """Methods used to detect flakiness."""

    STATISTICAL = "statistical"  # Statistical analysis of pass/fail rates
    HISTORICAL = "historical"  # Historical pattern analysis
    SEQUENCE_ANALYSIS = "sequence"  # Analyzing failure sequences
    TIMING_ANALYSIS = "timing"  # Duration variance analysis
    MACHINE_LEARNING = "ml"  # ML-based prediction
    MANUAL_FLAG = "manual"  # Manually flagged


@dataclass(frozen=True)
class FlakinessScore:
    """Score representing likelihood of flakiness."""

    score: float  # 0.0 to 1.0
    confidence: float  # Confidence in the score
    method: DetectionMethod

    def __post_init__(self):
        if not 0 <= self.score <= 1:
            raise ValueError("Score must be between 0 and 1")
        if not 0 <= self.confidence <= 1:
            raise ValueError("Confidence must be between 0 and 1")

    @property
    def is_flaky(self) -> bool:
        """Determine if score indicates flakiness."""
        return self.score >= 0.5

    @property
    def is_suspect(self) -> bool:
        """Determine if score indicates suspicion."""
        return 0.3 <= self.score < 0.5


@dataclass(frozen=True)
class TestIdentifier:
    """Unique identifier for a test."""

    test_id: str
    suite_id: str
    class_name: str | None
    method_name: str

    def __str__(self) -> str:
        if self.class_name:
            return f"{self.suite_id}::{self.class_name}::{self.method_name}"
        return f"{self.suite_id}::{self.method_name}"

    @classmethod
    def from_string(cls, identifier: str) -> "TestIdentifier":
        """Parse identifier from string."""
        parts = identifier.split("::")
        if len(parts) == 3:
            return cls(
                test_id=identifier,
                suite_id=parts[0],
                class_name=parts[1],
                method_name=parts[2],
            )
        elif len(parts) == 2:
            return cls(
                test_id=identifier,
                suite_id=parts[0],
                class_name=None,
                method_name=parts[1],
            )
        raise ValueError(f"Invalid test identifier format: {identifier}")


@dataclass(frozen=True)
class FailurePattern:
    """Pattern of failures for a test."""

    consecutive_failures: int
    max_consecutive_failures: int
    failure_positions: list  # Positions in test run where failure occurred
    alternating_pattern: bool  # Fail, pass, fail, pass pattern
    cluster_positions: list  # Positions where failures cluster

    @property
    def has_pattern(self) -> bool:
        """Check if a pattern is detected."""
        return (
            self.alternating_pattern
            or len(self.cluster_positions) > 0
            or self.consecutive_failures > 1
        )
