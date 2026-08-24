"""
Tests for Holdout Benchmark Support - Accuracy Testing (F-ACC-006)

Anti-overfitting design (ref: Dan Luu's agent that overfit the benchmark to
the holdout; HF study: 6/11 ASR models memorize public test sets):

- Deterministic eval/holdout split with configurable policy
- Holdout content (questions, ground truth, per-item results) is NEVER
  serialized: only aggregate counts/metrics are exposed
- HoldoutSummary carries aggregate metrics only
- HoldoutEvaluationService discards per-item results after aggregation
- Session exposes holdout only as an aggregate summary
"""

import json
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from src.domain.accuracy_testing.entities import (
    AccuracyBenchmark,
    AccuracyEvaluation,
    AccuracyTestSession,
)
from src.domain.accuracy_testing.holdout_service import HoldoutEvaluationService
from src.domain.accuracy_testing.splitting import (
    BenchmarkSplit,
    HoldoutSummary,
    SplitPolicy,
    split_benchmarks,
)
from src.domain.accuracy_testing.value_objects import LegalDomain

# ========================================================================
# Helpers
# ========================================================================


def make_benchmarks(n: int, prefix: str = "bench") -> list[AccuracyBenchmark]:
    """Create n distinct benchmarks with unique ids and marker content."""
    out = []
    for i in range(n):
        out.append(
            AccuracyBenchmark(
                id=f"{prefix}-{i:03d}-{uuid4().hex[:8]}",
                name=f"Benchmark {i}",
                question=f"SECRET-QUESTION-{prefix}-{i}?",
                ground_truth=f"SECRET-TRUTH-{prefix}-{i}",
                key_points=[f"secret point {i}"],
                legal_domain=LegalDomain.AI_LIABILITY,
                jurisdiction="DE",
            )
        )
    return out


class StubEvaluator:
    """Deterministic stub evaluator: passed iff response echoes the truth."""

    def evaluate(self, benchmark, ai_response, ai_model=""):
        passed = benchmark.ground_truth in ai_response
        score = 0.9 if passed else 0.1
        from src.domain.accuracy_testing.value_objects import CriterionScore, EvaluationCriterion

        ev = AccuracyEvaluation(
            benchmark_id=benchmark.id,
            prompt=benchmark.question,
            ai_response=ai_response,
            criterion_scores=[
                CriterionScore(
                    criterion=EvaluationCriterion.FACTUAL_ACCURACY,
                    score=score,
                )
            ],
            ai_model=ai_model,
        )
        return ev.compute_overall()


class HallucinatingStubEvaluator(StubEvaluator):
    """Marks every failed evaluation as containing hallucinations."""

    def evaluate(self, benchmark, ai_response, ai_model=""):
        ev = super().evaluate(benchmark, ai_response, ai_model)
        if not ev.passed:
            ev.hallucinations = ["invented legal reference"]
        return ev


