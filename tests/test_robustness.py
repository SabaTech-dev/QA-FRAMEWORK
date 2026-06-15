"""
Tests for Adversarial Robustness Module

Covers:
- Value objects: AttackType, RobustnessLevel, validation
- Entities: AttackResult, RobustnessTestSession, RobustnessReport, AdversarialExample
- Infrastructure: TextAttackSimulator, RobustnessScorer
- SARIF integration: ComplianceSARIFExporter robustness
- Edge cases: empty text, short text, max perturbations
"""

import json
import pytest
from datetime import datetime, timezone

from src.domain.robustness.value_objects import (
    AttackType,
    RobustnessLevel,
    PerturbationMethod,
    AdversarialExample,
    validate_attack_epsilon,
    validate_confidence_score,
    MAX_PERTURBATION_RATIO,
)
from src.domain.robustness.entities import (
    AttackResult,
    RobustnessTestSession,
    RobustnessReport,
)
from src.infrastructure.robustness.attack_simulator import TextAttackSimulator
from src.infrastructure.robustness.robustness_scorer import RobustnessScorer
from src.infrastructure.compliance.compliance_sarif_exporter import ComplianceSARIFExporter
from src.domain.compliance.entities import SystemDescription, SARIFReport
from src.domain.bias_fairness.value_objects import FairnessMetric, Subgroup


# ========================================================================
# Value Objects
# ========================================================================

class TestAttackType:
    def test_all_values(self):
        assert AttackType.FGSM.value == "fgsm"
        assert AttackType.PGD.value == "pgd"
        assert AttackType.TEXT_FGSM.value == "text_fgsm"
        assert AttackType.CHAR_SWAP.value == "char_swap"
        assert AttackType.WORD_SUBSTITUTION.value == "word_substitution"
        assert AttackType.SENTENCE_REORDER.value == "sentence_reorder"
        assert AttackType.KEYWORD_INJECTION.value == "keyword_injection"
        assert AttackType.COMBINED.value == "combined"

    def test_str_enum(self):
        assert isinstance(AttackType.FGSM, str)


class TestRobustnessLevel:
    def test_all_values(self):
        assert RobustnessLevel.ROBUST.value == "robust"
        assert RobustnessLevel.MODERATELY_ROBUST.value == "moderately_robust"
        assert RobustnessLevel.WEAK.value == "weak"
        assert RobustnessLevel.VULNERABLE.value == "vulnerable"


class TestPerturbationMethod:
    def test_values(self):
        assert PerturbationMethod.CHAR_SWAP.value == "char_swap"
        assert PerturbationMethod.WORD_SYNONYM.value == "word_synonym"


# ========================================================================
# Input Validation
# ========================================================================

class TestValidateAttackEpsilon:
    def test_valid(self):
        assert validate_attack_epsilon(0.1) == 0.1
        assert validate_attack_epsilon(0.5) == 0.5
        assert validate_attack_epsilon(1.0) == 1.0

    def test_zero_raises(self):
        with pytest.raises(ValueError, match="must be in"):
            validate_attack_epsilon(0.0)

    def test_negative_raises(self):
        with pytest.raises(ValueError, match="must be in"):
            validate_attack_epsilon(-0.1)

    def test_above_one_raises(self):
        with pytest.raises(ValueError, match="must be in"):
            validate_attack_epsilon(1.5)

    def test_nan_raises(self):
        with pytest.raises(ValueError, match="must not be NaN"):
            validate_attack_epsilon(float('nan'))

    def test_inf_raises(self):
        with pytest.raises(ValueError, match="must not be infinite"):
            validate_attack_epsilon(float('inf'))


class TestValidateConfidenceScore:
    def test_valid(self):
        assert validate_confidence_score(0.5) == 0.5
        assert validate_confidence_score(0.0) == 0.0
        assert validate_confidence_score(1.0) == 1.0

    def test_above_one_raises(self):
        with pytest.raises(ValueError, match="must be in"):
            validate_confidence_score(1.5)

    def test_negative_raises(self):
        with pytest.raises(ValueError, match="must be in"):
            validate_confidence_score(-0.1)


