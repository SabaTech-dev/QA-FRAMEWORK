"""
SARIF 2.1.0 Exporter

Transforms AccuracyTestSession results into a SARIF 2.1.0
report compatible with CI/CD tools (GitHub Code Scanning,
Azure DevOps, SonarQube, etc.).

SARIF spec: https://docs.oasis-open.org/sarif/sarif/v2.1.0/

Each evaluation result becomes a SARIF result entry:
- ruleId identifies the evaluation criterion
- level maps to severity (error/warning/note)
- kind indicates pass/fail/review status
- locations reference the benchmark/system being tested
"""

from datetime import datetime, timezone
from typing import Optional

from src.domain.accuracy_testing.entities import (
    AccuracyTestSession,
    AccuracyEvaluation,
)
from src.domain.accuracy_testing.value_objects import (
    AccuracyLevel,
    EvaluationCriterion,
    EvaluationStatus,
    ResponseVerdict,
)
from src.domain.compliance.entities import (
    SARIFReport,
    SARIFRun,
    SystemDescription,
)
from src.domain.compliance.value_objects import (
    SARIFLevel,
    SARIFResultKind,
)


# SARIF taxonomy rules for evaluation criteria
_CRITERION_RULES = {
    EvaluationCriterion.FACTUAL_ACCURACY: {
        "id": "QA-ACC-001",
        "name": "FactualAccuracy",
        "short_description": "AI response factual accuracy against ground truth",
        "default_level": SARIFLevel.ERROR,
    },
    EvaluationCriterion.LEGAL_REASONING: {
        "id": "QA-ACC-002",
        "name": "LegalReasoning",
        "short_description": "Quality of legal argumentation in AI response",
        "default_level": SARIFLevel.WARNING,
    },
    EvaluationCriterion.CITATION_CORRECTNESS: {
        "id": "QA-ACC-003",
        "name": "CitationCorrectness",
        "short_description": "Correctness of legal citations in AI response",
        "default_level": SARIFLevel.WARNING,
    },
    EvaluationCriterion.COMPLETENESS: {
        "id": "QA-ACC-004",
        "name": "Completeness",
        "short_description": "Completeness of AI response vs benchmark key points",
        "default_level": SARIFLevel.WARNING,
    },
    EvaluationCriterion.NUANCE_HANDLING: {
        "id": "QA-ACC-005",
        "name": "NuanceHandling",
        "short_description": "Handling of nuance and edge cases in AI response",
        "default_level": SARIFLevel.NOTE,
    },
    EvaluationCriterion.HARMFULNESS_SAFETY: {
        "id": "QA-ACC-006",
        "name": "HarmfulnessSafety",
        "short_description": "Safety check for harmful AI output",
        "default_level": SARIFLevel.ERROR,
    },
}


