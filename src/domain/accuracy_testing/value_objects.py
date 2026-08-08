"""
Value Objects for AI Accuracy Testing Domain

Core value objects for evaluating AI response accuracy
against legal/regulatory benchmarks.
"""

from enum import Enum
import re
from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime, timezone

# F-ACC-003: Maximum input length for regex operations
MAX_EVAL_INPUT_LENGTH = 10_000


class LegalDomain(str, Enum):
    """Legal domains for accuracy benchmarks."""
    AI_LIABILITY = "ai_liability"
    GDPR = "gdpr"
    EU_AI_ACT = "eu_ai_act"
    PRODUCT_LIABILITY = "product_liability"
    CONTRACT_LAW = "contract_law"


class EvaluationCriterion(str, Enum):
    """Criteria used to evaluate AI response accuracy."""
    FACTUAL_ACCURACY = "factual_accuracy"
    LEGAL_REASONING = "legal_reasoning"
    CITATION_CORRECTNESS = "citation_correctness"
    COMPLETENESS = "completeness"
    NUANCE_HANDLING = "nuance_handling"
    HARMFULNESS_SAFETY = "harmfulness_safety"


class AccuracyLevel(str, Enum):
    """Accuracy classification levels."""
    EXCELLENT = "excellent"    # 90-100%
    GOOD = "good"              # 75-89%
    ADEQUATE = "adequate"      # 60-74%
    POOR = "poor"              # 40-59%
    FAILING = "failing"        # 0-39%

    @classmethod
    def from_score(cls, score: float) -> "AccuracyLevel":
        """Convert a 0-1 score to an accuracy level."""
        if not 0.0 <= score <= 1.0:
            raise ValueError(f"Score must be in [0.0, 1.0], got {score}")
        if score >= 0.9:
            return cls.EXCELLENT
        elif score >= 0.75:
            return cls.GOOD
        elif score >= 0.6:
            return cls.ADEQUATE
        elif score >= 0.4:
            return cls.POOR
        return cls.FAILING


class EvaluationStatus(str, Enum):
    """Status of an accuracy evaluation."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


class ResponseVerdict(str, Enum):
    """Overall verdict for an evaluated response."""
    ACCURATE = "accurate"
    PARTIALLY_ACCURATE = "partially_accurate"
    INACCURATE = "inaccurate"
    MISLEADING = "misleading"
    REFUSED = "refused"


# F-ACC-002: Jurisdiction format validation (ISO 3166-1 alpha-2)
ISO_3166_PATTERN = re.compile(r'^[A-Z]{2}$')


def validate_jurisdiction(value: str) -> str:
    """Validate ISO 3166-1 alpha-2 jurisdiction code."""
    if not ISO_3166_PATTERN.match(value):
        raise ValueError(
            f"jurisdiction must be ISO 3166-1 alpha-2 (e.g. 'DE', 'US'), got '{value}'"
        )
    return value


# F-ACC-002: Threshold validation (0.0 to 1.0)
def validate_threshold(value: float) -> float:
    """Validate passing threshold is in [0.0, 1.0]."""
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"passing_threshold must be in [0.0, 1.0], got {value}")
    return value


@dataclass(frozen=True)
class CriterionScore:
    """Score for a single evaluation criterion."""
    criterion: EvaluationCriterion
    score: float  # 0.0 - 1.0
    max_score: float = 1.0
    explanation: str = ""
    evidence: List[str] = None

    def __post_init__(self):
        if self.evidence is None:
            object.__setattr__(self, "evidence", [])
        if not 0.0 <= self.score <= 1.0:
            raise ValueError(f"score must be in [0.0, 1.0], got {self.score}")
        if self.max_score <= 0:
            raise ValueError(f"max_score must be > 0, got {self.max_score}")

    @property
    def percentage(self) -> float:
        """Score as percentage."""
        return (self.score / self.max_score) * 100

    @property
    def level(self) -> AccuracyLevel:
        """Accuracy level for this criterion."""
        return AccuracyLevel.from_score(self.score / self.max_score)

    def to_dict(self) -> dict:
        return {
            "criterion": self.criterion.value,
            "score": self.score,
            "max_score": self.max_score,
            "percentage": self.percentage,
            "level": self.level.value,
            "explanation": self.explanation,
            "evidence": self.evidence,
        }
