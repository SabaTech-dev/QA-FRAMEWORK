"""
Annex IV Exporter

Transforms AccuracyTestSession results into a structured
Annex IV technical documentation report compliant with
EU AI Act requirements.

Maps testing evidence to specific Annex IV sections:
- §6 (Training/validation metrics) ← accuracy scores
- §7 (Testing methodology) ← evaluation criteria description
- §11 (Accuracy and robustness) ← evaluation results, pass rates
- §12 (Cybersecurity) ← safety/hallucination findings
"""

from datetime import datetime, timezone
from typing import Optional

from src.domain.accuracy_testing.entities import AccuracyTestSession, AccuracyEvaluation
from src.domain.accuracy_testing.value_objects import (
    AccuracyLevel,
    EvaluationCriterion,
    EvaluationStatus,
)
from src.domain.compliance.entities import (
    SystemDescription,
    TestingMethodology,
    ComplianceEvidence,
    AnnexIVReport,
)
from src.domain.compliance.value_objects import (
    AnnexIVSection,
    ComplianceStatus,
)
from .annex_iv_requirements import create_default_requirements


class AnnexIVExporter:
    """
    Exports AccuracyTestSession results as Annex IV compliance evidence.

    Usage:
        exporter = AnnexIVExporter()
        report = exporter.export(
            system_description=system,
            testing_methodology=methodology,
            test_session=session,
        )
        print(report.to_json())
    """

    def export(
        self,
        system_description: SystemDescription,
        testing_methodology: TestingMethodology,
        test_session: AccuracyTestSession,
    ) -> AnnexIVReport:
        """
        Generate an Annex IV report from a testing session.

        Args:
            system_description: AI system metadata
            testing_methodology: Testing approach documentation
            test_session: Completed (or partial) AccuracyTestSession

        Returns:
            AnnexIVReport with evidence mapped to Annex IV sections
        """
        report = AnnexIVReport(
            system=system_description,
            methodology=testing_methodology,
            requirements=create_default_requirements(),
        )

        # Populate aggregate metrics from the session
        self._populate_aggregate_metrics(report, test_session)

        # Generate evidence items for each evaluation
        for evaluation in test_session.evaluations:
            evidence_items = self._create_evidence_from_evaluation(evaluation, test_session.id)
            for evidence in evidence_items:
                report.add_evidence(evidence)

        # Mark requirements as satisfied based on available evidence
        self._evaluate_requirements(report)

        # Compute overall compliance status
        report.compute_compliance()

        return report

    def _populate_aggregate_metrics(
        self,
        report: AnnexIVReport,
        session: AccuracyTestSession,
    ) -> None:
        """Populate report-level aggregate metrics from session."""
        report.overall_accuracy_score = round(session.average_score, 4)
        report.overall_pass_rate = round(session.pass_rate, 4)
        report.total_evaluations = session.evaluations_completed
        report.evaluations_passed = session.evaluations_passed
        report.hallucination_count = session.hallucination_count

    def _create_evidence_from_evaluation(
        self,
        evaluation: AccuracyEvaluation,
        session_id: Optional[str],
    ) -> list[ComplianceEvidence]:
        """
        Create evidence items from a single evaluation result.

        Each evaluation contributes to:
        - §11 (Accuracy): overall score and verdict
        - §6 (Metrics): per-criterion scores
        - §12 (Cybersecurity): hallucinations and safety findings
        """
        evidence_items: list[ComplianceEvidence] = []

        # §11 — Accuracy evidence
        accuracy_evidence = ComplianceEvidence(
            annex_section=AnnexIVSection.ACCURACY_ROBUSTNESS,
            evidence_type="accuracy_test",
            title=f"Accuracy evaluation: {evaluation.benchmark_id}",
            description=(
                f"Verdict: {evaluation.verdict.value}. "
                f"Overall score: {evaluation.overall_score:.1%}. "
                f"Model: {evaluation.ai_model or 'unknown'}."
            ),
            source_session_id=session_id,
            metric_name="overall_accuracy_score",
            metric_value=evaluation.overall_score,
            metric_target=0.6,
            passed=evaluation.passed,
            artifact_data={
                "verdict": evaluation.verdict.value,
                "accuracy_level": evaluation.accuracy_level.value,
                "ai_model": evaluation.ai_model,
                "evaluation_time_ms": evaluation.evaluation_time_ms,
                "benchmark_id": evaluation.benchmark_id,
            },
        )
        evidence_items.append(accuracy_evidence)

        # §6 — Per-criterion metrics
        for cs in evaluation.criterion_scores:
            criterion_evidence = ComplianceEvidence(
                annex_section=AnnexIVSection.TRAINING_METRICS,
                evidence_type="criterion_score",
                title=f"Criterion: {cs.criterion.value}",
                description=cs.explanation,
                source_session_id=session_id,
                metric_name=cs.criterion.value,
                metric_value=cs.score,
                metric_target=0.6,
                passed=cs.score >= 0.6,
                artifact_data={
                    "criterion": cs.criterion.value,
                    "percentage": round(cs.percentage, 2),
                    "level": cs.level.value,
                    "explanation": cs.explanation,
                },
            )
            evidence_items.append(criterion_evidence)

        # §12 — Cybersecurity / safety evidence (hallucinations)
        if evaluation.has_hallucinations:
            safety_evidence = ComplianceEvidence(
                annex_section=AnnexIVSection.CYBERSECURITY,
                evidence_type="safety_finding",
                title=f"Safety finding: {len(evaluation.hallucinations)} hallucination(s)",
                description=(
                    f"Detected {len(evaluation.hallucinations)} potentially "
                    f"harmful or hallucinated claims: "
                    f"{'; '.join(evaluation.hallucinations[:5])}"
                ),
                source_session_id=session_id,
                metric_name="hallucination_count",
                metric_value=float(len(evaluation.hallucinations)),
                metric_target=0.0,
                passed=False,
                artifact_data={
                    "hallucinations": evaluation.hallucinations,
                    "benchmark_id": evaluation.benchmark_id,
                },
            )
            evidence_items.append(safety_evidence)

        return evidence_items

    def _evaluate_requirements(self, report: AnnexIVReport) -> None:
        """
        Mark Annex IV requirements as satisfied based on evidence.

        Requirements are satisfied when:
        - §11 (Accuracy): at least one passing accuracy test
        - §6 (Metrics): per-criterion evidence exists
        - §7 (Methodology): methodology description provided
        - §12 (Cybersecurity): no unaddressed safety findings (or documented)
        """
        # Gather evidence by section
        evidence_by_section: dict[str, list[ComplianceEvidence]] = {}
        for e in report.evidence:
            evidence_by_section.setdefault(e.annex_section.value, []).append(e)

        for req in report.requirements:
            section = req.section
            relevant = evidence_by_section.get(section.value, [])

            if section == AnnexIVSection.ACCURACY_ROBUSTNESS:
                # §11: satisfied if at least one passing accuracy test
                has_passing = any(
                    e.evidence_type == "accuracy_test" and e.passed for e in relevant
                )
                if has_passing:
                    req.is_satisfied = True
                    req.evidence_ref = f"{len(relevant)} accuracy evidence item(s)"
                else:
                    req.is_satisfied = False
                    req.gap_description = "No passing accuracy tests found"

            elif section == AnnexIVSection.TRAINING_METRICS:
                # §6: satisfied if criterion scores exist
                has_metrics = any(
                    e.evidence_type == "criterion_score" for e in relevant
                )
                if has_metrics:
                    req.is_satisfied = True
                    req.evidence_ref = f"{len(relevant)} metric evidence item(s)"
                else:
                    req.is_satisfied = False
                    req.gap_description = "No per-criterion metrics available"

            elif section == AnnexIVSection.VALIDATION_TESTING:
                # §7: satisfied if methodology is documented
                if report.methodology.methodology_name and report.methodology.description:
                    req.is_satisfied = True
                    req.evidence_ref = f"Methodology: {report.methodology.methodology_name}"
                else:
                    req.is_satisfied = False
                    req.gap_description = "Testing methodology not documented"

            elif section == AnnexIVSection.CYBERSECURITY:
                # §12: satisfied if no unaddressed safety findings
                unaddressed = [
                    e for e in relevant
                    if e.evidence_type == "safety_finding" and not e.passed
                ]
                if not unaddressed:
                    req.is_satisfied = True
                    req.evidence_ref = "No cybersecurity findings or all addressed"
                else:
                    req.is_satisfied = False
                    req.gap_description = (
                        f"{len(unaddressed)} unaddressed safety finding(s)"
                    )

            # Other sections require manual documentation — leave as is
