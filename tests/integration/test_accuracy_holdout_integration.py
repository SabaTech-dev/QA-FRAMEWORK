"""
Integration tests: Holdout benchmark flow (F-ACC-006)

Full pipeline with the real German AI liability benchmarks and the real
rule-based evaluator:

  benchmarks -> split (eval/holdout) -> eval-set session evaluations
            -> holdout via HoldoutEvaluationService (aggregates only)
            -> session with holdout_summary -> public to_dict()

Verifies the anti-gaming contract end to end: the serialized session is
JSON-safe and contains NO ground truth for any benchmark and NO content
(question/response) for any holdout benchmark.
"""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.domain.accuracy_testing.entities import AccuracyTestSession
from src.domain.accuracy_testing.holdout_service import HoldoutEvaluationService
from src.domain.accuracy_testing.splitting import SplitPolicy, split_benchmarks
from src.infrastructure.accuracy_testing.german_ai_liability_benchmarks import (
    create_german_ai_liability_benchmarks,
)
from src.infrastructure.accuracy_testing.rule_based_evaluator import RuleBasedAccuracyEvaluator


class ScriptedProvider:
    """Replays one canned response per benchmark, keyed by question."""

    def __init__(self, answers: dict[str, str], default: str = ""):
        self.answers = answers
        self.default = default
        self.prompts_seen: list[str] = []

    def get_response(self, prompt: str, model: str = "") -> str:
        self.prompts_seen.append(prompt)
        return self.answers.get(prompt, self.default)


def _build_answers(benchmarks, quality: str) -> dict[str, str]:
    """Build a response per benchmark: good answers echo key points."""
    answers = {}
    for b in benchmarks:
        if quality == "good":
            answers[b.question] = (
                f"{b.ground_truth} According to the court ruling, {b.name}: "
                + " ".join(b.key_points)
                + " However, this may depend on the specific case."
            )
        else:
            answers[b.question] = "I have no idea."
    return answers


@pytest.mark.integration
class TestHoldoutFullFlow:
    def test_end_to_end_split_eval_and_holdout(self):
        benchmarks = create_german_ai_liability_benchmarks()
        assert len(benchmarks) >= 4  # module ships enough cases to split

        # 1. Deterministic split
        policy = SplitPolicy(holdout_ratio=0.3, salt="integration")
        split = split_benchmarks(benchmarks, policy)
        assert split.holdout_count + split.eval_count == len(benchmarks)
        assert split.holdout_count >= 1

        # 2. Re-splitting is stable
        split_again = split_benchmarks(benchmarks, policy)
        assert {b.id for b in split_again.holdout_benchmarks} == {
            b.id for b in split.holdout_benchmarks
        }

        # 3. Eval-set session with the real rule-based evaluator
        evaluator = RuleBasedAccuracyEvaluator()
        provider = ScriptedProvider(_build_answers(benchmarks, "good"))
        session = AccuracyTestSession(
            name="beta-verification",
            ai_model="test-model",
            total_benchmarks=split.eval_count,
        )
        for bench in split.eval_benchmarks:
            response = provider.get_response(bench.question)
            evaluation = evaluator.evaluate(bench, response, ai_model="test-model")
            session = session.add_evaluation(evaluation)
        session = session.complete()
        assert session.evaluations_completed == split.eval_count

        # 4. Holdout run: aggregates only
        service = HoldoutEvaluationService(evaluator=evaluator)
        summary = service.run_holdout(split, provider, ai_model="test-model")
        assert summary.holdout_count == split.holdout_count
        assert 0.0 <= summary.pass_rate <= 1.0

        session = session.with_holdout_summary(summary)

        # 5. Anti-leak contract on the public payload
        payload = json.dumps(session.to_dict())
        for b in benchmarks:
            assert b.ground_truth not in payload  # F-ACC-004 (all benchmarks)
        # F-ACC-006: holdout questions/answers never appear. Eval-set prompts
        # are visible BY DESIGN (dev iteration set) — only holdout is sealed.
        for b in split.holdout_benchmarks:
            assert b.question not in payload
        for answer in _build_answers(split.holdout_benchmarks, "good").values():
            assert answer not in payload

        # 6. Summary shape: aggregate keys only
        holdout_dict = session.to_dict()["holdout_summary"]
        assert set(holdout_dict.keys()) == {
            "holdout_count",
            "pass_rate",
            "average_score",
            "hallucination_count",
            "accuracy_level",
            "evaluated_at",
        }

    def test_holdout_summary_differs_from_eval_on_degenerate_answers(self):
        """A model that only memorized the eval set fails the holdout.

        This is the core anti-overfitting scenario: perfect answers for the
        eval set, nonsense for the holdout — the aggregate summary must
        reflect the drop.
        """
        benchmarks = create_german_ai_liability_benchmarks()
        policy = SplitPolicy(holdout_ratio=0.3, salt="integration")
        split = split_benchmarks(benchmarks, policy)

        evaluator = RuleBasedAccuracyEvaluator()

        good_eval_answers = _build_answers(split.eval_benchmarks, "good")
        overfit_provider = ScriptedProvider(
            {**good_eval_answers},  # memorized eval answers only
            default="I have no idea.",  # holdout: nonsense
        )

        service = HoldoutEvaluationService(evaluator=evaluator)
        summary = service.run_holdout(split, overfit_provider)

        assert summary.holdout_count == split.holdout_count
        # Nonsense answers on the holdout must yield a poor aggregate score
        assert summary.average_score < 0.5

        # Eval-set session with the same provider scores much higher:
        session = AccuracyTestSession(name="overfit-demo", total_benchmarks=split.eval_count)
        for bench in split.eval_benchmarks:
            response = overfit_provider.get_response(bench.question)
            session = session.add_evaluation(
                evaluator.evaluate(bench, response, ai_model="memorizer")
            )
        assert session.average_score > summary.average_score

    def test_split_payload_is_ui_safe(self):
        """BenchmarkSplit serialization: counts only, no content."""
        benchmarks = create_german_ai_liability_benchmarks()
        split = split_benchmarks(benchmarks, SplitPolicy(holdout_ratio=0.3))

        dumped = json.dumps(split.to_dict())
        assert "eval_count" in dumped
        for b in benchmarks:
            assert b.question not in dumped
            assert b.ground_truth not in dumped
            assert b.id not in dumped

        # __repr__ safe for logs too
        r = repr(split)
        for b in benchmarks:
            assert b.question not in r
            assert b.id not in r