class TestAdversarialExample:
    def test_construction(self):
        ex = AdversarialExample(
            original_text="Hello world",
            perturbed_text="Helo world",
            attack_type=AttackType.CHAR_SWAP,
            perturbation_count=1,
            perturbation_ratio=0.1,
        )
        assert ex.has_perturbation is True
        assert ex.perturbation_count == 1

    def test_no_perturbation(self):
        ex = AdversarialExample(
            original_text="Hello",
            perturbed_text="Hello",
            perturbation_count=0,
            perturbation_ratio=0.0,
        )
        assert ex.has_perturbation is False

    def test_ratio_clamped(self):
        ex = AdversarialExample(perturbation_ratio=0.6)
        assert ex.perturbation_ratio == pytest.approx(0.5)  # clamped to MAX_PERTURBATION_RATIO

        ex2 = AdversarialExample(perturbation_ratio=-0.1)
        assert ex2.perturbation_ratio == pytest.approx(0.0)  # clamped min

    def test_to_dict_truncates_with_indicator(self):
        long_text = "x" * 1000
        ex = AdversarialExample(original_text=long_text, perturbed_text=long_text)
        d = ex.to_dict()
        assert d["original_text_length"] == 1000
        assert d["original_text"].endswith("...[truncated]")
        assert len(d["original_text"]) == 500 + len("...[truncated]")
        assert d["perturbed_text"].endswith("...[truncated]")
        assert d["perturbed_text_length"] == 1000


# ========================================================================
# Entities
# ========================================================================

class TestAttackResult:
    def test_construction(self):
        r = AttackResult(
            attack_type=AttackType.CHAR_SWAP,
            epsilon=0.1,
        )
        assert r.attack_type == AttackType.CHAR_SWAP
        assert r.epsilon == 0.1

    def test_robustness_score(self):
        r = AttackResult(accuracy_degradation=0.1)
        assert r.robustness_score == pytest.approx(0.9)

    def test_robustness_score_floor(self):
        r = AttackResult(accuracy_degradation=1.5)
        assert r.robustness_score == 0.0

    def test_robustness_level_robust(self):
        r = AttackResult(accuracy_degradation=0.05)
        assert r.robustness_level == RobustnessLevel.ROBUST

    def test_robustness_level_weak(self):
        r = AttackResult(accuracy_degradation=0.35)
        assert r.robustness_level == RobustnessLevel.WEAK

    def test_robustness_level_vulnerable(self):
        r = AttackResult(accuracy_degradation=0.6)
        assert r.robustness_level == RobustnessLevel.VULNERABLE

    def test_success_rate(self):
        r = AttackResult(total_samples=100, successful_attacks=30)
        assert r.success_rate == pytest.approx(0.3)

    def test_success_rate_zero_samples(self):
        r = AttackResult()
        assert r.success_rate == 0.0

    def test_compute_metrics(self):
        r = AttackResult()
        r.adversarial_examples = [
            AdversarialExample(perturbation_count=1, perturbation_ratio=0.1),
            AdversarialExample(perturbation_count=0, perturbation_ratio=0.0),
        ]
        r.compute_metrics()
        assert r.total_samples == 2
        assert r.successful_attacks == 1

    def test_to_dict(self):
        r = AttackResult(attack_type=AttackType.FGSM, epsilon=0.2)
        d = r.to_dict()
        assert d["attack_type"] == "fgsm"
        assert "aggregate" in d


class TestRobustnessTestSession:
    def test_construction(self):
        s = RobustnessTestSession(name="test")
        assert s.name == "test"
        assert s.status == "pending"

    def test_add_result(self):
        s = RobustnessTestSession()
        r = AttackResult(attack_type=AttackType.FGSM, accuracy_degradation=0.1)
        s.add_attack_result(r)
        assert s.attack_count == 1

    def test_average_robustness_score(self):
        s = RobustnessTestSession()
        s.add_attack_result(AttackResult(accuracy_degradation=0.1))
        s.add_attack_result(AttackResult(accuracy_degradation=0.3))
        # robustness_score = 1.0 - degradation: 0.9 + 0.7 = 1.6 / 2 = 0.8
        assert s.average_robustness_score == pytest.approx(0.8)

    def test_worst_robustness_score(self):
        s = RobustnessTestSession()
        s.add_attack_result(AttackResult(accuracy_degradation=0.1))
        s.add_attack_result(AttackResult(accuracy_degradation=0.7))
        # worst = min(0.9, 0.3) = 0.3
        assert s.worst_robustness_score == pytest.approx(0.3)

    def test_complete(self):
        s = RobustnessTestSession()
        s.complete()
        assert s.status == "completed"

    def test_complete_with_error(self):
        s = RobustnessTestSession()
        s.complete(error="crash")
        assert s.status == "failed"

    def test_to_dict(self):
        s = RobustnessTestSession(name="test")
        d = s.to_dict()
        assert d["name"] == "test"
        assert "tenant_id" not in d


