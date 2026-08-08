"""
AI Accuracy Testing Domain Module

Evaluates AI response accuracy against legal/regulatory benchmarks,
starting with the German AI Liability ruling (BGH, 2025).

Provides:
- Structured accuracy evaluation of AI outputs
- Scoring against legal/regulatory criteria
- Benchmark sessions for batch evaluation
"""

from .value_objects import (
    EvaluationCriterion,
    AccuracyLevel,
    EvaluationStatus,
    LegalDomain,
    ResponseVerdict,
    CriterionScore,
    validate_jurisdiction,
    validate_threshold,
    MAX_EVAL_INPUT_LENGTH,
)
from .entities import (
    AccuracyEvaluation,
    AccuracyBenchmark,
    AccuracyTestSession,
)
from .interfaces import (
    IAccuracyEvaluator,
    IResponseProvider,
    IBenchmarkRepository,
)

__all__ = [
    # Value Objects
    "EvaluationCriterion",
    "AccuracyLevel",
    "EvaluationStatus",
    "LegalDomain",
    "ResponseVerdict",
    "CriterionScore",
    "validate_jurisdiction",
    "validate_threshold",
    "MAX_EVAL_INPUT_LENGTH",
    # Entities
    "AccuracyEvaluation",
    "AccuracyBenchmark",
    "AccuracyTestSession",
    # Interfaces
    "IAccuracyEvaluator",
    "IResponseProvider",
    "IBenchmarkRepository",
]
