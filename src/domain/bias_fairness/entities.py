"""
Entities for Bias/Fairness Testing Domain

Core entities for fairness evaluation sessions, subgroup analysis,
and bias test reporting.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from uuid import uuid4
import json

from .value_objects import (
    FairnessMetric,
    FairnessLevel,
    BiasTestStatus,
    Subgroup,
    SubgroupMetric,
    validate_group_name,
)


@dataclass
class SubgroupAnalysis:
    """
    Fairness analysis for a single subgroup.

    Contains per-subgroup metrics, sample sizes, and a fairness
    determination for each protected attribute category.
    """
    subgroup_name: str = ""
    protected_attribute: Subgroup = Subgroup.GENDER
    sample_size: int = 0
    metrics: List[SubgroupMetric] = field(default_factory=list)
    overall_fairness_level: FairnessLevel = FairnessLevel.FAIR
    bias_detected: bool = False
    notes: List[str] = field(default_factory=list)

    def __post_init__(self):
        if self.subgroup_name:
            validate_group_name(self.subgroup_name)

    @property
    def metric_count(self) -> int:
        return len(self.metrics)

    @property
    def average_metric_value(self) -> float:
        if not self.metrics:
            return 0.0
        return sum(m.value for m in self.metrics) / len(self.metrics)

    @property
    def worst_metric(self) -> Optional[SubgroupMetric]:
        """Get the metric with highest disparity from parity."""
        if not self.metrics:
            return None
        return max(self.metrics, key=lambda m: m.disparity_from_parity)

    def compute_fairness(self) -> FairnessLevel:
        """
        Determine fairness level based on metrics.

        Rules:
        - FAIR: all metrics in [0.4, 0.6]
        - MARGINAL: one metric outside [0.35, 0.65]
        - BIASED: one metric outside [0.3, 0.7]
        - SEVERELY_BIASED: one metric outside [0.2, 0.8]
        """
        if not self.metrics:
            self.overall_fairness_level = FairnessLevel.FAIR
            self.bias_detected = False
            return self.overall_fairness_level

        worst = self.worst_metric
        if worst is None:
            self.overall_fairness_level = FairnessLevel.FAIR
            self.bias_detected = False
            return self.overall_fairness_level

        disparity = worst.disparity_from_parity

        if disparity > 0.3:
            self.overall_fairness_level = FairnessLevel.SEVERELY_BIASED
            self.bias_detected = True
        elif disparity > 0.2:
            self.overall_fairness_level = FairnessLevel.BIASED
            self.bias_detected = True
        elif disparity > 0.15:
            self.overall_fairness_level = FairnessLevel.MARGINAL
            self.bias_detected = True
        else:
            self.overall_fairness_level = FairnessLevel.FAIR
            self.bias_detected = False

        return self.overall_fairness_level

    def to_dict(self) -> Dict[str, Any]:
        return {
            "subgroup_name": self.subgroup_name,
            "protected_attribute": self.protected_attribute.value,
            "sample_size": self.sample_size,
            "metrics": [m.to_dict() for m in self.metrics],
            "overall_fairness_level": self.overall_fairness_level.value,
            "bias_detected": self.bias_detected,
            "average_metric_value": round(self.average_metric_value, 4),
            "notes": self.notes,
        }


@dataclass
class FairnessReport:
    """
    Complete fairness evaluation report.

    Aggregates subgroup analyses into a comprehensive fairness
    assessment with cross-subgroup comparisons.
    """
    id: str = field(default_factory=lambda: str(uuid4()))
    system_id: str = ""
    dataset_name: str = ""
    model_name: str = ""

    # Results per subgroup
    subgroup_analyses: List[SubgroupAnalysis] = field(default_factory=list)

    # Aggregate metrics
    total_samples: int = 0
    groups_analyzed: int = 0
    overall_fairness_level: FairnessLevel = FairnessLevel.FAIR
    bias_detected: bool = False
    overall_disparate_impact: float = 1.0  # 4/5ths rule ratio

    # Fairness thresholds
    disparate_impact_threshold: float = 0.8  # 4/5ths rule
    demographic_parity_threshold: float = 0.1  # max deviation

    # Metadata
    assessment_date: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    assessor: str = ""
    methodology: str = ""
    notes: List[str] = field(default_factory=list)
    tenant_id: Optional[str] = None

    @property
    def subgroup_count(self) -> int:
        return len(self.subgroup_analyses)

    @property
    def biased_subgroup_count(self) -> int:
        return sum(1 for a in self.subgroup_analyses if a.bias_detected)

    @property
    def worst_subgroup(self) -> Optional[SubgroupAnalysis]:
        """Get the subgroup with worst fairness."""
        if not self.subgroup_analyses:
            return None
        return max(
            self.subgroup_analyses,
            key=lambda a: max(
                (m.disparity_from_parity for m in a.metrics),
                default=0.0
            ),
        )

    def compute_overall_fairness(self) -> FairnessLevel:
        """
        Determine overall fairness across all subgroups.

        Uses the worst-case approach: overall fairness is the
        worst fairness level across all subgroups.
        """
        if not self.subgroup_analyses:
            self.overall_fairness_level = FairnessLevel.FAIR
            self.bias_detected = False
            return self.overall_fairness_level

        level_order = [
            FairnessLevel.FAIR,
            FairnessLevel.MARGINAL,
            FairnessLevel.BIASED,
            FairnessLevel.SEVERELY_BIASED,
        ]

        worst_level = FairnessLevel.FAIR
        for analysis in self.subgroup_analyses:
            analysis.compute_fairness()
            if level_order.index(analysis.overall_fairness_level) > level_order.index(worst_level):
                worst_level = analysis.overall_fairness_level

        self.overall_fairness_level = worst_level
        self.bias_detected = worst_level != FairnessLevel.FAIR
        self.groups_analyzed = len(self.subgroup_analyses)
        self.total_samples = sum(a.sample_size for a in self.subgroup_analyses)

        # Compute disparate impact (4/5ths rule)
        self._compute_disparate_impact()

        return self.overall_fairness_level

    def _compute_disparate_impact(self) -> None:
        """
        Compute disparate impact ratio using the 4/5ths rule.

        Compares the smallest group's positive outcome rate
        to the largest group's positive outcome rate.
        """
        # Find groups with demographic_parity metrics
        rates = []
        for analysis in self.subgroup_analyses:
            for m in analysis.metrics:
                if m.metric == FairnessMetric.DEMOGRAPHIC_PARITY:
                    rates.append((analysis.subgroup_name, m.value))

        if len(rates) < 2:
            self.overall_disparate_impact = 1.0
            return

        values = [r[1] for r in rates]
        max_rate = max(values)
        min_rate = min(values)

        if max_rate == 0:
            self.overall_disparate_impact = 1.0
        else:
            self.overall_disparate_impact = round(min_rate / max_rate, 4)

    def add_subgroup_analysis(self, analysis: SubgroupAnalysis) -> None:
        """Add a subgroup analysis to the report."""
        self.subgroup_analyses.append(analysis)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary (excludes tenant_id)."""
        return {
            "id": self.id,
            "system_id": self.system_id,
            "dataset_name": self.dataset_name,
            "model_name": self.model_name,
            "subgroup_analyses": [a.to_dict() for a in self.subgroup_analyses],
            "aggregate": {
                "total_samples": self.total_samples,
                "groups_analyzed": self.groups_analyzed,
                "overall_fairness_level": self.overall_fairness_level.value,
                "bias_detected": self.bias_detected,
                "overall_disparate_impact": self.overall_disparate_impact,
                "biased_subgroup_count": self.biased_subgroup_count,
            },
            "thresholds": {
                "disparate_impact_threshold": self.disparate_impact_threshold,
                "demographic_parity_threshold": self.demographic_parity_threshold,
            },
            "assessment_date": self.assessment_date.isoformat(),
            "assessor": self.assessor,
            "methodology": self.methodology,
            "notes": self.notes,
        }

    def to_json(self, indent: int = 2) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


