"""
Value Objects for Bias/Fairness Testing Domain

Core types for fairness evaluation, including statistical
metrics definitions and subgroup representation.
"""

from enum import Enum
import re
from dataclasses import dataclass
from typing import Optional, List

# Security: limits to prevent resource exhaustion
MAX_GROUP_NAME_LENGTH = 200
MAX_SUBGROUPS = 50
MAX_METRIC_VALUE = 1.0


class FairnessMetric(str, Enum):
    """
    Statistical fairness metrics.

    Each metric captures a different dimension of fairness
    as defined in the fairness-aware ML literature.
    """
    DEMOGRAPHIC_PARITY = "demographic_parity"
    EQUAL_OPPORTUNITY = "equal_opportunity"
    EQUALIZED_ODDS = "equalized_odds"
    PREDICTIVE_PARITY = "predictive_parity"
    DISPARATE_IMPACT = "disparate_impact"
    CALIBRATION = "calibration"


class FairnessLevel(str, Enum):
    """Fairness assessment classification."""
    FAIR = "fair"                  # metric within acceptable range
    MARGINAL = "marginal"          # metric near threshold
    BIASED = "biased"             # metric indicates significant bias
    SEVERELY_BIASED = "severely_biased"  # critical fairness violation


class BiasTestStatus(str, Enum):
    """Status of a bias/fairness test session."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


class Subgroup(str, Enum):
    """
    Protected attribute categories for subgroup analysis.

    Each subgroup represents a protected characteristic
    under anti-discrimination law.
    """
    AGE = "age"
    GENDER = "gender"
    RACE_ETHNICITY = "race_ethnicity"
    NATIONALITY = "nationality"
    DISABILITY = "disability"
    RELIGION = "religion"
    SEXUAL_ORIENTATION = "sexual_orientation"
    SOCIOECONOMIC = "socioeconomic"


# Validation patterns
_GROUP_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9._\s-]{0,199}$')


def validate_group_name(value: str) -> str:
    """
    Validate a subgroup name/label.

    Must start with alphanumeric, contain only safe characters.
    Max MAX_GROUP_NAME_LENGTH chars.
    """
    if not value or not isinstance(value, str):
        raise ValueError("group_name must be a non-empty string")
    if len(value) > MAX_GROUP_NAME_LENGTH:
        raise ValueError(
            f"group_name exceeds max length {MAX_GROUP_NAME_LENGTH}, got {len(value)}"
        )
    if not _GROUP_NAME_PATTERN.match(value):
        raise ValueError(
            "group_name must start with alphanumeric and contain only "
            "[a-zA-Z0-9._ -] characters"
        )
    return value


def validate_metric_value(value: float, name: str = "metric") -> float:
    """
    Validate a fairness metric value is in [0.0, MAX_METRIC_VALUE].

    Args:
        value: The metric value to validate
        name: Field name for error messages

    Returns:
        The validated value

    Raises:
        ValueError if value is out of range
    """
    if not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number, got {type(value).__name__}")
    if value != value:  # NaN check
        raise ValueError(f"{name} must not be NaN")
    if value == float('inf') or value == float('-inf'):
        raise ValueError(f"{name} must not be infinite")
    if not 0.0 <= value <= MAX_METRIC_VALUE:
        raise ValueError(
            f"{name} must be in [0.0, {MAX_METRIC_VALUE}], got {value}"
        )
    return value


@dataclass(frozen=True)
class SubgroupMetric:
    """A single fairness metric result for a specific subgroup."""
    metric: FairnessMetric
    value: float
    sample_size: int = 0
    confidence_interval_lower: float = 0.0
    confidence_interval_upper: float = 0.0

    def __post_init__(self):
        validate_metric_value(self.value, "value")
        if self.sample_size < 0:
            raise ValueError(f"sample_size must be >= 0, got {self.sample_size}")

    @property
    def is_fair(self) -> bool:
        """Check if metric value is within fair range (0.4-0.6 centered on 0.5)."""
        return 0.4 <= self.value <= 0.6

    @property
    def disparity_from_parity(self) -> float:
        """Distance from perfect parity (0.5)."""
        return abs(self.value - 0.5)

    def to_dict(self) -> dict:
        return {
            "metric": self.metric.value,
            "value": round(self.value, 4),
            "sample_size": self.sample_size,
            "confidence_interval_lower": round(self.confidence_interval_lower, 4),
            "confidence_interval_upper": round(self.confidence_interval_upper, 4),
        }
