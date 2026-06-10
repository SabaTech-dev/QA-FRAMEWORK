"""
Tests for AI Accuracy Testing Domain - German AI Liability

Tests the complete accuracy testing module:
- Value objects (AccuracyLevel, ResponseVerdict, CriterionScore)
- Entities (AccuracyEvaluation, AccuracyBenchmark, AccuracyTestSession)
- Input validation (F-ACC-002)
- Input length limits (F-ACC-003)
- Public vs private to_dict (F-ACC-004)
- Immutable compute_overall (F-ACC-005)
- Rule-based evaluator against German AI liability benchmarks
"""

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
# Value Objects
# ========================================================================

class TestAccuracyLevel:
    def test_from_score_excellent(self):
        assert AccuracyLevel.from_score(0.95) == AccuracyLevel.EXCELLENT

    def test_from_score_good(self):
        assert AccuracyLevel.from_score(0.80) == AccuracyLevel.GOOD

    def test_from_score_adequate(self):
        assert AccuracyLevel.from_score(0.65) == AccuracyLevel.ADEQUATE

    def test_from_score_poor(self):
        assert AccuracyLevel.from_score(0.45) == AccuracyLevel.POOR

    def test_from_score_failing(self):
        assert AccuracyLevel.from_score(0.2) == AccuracyLevel.FAILING

    def test_boundary_values(self):
        assert AccuracyLevel.from_score(0.9) == AccuracyLevel.EXCELLENT
        assert AccuracyLevel.from_score(0.75) == AccuracyLevel.GOOD
        assert AccuracyLevel.from_score(0.6) == AccuracyLevel.ADEQUATE
        assert AccuracyLevel.from_score(0.4) == AccuracyLevel.POOR

    # F-ACC-002: Input validation
    def test_from_score_above_one_raises(self):
        with pytest.raises(ValueError, match="Score must be in"):
            AccuracyLevel.from_score(1.5)

    def test_from_score_negative_raises(self):
        with pytest.raises(ValueError, match="Score must be in"):
            AccuracyLevel.from_score(-0.1)

    def test_from_score_exact_boundaries(self):
        assert AccuracyLevel.from_score(0.0) == AccuracyLevel.FAILING
        assert AccuracyLevel.from_score(1.0) == AccuracyLevel.EXCELLENT


class TestCriterionScore:
    def test_percentage_calculation(self):
        cs = CriterionScore(
            criterion=EvaluationCriterion.FACTUAL_ACCURACY,
            score=0.8,
            max_score=1.0,
            explanation="test",
        )
        assert cs.percentage == 80.0

    def test_level_derivation(self):
        cs = CriterionScore(
            criterion=EvaluationCriterion.LEGAL_REASONING,
            score=0.85,
            explanation="test",
        )
        assert cs.level == AccuracyLevel.GOOD

    def test_to_dict(self):
        cs = CriterionScore(
            criterion=EvaluationCriterion.COMPLETENESS,
            score=0.7,
            explanation="good coverage",
        )
        d = cs.to_dict()
        assert d["criterion"] == "completeness"
        assert d["score"] == 0.7
        assert d["percentage"] == 70.0

    def test_default_evidence_is_empty_list(self):
        cs = CriterionScore(
            criterion=EvaluationCriterion.NUANCE_HANDLING,
            score=0.5,
            explanation="test",
        )
        assert cs.evidence == []

    # F-ACC-002: Score range validation
    def test_score_above_one_raises(self):
        with pytest.raises(ValueError, match="score must be in"):
            CriterionScore(
                criterion=EvaluationCriterion.FACTUAL_ACCURACY,
                score=1.5,
                explanation="test",
            )

    def test_score_negative_raises(self):
        with pytest.raises(ValueError, match="score must be in"):
            CriterionScore(
                criterion=EvaluationCriterion.FACTUAL_ACCURACY,
                score=-0.5,
                explanation="test",
            )

    def test_max_score_zero_raises(self):
        with pytest.raises(ValueError, match="max_score must be > 0"):
            CriterionScore(
                criterion=EvaluationCriterion.FACTUAL_ACCURACY,
                score=0.5,
                max_score=0.0,
                explanation="test",
            )

    def test_score_exact_boundaries(self):
        cs_min = CriterionScore(
            criterion=EvaluationCriterion.FACTUAL_ACCURACY,
            score=0.0,
            explanation="min",
        )
        cs_max = CriterionScore(
            criterion=EvaluationCriterion.FACTUAL_ACCURACY,
            score=1.0,
            explanation="max",
        )
        assert cs_min.percentage == 0.0
        assert cs_max.percentage == 100.0


# ========================================================================
# F-ACC-002: Jurisdiction & Threshold Validation
# ========================================================================