class TestRobustnessReport:
    def test_empty_report(self):
        r = RobustnessReport()
        assert r.overall_robustness_level == RobustnessLevel.ROBUST

    def test_compute_overall_robust(self):
        r = RobustnessReport()
        r.add_attack_result(AttackResult(accuracy_degradation=0.05))
        r.add_attack_result(AttackResult(accuracy_degradation=0.08))
        level = r.compute_overall_robustness()
        assert level == RobustnessLevel.ROBUST

    def test_compute_overall_vulnerable(self):
        r = RobustnessReport()
        r.add_attack_result(AttackResult(accuracy_degradation=0.6))
        level = r.compute_overall_robustness()
        assert level == RobustnessLevel.VULNERABLE

    def test_to_dict(self):
        r = RobustnessReport(system_id="sys-001")
        d = r.to_dict()
        assert d["system_id"] == "sys-001"
        assert "tenant_id" not in d

    def test_to_json(self):
        r = RobustnessReport()
        j = r.to_json()
        parsed = json.loads(j)
        assert "aggregate" in parsed


# ========================================================================
# Infrastructure: TextAttackSimulator
# ========================================================================

class TestTextAttackSimulator:
    def test_init(self):
        s = TextAttackSimulator(seed=42)
        assert s._rng is not None

    def test_char_swap_attack(self):
        s = TextAttackSimulator(seed=42)
        examples = s.generate_adversarial_examples(
            "This is a test sentence for evaluation.",
            AttackType.CHAR_SWAP,
            epsilon=0.1,
        )
        assert len(examples) > 0
        for ex in examples:
            assert ex.attack_type == AttackType.CHAR_SWAP
            assert ex.has_perturbation

    def test_word_substitution_attack(self):
        s = TextAttackSimulator(seed=42)
        examples = s.generate_adversarial_examples(
            "This is a good and helpful response.",
            AttackType.WORD_SUBSTITUTION,
            epsilon=0.3,
        )
        assert len(examples) > 0
        assert examples[0].attack_type == AttackType.WORD_SUBSTITUTION

    def test_keyword_injection_attack(self):
        s = TextAttackSimulator(seed=42)
        examples = s.generate_adversarial_examples(
            "Legal advice about AI liability law.",
            AttackType.KEYWORD_INJECTION,
            epsilon=0.2,
        )
        assert len(examples) > 0
        assert examples[0].attack_type == AttackType.KEYWORD_INJECTION

    def test_sentence_reorder_attack(self):
        s = TextAttackSimulator(seed=42)
        examples = s.generate_adversarial_examples(
            "First sentence. Second sentence. Third sentence.",
            AttackType.SENTENCE_REORDER,
            epsilon=0.5,
        )
        # May be empty if text has <3 sentences after split
        # Just verify no error
        assert isinstance(examples, list)

    def test_fgsm_attack(self):
        s = TextAttackSimulator(seed=42)
        examples = s.generate_adversarial_examples(
            "This is a sufficiently long text for FGSM attack.",
            AttackType.FGSM,
            epsilon=0.2,
        )
        assert len(examples) > 0

    def test_pgd_attack(self):
        s = TextAttackSimulator(seed=42)
        examples = s.generate_adversarial_examples(
            "This is a sufficiently long text for PGD attack.",
            AttackType.PGD,
            epsilon=0.2,
        )
        assert len(examples) > 0

    def test_combined_attack(self):
        s = TextAttackSimulator(seed=42)
        examples = s.generate_adversarial_examples(
            "This is a good test for combined attack evaluation.",
            AttackType.COMBINED,
            epsilon=0.3,
        )
        assert len(examples) > 0

    def test_empty_text(self):
        s = TextAttackSimulator(seed=42)
        examples = s.generate_adversarial_examples("", AttackType.CHAR_SWAP)
        assert examples == []

    def test_short_text(self):
        s = TextAttackSimulator(seed=42)
        examples = s.generate_adversarial_examples("Hi", AttackType.CHAR_SWAP)
        # May be empty for very short text
        assert isinstance(examples, list)

    def test_reproducible_with_seed(self):
        s1 = TextAttackSimulator(seed=42)
        s2 = TextAttackSimulator(seed=42)
        ex1 = s1.generate_adversarial_examples("Test text here.", AttackType.CHAR_SWAP)
        ex2 = s2.generate_adversarial_examples("Test text here.", AttackType.CHAR_SWAP)
        assert len(ex1) == len(ex2)
        for e1, e2 in zip(ex1, ex2):
            assert e1.perturbed_text == e2.perturbed_text

    def test_run_attack_session(self):
        s = TextAttackSimulator(seed=42)
        texts = ["Test text one.", "Test text two."]
        labels = ["positive", "negative"]
        session = s.run_attack_session(
            texts, labels,
            attack_types=[AttackType.CHAR_SWAP],
            epsilon=0.1,
        )
        assert session.status == "completed"
        assert session.attack_count == 1

    def test_evaluate_attack_with_model(self):
        s = TextAttackSimulator(seed=42)
        def mock_model(text):
            return "positive", 0.9

        pred, conf, changed = s.evaluate_attack(
            "Original text",
            "Perturbed text",
            "positive",
            0.9,
            model_predict_fn=mock_model,
        )
        assert pred == "positive"
        assert conf == 0.9
        assert changed is False

    def test_evaluate_attack_without_model(self):
        s = TextAttackSimulator(seed=42)
        pred, conf, changed = s.evaluate_attack(
            "Original", "Perturbed", "pos", 0.9,
        )
        assert pred == "pos"
        assert changed is False


