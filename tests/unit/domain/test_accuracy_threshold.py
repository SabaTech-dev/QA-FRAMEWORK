"""Threshold threading: AccuracyBenchmark.passing_threshold must be honoured.

compute_overall() hardcoded 0.6, making the per-benchmark config dead. The
evaluator must thread benchmark.passing_threshold into the pass decision.
"""

from src.domain.accuracy_testing.entities import AccuracyBenchmark, AccuracyEvaluation
from src.domain.accuracy_testing.splitting import split_benchmarks
from src.infrastructure.accuracy_testing.rule_based_evaluator import RuleBasedAccuracyEvaluator


def _benchmark(threshold: float) -> AccuracyBenchmark:
    return AccuracyBenchmark(
        id="bench-threshold",
        question="What is the liability regime for AI products in Germany?",
        ground_truth="Strict liability under the Produkthaftungsgesetz...",
        passing_threshold=threshold,
    )


def _evaluation_with_score(overall: float) -> AccuracyEvaluation:
    from src.domain.accuracy_testing.value_objects import CriterionScore, EvaluationCriterion

    return AccuracyEvaluation(
        benchmark_id="bench-threshold",
        criterion_scores=[
            CriterionScore(
                criterion=EvaluationCriterion.FACTUAL_ACCURACY,
                score=overall,
                explanation="unit-test score",
            )
        ],
    )


class TestComputeOverallThreshold:
    def test_high_threshold_fails_mid_score(self):
        """Score 0.7 vs threshold 0.8 must NOT pass (0.6 hardcode would pass it)."""
        ev = _evaluation_with_score(0.7)
        result = ev.compute_overall(passing_threshold=0.8)
        assert result.passed is False

    def test_default_threshold_keeps_legacy_behaviour(self):
        """Backwards compat: no threshold arg -> 0.6 boundary semantics."""
        assert _evaluation_with_score(0.7).compute_overall().passed is True
        assert _evaluation_with_score(0.5).compute_overall().passed is False

    def test_evaluator_respects_benchmark_threshold(self):
        """End-to-end threading: evaluator passes benchmark.passing_threshold."""
        bench = _benchmark(threshold=0.95)
        evaluator = RuleBasedAccuracyEvaluator()
        evaluation = evaluator.evaluate(bench, "some response", "test-model")
        computed = evaluation.compute_overall()
        assert computed.passed == (computed.overall_score >= 0.95)

    def test_split_preserves_benchmark_threshold(self):
        """The split must not lose the threshold config along the way."""
        bench = _benchmark(threshold=0.9)
        split = split_benchmarks([bench], SplitPolicyForTest.salt_only())
        # Single benchmark -> everything eval, threshold intact
        assert split.eval_benchmarks[0].passing_threshold == 0.9


class SplitPolicyForTest:
    @staticmethod
    def salt_only():
        from src.domain.accuracy_testing.splitting import SplitPolicy

        return SplitPolicy(holdout_ratio=0.2, salt="unit-test")
