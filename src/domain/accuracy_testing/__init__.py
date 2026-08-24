"""
AI Accuracy Testing Domain Module

Evaluates AI response accuracy against legal/regulatory benchmarks,
starting with the German AI Liability ruling (BGH, 2025).

Provides:
- Structured accuracy evaluation of AI outputs
- Scoring against legal/regulatory criteria
- Benchmark sessions for batch evaluation
"""

from .entities import AccuracyBenchmark, AccuracyEvaluation, AccuracyTestSession
from .holdout_service import HoldoutEvaluationService
from .interfaces import IAccuracyEvaluator, IBenchmarkRepository, IResponseProvider
from .splitting import BenchmarkSplit, HoldoutSummary, SplitPolicy, split_benchmarks
from .value_objects import (
    MAX_EVAL_INPUT_LENGTH,
    AccuracyLevel,
    CriterionScore,
    EvaluationCriterion,
    EvaluationStatus,
    LegalDomain,
    ResponseVerdict,
    validate_jurisdiction,
    validate_threshold,
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
    # Splitting (F-ACC-006)
    "SplitPolicy",
    "BenchmarkSplit",
    "HoldoutSummary",
    "split_benchmarks",
    # Entities
    "AccuracyEvaluation",
    "AccuracyBenchmark",
    "AccuracyTestSession",
    # Interfaces
    "IAccuracyEvaluator",
    "IResponseProvider",
    "IBenchmarkRepository",
    # Services
    "HoldoutEvaluationService",
]