# ========================================================================
# Infrastructure: RobustnessScorer
# ========================================================================

class TestRobustnessScorer:
    def test_init(self):
        s = RobustnessScorer()
        assert s.robustness_threshold == 0.8

    def test_init_invalid(self):
        with pytest.raises(ValueError, match="robustness_threshold"):
            RobustnessScorer(robustness_threshold=1.5)

    def test_score_session(self):
        scorer = RobustnessScorer()
        session = RobustnessTestSession()
        session.add_attack_result(AttackResult(
            attack_type=AttackType.FGSM,
            accuracy_degradation=0.1,
        ))
        session.add_attack_result(AttackResult(
            attack_type=AttackType.CHAR_SWAP,
            accuracy_degradation=0.05,
        ))
        report = scorer.score_session(session, system_id="test")
        assert report.system_id == "test"
        assert report.overall_robustness_score > 0

    def test_score_attack_result(self):
        scorer = RobustnessScorer()
        result = AttackResult(
            attack_type=AttackType.FGSM,
            accuracy_degradation=0.3,
        )
        report = scorer.score_attack_result(result)
        assert report.attacks_tested == 1

    def test_compute_attack_type_summary(self):
        scorer = RobustnessScorer()
        results = [
            AttackResult(attack_type=AttackType.FGSM, accuracy_degradation=0.1, total_samples=10, successful_attacks=2),
            AttackResult(attack_type=AttackType.FGSM, accuracy_degradation=0.2, total_samples=10, successful_attacks=3),
            AttackResult(attack_type=AttackType.CHAR_SWAP, accuracy_degradation=0.05, total_samples=10, successful_attacks=1),
        ]
        summary = scorer.compute_attack_type_summary(results)
        assert "fgsm" in summary
        assert "char_swap" in summary
        assert summary["fgsm"]["count"] == 2
        assert summary["char_swap"]["count"] == 1

    def test_get_recommendations_robust(self):
        scorer = RobustnessScorer()
        report = RobustnessReport()
        report.add_attack_result(AttackResult(accuracy_degradation=0.05))
        report.compute_overall_robustness()
        recs = scorer.get_recommendations(report)
        assert len(recs) > 0
        assert any("good" in r.lower() or "monitoring" in r.lower() for r in recs)

    def test_get_recommendations_vulnerable(self):
        scorer = RobustnessScorer()
        report = RobustnessReport()
        report.add_attack_result(AttackResult(accuracy_degradation=0.7))
        report.compute_overall_robustness()
        recs = scorer.get_recommendations(report)
        assert any("adversarial" in r.lower() for r in recs)


# ========================================================================
# SARIF Integration
# ========================================================================

