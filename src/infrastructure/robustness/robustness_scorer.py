"""
Robustness Scorer

Computes comprehensive robustness scores from attack results.
Aggregates per-attack metrics into system-level robustness
assessment for compliance reporting.
"""

from typing import List, Optional

from src.domain.robustness.entities import (
    AttackResult,
    RobustnessReport,
    RobustnessTestSession,
)
from src.domain.robustness.value_objects import (
    AttackType,
    RobustnessLevel,
)


class RobustnessScorer:
    """
    Computes robustness scores from attack results.

    Usage:
        scorer = RobustnessScorer()
        report = scorer.score_session(session)
    """

    def __init__(
        self,
        robustness_threshold: float = 0.8,
        degradation_warning: float = 0.25,
    ):
        """
        Args:
            robustness_threshold: Minimum acceptable robustness score (0-1)
            degradation_warning: Accuracy degradation level for warnings
        """
        if not 0.0 < robustness_threshold <= 1.0:
            raise ValueError(f"robustness_threshold must be in (0.0, 1.0], got {robustness_threshold}")
        if not 0.0 <= degradation_warning < 1.0:
            raise ValueError(f"degradation_warning must be in [0.0, 1.0), got {degradation_warning}")

        self.robustness_threshold = robustness_threshold
        self.degradation_warning = degradation_warning

    def score_session(
        self,
        session: RobustnessTestSession,
        system_id: str = "",
        model_name: str = "",
    ) -> RobustnessReport:
        """
        Create a robustness report from a test session.

        Args:
            session: Completed robustness test session
            system_id: System identifier for the report
            model_name: Model name for the report

        Returns:
            RobustnessReport with aggregated scores
        """
        report = RobustnessReport(
            system_id=system_id or session.system_id,
            model_name=model_name or session.model_name,
            methodology="Adversarial robustness evaluation",
            robustness_threshold=self.robustness_threshold,
        )

        for result in session.attack_results:
            report.add_attack_result(result)

        report.compute_overall_robustness()

        # Add notes based on findings
        if report.overall_robustness_level == RobustnessLevel.VULNERABLE:
            report.notes.append(
                "CRITICAL: Model shows high vulnerability to adversarial attacks. "
                "Consider adversarial training and input validation."
            )
        elif report.overall_robustness_level == RobustnessLevel.WEAK:
            report.notes.append(
                "WARNING: Model has moderate vulnerability. "
                "Review attack vectors and consider robustness improvements."
            )

        return report

    def score_attack_result(
        self,
        result: AttackResult,
        system_id: str = "",
        model_name: str = "",
    ) -> RobustnessReport:
        """
        Create a report from a single attack result.

        Convenience method for evaluating one attack at a time.
        """
        report = RobustnessReport(
            system_id=system_id,
            model_name=model_name,
            methodology="Adversarial robustness evaluation",
            robustness_threshold=self.robustness_threshold,
        )
        report.add_attack_result(result)
        report.compute_overall_robustness()

        return report

    def compute_attack_type_summary(
        self,
        results: List[AttackResult],
    ) -> dict:
        """
        Compute summary statistics grouped by attack type.

        Returns:
            Dict mapping attack type to aggregate metrics
        """
        summary: dict = {}

        for result in results:
            at = result.attack_type.value
            if at not in summary:
                summary[at] = {
                    "attack_type": at,
                    "count": 0,
                    "total_samples": 0,
                    "total_successful": 0,
                    "scores": [],
                    "degradations": [],
                }

            entry = summary[at]
            entry["count"] += 1
            entry["total_samples"] += result.total_samples
            entry["total_successful"] += result.successful_attacks
            entry["scores"].append(result.robustness_score)
            entry["degradations"].append(result.accuracy_degradation)

        # Compute averages
        for at, entry in summary.items():
            n = entry["count"]
            entry["average_score"] = round(sum(entry["scores"]) / n, 4) if n else 0.0
            entry["average_degradation"] = round(sum(entry["degradations"]) / n, 4) if n else 0.0
            entry["success_rate"] = (
                round(entry["total_successful"] / entry["total_samples"], 4)
                if entry["total_samples"] > 0 else 0.0
            )
            # Clean up raw lists
            del entry["scores"]
            del entry["degradations"]

        return summary

    def get_recommendations(
        self,
        report: RobustnessReport,
    ) -> List[str]:
        """
        Generate actionable recommendations based on report findings.

        Returns:
            List of recommendation strings
        """
        recommendations = []

        if report.overall_robustness_level == RobustnessLevel.VULNERABLE:
            recommendations.extend([
                "Implement adversarial training with PGD/FGSM examples",
                "Add input validation and sanitization layers",
                "Consider deploying an adversarial detection filter",
                "Review model architecture for robustness (e.g., certified defenses)",
            ])
        elif report.overall_robustness_level == RobustnessLevel.WEAK:
            recommendations.extend([
                "Augment training data with adversarial examples",
                "Add input preprocessing (typo correction, normalization)",
                "Implement ensemble methods for robustness",
            ])
        elif report.overall_robustness_level == RobustnessLevel.MODERATELY_ROBUST:
            recommendations.extend([
                "Monitor for new attack vectors in production",
                "Consider periodic robustness re-evaluation",
            ])
        else:
            recommendations.append(
                "Model shows good robustness. Continue monitoring."
            )

        # Per-attack-type recommendations
        attack_summary = self.compute_attack_type_summary(report.attack_results)
        for at, stats in attack_summary.items():
            if stats["success_rate"] > 0.3:
                recommendations.append(
                    f"High success rate ({stats['success_rate']:.0%}) for {at} attacks — "
                    f"specific hardening recommended"
                )

        return recommendations
