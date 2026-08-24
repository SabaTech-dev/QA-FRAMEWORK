"""
Holdout Evaluation Service (F-ACC-006)

Runs an accuracy evaluation over the HOLDOUT subset of a benchmark split
and returns aggregate metrics only.

Anti-gaming design: per-item results (questions, AI responses, scores,
verdicts) are consumed to compute aggregates and then DISCARDED — they are
never stored, returned, logged, or serialized. Only a HoldoutSummary
(counts and rates) leaves this service, so neither UI payloads nor
execution logs can reveal holdout content that could be tuned against.
"""

from __future__ import annotations

from datetime import UTC, datetime

from .interfaces import IAccuracyEvaluator, IResponseProvider
from .splitting import BenchmarkSplit, HoldoutSummary


class HoldoutEvaluationService:
    """
    Domain service: evaluate holdout benchmarks, keep aggregates only.

    Depends exclusively on domain abstractions (IAccuracyEvaluator,
    IResponseProvider protocols), following the module's clean architecture.
    """

    def __init__(self, evaluator: IAccuracyEvaluator):
        self._evaluator = evaluator

    def run_holdout(
        self,
        split: BenchmarkSplit,
        response_provider: IResponseProvider,
        ai_model: str = "",
    ) -> HoldoutSummary:
        """
        Evaluate every holdout benchmark and aggregate the results.

        Args:
            split: benchmark split; only holdout_benchmarks are evaluated.
            response_provider: supplies AI responses for holdout questions.
            ai_model: model identifier recorded in evaluations.

        Returns:
            HoldoutSummary with aggregate metrics. Per-item evaluations are
            intentionally discarded after aggregation (F-ACC-006).
        """
        holdout: list = split.holdout_benchmarks
        if not holdout:
            return HoldoutSummary.empty()

        count = 0
        passed = 0
        score_sum = 0.0
        hallucinations = 0

        for benchmark in holdout:
            response = response_provider.get_response(benchmark.question, ai_model)
            evaluation = self._evaluator.evaluate(benchmark, response, ai_model)

            count += 1
            if evaluation.passed:
                passed += 1
            score_sum += evaluation.overall_score
            if evaluation.has_hallucinations:
                hallucinations += 1
            # F-ACC-006: `evaluation` (with question, response, per-item
            # scores) is NOT retained beyond this loop iteration.

        return HoldoutSummary(
            holdout_count=count,
            pass_rate=passed / count,
            average_score=score_sum / count,
            hallucination_count=hallucinations,
            evaluated_at=datetime.now(UTC),
        )