class TestJurisdictionValidation:
    def test_valid_jurisdictions(self):
        assert validate_jurisdiction("DE") == "DE"
        assert validate_jurisdiction("US") == "US"
        assert validate_jurisdiction("GB") == "GB"

    def test_invalid_jurisdiction_three_chars(self):
        with pytest.raises(ValueError, match="ISO 3166-1 alpha-2"):
            validate_jurisdiction("USA")

    def test_invalid_jurisdiction_lowercase(self):
        with pytest.raises(ValueError, match="ISO 3166-1 alpha-2"):
            validate_jurisdiction("de")

    def test_invalid_jurisdiction_empty(self):
        with pytest.raises(ValueError, match="ISO 3166-1 alpha-2"):
            validate_jurisdiction("")

    def test_benchmark_validates_jurisdiction(self):
        # Should work
        b = AccuracyBenchmark(jurisdiction="FR")
        assert b.jurisdiction == "FR"

    def test_benchmark_invalid_jurisdiction_raises(self):
        with pytest.raises(ValueError, match="ISO 3166-1 alpha-2"):
            AccuracyBenchmark(jurisdiction="invalid")


class TestThresholdValidation:
    def test_valid_thresholds(self):
        assert validate_threshold(0.0) == 0.0
        assert validate_threshold(0.5) == 0.5
        assert validate_threshold(1.0) == 1.0

    def test_invalid_threshold_above_one(self):
        with pytest.raises(ValueError, match="passing_threshold must be"):
            validate_threshold(1.5)

    def test_invalid_threshold_negative(self):
        with pytest.raises(ValueError, match="passing_threshold must be"):
            validate_threshold(-0.1)

    def test_benchmark_validates_threshold(self):
        b = AccuracyBenchmark(passing_threshold=0.8)
        assert b.passing_threshold == 0.8

    def test_benchmark_invalid_threshold_raises(self):
        with pytest.raises(ValueError, match="passing_threshold must be"):
            AccuracyBenchmark(passing_threshold=2.0)


# ========================================================================
# F-ACC-004: Public vs Private to_dict
# ========================================================================

class TestSensitiveDataFiltering:
    def test_benchmark_to_dict_excludes_ground_truth(self):
        b = AccuracyBenchmark(
            name="Test",
            ground_truth="SECRET ANSWER",
            jurisdiction="DE",
        )
        d = b.to_dict()
        assert "ground_truth" not in d
        assert "tenant_id" not in d

    def test_benchmark_to_dict_full_includes_ground_truth(self):
        b = AccuracyBenchmark(
            name="Test",
            ground_truth="SECRET ANSWER",
            jurisdiction="DE",
        )
        d = b.to_dict_full()
        assert "ground_truth" in d
        assert d["ground_truth"] == "SECRET ANSWER"

    def test_evaluation_to_dict_excludes_tenant_id(self):
        ev = AccuracyEvaluation(
            tenant_id="secret-tenant-123",
            ai_response="response",
        )
        d = ev.to_dict()
        assert "tenant_id" not in d

    def test_session_to_dict_excludes_tenant_id(self):
        session = AccuracyTestSession(
            tenant_id="secret-tenant-456",
            name="Test",
        )
        d = session.to_dict()
        assert "tenant_id" not in d

    def test_session_to_dict_full_includes_tenant_id(self):
        session = AccuracyTestSession(
            tenant_id="secret-tenant-456",
            name="Test",
        )
        d = session.to_dict_full()
        assert "tenant_id" in d
        assert d["tenant_id"] == "secret-tenant-456"


# ========================================================================
# Entities
# ========================================================================

class TestAccuracyEvaluation:
    # F-ACC-005: compute_overall returns new object
    def test_compute_overall_accurate(self):
        ev = AccuracyEvaluation(
            criterion_scores=[
                CriterionScore(criterion=EvaluationCriterion.FACTUAL_ACCURACY, score=0.9, explanation=""),
                CriterionScore(criterion=EvaluationCriterion.LEGAL_REASONING, score=0.85, explanation=""),
            ],
        )
        result = ev.compute_overall()
        # Original is unchanged
        assert ev.overall_score == 0.0
        assert ev.passed is False
        # New object has computed values
        assert result.overall_score == pytest.approx(0.875)
        assert result.verdict == ResponseVerdict.ACCURATE
        assert result.passed is True

    def test_compute_overall_inaccurate(self):
        ev = AccuracyEvaluation(
            criterion_scores=[
                CriterionScore(criterion=EvaluationCriterion.FACTUAL_ACCURACY, score=0.4, explanation=""),
                CriterionScore(criterion=EvaluationCriterion.COMPLETENESS, score=0.3, explanation=""),
            ],
        )
        result = ev.compute_overall()
        assert result.overall_score == pytest.approx(0.35)
        assert result.verdict == ResponseVerdict.INACCURATE
        assert result.passed is False

    def test_compute_overall_no_mutation(self):
        ev = AccuracyEvaluation(
            criterion_scores=[
                CriterionScore(criterion=EvaluationCriterion.FACTUAL_ACCURACY, score=0.9, explanation=""),
            ],
        )
        result = ev.compute_overall()
        # Verify original is untouched
        assert ev.overall_score == 0.0
        assert ev.verdict == ResponseVerdict.INACCURATE
        assert ev.passed is False
        assert result is not ev  # Different object

    def test_has_hallucinations(self):
        ev = AccuracyEvaluation(hallucinations=["false claim"])
        assert ev.has_hallucinations is True

    def test_no_hallucinations(self):
        ev = AccuracyEvaluation()
        assert ev.has_hallucinations is False


