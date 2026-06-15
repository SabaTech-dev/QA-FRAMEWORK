"""
Tests for Annex IV Exporter and SARIF Exporter

Integration tests covering:
- AnnexIVExporter transforms AccuracyTestSession → AnnexIVReport
- SARIFExporter transforms AccuracyTestSession → SARIFReport
- Evidence mapping correctness
- Requirements evaluation
- SARIF structural compliance
- Edge cases: empty sessions, partial sessions, unicode
"""

import json
import pytest
from datetime import datetime, timezone

from src.domain.accuracy_testing.entities import (
    AccuracyTestSession,
    AccuracyEvaluation,
    AccuracyBenchmark,
)
from src.domain.accuracy_testing.value_objects import (
    EvaluationCriterion,
    AccuracyLevel,
    EvaluationStatus,
    LegalDomain,
    ResponseVerdict,
    CriterionScore,
)
from src.domain.compliance.entities import (
    SystemDescription,
    TestingMethodology,
    AnnexIVReport,
    SARIFReport,
)
from src.domain.compliance.value_objects import (
    RiskTier,
    SystemType,
    ComplianceStatus,
    AnnexIVSection,
    SARIFLevel,
)
from src.infrastructure.accuracy_testing.rule_based_evaluator import RuleBasedAccuracyEvaluator
from src.infrastructure.accuracy_testing.german_ai_liability_benchmarks import (
    create_german_ai_liability_benchmarks,
)
from src.infrastructure.compliance.annex_iv_exporter import AnnexIVExporter
from src.infrastructure.compliance.sarif_exporter import SARIFExporter
from src.infrastructure.compliance.annex_iv_requirements import create_default_requirements


# ========================================================================
# Fixtures
# ========================================================================

@pytest.fixture
def evaluator():
    return RuleBasedAccuracyEvaluator()


@pytest.fixture
def benchmarks():
    return create_german_ai_liability_benchmarks()


@pytest.fixture
def completed_session(evaluator, benchmarks):
    """A fully completed accuracy test session."""
    good_response = (
        "According to the BGH ruling VI ZR 67/24, AI outputs constitute products "
        "under ProdHaftG § 1. The Hersteller bears strict liability. Beweislastumkehr "
        "applies due to AI opacity. Users have Prüfungspflicht; § 254 BGB applies. "
        "The EU AI Act (Regulation 2024/1689) complements this ex post. However, "
        "specifics depend on the case. Generally, compliance evidences due diligence."
    )
    session = AccuracyTestSession(
        name="Test Session",
        legal_domain=LegalDomain.AI_LIABILITY,
        ai_model="test-model-v1",
        benchmarks=benchmarks,
        total_benchmarks=len(benchmarks),
    )
    for bench in benchmarks:
        ev = evaluator.evaluate(bench, good_response, "test-model-v1")
        session = session.add_evaluation(ev)
    return session.complete()


@pytest.fixture
def system_description():
    return SystemDescription(
        system_id="legal-ai-001",
        name="LegalAI Assistant",
        provider_name="SabaTech",
        system_type=SystemType.STANDALONE,
        risk_tier=RiskTier.HIGH_RISK,
        version="1.2.0",
        description="AI system for legal advice on German AI liability law",
        intended_purpose="Provide legal information about AI liability",
        target_users="Legal professionals",
        likely_affected_persons="AI system users and third parties",
    )


@pytest.fixture
def methodology():
    return TestingMethodology(
        methodology_name="Rule-based Accuracy Evaluation",
        description="Deterministic evaluation using keyword matching and coverage analysis",
        test_categories=["accuracy", "legal_reasoning", "citations", "completeness", "nuance"],
        benchmarks_used=["BGH-AI-001", "BGH-AI-002", "BGH-AI-003", "BGH-AI-004"],
        evaluation_metrics=[
            "factual_accuracy", "legal_reasoning", "citation_correctness",
            "completeness", "nuance_handling",
        ],
        passing_threshold=0.6,
        environment="QA-FRAMEWORK v1.0.0",
    )


# ========================================================================
# Annex IV Exporter
# ========================================================================

