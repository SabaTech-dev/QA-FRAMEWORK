"""
Extended QA Tests for Accuracy Testing Module — German AI Liability

Covers:
1. Funcional: per-benchmark evaluation for each of the 4 BGH benchmarks
2. Validación: additional edge cases (NaN, None, special chars)
3. ReDoS: regex-bomb patterns beyond 10K chars
4. Inmutabilidad: compute_overall + add_evaluation immutability
5. Data leak: thorough to_dict audit for sensitive fields
6. Integración: module import paths
"""

import math
import pytest
from datetime import datetime, timezone

from src.domain.accuracy_testing.value_objects import (
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
from src.domain.accuracy_testing.entities import (
    AccuracyEvaluation,
    AccuracyBenchmark,
    AccuracyTestSession,
)
from src.infrastructure.accuracy_testing.rule_based_evaluator import RuleBasedAccuracyEvaluator
from src.infrastructure.accuracy_testing.german_ai_liability_benchmarks import (
    create_german_ai_liability_benchmarks,
)


# ========================================================================
# 1. FUNCIONAL — Per-Benchmark Evaluation (4 BGH benchmarks)
# ========================================================================

class TestBenchmarkFunctional:
    """Each BGH benchmark evaluated with a response that targets its specific content."""

    @pytest.fixture
    def evaluator(self):
        return RuleBasedAccuracyEvaluator()

    @pytest.fixture
    def all_benchmarks(self):
        return create_german_ai_liability_benchmarks()

    @pytest.fixture
    def bench_de_ai_001(self, all_benchmarks):
        return all_benchmarks[0]  # Product Liability

    @pytest.fixture
    def bench_de_ai_002(self, all_benchmarks):
        return all_benchmarks[1]  # Burden of Proof

    @pytest.fixture
    def bench_de_ai_003(self, all_benchmarks):
        return all_benchmarks[2]  # User Due Diligence

    @pytest.fixture
    def bench_de_ai_004(self, all_benchmarks):
        return all_benchmarks[3]  # EU AI Act Interaction

    def test_de_ai_001_product_liability_pass(self, evaluator, bench_de_ai_001):
        """DE-AI-001: A response covering product liability key points should pass."""
        response = (
            "Under the BGH ruling VI ZR 67/24, AI outputs constitute a 'product' "
            "under the Produkthaftungsgesetz (ProdHaftG). The producer (Hersteller) "
            "bears strict liability under § 1 ProdHaftG for defective AI outputs. "
            "Protected legal interests include life, body, health, and property. "
            "This establishes precedent for AI product liability in Germany. "
            "However, liability may depend on the specific AI system involved."
        )
        result = evaluator.evaluate(bench_de_ai_001, response, "test-model")
        assert result.passed is True
        assert result.overall_score >= 0.5
        # Should have 5 criterion scores (FACTUAL, LEGAL, CITATION, COMPLETENESS, NUANCE)
        assert len(result.criterion_scores) == 5
        # Factual accuracy should be high (most key points covered)
        factual = next(s for s in result.criterion_scores if s.criterion == EvaluationCriterion.FACTUAL_ACCURACY)
        assert factual.score >= 0.5

    def test_de_ai_001_product_liability_fail(self, evaluator, bench_de_ai_001):
        """DE-AI-001: Irrelevant response should fail."""
        response = "The weather in Berlin is usually cold in winter."
        result = evaluator.evaluate(bench_de_ai_001, response)
        assert result.passed is False
        assert result.overall_score < 0.4

    def test_de_ai_002_burden_of_proof_pass(self, evaluator, bench_de_ai_002):
        """DE-AI-002: Response covering burden of proof reversal should pass."""
        response = (
            "The BGH ruling establishes that burden of proof reversal "
            "(Beweislastumkehr) applies in AI damage cases. Given AI opacity, "
            "the injured party cannot prove which defect caused damage. "
            "The producer must demonstrate the AI was not defective. "
            "This mirrors pharmaceutical liability under § 84 AMG and "
            "environmental liability principles. Consumer protection "
            "rationale underpins this reversal."
        )
        result = evaluator.evaluate(bench_de_ai_002, response)
        assert result.passed is True
        assert result.overall_score >= 0.4
        # Legal reasoning should be strong
        legal = next(s for s in result.criterion_scores if s.criterion == EvaluationCriterion.LEGAL_REASONING)
        assert legal.score >= 0.3

    def test_de_ai_002_burden_of_proof_partial(self, evaluator, bench_de_ai_002):
        """DE-AI-002: Partial response covering some but not all key points."""
        response = (
            "Burden of proof reversal may apply in AI cases. "
            "The producer might need to show the AI wasn't defective."
        )
        result = evaluator.evaluate(bench_de_ai_002, response)
        # Should have some score but incomplete
        assert 0.0 < result.overall_score < 0.9
        assert len(result.missing_points) > 0

    def test_de_ai_003_user_due_diligence_pass(self, evaluator, bench_de_ai_003):
        """DE-AI-003: Response covering user verification duties should pass."""
        response = (
            "Users have a duty of reasonable verification (Prüfungspflicht) of "
            "AI outputs. Blind reliance is not protected, especially in high-stakes "
            "domains. Verification scope depends on risk level, user expertise, "
            "and consequences. Under § 254 BGB, contributory negligence may reduce "
            "damages if verification duties were breached."
        )
        result = evaluator.evaluate(bench_de_ai_003, response)
        assert result.passed is True
        assert result.overall_score >= 0.4

    def test_de_ai_003_user_due_diligence_fail(self, evaluator, bench_de_ai_003):
        """DE-AI-003: Completely irrelevant response should fail."""
        response = "The color blue is a primary color in visual art."
        result = evaluator.evaluate(bench_de_ai_003, response)
        # Completeness should be very low (no key point keywords matched)
        completeness = next(s for s in result.criterion_scores if s.criterion == EvaluationCriterion.COMPLETENESS)
        assert completeness.score < 0.4

    def test_de_ai_004_eu_ai_act_pass(self, evaluator, bench_de_ai_004):
        """DE-AI-004: Response covering EU AI Act interaction should pass."""
        response = (
            "The BGH ruling and EU AI Act (Regulation 2024/1689) are complementary. "
            "The AI Act is ex ante regulation; the BGH ruling is ex post liability. "
            "AI Act compliance may evidence due diligence. Non-compliance may indicate "
            "a defect under ProdHaftG. High-risk AI systems face stricter liability. "
            "The upcoming EU AI Liability Directive will harmonize these rules."
        )
        result = evaluator.evaluate(bench_de_ai_004, response)
        assert result.passed is True
        assert result.overall_score >= 0.4
        # Citation should find Regulation 2024/1689
        citation = next(s for s in result.criterion_scores if s.criterion == EvaluationCriterion.CITATION_CORRECTNESS)
        assert citation.score >= 0.3

    def test_de_ai_004_eu_ai_act_partial(self, evaluator, bench_de_ai_004):
        """DE-AI-004: Response mentioning EU AI Act but missing interactions."""
        response = "The EU AI Act exists and regulates AI systems in Europe."
        result = evaluator.evaluate(bench_de_ai_004, response)
        assert result.overall_score < 0.8  # incomplete coverage

    def test_all_benchmarks_produce_valid_scores(self, evaluator, all_benchmarks):
        """Every benchmark produces valid criterion scores with no zeros in individual scores."""
        good_response = (
            "Under the BGH ruling VI ZR 67/24, AI outputs can be products under "
            "ProdHaftG § 1. The producer (Hersteller) bears strict liability. "
            "Burden of proof reversal applies due to AI opacity, mirroring § 84 AMG. "
            "Users have Prüfungspflicht; § 254 BGB contributory negligence may apply. "
            "The EU AI Act (Regulation 2024/1689) is complementary ex ante regulation. "
            "However, specifics depend on the case. Generally, compliance evidences "
            "due diligence. Pursuant to the ruling, non-compliance indicates defect."
        )
        for bench in all_benchmarks:
            result = evaluator.evaluate(bench, good_response, "qa-model")
            assert result.overall_score > 0.0, f"Zero score for {bench.name}"
            assert len(result.criterion_scores) == len(bench.criteria)
            for cs in result.criterion_scores:
                assert 0.0 <= cs.score <= 1.0, f"Score out of range in {bench.name}/{cs.criterion}"


# ========================================================================
# 2. VALIDACIÓN — Additional Edge Cases
# ========================================================================

class TestInputValidationExtended:
    """Additional validation edge cases beyond existing tests."""

    def test_nan_score_raises(self):
        """NaN is not a valid score."""
        with pytest.raises(ValueError):
            CriterionScore(
                criterion=EvaluationCriterion.FACTUAL_ACCURACY,
                score=float('nan'),
                explanation="test",
            )

    def test_inf_score_raises(self):
        """Infinity is not a valid score."""
        with pytest.raises(ValueError):
            CriterionScore(
                criterion=EvaluationCriterion.FACTUAL_ACCURACY,
                score=float('inf'),
                explanation="test",
            )

    def test_accuracy_level_from_nan_raises(self):
        with pytest.raises((ValueError, Exception)):
            AccuracyLevel.from_score(float('nan'))

    def test_jurisdiction_special_chars(self):
        """Special characters in jurisdiction should fail."""
        with pytest.raises(ValueError):
            validate_jurisdiction("D@E")

    def test_jurisdiction_single_char(self):
        with pytest.raises(ValueError):
            validate_jurisdiction("D")

    def test_jurisdiction_numbers(self):
        with pytest.raises(ValueError):
            validate_jurisdiction("D1")

    def test_threshold_nan(self):
        with pytest.raises(ValueError):
            validate_threshold(float('nan'))

    def test_threshold_inf(self):
        with pytest.raises(ValueError):
            validate_threshold(float('inf'))

    def test_benchmark_empty_jurisdiction_raises(self):
        with pytest.raises(ValueError):
            AccuracyBenchmark(jurisdiction="")

    def test_criterion_score_with_none_explanation(self):
        """CriterionScore should handle None explanation gracefully."""
        cs = CriterionScore(
            criterion=EvaluationCriterion.FACTUAL_ACCURACY,
            score=0.5,
            explanation=None,
        )
        assert cs.explanation is None or cs.explanation == ""

    def test_evaluator_handles_unicode_response(self):
        """Evaluator should handle Unicode characters without error."""
        evaluator = RuleBasedAccuracyEvaluator()
        benches = create_german_ai_liability_benchmarks()
        response = (
            "Nach dem BGH-Urteil VI ZR 67/24 können KI-Ergebnisse ein 'Produkt' "
            "im Sinne des ProdHaftG darstellen. Der Hersteller trägt die strict "
            "liability. Die Beweislastumkehr gilt bei KI-Schäden. § 254 BGB "
            "konto CONTRIBUTORY NEGLIGENCE. Die EU-KI-Verordnung (2024/1689) "
            "ergänzt diese Regelungen. Allerdings hängt es von den "
            "Einzelfallumständen ab."
        )
        result = evaluator.evaluate(benches[0], response, "unicode-test")
        assert result.overall_score >= 0.0

    def test_evaluator_handles_mixed_language(self):
        """Evaluator handles mixed German/English responses."""
        evaluator = RuleBasedAccuracyEvaluator()
        benches = create_german_ai_liability_benchmarks()
        response = (
            "The BGH ruling establishes Beweislastumkehr for AI liability. "
            "Under ProdHaftG § 1, the Hersteller bears liability. However, "
            "the Prüfungspflicht of the user may limit damages under § 254 BGB. "
            "EU AI Act Regulation 2024/1689 provides ex ante framework."
        )
        result = evaluator.evaluate(benches[0], response)
        assert result.overall_score > 0.0


# ========================================================================
# 3. ReDoS — Regex Bomb Inputs
# ========================================================================

class TestReDoSProtection:
    """Verify the evaluator handles adversarial regex-triggering inputs."""

    @pytest.fixture
    def evaluator(self):
        return RuleBasedAccuracyEvaluator()

    @pytest.fixture
    def benchmark(self):
        return create_german_ai_liability_benchmarks()[0]

    def test_alternation_bomb(self, evaluator, benchmark):
        """Input with many alternating patterns that could cause catastrophic backtracking."""
        bomb = ("a|b" * 5000) + " some actual content about liability"
        result = evaluator.evaluate(benchmark, bomb)
        assert result.overall_score >= 0.0
        assert result.evaluation_time_ms < 5000  # Should complete in <5s

    def test_nested_quantifiers(self, evaluator, benchmark):
        """Input with nested quantifiers that could cause exponential backtracking."""
        bomb = "a" * 15000 + "!"
        result = evaluator.evaluate(benchmark, bomb)
        assert result.overall_score >= 0.0

    def test_repeated_groups(self, evaluator, benchmark):
        """Input with many repeated groups."""
        bomb = "(?:ab){10000}" * 100
        result = evaluator.evaluate(benchmark, bomb)
        assert result.overall_score >= 0.0

    def test_unicode_bomb(self, evaluator, benchmark):
        """Input with many Unicode characters that could slow regex."""
        bomb = "§" * 15000 + " liability product"
        result = evaluator.evaluate(benchmark, bomb)
        assert result.overall_score >= 0.0

    def test_mixed_bomb_patterns(self, evaluator, benchmark):
        """Combination of multiple adversarial patterns."""
        bomb = ("[a-z]" * 3000) + ("(x|y)" * 2000) + " liability"
        result = evaluator.evaluate(benchmark, bomb)
        assert result.overall_score >= 0.0
        assert result.evaluation_time_ms < 5000

    def test_exact_limit_input(self, evaluator, benchmark):
        """Input exactly at MAX_EVAL_INPUT_LENGTH boundary."""
        bomb = "x" * MAX_EVAL_INPUT_LENGTH
        result = evaluator.evaluate(benchmark, bomb)
        assert result.overall_score >= 0.0

    def test_over_limit_input(self, evaluator, benchmark):
        """Input significantly over MAX_EVAL_INPUT_LENGTH."""
        bomb = "x" * (MAX_EVAL_INPUT_LENGTH * 3)
        result = evaluator.evaluate(benchmark, bomb)
        assert result.overall_score >= 0.0

    def test_newline_heavy_input(self, evaluator, benchmark):
        """Input with many newlines (can slow some regex engines)."""
        bomb = "\n" * 15000 + " liability"
        result = evaluator.evaluate(benchmark, bomb)
        assert result.overall_score >= 0.0


# ========================================================================
# 4. INMUTABILIDAD — compute_overall + add_evaluation
# ========================================================================

class TestImmutabilityExtended:
    """Verify all mutation methods return new objects without side effects."""

    def test_compute_overall_preserves_original_scores(self):
        """compute_overall must not modify the original criterion_scores list."""
        scores = [
            CriterionScore(criterion=EvaluationCriterion.FACTUAL_ACCURACY, score=0.9, explanation="a"),
            CriterionScore(criterion=EvaluationCriterion.LEGAL_REASONING, score=0.7, explanation="b"),
        ]
        ev = AccuracyEvaluation(criterion_scores=scores)
        original_scores = list(ev.criterion_scores)
        _ = ev.compute_overall()
        assert ev.criterion_scores == original_scores
        assert ev.overall_score == 0.0  # unchanged
        assert ev.verdict == ResponseVerdict.INACCURATE  # unchanged

    def test_compute_overall_preserves_original_id(self):
        """compute_overall preserves the original evaluation ID."""
        ev = AccuracyEvaluation(id="test-id-123")
        result = ev.compute_overall()
        assert result.id == "test-id-123"

    def test_add_evaluation_does_not_mutate_original(self):
        """add_evaluation returns new session, original unchanged."""
        session = AccuracyTestSession(
            name="original",
            total_benchmarks=3,
            evaluations_completed=0,
            evaluations_passed=0,
        )
        ev = AccuracyEvaluation(overall_score=0.8, passed=True)
        new_session = session.add_evaluation(ev)

        # Original unchanged
        assert len(session.evaluations) == 0
        assert session.evaluations_completed == 0
        assert session.evaluations_passed == 0
        assert session.pass_rate == 0.0

        # New session has the evaluation
        assert len(new_session.evaluations) == 1
        assert new_session.evaluations_completed == 1
        assert new_session.evaluations_passed == 1
        assert new_session.pass_rate == 1.0

    def test_add_multiple_evaluations_immutable(self):
        """Multiple add_evaluation calls each return new sessions."""
        session = AccuracyTestSession(name="multi", total_benchmarks=3)
        ev1 = AccuracyEvaluation(overall_score=0.9, passed=True)
        ev2 = AccuracyEvaluation(overall_score=0.4, passed=False)

        s1 = session.add_evaluation(ev1)
        s2 = s1.add_evaluation(ev2)

        # Original untouched
        assert len(session.evaluations) == 0
        # s1 has 1 evaluation
        assert len(s1.evaluations) == 1
        assert s1.evaluations_passed == 1
        # s2 has 2 evaluations
        assert len(s2.evaluations) == 2
        assert s2.evaluations_passed == 1
        assert s2.evaluations_completed == 2

    def test_complete_returns_new_session(self):
        """complete() returns a new session with updated status."""
        session = AccuracyTestSession(
            name="to-complete",
            evaluations_completed=2,
            evaluations_passed=2,
        )
        completed = session.complete()
        assert completed is not session
        assert completed.status == EvaluationStatus.COMPLETED
        assert completed.completed_at is not None
        # Original unchanged
        assert session.status == EvaluationStatus.PENDING
        assert session.completed_at is None

    def test_session_average_score_calculation(self):
        """average_score property computes correctly without mutation."""
        session = AccuracyTestSession(
            evaluations=[
                AccuracyEvaluation(overall_score=0.8),
                AccuracyEvaluation(overall_score=0.6),
                AccuracyEvaluation(overall_score=0.0),  # not counted (not > 0)
            ],
            evaluations_completed=2,
        )
        assert session.average_score == pytest.approx(0.7)

    def test_session_hallucination_count(self):
        """hallucination_count counts evaluations with hallucinations."""
        session = AccuracyTestSession(
            evaluations=[
                AccuracyEvaluation(hallucinations=["false claim"]),
                AccuracyEvaluation(hallucinations=[]),
                AccuracyEvaluation(hallucinations=["lie 1", "lie 2"]),
            ],
        )
        assert session.hallucination_count == 2


# ========================================================================
# 5. DATA LEAK — Thorough to_dict Audit
# ========================================================================

class TestDataLeakAudit:
    """Thoroughly verify no sensitive data leaks through public to_dict methods."""

    SENSITIVE_FIELDS = {"tenant_id", "ground_truth"}

    def test_benchmark_to_dict_no_sensitive_fields(self):
        b = AccuracyBenchmark(
            name="Leak Test",
            ground_truth="SUPER SECRET ground truth",
            tenant_id="tenant-abc-123",
            jurisdiction="DE",
        )
        d = b.to_dict()
        for field in self.SENSITIVE_FIELDS:
            assert field not in d, f"Field '{field}' leaked in AccuracyBenchmark.to_dict()"

    def test_evaluation_to_dict_no_tenant_id(self):
        ev = AccuracyEvaluation(
            tenant_id="tenant-leak-456",
            ai_response="test response",
            benchmark_id="bench-1",
        )
        d = ev.to_dict()
        assert "tenant_id" not in d, "tenant_id leaked in AccuracyEvaluation.to_dict()"
        # Verify ai_response is truncated
        assert len(d["ai_response"]) <= 500

    def test_session_to_dict_no_tenant_id(self):
        session = AccuracyTestSession(
            tenant_id="secret-session-789",
            name="Leak Test Session",
        )
        d = session.to_dict()
        assert "tenant_id" not in d, "tenant_id leaked in AccuracyTestSession.to_dict()"

    def test_full_dict_includes_sensitive_fields(self):
        """to_dict_full should include sensitive fields for admin use."""
        b = AccuracyBenchmark(
            name="Full Test",
            ground_truth="SECRET",
            tenant_id="tenant-admin",
            jurisdiction="DE",
        )
        d_full = b.to_dict_full()
        assert "ground_truth" in d_full
        assert d_full["ground_truth"] == "SECRET"
        assert "tenant_id" in d_full
        assert d_full["tenant_id"] == "tenant-admin"

    def test_session_full_dict_includes_tenant_id(self):
        session = AccuracyTestSession(
            tenant_id="admin-tenant",
            name="Full Test",
        )
        d_full = session.to_dict_full()
        assert "tenant_id" in d_full
        assert d_full["tenant_id"] == "admin-tenant"

    def test_evaluation_to_dict_truncates_long_response(self):
        """to_dict truncates ai_response to 500 chars."""
        long_response = "x" * 1000
        ev = AccuracyEvaluation(ai_response=long_response)
        d = ev.to_dict()
        assert len(d["ai_response"]) == 500

    def test_nested_evaluations_in_session_exclude_tenant(self):
        """Evaluations nested inside session.to_dict() also exclude tenant_id."""
        ev = AccuracyEvaluation(
            tenant_id="nested-leak",
            ai_response="response",
            overall_score=0.8,
        )
        session = AccuracyTestSession(
            tenant_id="session-tenant",
            evaluations=[ev],
        )
        d = session.to_dict()
        assert "tenant_id" not in d
        # Nested evaluation should also not have tenant_id
        if d.get("evaluations"):
            for eval_dict in d["evaluations"]:
                assert "tenant_id" not in eval_dict


# ========================================================================
# 6. INTEGRACIÓN — Module Import Paths
# ========================================================================

class TestModuleIntegration:
    """Verify the accuracy testing module is correctly importable from expected paths."""

    def test_import_domain_entities(self):
        from src.domain.accuracy_testing.entities import (
            AccuracyBenchmark,
            AccuracyEvaluation,
            AccuracyTestSession,
        )
        assert AccuracyBenchmark is not None
        assert AccuracyEvaluation is not None
        assert AccuracyTestSession is not None

    def test_import_domain_value_objects(self):
        from src.domain.accuracy_testing.value_objects import (
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
        assert EvaluationCriterion is not None
        assert MAX_EVAL_INPUT_LENGTH == 10_000

    def test_import_domain_interfaces(self):
        from src.domain.accuracy_testing.interfaces import (
            IAccuracyEvaluator,
            IResponseProvider,
            IBenchmarkRepository,
        )
        assert IAccuracyEvaluator is not None
        assert IResponseProvider is not None
        assert IBenchmarkRepository is not None

    def test_import_infrastructure_evaluator(self):
        from src.infrastructure.accuracy_testing.rule_based_evaluator import RuleBasedAccuracyEvaluator
        evaluator = RuleBasedAccuracyEvaluator()
        assert evaluator is not None
        assert hasattr(evaluator, 'evaluate')

    def test_import_infrastructure_benchmarks(self):
        from src.infrastructure.accuracy_testing.german_ai_liability_benchmarks import (
            create_german_ai_liability_benchmarks,
        )
        benches = create_german_ai_liability_benchmarks()
        assert len(benches) == 4

    def test_import_domain_package_init(self):
        """Domain __init__.py exports all expected symbols."""
        import src.domain.accuracy_testing as domain_pkg
        expected = [
            "EvaluationCriterion", "AccuracyLevel", "EvaluationStatus",
            "LegalDomain", "ResponseVerdict", "CriterionScore",
            "validate_jurisdiction", "validate_threshold", "MAX_EVAL_INPUT_LENGTH",
            "AccuracyEvaluation", "AccuracyBenchmark", "AccuracyTestSession",
            "IAccuracyEvaluator", "IResponseProvider", "IBenchmarkRepository",
        ]
        for name in expected:
            assert hasattr(domain_pkg, name), f"Missing export: {name}"

    def test_import_infrastructure_package_init(self):
        """Infrastructure __init__.py exports evaluator and benchmarks."""
        import src.infrastructure.accuracy_testing as infra_pkg
        assert hasattr(infra_pkg, "RuleBasedAccuracyEvaluator")
        assert hasattr(infra_pkg, "create_german_ai_liability_benchmarks")

    def test_cross_module_import_consistency(self):
        """Entities imported from domain match those used in infrastructure."""
        from src.domain.accuracy_testing.entities import AccuracyBenchmark as DomainBench
        from src.infrastructure.accuracy_testing.german_ai_liability_benchmarks import (
            create_german_ai_liability_benchmarks,
        )
        benches = create_german_ai_liability_benchmarks()
        for b in benches:
            assert isinstance(b, DomainBench)

    def test_evaluator_produces_domain_entities(self):
        """Evaluator returns entities from the domain layer."""
        from src.domain.accuracy_testing.entities import AccuracyEvaluation
        evaluator = RuleBasedAccuracyEvaluator()
        bench = create_german_ai_liability_benchmarks()[0]
        result = evaluator.evaluate(bench, "test response")
        assert isinstance(result, AccuracyEvaluation)

    def test_criterion_score_is_frozen(self):
        """CriterionScore is frozen (immutable) — fields cannot be reassigned."""
        cs = CriterionScore(
            criterion=EvaluationCriterion.FACTUAL_ACCURACY,
            score=0.5,
            explanation="test",
        )
        with pytest.raises(AttributeError):
            cs.score = 0.9
        with pytest.raises(AttributeError):
            cs.criterion = EvaluationCriterion.LEGAL_REASONING

    def test_value_object_enums_are_str_enums(self):
        """All enum value objects should be string enums."""
        assert isinstance(LegalDomain.AI_LIABILITY, str)
        assert isinstance(EvaluationCriterion.FACTUAL_ACCURACY, str)
        assert isinstance(AccuracyLevel.EXCELLENT, str)
        assert isinstance(ResponseVerdict.ACCURATE, str)
        assert isinstance(EvaluationStatus.PENDING, str)