class TestComplianceSARIFRobustness:
    def _make_robust_report(self):
        report = RobustnessReport(system_id="test-sys")
        report.add_attack_result(AttackResult(
            attack_type=AttackType.FGSM,
            accuracy_degradation=0.08,
            total_samples=100,
            successful_attacks=8,
        ))
        report.add_attack_result(AttackResult(
            attack_type=AttackType.CHAR_SWAP,
            accuracy_degradation=0.05,
            total_samples=100,
            successful_attacks=5,
        ))
        report.compute_overall_robustness()
        return report

    def _make_vulnerable_report(self):
        report = RobustnessReport(system_id="test-sys")
        report.add_attack_result(AttackResult(
            attack_type=AttackType.FGSM,
            accuracy_degradation=0.7,
            total_samples=100,
            successful_attacks=70,
        ))
        report.compute_overall_robustness()
        return report

    def test_export_returns_report(self):
        exporter = ComplianceSARIFExporter()
        report = exporter.export_robustness(self._make_robust_report())
        assert isinstance(report, SARIFReport)

    def test_version_2_1_0(self):
        exporter = ComplianceSARIFExporter()
        report = exporter.export_robustness(self._make_robust_report())
        assert report.version == "2.1.0"

    def test_has_one_run(self):
        exporter = ComplianceSARIFExporter()
        report = exporter.export_robustness(self._make_robust_report())
        assert len(report.runs) == 1

    def test_robust_report_passing(self):
        exporter = ComplianceSARIFExporter()
        report = exporter.export_robustness(self._make_robust_report())
        run = report.runs[0]
        overall = [r for r in run.results if r["ruleId"] == "QA-ROB-OVERALL"]
        assert len(overall) == 1
        assert overall[0]["kind"] == "pass"

    def test_vulnerable_report_failing(self):
        exporter = ComplianceSARIFExporter()
        report = exporter.export_robustness(self._make_vulnerable_report())
        run = report.runs[0]
        overall = [r for r in run.results if r["ruleId"] == "QA-ROB-OVERALL"]
        assert len(overall) == 1
        assert overall[0]["kind"] == "fail"

    def test_has_taxonomy(self):
        exporter = ComplianceSARIFExporter()
        report = exporter.export_robustness(self._make_robust_report())
        run = report.runs[0]
        assert len(run.taxonomy) >= 7  # 6 attack types + overall

    def test_attack_results_exist(self):
        exporter = ComplianceSARIFExporter()
        report = exporter.export_robustness(self._make_robust_report())
        run = report.runs[0]
        # 2 attack types + 1 overall = 3 results
        attack_results = [
            r for r in run.results
            if r["ruleId"].startswith("QA-ROB-") and r["ruleId"] != "QA-ROB-OVERALL"
        ]
        assert len(attack_results) == 2

    def test_to_json_valid(self):
        exporter = ComplianceSARIFExporter()
        report = exporter.export_robustness(self._make_robust_report())
        j = report.to_json()
        parsed = json.loads(j)
        assert parsed["version"] == "2.1.0"

    def test_with_system_description(self):
        exporter = ComplianceSARIFExporter()
        sys = SystemDescription(system_id="ai-001", provider_name="Corp")
        report = exporter.export_robustness(self._make_robust_report(), sys)
        run = report.runs[0]
        for r in run.results[:1]:
            if "locations" in r:
                locs = r["locations"][0].get("logicalLocations", [])
                system_locs = [l for l in locs if l.get("kind") == "aiSystem"]
                assert len(system_locs) >= 1

    def test_has_invocation(self):
        exporter = ComplianceSARIFExporter()
        report = exporter.export_robustness(self._make_robust_report())
        run = report.runs[0]
        assert len(run.invocations) >= 1


# ========================================================================
# Module Imports
# ========================================================================

class TestModuleImports:
    def test_import_domain(self):
        import src.domain.robustness as pkg
        expected = [
            "AttackType", "RobustnessLevel", "PerturbationMethod",
            "validate_attack_epsilon", "validate_confidence_score",
            "AttackResult", "RobustnessTestSession", "RobustnessReport",
            "AdversarialExample", "IAttackSimulator", "IModelPredictor",
        ]
        for name in expected:
            assert hasattr(pkg, name), f"Missing export: {name}"

    def test_import_infrastructure(self):
        import src.infrastructure.robustness as pkg
        assert hasattr(pkg, "TextAttackSimulator")
        assert hasattr(pkg, "RobustnessScorer")

    def test_import_bias_fairness_domain(self):
        import src.domain.bias_fairness as pkg
        expected = [
            "FairnessMetric", "Subgroup", "BiasTestStatus", "FairnessLevel",
            "SubgroupMetric", "validate_group_name", "validate_metric_value",
            "SubgroupAnalysis", "FairnessReport", "BiasTestSession",
            "IFairnessAnalyzer", "IDatasetProvider",
        ]
        for name in expected:
            assert hasattr(pkg, name), f"Missing export: {name}"

    def test_import_bias_fairness_infrastructure(self):
        import src.infrastructure.bias_fairness as pkg
        assert hasattr(pkg, "StatisticalFairnessAnalyzer")

    def test_import_compliance_sarif_exporter(self):
        from src.infrastructure.compliance.compliance_sarif_exporter import ComplianceSARIFExporter
        assert ComplianceSARIFExporter is not None

    def test_str_enums(self):
        assert isinstance(AttackType.FGSM, str)
        assert isinstance(RobustnessLevel.ROBUST, str)
        assert isinstance(FairnessMetric.DEMOGRAPHIC_PARITY, str)
        assert isinstance(Subgroup.GENDER, str)