class TestAnnexIVExporterBasic:
    def test_export_returns_report(self, system_description, methodology, completed_session):
        exporter = AnnexIVExporter()
        report = exporter.export(system_description, methodology, completed_session)
        assert isinstance(report, AnnexIVReport)

    def test_report_has_system_info(self, system_description, methodology, completed_session):
        exporter = AnnexIVExporter()
        report = exporter.export(system_description, methodology, completed_session)
        assert report.system.system_id == "legal-ai-001"
        assert report.system.provider_name == "SabaTech"
        assert report.system.risk_tier == RiskTier.HIGH_RISK

    def test_report_has_methodology(self, system_description, methodology, completed_session):
        exporter = AnnexIVExporter()
        report = exporter.export(system_description, methodology, completed_session)
        assert report.methodology.methodology_name == "Rule-based Accuracy Evaluation"

    def test_report_has_16_requirements(self, system_description, methodology, completed_session):
        exporter = AnnexIVExporter()
        report = exporter.export(system_description, methodology, completed_session)
        assert len(report.requirements) == 16

    def test_report_has_evidence(self, system_description, methodology, completed_session):
        exporter = AnnexIVExporter()
        report = exporter.export(system_description, methodology, completed_session)
        assert len(report.evidence) > 0

    def test_report_aggregate_metrics(self, system_description, methodology, completed_session):
        exporter = AnnexIVExporter()
        report = exporter.export(system_description, methodology, completed_session)
        assert report.total_evaluations == 4
        assert report.evaluations_passed >= 0
        assert 0.0 <= report.overall_accuracy_score <= 1.0
        assert 0.0 <= report.overall_pass_rate <= 1.0


class TestAnnexIVEvidenceMapping:
    def test_accuracy_evidence_mapped_to_section_11(self, system_description, methodology, completed_session):
        exporter = AnnexIVExporter()
        report = exporter.export(system_description, methodology, completed_session)
        accuracy_evidence = [
            e for e in report.evidence
            if e.annex_section == AnnexIVSection.ACCURACY_ROBUSTNESS
        ]
        assert len(accuracy_evidence) >= 4  # one per benchmark

    def test_criterion_evidence_mapped_to_section_6(self, system_description, methodology, completed_session):
        exporter = AnnexIVExporter()
        report = exporter.export(system_description, methodology, completed_session)
        metric_evidence = [
            e for e in report.evidence
            if e.annex_section == AnnexIVSection.TRAINING_METRICS
        ]
        # Each benchmark has 4-5 criteria
        assert len(metric_evidence) >= 16  # at least 4 benchmarks * 4 criteria

    def test_safety_evidence_mapped_to_section_12(self, system_description, methodology, evaluator, benchmarks):
        """If hallucinations exist, they map to §12."""
        # Create a session with a hallucination
        harmful_bench = AccuracyBenchmark(
            name="Safety Test",
            criteria=[EvaluationCriterion.HARMFULNESS_SAFETY],
        )
        ev = evaluator.evaluate(harmful_bench, "This is definitely legal and guaranteed to win.")
        session = AccuracyTestSession(
            evaluations=[ev],
            evaluations_completed=1,
            evaluations_passed=0,
        ).complete()

        exporter = AnnexIVExporter()
        report = exporter.export(
            SystemDescription(system_id="test", provider_name="Corp"),
            TestingMethodology(methodology_name="Test", description="Test"),
            session,
        )
        safety_evidence = [
            e for e in report.evidence
            if e.annex_section == AnnexIVSection.CYBERSECURITY
        ]
        assert len(safety_evidence) > 0


class TestAnnexIVRequirementsEvaluation:
    def test_section_11_satisfied_when_accuracy_passes(self, system_description, methodology, completed_session):
        exporter = AnnexIVExporter()
        report = exporter.export(system_description, methodology, completed_session)
        req_11 = next(r for r in report.requirements if r.section == AnnexIVSection.ACCURACY_ROBUSTNESS)
        # Should be satisfied if any test passed
        if report.evaluations_passed > 0:
            assert req_11.is_satisfied is True

    def test_section_7_satisfied_when_methodology_documented(self, system_description, methodology, completed_session):
        exporter = AnnexIVExporter()
        report = exporter.export(system_description, methodology, completed_session)
        req_7 = next(r for r in report.requirements if r.section == AnnexIVSection.VALIDATION_TESTING)
        assert req_7.is_satisfied is True
        assert "Rule-based" in req_7.evidence_ref

    def test_section_7_not_satisfied_when_methodology_empty(self, system_description, completed_session):
        exporter = AnnexIVExporter()
        empty_methodology = TestingMethodology()
        report = exporter.export(system_description, empty_methodology, completed_session)
        req_7 = next(r for r in report.requirements if r.section == AnnexIVSection.VALIDATION_TESTING)
        assert req_7.is_satisfied is False

    def test_section_6_satisfied_when_criterion_scores_exist(self, system_description, methodology, completed_session):
        exporter = AnnexIVExporter()
        report = exporter.export(system_description, methodology, completed_session)
        req_6 = next(r for r in report.requirements if r.section == AnnexIVSection.TRAINING_METRICS)
        assert req_6.is_satisfied is True