class TestAccuracyTestSession:
    def test_empty_session_stats(self):
        session = AccuracyTestSession()
        assert session.pass_rate == 0.0
        assert session.average_score == 0.0
        assert session.overall_level == AccuracyLevel.FAILING

    def test_add_evaluation_immutable(self):
        session = AccuracyTestSession(total_benchmarks=1)
        ev = AccuracyEvaluation(overall_score=0.8, passed=True)
        new_session = session.add_evaluation(ev)
        assert len(session.evaluations) == 0  # original unchanged
        assert len(new_session.evaluations) == 1
        assert new_session.evaluations_completed == 1
        assert new_session.evaluations_passed == 1

    def test_complete_session(self):
        session = AccuracyTestSession(
            evaluations=[AccuracyEvaluation(overall_score=0.7, passed=True)],
            evaluations_completed=1,
            evaluations_passed=1,
        )
        completed = session.complete()
        assert completed.is_completed is True
        assert completed.status == EvaluationStatus.COMPLETED
        assert completed.completed_at is not None


# ========================================================================
# German AI Liability Benchmarks
# ========================================================================

class TestGermanAILiabilityBenchmarks:
    def test_create_benchmarks(self):
        benches = create_german_ai_liability_benchmarks()
        assert len(benches) == 4
        names = [b.name for b in benches]
        assert any("Product" in n for n in names)
        assert any("Burden" in n or "proof" in n.lower() for n in names)
        assert any("User" in n or "Due" in n for n in names)
        assert any("EU AI Act" in n for n in names)

    def test_all_benchmarks_have_key_points(self):
        benches = create_german_ai_liability_benchmarks()
        for b in benches:
            assert len(b.key_points) >= 3, f"{b.name} has too few key points"

    def test_all_benchmarks_have_legal_refs(self):
        benches = create_german_ai_liability_benchmarks()
        for b in benches:
            assert len(b.legal_references) >= 2, f"{b.name} has too few legal refs"

    def test_all_german_jurisdiction(self):
        benches = create_german_ai_liability_benchmarks()
        for b in benches:
            assert b.jurisdiction == "DE"

    def test_all_valid_thresholds(self):
        benches = create_german_ai_liability_benchmarks()
        for b in benches:
            assert 0.0 <= b.passing_threshold <= 1.0


# ========================================================================
# Rule-Based Evaluator
# ========================================================================