@dataclass
class BiasTestSession:
    """
    A session for batch bias/fairness evaluation.

    Groups multiple subgroup analyses and tracks progress.
    """
    id: str = field(default_factory=lambda: str(uuid4()))
    tenant_id: Optional[str] = None

    # Config
    name: str = ""
    description: str = ""
    system_id: str = ""
    dataset_name: str = ""
    model_name: str = ""

    # Contents
    analyses: List[SubgroupAnalysis] = field(default_factory=list)
    report: Optional[FairnessReport] = None

    # Timing
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    total_time_ms: int = 0

    status: BiasTestStatus = BiasTestStatus.PENDING
    error_message: Optional[str] = None

    @property
    def is_completed(self) -> bool:
        return self.status in (
            BiasTestStatus.COMPLETED,
            BiasTestStatus.FAILED,
            BiasTestStatus.PARTIAL,
        )

    @property
    def analysis_count(self) -> int:
        return len(self.analyses)

    @property
    def total_samples(self) -> int:
        return sum(a.sample_size for a in self.analyses)

    def add_analysis(self, analysis: SubgroupAnalysis) -> None:
        """Add a subgroup analysis to the session."""
        self.analyses.append(analysis)

    def complete(
        self,
        status: BiasTestStatus = None,
        error: str = None,
    ) -> None:
        """Mark session as completed."""
        self.status = status or BiasTestStatus.COMPLETED
        self.completed_at = datetime.now(timezone.utc)
        self.total_time_ms = int(
            (self.completed_at - self.started_at).total_seconds() * 1000
        )
        if error:
            self.error_message = error
            self.status = BiasTestStatus.FAILED

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary (excludes tenant_id)."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "system_id": self.system_id,
            "dataset_name": self.dataset_name,
            "model_name": self.model_name,
            "analyses": [a.to_dict() for a in self.analyses],
            "report": self.report.to_dict() if self.report else None,
            "status": self.status.value,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "total_time_ms": self.total_time_ms,
            "analysis_count": self.analysis_count,
            "total_samples": self.total_samples,
        }