class TestAnnexIVComplianceComputation:
    def test_compliance_computed(self, system_description, methodology, completed_session):
        exporter = AnnexIVExporter()
        report = exporter.export(system_description, methodology, completed_session)
        # Should not be pending after export
        assert report.compliance_status != ComplianceStatus.PENDING_REVIEW or len(report.evidence) == 0

    def test_to_json_valid(self, system_description, methodology, completed_session):
        exporter = AnnexIVExporter()
        report = exporter.export(system_description, methodology, completed_session)
        json_str = report.to_json()
        parsed = json.loads(json_str)
        assert "system" in parsed
        assert "evidence" in parsed
        assert "requirements" in parsed
        assert "compliance_status" in parsed

    def test_no_tenant_id_in_json(self, system_description, methodology, completed_session):
        exporter = AnnexIVExporter()
        report = exporter.export(system_description, methodology, completed_session)
        report.tenant_id = "secret-tenant-123"
        json_str = report.to_json()
        parsed = json.loads(json_str)
        assert "tenant_id" not in parsed


class TestAnnexIVExporterEdgeCases:
    def test_empty_session(self, system_description, methodology):
        exporter = AnnexIVExporter()
        empty_session = AccuracyTestSession(
            name="empty",
            total_benchmarks=4,
        )
        report = exporter.export(system_description, methodology, empty_session)
        assert report.total_evaluations == 0
        assert len(report.evidence) == 0

    def test_partial_session(self, system_description, methodology, evaluator, benchmarks):
        """Session with only 1 of 4 benchmarks evaluated."""
        ev = evaluator.evaluate(benchmarks[0], "AI liability under ProdHaftG")
        session = AccuracyTestSession(
            total_benchmarks=4,
            evaluations_completed=1,
        ).add_evaluation(ev)

        exporter = AnnexIVExporter()
        report = exporter.export(system_description, methodology, session)
        assert report.total_evaluations == 1

    def test_unicode_system_description(self):
        """System description with Unicode characters."""
        system = SystemDescription(
            system_id="system-es-001",
            name="Asistente Legal IA",
            provider_name="SabaTech España",
            description="Sistema de IA para asesoría legal",
        )
        exporter = AnnexIVExporter()
        empty_session = AccuracyTestSession()
        report = exporter.export(
            system,
            TestingMethodology(methodology_name="T", description="T"),
            empty_session,
        )
        assert "España" in report.system.provider_name


# ========================================================================
# SARIF Exporter
# ========================================================================

class TestSARIFExporterBasic:
    def test_export_returns_report(self, completed_session):
        exporter = SARIFExporter()
        report = exporter.export(completed_session)
        assert isinstance(report, SARIFReport)

    def test_version_2_1_0(self, completed_session):
        exporter = SARIFExporter()
        report = exporter.export(completed_session)
        assert report.version == "2.1.0"

    def test_has_schema_uri(self, completed_session):
        exporter = SARIFExporter()
        report = exporter.export(completed_session)
        assert report.schema_uri.startswith("https://")

    def test_has_at_least_one_run(self, completed_session):
        exporter = SARIFExporter()
        report = exporter.export(completed_session)
        assert len(report.runs) >= 1

    def test_run_has_tool_info(self, completed_session):
        exporter = SARIFExporter()
        report = exporter.export(completed_session)
        run = report.runs[0]
        assert run.tool_name == "qa-framework"
        assert run.tool_version

    def test_to_json_valid(self, completed_session):
        exporter = SARIFExporter()
        report = exporter.export(completed_session)
        json_str = report.to_json()
        parsed = json.loads(json_str)
        assert parsed["version"] == "2.1.0"
        assert "$schema" in parsed
        assert len(parsed["runs"]) >= 1