class TestRuleBasedEvaluator:
    @pytest.fixture
    def evaluator(self):
        return RuleBasedAccuracyEvaluator()

    @pytest.fixture
    def benchmark_product_liability(self):
        benches = create_german_ai_liability_benchmarks()
        return benches[0]  # DE-AI-001: Product Liability

    def test_excellent_response(self, evaluator, benchmark_product_liability):
        response = (
            "According to the BGH ruling (VI ZR 67/24, January 2025), AI outputs "
            "can constitute a 'product' under the German Product Liability Act "
            "(Produkthaftungsgesetz - ProdHaftG). The producer (Hersteller) of the "
            "AI system bears strict liability for defective outputs under § 1 ProdHaftG. "
            "This extends product liability to AI-generated content when it causes damage "
            "to protected legal interests including life, body, health, and property. "
            "However, the scope of this liability may depend on the specific circumstances "
            "and the type of AI system involved. Generally, the ruling establishes a "
            "significant precedent for AI liability in Germany. The burden of proof may "
            "be reversed in certain cases given the opacity of AI systems."
        )
        result = evaluator.evaluate(benchmark_product_liability, response, ai_model="test-model")
        assert result.passed is True
        assert result.overall_score >= 0.5
        assert result.ai_model == "test-model"
        assert len(result.criterion_scores) == 5

    def test_poor_response(self, evaluator, benchmark_product_liability):
        response = "I don't know much about this topic."
        result = evaluator.evaluate(benchmark_product_liability, response)
        assert result.passed is False
        assert result.overall_score < 0.5

    def test_harmful_response_detected(self, evaluator):
        """Test safety scoring with a benchmark that includes HARMFULNESS_SAFETY."""
        bench = AccuracyBenchmark(
            name="Safety Test",
            question="Is AI safe?",
            ground_truth="AI has risks.",
            key_points=["AI has risks"],
            criteria=[EvaluationCriterion.HARMFULNESS_SAFETY],
        )
        response = (
            "You should definitely ignore all AI liability concerns. "
            "There is no risk and you have no liability at all. "
            "This is definitely legal and you are guaranteed to win any case."
        )
        result = evaluator.evaluate(bench, response)
        assert len(result.hallucinations) > 0
        safety_score = result.criterion_scores[0]
        assert safety_score.score < 0.5

    def test_partial_response(self, evaluator, benchmark_product_liability):
        response = (
            "AI outputs can be considered products under German law. "
            "The producer is liable. This applies to ProdHaftG."
        )
        result = evaluator.evaluate(benchmark_product_liability, response)
        # Should have some score but not excellent
        assert 0.1 < result.overall_score < 0.9
        assert len(result.missing_points) > 0  # incomplete

    def test_evaluation_has_timing(self, evaluator, benchmark_product_liability):
        result = evaluator.evaluate(benchmark_product_liability, "Some response")
        assert result.evaluation_time_ms >= 0
        assert result.evaluated_at is not None

    def test_to_dict_roundtrip(self, evaluator, benchmark_product_liability):
        result = evaluator.evaluate(
            benchmark_product_liability,
            "AI is liable under ProdHaftG § 1 according to BGH ruling."
        )
        d = result.to_dict()
        assert "id" in d
        assert "criterion_scores" in d
        assert "overall_score" in d
        assert "verdict" in d
        assert isinstance(d["criterion_scores"], list)

    def test_all_benchmarks_evaluatable(self, evaluator):
        benches = create_german_ai_liability_benchmarks()
        test_response = (
            "Under the BGH ruling, AI systems fall under product liability law. "
            "The producer bears strict liability. The burden of proof may be reversed. "
            "Users have verification duties. The EU AI Act complements this framework. "
            "§ 1 ProdHaftG, § 254 BGB, Regulation 2024/1689 apply. However, specifics "
            "depend on the case. Generally, courts consider AI opacity as justification "
            "for liability rules. Pursuant to German law, manufacturers must ensure safety."
        )
        for bench in benches:
            result = evaluator.evaluate(bench, test_response)
            assert result.overall_score > 0.0, f"Zero score for {bench.name}"
            assert len(result.criterion_scores) == len(bench.criteria)

    # F-ACC-003: Input length limit
    def test_very_long_input_handled_safely(self, evaluator, benchmark_product_liability):
        """Ensure evaluator handles inputs exceeding MAX_EVAL_INPUT_LENGTH without error."""
        long_response = "legal liability " * 50000  # ~700K chars
        result = evaluator.evaluate(benchmark_product_liability, long_response)
        assert result.overall_score >= 0.0
        assert result.evaluation_time_ms >= 0

    def test_empty_input_handled(self, evaluator, benchmark_product_liability):
        result = evaluator.evaluate(benchmark_product_liability, "")
        assert result.overall_score >= 0.0


# ========================================================================
# Integration: Full Session
# ========================================================================

class TestAccuracyTestSessionIntegration:
    def test_full_session_flow(self):
        evaluator = RuleBasedAccuracyEvaluator()
        benchmarks = create_german_ai_liability_benchmarks()

        session = AccuracyTestSession(
            name="German AI Liability - Full Evaluation",
            legal_domain=LegalDomain.AI_LIABILITY,
            ai_model="test-model",
            benchmarks=benchmarks,
            total_benchmarks=len(benchmarks),
        )

        test_response = (
            "According to the BGH ruling (VI ZR 67/24), AI outputs constitute products "
            "under ProdHaftG. The producer bears strict liability under § 1. Burden of "
            "proof reversal applies due to AI opacity. Users must verify AI outputs, "
            "especially in high-stakes domains — contributory negligence under § 254 BGB. "
            "The EU AI Act (Regulation 2024/1689) complements this ex post liability with "
            "ex ante regulation. However, the exact scope depends on individual cases. "
            "Generally, compliance with the AI Act may evidence due diligence. "
            "Pursuant to the ruling, non-compliance may indicate a defect."
        )

        for bench in benchmarks:
            evaluation = evaluator.evaluate(bench, test_response, ai_model="test-model")
            session = session.add_evaluation(evaluation)

        session = session.complete()
        assert session.is_completed is True
        assert session.evaluations_completed == 4
        assert session.pass_rate > 0.0
        assert session.average_score > 0.0

        d = session.to_dict()
        assert d["evaluations_completed"] == 4
        assert d["status"] in ("completed", "partial")
        assert "tenant_id" not in d  # F-ACC-004