class SARIFExporter:
    """
    Exports AccuracyTestSession results as SARIF 2.1.0.

    Usage:
        exporter = SARIFExporter()
        report = exporter.export(test_session, system_description)
        print(report.to_json())
    """

    def export(
        self,
        test_session: AccuracyTestSession,
        system_description: Optional[SystemDescription] = None,
    ) -> SARIFReport:
        """
        Generate a SARIF 2.1.0 report from a testing session.

        Args:
            test_session: AccuracyTestSession with evaluation results
            system_description: Optional system metadata for locations

        Returns:
            SARIFReport with one run containing all evaluation results
        """
        # Build tool driver info
        tool_name = "qa-framework"
        tool_version = "1.0.0"
        information_uri = "https://github.com/SabaTech-dev/QA-FRAMEWORK"

        # Build taxonomy from criteria rules
        taxonomy = [
            {
                "id": cfg["id"],
                "name": cfg["name"],
                "shortDescription": {"text": cfg["short_description"]},
                "defaultConfiguration": {"level": cfg["default_level"].value},
                "properties": {
                    "criterion": criterion.value,
                    "tags": ["ai-act-compliance", "accuracy-testing"],
                },
            }
            for criterion, cfg in _CRITERION_RULES.items()
        ]

        run = SARIFRun(
            tool_name=tool_name,
            tool_version=tool_version,
            tool_information_uri=information_uri,
            taxonomy=taxonomy,
        )

        # Add invocation record
        run.invocations.append(self._create_invocation(test_session))

        # Add results for each evaluation
        for evaluation in test_session.evaluations:
            self._add_evaluation_results(run, evaluation, system_description)

        # Build the report
        report = SARIFReport(
            runs=[run],
            generated_at=datetime.now(timezone.utc),
        )

        if system_description:
            report.tenant_id = None  # never expose tenant in SARIF

        return report

    def _create_invocation(
        self, session: AccuracyTestSession
    ) -> dict:
        """Create a SARIF invocation object for the test session."""
        end_time = session.completed_at or datetime.now(timezone.utc)
        duration_seconds = session.total_time_ms / 1000.0 if session.total_time_ms else 0.0

        # Determine exit status
        if session.status == EvaluationStatus.COMPLETED:
            exit_code = 0
            execution_successful = True
        elif session.status == EvaluationStatus.PARTIAL:
            exit_code = 0
            execution_successful = True
        else:
            exit_code = 1
            execution_successful = False

        return {
            "executionSuccessful": execution_successful,
            "exitCode": exit_code,
            "startTimeUtc": session.started_at.isoformat(),
            "endTimeUtc": end_time.isoformat(),
            "toolExecutionNotifications": [
                {
                    "level": "note",
                    "message": {
                        "text": (
                            f"Session: {session.name or session.id}. "
                            f"Evaluations: {session.evaluations_completed}. "
                            f"Passed: {session.evaluations_passed}. "
                            f"Pass rate: {session.pass_rate:.1%}. "
                            f"Average score: {session.average_score:.1%}."
                        )
                    },
                },
            ],
            "properties": {
                "totalDurationSeconds": round(duration_seconds, 3),
                "evaluationsCompleted": session.evaluations_completed,
                "evaluationsPassed": session.evaluations_passed,
                "hallucinationCount": session.hallucination_count,
                "aiModel": session.ai_model,
            },
        }

    def _add_evaluation_results(
        self,
        run: SARIFRun,
        evaluation: AccuracyEvaluation,
        system: Optional[SystemDescription],
    ) -> None:
        """Add SARIF result entries for a single evaluation."""

        # Build location reference
        locations = self._build_locations(evaluation, system)

        # Overall evaluation result
        overall_level = self._score_to_sarif_level(evaluation.overall_score)
        overall_kind = SARIFResultKind.PASS if evaluation.passed else SARIFResultKind.FAIL

        run.add_result(
            rule_id="QA-OVERALL",
            level=overall_level,
            kind=overall_kind,
            message=(
                f"Benchmark {evaluation.benchmark_id}: verdict={evaluation.verdict.value}, "
                f"score={evaluation.overall_score:.1%}, "
                f"model={evaluation.ai_model or 'unknown'}"
            ),
            locations=locations,
            properties={
                "benchmark_id": evaluation.benchmark_id,
                "overall_score": round(evaluation.overall_score, 4),
                "verdict": evaluation.verdict.value,
                "accuracy_level": evaluation.accuracy_level.value,
                "ai_model": evaluation.ai_model,
                "evaluation_time_ms": evaluation.evaluation_time_ms,
                "has_hallucinations": evaluation.has_hallucinations,
            },
        )

        # Per-criterion results
        for cs in evaluation.criterion_scores:
            cfg = _CRITERION_RULES.get(cs.criterion)
            rule_id = cfg["id"] if cfg else f"QA-ACC-UNKNOWN"

            # Level based on score vs threshold
            if cs.score >= 0.6:
                level = SARIFLevel.NONE
                kind = SARIFResultKind.PASS
            elif cs.score >= 0.3:
                level = SARIFLevel.WARNING
                kind = SARIFResultKind.FAIL
            else:
                level = SARIFLevel.ERROR
                kind = SARIFResultKind.FAIL

            run.add_result(
                rule_id=rule_id,
                level=level,
                kind=kind,
                message=f"{cs.criterion.value}: {cs.explanation} (score: {cs.score:.1%})",
                locations=locations,
                partial_fingerprints={
                    "criterion": cs.criterion.value,
                    "score": str(round(cs.score, 4)),
                },
                properties={
                    "criterion": cs.criterion.value,
                    "score": round(cs.score, 4),
                    "percentage": round(cs.percentage, 2),
                    "level": cs.level.value,
                    "explanation": cs.explanation,
                    "evidence": cs.evidence,
                },
            )

        # Hallucinations as separate findings (safety)
        if evaluation.has_hallucinations:
            for idx, hallucination in enumerate(evaluation.hallucinations):
                run.add_result(
                    rule_id="QA-SAFETY-001",
                    level=SARIFLevel.ERROR,
                    kind=SARIFResultKind.FAIL,
                    message=(
                        f"Hallucination/safety finding #{idx + 1}: "
                        f"'{hallucination[:200]}'"
                    ),
                    locations=locations,
                    properties={
                        "finding_type": "hallucination",
                        "benchmark_id": evaluation.benchmark_id,
                        "hallucination_index": idx,
                    },
                )

    def _build_locations(
        self,
        evaluation: AccuracyEvaluation,
        system: Optional[SystemDescription],
    ) -> list[dict]:
        """
        Build SARIF location objects.

        References the AI system and benchmark as logical locations
        (no physical file/line needed for compliance testing).
        """
        locations = [
            {
                "logicalLocations": [
                    {
                        "name": evaluation.benchmark_id or "unknown-benchmark",
                        "kind": "benchmark",
                        "properties": {
                            "fullyQualifiedName": evaluation.benchmark_id,
                        },
                    }
                ]
            }
        ]

        if system and system.system_id:
            locations[0]["logicalLocations"].append({
                "name": system.system_id,
                "kind": "aiSystem",
                "properties": {
                    "fullyQualifiedName": system.system_id,
                    "provider": system.provider_name,
                },
            })

        return locations

    @staticmethod
    def _score_to_sarif_level(score: float) -> SARIFLevel:
        """Map a 0-1 score to SARIF severity level."""
        if score >= 0.6:
            return SARIFLevel.NONE      # passing — no issue
        elif score >= 0.3:
            return SARIFLevel.WARNING   # marginal — warning
        else:
            return SARIFLevel.ERROR     # failing — error