class TestSARIFResults:
    def test_results_per_evaluation(self, completed_session):
        """Each evaluation produces at least 2 results (overall + criterion)."""
        exporter = SARIFExporter()
        report = exporter.export(completed_session)
        run = report.runs[0]
        # 4 evaluations * (1 overall + ~5 criteria each) = ~24 results
        assert len(run.results) >= 8

    def test_passing_result_level_none(self, completed_session):
        exporter = SARIFExporter()
        report = exporter.export(completed_session)
        run = report.runs[0]
        none_results = [r for r in run.results if r["level"] == "none"]
        # At least some should be passing
        if completed_session.evaluations_passed > 0:
            assert len(none_results) > 0

    def test_failing_result_level_error_or_warning(self, completed_session):
        exporter = SARIFExporter()
        report = exporter.export(completed_session)
        run = report.runs[0]
        # Check for any error/warning results
        issue_results = [
            r for r in run.results
            if r["level"] in ("error", "warning")
        ]
        # Depending on session quality, there may or may not be failures
        # but the structure should be valid
        for r in issue_results:
            assert "ruleId" in r
            assert "message" in r

    def test_result_has_message(self, completed_session):
        exporter = SARIFExporter()
        report = exporter.export(completed_session)
        run = report.runs[0]
        for result in run.results:
            assert "message" in result
            assert "text" in result["message"]
            assert len(result["message"]["text"]) > 0

    def test_result_has_kind(self, completed_session):
        exporter = SARIFExporter()
        report = exporter.export(completed_session)
        run = report.runs[0]
        for result in run.results:
            assert result["kind"] in ("pass", "fail", "review", "open", "informational", "notApplicable")

    def test_result_locations_reference_benchmark(self, completed_session):
        exporter = SARIFExporter()
        report = exporter.export(completed_session)
        run = report.runs[0]
        for result in run.results:
            if "locations" in result:
                for loc in result["locations"]:
                    assert "logicalLocations" in loc
                    for ll in loc["logicalLocations"]:
                        assert "name" in ll

    def test_overall_result_has_properties(self, completed_session):
        exporter = SARIFExporter()
        report = exporter.export(completed_session)
        run = report.runs[0]
        overall_results = [r for r in run.results if r["ruleId"] == "QA-OVERALL"]
        assert len(overall_results) >= 4  # one per evaluation
        for r in overall_results:
            assert "properties" in r
            assert "overall_score" in r["properties"]
            assert "verdict" in r["properties"]
            assert "benchmark_id" in r["properties"]


class TestSARIFTaxonomy:
    def test_taxonomy_has_rules(self, completed_session):
        exporter = SARIFExporter()
        report = exporter.export(completed_session)
        run = report.runs[0]
        assert len(run.taxonomy) >= 6  # 6 criterion rules

    def test_taxonomy_rules_have_ids(self, completed_session):
        exporter = SARIFExporter()
        report = exporter.export(completed_session)
        run = report.runs[0]
        for rule in run.taxonomy:
            assert "id" in rule
            assert rule["id"].startswith("QA-ACC-")

    def test_taxonomy_rules_have_default_level(self, completed_session):
        exporter = SARIFExporter()
        report = exporter.export(completed_session)
        run = report.runs[0]
        for rule in run.taxonomy:
            assert "defaultConfiguration" in rule
            assert "level" in rule["defaultConfiguration"]


class TestSARIFInvocation:
    def test_invocation_has_start_end_time(self, completed_session):
        exporter = SARIFExporter()
        report = exporter.export(completed_session)
        run = report.runs[0]
        assert len(run.invocations) >= 1
        inv = run.invocations[0]
        assert "startTimeUtc" in inv
        assert "endTimeUtc" in inv

    def test_invocation_execution_successful_for_completed(self, completed_session):
        exporter = SARIFExporter()
        report = exporter.export(completed_session)
        run = report.runs[0]
        inv = run.invocations[0]
        assert inv["executionSuccessful"] is True
        assert inv["exitCode"] == 0

    def test_invocation_has_properties(self, completed_session):
        exporter = SARIFExporter()
        report = exporter.export(completed_session)
        run = report.runs[0]
        inv = run.invocations[0]
        assert "properties" in inv
        props = inv["properties"]
        assert "evaluationsCompleted" in props
        assert "evaluationsPassed" in props


class TestSARIFWithSystemDescription:
    def test_system_in_locations(self, completed_session, system_description):
        exporter = SARIFExporter()
        report = exporter.export(completed_session, system_description)
        run = report.runs[0]
        for result in run.results[:1]:
            if "locations" in result:
                locs = result["locations"][0].get("logicalLocations", [])
                system_locs = [l for l in locs if l.get("kind") == "aiSystem"]
                assert len(system_locs) >= 1
                assert system_locs[0]["name"] == "legal-ai-001"


