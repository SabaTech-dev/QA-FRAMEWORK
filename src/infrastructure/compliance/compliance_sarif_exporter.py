"""
SARIF 2.1.0 Integration for Bias/Fairness and Robustness

Extends the SARIF exporter to handle evidence from:
- Bias/fairness testing sessions
- Adversarial robustness testing sessions

Generates SARIF-compliant results that integrate with
the existing accuracy testing SARIF infrastructure.
"""

from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from src.domain.bias_fairness.entities import FairnessReport, BiasTestSession
from src.domain.bias_fairness.value_objects import (
    FairnessMetric,
    FairnessLevel,
)
from src.domain.robustness.entities import RobustnessReport, RobustnessTestSession
from src.domain.robustness.value_objects import (
    AttackType,
    RobustnessLevel,
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


# SARIF taxonomy rules for bias/fairness
_FAIRNESS_RULES = {
    FairnessMetric.DEMOGRAPHIC_PARITY: {
        "id": "QA-FAIR-001",
        "name": "DemographicParity",
        "short_description": "Demographic parity across subgroups",
        "default_level": SARIFLevel.WARNING,
    },
    FairnessMetric.EQUAL_OPPORTUNITY: {
        "id": "QA-FAIR-002",
        "name": "EqualOpportunity",
        "short_description": "Equal opportunity (TPR equality) across subgroups",
        "default_level": SARIFLevel.WARNING,
    },
    FairnessMetric.EQUALIZED_ODDS: {
        "id": "QA-FAIR-003",
        "name": "EqualizedOdds",
        "short_description": "Equalized odds (TPR + FPR equality) across subgroups",
        "default_level": SARIFLevel.WARNING,
    },
    FairnessMetric.DISPARATE_IMPACT: {
        "id": "QA-FAIR-004",
        "name": "DisparateImpact",
        "short_description": "Disparate impact ratio (4/5ths rule)",
        "default_level": SARIFLevel.ERROR,
    },
    FairnessMetric.CALIBORATION: {
        "id": "QA-FAIR-005",
        "name": "PerSubgroupAccuracy",
        "short_description": "Per-subgroup accuracy disparity",
        "default_level": SARIFLevel.WARNING,
    },
}

# SARIF taxonomy rules for robustness
_ROBUSTNESS_RULES = {
    AttackType.FGSM: {
        "id": "QA-ROB-001",
        "name": "FGSMRobustness",
        "short_description": "Robustness against FGSM text attacks",
        "default_level": SARIFLevel.WARNING,
    },
    AttackType.PGD: {
        "id": "QA-ROB-002",
        "name": "PGDRobustness",
        "short_description": "Robustness against PGD text attacks",
        "default_level": SARIFLevel.WARNING,
    },
    AttackType.CHAR_SWAP: {
        "id": "QA-ROB-003",
        "name": "CharSwapRobustness",
        "short_description": "Robustness against character swap attacks",
        "default_level": SARIFLevel.NOTE,
    },
    AttackType.WORD_SUBSTITUTION: {
        "id": "QA-ROB-004",
        "name": "WordSubstitutionRobustness",
        "short_description": "Robustness against word substitution attacks",
        "default_level": SARIFLevel.WARNING,
    },
    AttackType.KEYWORD_INJECTION: {
        "id": "QA-ROB-005",
        "name": "KeywordInjectionRobustness",
        "short_description": "Robustness against keyword injection attacks",
        "default_level": SARIFLevel.WARNING,
    },
    AttackType.SENTENCE_REORDER: {
        "id": "QA-ROB-006",
        "name": "SentenceReorderRobustness",
        "short_description": "Robustness against sentence reordering attacks",
        "default_level": SARIFLevel.NOTE,
    },
    AttackType.COMBINED: {
        "id": "QA-ROB-007",
        "name": "CombinedAttackRobustness",
        "short_description": "Robustness against combined attack methods",
        "default_level": SARIFLevel.ERROR,
    },
}


class ComplianceSARIFExporter:
    """
    Unified SARIF exporter for all compliance testing domains.

    Generates SARIF 2.1.0 reports from:
    - Accuracy test sessions (delegates to existing SARIFExporter)
    - Bias/fairness reports
    - Robustness reports

    Usage:
        exporter = ComplianceSARIFExporter()
        report = exporter.export_fairness(fairness_report)
        report = exporter.export_robustness(robustness_report)
    """

    def export_fairness(
        self,
        fairness_report: FairnessReport,
        system_description: Optional[SystemDescription] = None,
    ) -> SARIFReport:
        """
        Generate a SARIF 2.1.0 report from a fairness report.

        Args:
            fairness_report: FairnessReport with subgroup analyses
            system_description: Optional system metadata

        Returns:
            SARIFReport with one run containing fairness results
        """
        run = SARIFRun(
            tool_name="qa-framework-fairness",
            tool_version="1.0.0",
            tool_information_uri="https://github.com/SabaTech-dev/QA-FRAMEWORK",
            taxonomy=self._build_fairness_taxonomy(),
        )

        # Add invocation
        run.invocations.append({
            "executionSuccessful": True,
            "exitCode": 0,
            "toolExecutionNotifications": [
                {
                    "level": "note",
                    "message": {
                        "text": (
                            f"Fairness analysis: {fairness_report.groups_analyzed} groups, "
                            f"{fairness_report.total_samples} samples. "
                            f"Overall: {fairness_report.overall_fairness_level.value}. "
                            f"Disparate impact: {fairness_report.overall_disparate_impact:.2f}."
                        )
                    },
                }
            ],
            "properties": {
                "groupsAnalyzed": fairness_report.groups_analyzed,
                "totalSamples": fairness_report.total_samples,
                "overallFairnessLevel": fairness_report.overall_fairness_level.value,
                "biasDetected": fairness_report.bias_detected,
                "disparateImpact": fairness_report.overall_disparate_impact,
            },
        })

        # Build locations
        locations = self._build_system_locations(system_description)

        # Add results for each subgroup analysis
        for analysis in fairness_report.subgroup_analyses:
            self._add_fairness_subgroup_results(run, analysis, locations)

        # Add overall result
        overall_level = self._fairness_level_to_sarif(fairness_report.overall_fairness_level)
        run.add_result(
            rule_id="QA-FAIR-OVERALL",
            level=overall_level,
            kind=SARIFResultKind.FAIL if fairness_report.bias_detected else SARIFResultKind.PASS,
            message=(
                f"Overall fairness: {fairness_report.overall_fairness_level.value}. "
                f"Biased subgroups: {fairness_report.biased_subgroup_count}/{fairness_report.groups_analyzed}. "
                f"Disparate impact: {fairness_report.overall_disparate_impact:.2f}"
            ),
            locations=locations,
            properties={
                "overall_fairness_level": fairness_report.overall_fairness_level.value,
                "bias_detected": fairness_report.bias_detected,
                "overall_disparate_impact": fairness_report.overall_disparate_impact,
                "groups_analyzed": fairness_report.groups_analyzed,
                "biased_subgroup_count": fairness_report.biased_subgroup_count,
            },
        )

        return SARIFReport(runs=[run])

    def export_robustness(
        self,
        robustness_report: RobustnessReport,
        system_description: Optional[SystemDescription] = None,
    ) -> SARIFReport:
        """
        Generate a SARIF 2.1.0 report from a robustness report.

        Args:
            robustness_report: RobustnessReport with attack results
            system_description: Optional system metadata

        Returns:
            SARIFReport with one run containing robustness results
        """
        run = SARIFRun(
            tool_name="qa-framework-robustness",
            tool_version="1.0.0",
            tool_information_uri="https://github.com/SabaTech-dev/QA-FRAMEWORK",
            taxonomy=self._build_robustness_taxonomy(),
        )

        # Add invocation
        run.invocations.append({
            "executionSuccessful": True,
            "exitCode": 0,
            "toolExecutionNotifications": [
                {
                    "level": "note",
                    "message": {
                        "text": (
                            f"Robustness evaluation: {robustness_report.attacks_tested} attacks, "
                            f"{robustness_report.attack_type_count} types. "
                            f"Overall score: {robustness_report.overall_robustness_score:.1%}. "
                            f"Level: {robustness_report.overall_robustness_level.value}."
                        )
                    },
                }
            ],
            "properties": {
                "attacksTested": robustness_report.attacks_tested,
                "attackTypeCount": robustness_report.attack_type_count,
                "overallRobustnessScore": round(robustness_report.overall_robustness_score, 4),
                "overallRobustnessLevel": robustness_report.overall_robustness_level.value,
                "averageDegradation": round(robustness_report.average_degradation, 4),
                "worstDegradation": round(robustness_report.worst_degradation, 4),
            },
        })

        # Build locations
        locations = self._build_system_locations(system_description)

        # Add results for each attack
        for attack in robustness_report.attack_results:
            self._add_robustness_attack_results(run, attack, locations)

        # Add overall result
        overall_level = self._robustness_level_to_sarif(robustness_report.overall_robustness_level)
        run.add_result(
            rule_id="QA-ROB-OVERALL",
            level=overall_level,
            kind=SARIFResultKind.PASS
            if robustness_report.overall_robustness_score >= 0.8
            else SARIFResultKind.FAIL,
            message=(
                f"Overall robustness: {robustness_report.overall_robustness_level.value} "
                f"(score: {robustness_report.overall_robustness_score:.1%}). "
                f"Average degradation: {robustness_report.average_degradation:.1%}. "
                f"Worst degradation: {robustness_report.worst_degradation:.1%}"
            ),
            locations=locations,
            properties={
                "overall_robustness_score": round(robustness_report.overall_robustness_score, 4),
                "overall_robustness_level": robustness_report.overall_robustness_level.value,
                "average_degradation": round(robustness_report.average_degradation, 4),
                "worst_degradation": round(robustness_report.worst_degradation, 4),
            },
        )

        return SARIFReport(runs=[run])

    # -- Private helpers --

    def _add_fairness_subgroup_results(
        self,
        run: SARIFRun,
        analysis,
        locations: list,
    ) -> None:
        """Add SARIF results for a single subgroup analysis."""
        subgroup_locations = [
            {
                "logicalLocations": [
                    {
                        "name": analysis.subgroup_name,
                        "kind": "subgroup",
                        "properties": {
                            "protectedAttribute": analysis.protected_attribute.value,
                            "sampleSize": analysis.sample_size,
                        },
                    }
                ]
            }
        ]

        # Per-metric results
        for metric in analysis.metrics:
            rule_cfg = _FAIRNESS_RULES.get(metric.metric)
            rule_id = rule_cfg["id"] if rule_cfg else "QA-FAIR-UNKNOWN"

            # Level based on metric value and fairness
            if metric.is_fair:
                level = SARIFLevel.NONE
                kind = SARIFResultKind.PASS
            elif metric.disparity_from_parity <= 0.15:
                level = SARIFLevel.NOTE
                kind = SARIFResultKind.REVIEW
            else:
                level = SARIFLevel.WARNING
                kind = SARIFResultKind.FAIL

            run.add_result(
                rule_id=rule_id,
                level=level,
                kind=kind,
                message=(
                    f"{analysis.subgroup_name}: {metric.metric.value} = {metric.value:.3f} "
                    f"(n={metric.sample_size}, fairness: "
                    f"{'fair' if metric.is_fair else 'biased'})"
                ),
                locations=locations + subgroup_locations,
                properties={
                    "subgroup": analysis.subgroup_name,
                    "protected_attribute": analysis.protected_attribute.value,
                    "metric": metric.metric.value,
                    "value": round(metric.value, 4),
                    "sample_size": metric.sample_size,
                    "is_fair": metric.is_fair,
                },
            )

        # Subgroup overall
        subgroup_level = self._fairness_level_to_sarif(analysis.overall_fairness_level)
        run.add_result(
            rule_id="QA-FAIR-SUBGROUP",
            level=subgroup_level,
            kind=SARIFResultKind.FAIL if analysis.bias_detected else SARIFResultKind.PASS,
            message=(
                f"Subgroup {analysis.subgroup_name}: "
                f"{analysis.overall_fairness_level.value} "
                f"({analysis.sample_size} samples, "
                f"{analysis.metric_count} metrics)"
            ),
            locations=locations + subgroup_locations,
            properties={
                "subgroup": analysis.subgroup_name,
                "fairness_level": analysis.overall_fairness_level.value,
                "bias_detected": analysis.bias_detected,
            },
        )

    def _add_robustness_attack_results(
        self,
        run: SARIFRun,
        attack,
        locations: list,
    ) -> None:
        """Add SARIF results for a single attack result."""
        rule_cfg = _ROBUSTNESS_RULES.get(attack.attack_type)
        rule_id = rule_cfg["id"] if rule_cfg else "QA-ROB-UNKNOWN"

        attack_locations = [
            {
                "logicalLocations": [
                    {
                        "name": f"attack-{attack.attack_type.value}",
                        "kind": "attack",
                        "properties": {
                            "attackType": attack.attack_type.value,
                            "epsilon": attack.epsilon,
                        },
                    }
                ]
            }
        ]

        level = self._robustness_level_to_sarif(attack.robustness_level)
        kind = (
            SARIFResultKind.PASS
            if attack.robustness_score >= 0.8
            else SARIFResultKind.FAIL
        )

        run.add_result(
            rule_id=rule_id,
            level=level,
            kind=kind,
            message=(
                f"{attack.attack_type.value} (ε={attack.epsilon}): "
                f"robustness={attack.robustness_score:.1%}, "
                f"degradation={attack.accuracy_degradation:.1%}, "
                f"success_rate={attack.success_rate:.1%} "
                f"({attack.successful_attacks}/{attack.total_samples})"
            ),
            locations=locations + attack_locations,
            properties={
                "attack_type": attack.attack_type.value,
                "epsilon": attack.epsilon,
                "robustness_score": round(attack.robustness_score, 4),
                "accuracy_degradation": round(attack.accuracy_degradation, 4),
                "success_rate": round(attack.success_rate, 4),
                "total_samples": attack.total_samples,
                "successful_attacks": attack.successful_attacks,
                "robustness_level": attack.robustness_level.value,
            },
        )

    @staticmethod
    def _build_fairness_taxonomy() -> list:
        return [
            {
                "id": cfg["id"],
                "name": cfg["name"],
                "shortDescription": {"text": cfg["short_description"]},
                "defaultConfiguration": {"level": cfg["default_level"].value},
                "properties": {
                    "metric": metric.value,
                    "tags": ["ai-act-compliance", "bias-fairness", "art-10"],
                },
            }
            for metric, cfg in _FAIRNESS_RULES.items()
        ] + [
            {
                "id": "QA-FAIR-OVERALL",
                "name": "OverallFairness",
                "shortDescription": {"text": "Overall fairness assessment across all subgroups"},
                "defaultConfiguration": {"level": SARIFLevel.WARNING.value},
                "properties": {"tags": ["ai-act-compliance", "bias-fairness", "art-10"]},
            },
            {
                "id": "QA-FAIR-SUBGROUP",
                "name": "SubgroupFairness",
                "shortDescription": {"text": "Per-subgroup fairness assessment"},
                "defaultConfiguration": {"level": SARIFLevel.NOTE.value},
                "properties": {"tags": ["ai-act-compliance", "bias-fairness"]},
            },
        ]

    @staticmethod
    def _build_robustness_taxonomy() -> list:
        return [
            {
                "id": cfg["id"],
                "name": cfg["name"],
                "shortDescription": {"text": cfg["short_description"]},
                "defaultConfiguration": {"level": cfg["default_level"].value},
                "properties": {
                    "attack_type": at.value,
                    "tags": ["ai-act-compliance", "robustness", "art-15"],
                },
            }
            for at, cfg in _ROBUSTNESS_RULES.items()
        ] + [
            {
                "id": "QA-ROB-OVERALL",
                "name": "OverallRobustness",
                "shortDescription": {"text": "Overall robustness assessment across all attack types"},
                "defaultConfiguration": {"level": SARIFLevel.WARNING.value},
                "properties": {"tags": ["ai-act-compliance", "robustness", "art-15"]},
            },
        ]

    @staticmethod
    def _build_system_locations(system: Optional[SystemDescription]) -> list:
        if not system or not system.system_id:
            return [{"logicalLocations": [{"name": "unknown-system", "kind": "aiSystem"}]}]
        return [
            {
                "logicalLocations": [
                    {
                        "name": system.system_id,
                        "kind": "aiSystem",
                        "properties": {
                            "fullyQualifiedName": system.system_id,
                            "provider": system.provider_name,
                        },
                    }
                ]
            }
        ]

    @staticmethod
    def _fairness_level_to_sarif(level: FairnessLevel) -> SARIFLevel:
        mapping = {
            FairnessLevel.FAIR: SARIFLevel.NONE,
            FairnessLevel.MARGINAL: SARIFLevel.NOTE,
            FairnessLevel.BIASED: SARIFLevel.WARNING,
            FairnessLevel.SEVERELY_BIASED: SARIFLevel.ERROR,
        }
        return mapping.get(level, SARIFLevel.WARNING)

    @staticmethod
    def _robustness_level_to_sarif(level: RobustnessLevel) -> SARIFLevel:
        mapping = {
            RobustnessLevel.ROBUST: SARIFLevel.NONE,
            RobustnessLevel.MODERATELY_ROBUST: SARIFLevel.NOTE,
            RobustnessLevel.WEAK: SARIFLevel.WARNING,
            RobustnessLevel.VULNERABLE: SARIFLevel.ERROR,
        }
        return mapping.get(level, SARIFLevel.WARNING)