class RecordingProvider:
    """Records every prompt it receives; returns canned answers."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.prompts_seen: list[str] = []

    def get_response(self, prompt, model=""):
        self.prompts_seen.append(prompt)
        return self.responses.pop(0) if self.responses else ""


# ========================================================================
# SplitPolicy
# ========================================================================


class TestSplitPolicy:
    def test_defaults(self):
        p = SplitPolicy()
        assert p.holdout_ratio == 0.2
        assert p.salt == ""
        assert p.min_eval_size == 1
        assert p.min_holdout_size == 1

    def test_custom_values(self):
        p = SplitPolicy(holdout_ratio=0.3, salt="tenant-42", min_eval_size=4, min_holdout_size=2)
        assert p.holdout_ratio == 0.3
        assert p.salt == "tenant-42"

    @pytest.mark.parametrize("bad_ratio", [0.0, -0.1, 1.0, 1.5])
    def test_ratio_must_be_open_interval(self, bad_ratio):
        with pytest.raises(ValueError):
            SplitPolicy(holdout_ratio=bad_ratio)

    @pytest.mark.parametrize("bad_min", [0, -1])
    def test_min_sizes_must_be_positive(self, bad_min):
        with pytest.raises(ValueError):
            SplitPolicy(min_eval_size=bad_min)
        with pytest.raises(ValueError):
            SplitPolicy(min_holdout_size=bad_min)

    def test_frozen(self):
        p = SplitPolicy()
        with pytest.raises(AttributeError):
            p.holdout_ratio = 0.5


# ========================================================================
# split_benchmarks — determinism & invariants
# ========================================================================


class TestSplitBenchmarks:
    def test_split_covers_all_benchmarks_exactly_once(self):
        benches = make_benchmarks(10)
        policy = SplitPolicy(holdout_ratio=0.2)
        split = split_benchmarks(benches, policy)

        all_ids = [b.id for b in split.eval_benchmarks] + [b.id for b in split.holdout_benchmarks]
        assert sorted(all_ids) == sorted(b.id for b in benches)
        assert len(all_ids) == len(set(all_ids))  # no benchmark in both subsets

    def test_exact_ratio_on_large_set(self):
        benches = make_benchmarks(20)
        split = split_benchmarks(benches, SplitPolicy(holdout_ratio=0.2))
        assert len(split.holdout_benchmarks) == 4
        assert len(split.eval_benchmarks) == 16

    def test_deterministic_same_input_same_output(self):
        benches = make_benchmarks(15)
        policy = SplitPolicy(holdout_ratio=0.2, salt="abc")
        s1 = split_benchmarks(benches, policy)
        s2 = split_benchmarks(benches, policy)
        assert [b.id for b in s1.holdout_benchmarks] == [b.id for b in s2.holdout_benchmarks]
        assert [b.id for b in s1.eval_benchmarks] == [b.id for b in s2.eval_benchmarks]

    def test_deterministic_across_instance_ordering(self):
        """Re-creating identical benchmarks (same ids) yields the same split."""
        benches = make_benchmarks(12)
        same_ids = [
            AccuracyBenchmark(
                id=b.id, name=b.name, question=b.question, ground_truth=b.ground_truth
            )
            for b in benches
        ]
        policy = SplitPolicy(holdout_ratio=0.25)
        s1 = split_benchmarks(benches, policy)
        s2 = split_benchmarks(same_ids, policy)
        assert {b.id for b in s1.holdout_benchmarks} == {b.id for b in s2.holdout_benchmarks}

    def test_uses_sha256_not_native_hash(self):
        """Split must be reproducible across processes: sha256-based bucketing.

        We re-implement the expected ordering with hashlib and check the
        holdout membership matches.
        """
        import hashlib

        benches = make_benchmarks(10)
        policy = SplitPolicy(holdout_ratio=0.2, salt="xyz")
        split = split_benchmarks(benches, policy)

        expected_order = sorted(
            benches,
            key=lambda b: (hashlib.sha256(f"xyz:{b.id}".encode()).hexdigest(), b.id),
        )
        expected_holdout = {b.id for b in expected_order[:2]}
        assert {b.id for b in split.holdout_benchmarks} == expected_holdout

    def test_different_salt_different_split(self):
        benches = make_benchmarks(30)
        s1 = split_benchmarks(benches, SplitPolicy(holdout_ratio=0.2, salt="a"))
        s2 = split_benchmarks(benches, SplitPolicy(holdout_ratio=0.2, salt="b"))
        assert {b.id for b in s1.holdout_benchmarks} != {b.id for b in s2.holdout_benchmarks}

    def test_fewer_than_two_benchmarks_all_eval(self):
        benches = make_benchmarks(1)
        split = split_benchmarks(benches, SplitPolicy())
        assert len(split.eval_benchmarks) == 1
        assert len(split.holdout_benchmarks) == 0

    def test_empty_input(self):
        split = split_benchmarks([], SplitPolicy())
        assert split.eval_benchmarks == []
        assert split.holdout_benchmarks == []

    def test_min_sizes_respected(self):
        benches = make_benchmarks(4)
        split = split_benchmarks(
            benches,
            SplitPolicy(holdout_ratio=0.5, min_eval_size=3, min_holdout_size=1),
        )
        assert len(split.eval_benchmarks) >= 3
        assert len(split.holdout_benchmarks) >= 1

    def test_infeasible_constraints_raise(self):
        benches = make_benchmarks(3)
        with pytest.raises(ValueError):
            split_benchmarks(
                benches,
                SplitPolicy(holdout_ratio=0.5, min_eval_size=2, min_holdout_size=2),
            )

    def test_duplicate_benchmark_ids_rejected(self):
        b = make_benchmarks(1)[0]
        with pytest.raises(ValueError):
            split_benchmarks([b, b], SplitPolicy())


# ========================================================================
# BenchmarkSplit — redaction (F-ACC-006)
# ========================================================================


class TestBenchmarkSplitRedaction:
    def test_to_dict_contains_only_counts(self):
        benches = make_benchmarks(10)
        split = split_benchmarks(benches, SplitPolicy(holdout_ratio=0.2))
        d = split.to_dict()
        assert d == {
            "eval_count": 8,
            "holdout_count": 2,
            "holdout_ratio": 0.2,
        }

    def test_to_dict_leaks_no_holdout_content(self):
        benches = make_benchmarks(10)
        split = split_benchmarks(benches, SplitPolicy(holdout_ratio=0.3))
        dumped = json.dumps(split.to_dict())
        for b in benches:
            assert b.question not in dumped
            assert b.ground_truth not in dumped
            assert b.id not in dumped

    def test_repr_is_redacted(self):
        benches = make_benchmarks(6)
        split = split_benchmarks(benches, SplitPolicy(holdout_ratio=0.2))
        r = repr(split)
        assert "eval_count=" in r
        assert "holdout_count=" in r
        for b in benches:
            assert b.question not in r
            assert b.ground_truth not in r
            assert b.id not in r

    def test_counts_properties(self):
        benches = make_benchmarks(5)
        split = split_benchmarks(benches, SplitPolicy(holdout_ratio=0.2))
        assert split.eval_count == len(split.eval_benchmarks)
        assert split.holdout_count == len(split.holdout_benchmarks)


class TestBenchmarkSplitConstructionInvariants:
    """Direct construction must enforce the same contract as split_benchmarks."""

    def test_duplicate_eval_ids_rejected(self):
        b = make_benchmarks(1)[0]
        with pytest.raises(ValueError, match="Duplicate benchmark ids in eval"):
            BenchmarkSplit(eval_benchmarks=[b, b])

    def test_duplicate_holdout_ids_rejected(self):
        b = make_benchmarks(1)[0]
        with pytest.raises(ValueError, match="Duplicate benchmark ids in holdout"):
            BenchmarkSplit(holdout_benchmarks=[b, b])

    def test_overlapping_sets_rejected(self):
        b = make_benchmarks(1)[0]
        other = make_benchmarks(1)[0]
        with pytest.raises(ValueError, match="disjoint"):
            BenchmarkSplit(eval_benchmarks=[b], holdout_benchmarks=[b, other])

    def test_holdout_below_policy_minimum_rejected(self):
        b = make_benchmarks(1)[0]
        other = make_benchmarks(1)[0]
        policy = SplitPolicy(min_holdout_size=2)
        with pytest.raises(ValueError, match="below policy minimum"):
            BenchmarkSplit(eval_benchmarks=[b], holdout_benchmarks=[other], policy=policy)

    def test_eval_below_policy_minimum_rejected(self):
        benches = make_benchmarks(2)
        policy = SplitPolicy(min_eval_size=2)
        with pytest.raises(ValueError, match="below policy minimum"):
            BenchmarkSplit(
                eval_benchmarks=[benches[0]], holdout_benchmarks=[benches[1]], policy=policy
            )

    def test_empty_holdout_allowed_regardless_of_minimum(self):
        b = make_benchmarks(1)[0]
        split = BenchmarkSplit(eval_benchmarks=[b], policy=SplitPolicy(min_holdout_size=2))
        assert split.holdout_count == 0


# ========================================================================
# HoldoutSummary
# ========================================================================


class TestHoldoutSummary:
    def test_properties_and_level(self):
        s = HoldoutSummary(
            holdout_count=10,
            pass_rate=0.8,
            average_score=0.85,
            hallucination_count=1,
            evaluated_at=datetime.now(timezone.utc),
        )
        assert s.accuracy_level.value == "good"
        assert s.holdout_count == 10

    def test_to_dict_aggregates_only(self):
        s = HoldoutSummary(
            holdout_count=5,
            pass_rate=0.6,
            average_score=0.7,
            hallucination_count=0,
            evaluated_at=datetime(2026, 8, 23, 12, 0, tzinfo=timezone.utc),
        )
        d = s.to_dict()
        assert set(d.keys()) == {
            "holdout_count",
            "pass_rate",
            "average_score",
            "hallucination_count",
            "accuracy_level",
            "evaluated_at",
        }

    def test_empty_summary(self):
        s = HoldoutSummary.empty()
        assert s.holdout_count == 0
        assert s.pass_rate == 0.0
        assert s.is_empty

    @pytest.mark.parametrize(
        "bad", [(-0.1, 0.5, 0, 0), (0.5, -0.1, 0, 0), (0.5, 0.5, -1, 0), (0.5, 0.5, 0, -1)]
    )
    def test_invalid_values_rejected(self, bad):
        with pytest.raises(ValueError):
            HoldoutSummary(
                holdout_count=bad[2],
                pass_rate=bad[0],
                average_score=bad[1],
                hallucination_count=bad[3],
                evaluated_at=datetime.now(timezone.utc),
            )

    def test_frozen(self):
        s = HoldoutSummary.empty()
        with pytest.raises(AttributeError):
            s.pass_rate = 0.9


# ========================================================================
# HoldoutEvaluationService
# ========================================================================


class TestHoldoutEvaluationService:
    def _make_split(self, n=10):
        benches = make_benchmarks(n, prefix="hold")
        return benches, split_benchmarks(benches, SplitPolicy(holdout_ratio=0.2))

    def test_returns_aggregate_summary(self):
        _, split = self._make_split()
        provider = RecordingProvider(responses=[])
        service = HoldoutEvaluationService(evaluator=StubEvaluator())
        summary = service.run_holdout(split, provider)
        assert isinstance(summary, HoldoutSummary)
        assert summary.holdout_count == len(split.holdout_benchmarks)
        assert 0.0 <= summary.average_score <= 1.0

    def test_summary_math_is_correct(self):
        _, split = self._make_split(10)
        holdout_benches = split.holdout_benchmarks
        # Provider answers half correctly (echo ground truth), half wrongly
        responses = [
            b.ground_truth if i % 2 == 0 else "totally wrong answer"
            for i, b in enumerate(holdout_benches)
        ]
        provider = RecordingProvider(responses=responses)
        service = HoldoutEvaluationService(evaluator=StubEvaluator())
        summary = service.run_holdout(split, provider)

        expected_pass = sum(1 for i in range(len(holdout_benches)) if i % 2 == 0)
        assert summary.holdout_count == len(holdout_benches)
        assert summary.pass_rate == pytest.approx(expected_pass / len(holdout_benches))
        expected_avg = (0.9 * expected_pass + 0.1 * (len(holdout_benches) - expected_pass)) / len(
            holdout_benches
        )
        assert summary.average_score == pytest.approx(expected_avg)

    def test_evaluates_only_holdout_questions(self):
        _, split = self._make_split(10)
        provider = RecordingProvider(responses=["x"] * len(split.holdout_benchmarks))
        service = HoldoutEvaluationService(evaluator=StubEvaluator())
        service.run_holdout(split, provider)

        holdout_questions = {b.question for b in split.holdout_benchmarks}
        eval_questions = {b.question for b in split.eval_benchmarks}
        assert set(provider.prompts_seen) == holdout_questions
        assert not (set(provider.prompts_seen) & eval_questions)

    def test_summary_and_dict_leak_no_content(self):
        benches, split = self._make_split(10)
        provider = RecordingProvider(responses=["SECRET-AI-ANSWER"] * len(split.holdout_benchmarks))
        service = HoldoutEvaluationService(evaluator=StubEvaluator())
        summary = service.run_holdout(split, provider)

        dumped = json.dumps(summary.to_dict())
        for b in benches:
            assert b.question not in dumped
            assert b.ground_truth not in dumped
        assert "SECRET-AI-ANSWER" not in dumped

    def test_empty_holdout_returns_zero_summary(self):
        benches = make_benchmarks(1)
        split = split_benchmarks(benches, SplitPolicy())
        service = HoldoutEvaluationService(evaluator=StubEvaluator())
        summary = service.run_holdout(split, RecordingProvider([]))
        assert summary.holdout_count == 0
        assert summary.pass_rate == 0.0

    def test_hallucination_count_aggregated(self):
        benches = make_benchmarks(10)
        split = split_benchmarks(benches, SplitPolicy(holdout_ratio=0.4))
        # Every answer wrong -> every holdout evaluation hallucinates
        provider = RecordingProvider(responses=["wrong"] * len(split.holdout_benchmarks))
        service = HoldoutEvaluationService(evaluator=HallucinatingStubEvaluator())
        summary = service.run_holdout(split, provider)
        assert summary.hallucination_count == len(split.holdout_benchmarks)
        assert summary.pass_rate == 0.0

    def test_service_does_not_log_content(self, capsys):
        """The service module must not print/write holdout content anywhere."""
        _, split = self._make_split(10)
        provider = RecordingProvider(responses=["answer"] * len(split.holdout_benchmarks))
        service = HoldoutEvaluationService(evaluator=StubEvaluator())
        service.run_holdout(split, provider)
        captured = capsys.readouterr()
        combined = captured.out + captured.err
        for b in split.holdout_benchmarks:
            assert b.question not in combined
            assert b.ground_truth not in combined


# ========================================================================
# Session integration (F-ACC-006)
# ========================================================================


class TestSessionHoldoutIntegration:
    def test_with_holdout_summary_immutable(self):
        session = AccuracyTestSession(name="s")
        summary = HoldoutSummary(
            holdout_count=2,
            pass_rate=1.0,
            average_score=0.95,
            hallucination_count=0,
            evaluated_at=datetime.now(timezone.utc),
        )
        updated = session.with_holdout_summary(summary)
        assert updated is not session
        assert updated.holdout_summary is summary
        assert session.holdout_summary is None

    def test_summary_propagates_through_add_evaluation(self):
        summary = HoldoutSummary(
            holdout_count=1,
            pass_rate=1.0,
            average_score=1.0,
            hallucination_count=0,
            evaluated_at=datetime.now(timezone.utc),
        )
        session = AccuracyTestSession(name="s").with_holdout_summary(summary)
        ev = AccuracyEvaluation(benchmark_id="b1")
        session2 = session.add_evaluation(ev)
        assert session2.holdout_summary is summary

    def test_summary_propagates_through_complete(self):
        summary = HoldoutSummary(
            holdout_count=1,
            pass_rate=0.0,
            average_score=0.2,
            hallucination_count=0,
            evaluated_at=datetime.now(timezone.utc),
        )
        session = AccuracyTestSession(name="s").with_holdout_summary(summary)
        done = session.complete()
        assert done.holdout_summary is summary

    def test_session_to_dict_holdout_aggregates_only(self):
        benches = make_benchmarks(10)
        split = split_benchmarks(benches, SplitPolicy(holdout_ratio=0.2))
        provider = RecordingProvider(responses=["ans"] * len(split.holdout_benchmarks))
        service = HoldoutEvaluationService(evaluator=StubEvaluator())
        summary = service.run_holdout(split, provider)

        session = AccuracyTestSession(name="verification").with_holdout_summary(summary)
        d = session.to_dict()

        assert "holdout_summary" in d
        assert set(d["holdout_summary"].keys()) == {
            "holdout_count",
            "pass_rate",
            "average_score",
            "hallucination_count",
            "accuracy_level",
            "evaluated_at",
        }

    def test_session_to_dict_leaks_no_holdout_content(self):
        benches = make_benchmarks(10)
        split = split_benchmarks(benches, SplitPolicy(holdout_ratio=0.3))
        provider = RecordingProvider(
            responses=["SECRET-HOLDOUT-ANSWER"] * len(split.holdout_benchmarks)
        )
        service = HoldoutEvaluationService(evaluator=StubEvaluator())
        summary = service.run_holdout(split, provider)

        session = AccuracyTestSession(name="verification").with_holdout_summary(summary)
        dumped = json.dumps(session.to_dict())

        for b in split.holdout_benchmarks:
            assert b.question not in dumped
            assert b.ground_truth not in dumped
        assert "SECRET-HOLDOUT-ANSWER" not in dumped
        # Full view must not leak either
        dumped_full = json.dumps(session.to_dict_full())
        assert "SECRET-HOLDOUT-ANSWER" not in dumped_full