class TestSARIFExporterEdgeCases:
    def test_empty_session(self):
        exporter = SARIFExporter()
        empty = AccuracyTestSession()
        report = exporter.export(empty)
        assert len(report.runs) == 1
        assert len(report.runs[0].results) == 0

    def test_session_with_no_completions(self):
        """Session that started but has 0 completed evaluations."""
        exporter = SARIFExporter()
        session = AccuracyTestSession(
            status=EvaluationStatus.RUNNING,
            total_benchmarks=4,
        )
        report = exporter.export(session)
        inv = report.runs[0].invocations[0]
        assert inv["executionSuccessful"] is False

    def test_no_tenant_id_in_json(self, completed_session):
        exporter = SARIFExporter()
        report = exporter.export(completed_session)
        report.tenant_id = "secret"
        json_str = report.to_json()
        parsed = json.loads(json_str)
        assert "tenant_id" not in json_str.lower() or "tenant" not in str(parsed).lower()

    def test_hallucination_produces_safety_result(self):
        """A session with hallucinations should produce QA-SAFETY-001 results."""
        ev = AccuracyEvaluation(
            benchmark_id="bench-safety",
            criterion_scores=[
                CriterionScore(
                    criterion=EvaluationCriterion.HARMFULNESS_SAFETY,
                    score=0.3,
                    explanation="harmful",
                ),
            ],
            overall_score=0.3,
            verdict=ResponseVerdict.INACCURATE,
            passed=False,
            hallucinations=["you have no liability", "guaranteed to win"],
            ai_model="test",
        )
        ev.compute_overall()
        session = AccuracyTestSession(
            evaluations=[ev],
            evaluations_completed=1,
            evaluations_passed=0,
        ).complete()

        exporter = SARIFExporter()
        report = exporter.export(session)
        run = report.runs[0]
        safety_results = [r for r in run.results if r["ruleId"] == "QA-SAFETY-001"]
        assert len(safety_results) >= 2  # one per hallucination


# ========================================================================
# Integration: Full Pipeline (Session → Annex IV + SARIF)
# ========================================================================

class TestFullPipelineIntegration:
    def test_annex_iv_and_sarif_from_same_session(
        self,
        evaluator,
        benchmarks,
        system_description,
        methodology,
    ):
        """Both exporters produce valid reports from the same session."""
        response = (
            "Under the BGH ruling VI ZR 67/24, AI outputs are products under ProdHaftG. "
            "The Hersteller bears strict liability per § 1. Beweislastumkehr applies. "
            "Users have Prüfungspflicht; § 254 BGB contributory negligence. "
            "The EU AI Act Regulation 2024/1689 complements ex post. However, "
            "it depends on the case. Generally, compliance shows diligence."
        )
        session = AccuracyTestSession(
            name="Full Pipeline Test",
            legal_domain=LegalDomain.AI_LIABILITY,
            ai_model="pipeline-test-v1",
            benchmarks=benchmarks,
            total_benchmarks=len(benchmarks),
        )
        for bench in benchmarks:
            ev = evaluator.evaluate(bench, response, "pipeline-test-v1")
            session = session.add_evaluation(ev)
        session = session.complete()

        # Annex IV export
        annex_exporter = AnnexIVExporter()
        annex_report = annex_exporter.export(system_description, methodology, session)
        assert annex_report.total_evaluations == 4

        # SARIF export
        sarif_exporter = SARIFExporter()
        sarif_report = sarif_exporter.export(session, system_description)
        assert sarif_report.version == "2.1.0"
        assert len(sarif_report.runs[0].results) >= 8

        # Cross-validation: pass rate consistent
        assert annex_report.overall_pass_rate == round(session.pass_rate, 4)

    def test_requirements_count_constant(
        self,
        system_description,
        methodology,
        completed_session,
    ):
        """Annex IV always has 16 requirements regardless of session size."""
        exporter = AnnexIVExporter()
        report = exporter.export(system_description, methodology, completed_session)
        assert len(report.requirements) == 16

    def test_create_default_requirements(self):
        """Default requirements factory creates all 16 sections."""
        reqs = create_default_requirements()
        assert len(reqs) == 16
        sections = {r.section for r in reqs}
        assert len(sections) == 16  # all unique
