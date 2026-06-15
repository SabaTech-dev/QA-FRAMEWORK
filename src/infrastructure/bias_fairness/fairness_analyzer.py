"""
Statistical Fairness Analyzer

Implements statistical tests for fairness evaluation including:
- Demographic parity (statistical parity)
- Equal opportunity (true positive rate equality)
- Equalized odds (TPR + FPR equality)
- Disparate impact (4/5ths rule)
- Per-subgroup accuracy analysis

All computations are deterministic and use only stdlib math.
For production use with large datasets, consider pandas/numpy.
"""

import math
from typing import List, Tuple, Optional

from src.domain.bias_fairness.entities import (
    SubgroupAnalysis,
    FairnessReport,
    BiasTestSession,
)
from src.domain.bias_fairness.value_objects import (
    FairnessMetric,
    FairnessLevel,
    Subgroup,
    SubgroupMetric,
    BiasTestStatus,
)


class StatisticalFairnessAnalyzer:
    """
    Analyzes fairness across demographic subgroups using statistical metrics.

    Usage:
        analyzer = StatisticalFairnessAnalyzer()
        report = analyzer.analyze_session(
            predictions=all_predictions,
            labels=all_labels,
            subgroup_values=all_subgroups,
            protected_attribute=Subgroup.GENDER,
        )
    """

    def __init__(
        self,
        fairness_threshold: float = 0.1,
        disparate_impact_threshold: float = 0.8,
    ):
        """
        Args:
            fairness_threshold: Max allowed deviation from parity (0.0-1.0)
            disparate_impact_threshold: Minimum disparate impact ratio (4/5ths rule)
        """
        if not 0.0 < fairness_threshold < 1.0:
            raise ValueError(f"fairness_threshold must be in (0.0, 1.0), got {fairness_threshold}")
        if not 0.0 < disparate_impact_threshold <= 1.0:
            raise ValueError(
                f"disparate_impact_threshold must be in (0.0, 1.0], got {disparate_impact_threshold}"
            )
        self.fairness_threshold = fairness_threshold
        self.disparate_impact_threshold = disparate_impact_threshold

    def compute_demographic_parity(
        self,
        predictions: List[bool],
        subgroup_labels: List[str],
    ) -> List[SubgroupMetric]:
        """
        Compute demographic parity per subgroup.

        Demographic parity: P(Ŷ=1 | G=g) should be equal across groups g.
        Returns metric per unique subgroup value.
        """
        if len(predictions) != len(subgroup_labels):
            raise ValueError(
                f"predictions ({len(predictions)}) and subgroup_labels "
                f"({len(subgroup_labels)}) must have same length"
            )
        if not predictions:
            return []

        groups = self._group_by(subgroup_labels)
        metrics = []

        for group_name, indices in groups.items():
            positive_count = sum(1 for i in indices if predictions[i])
            rate = positive_count / len(indices)
            ci = self._wilson_ci(positive_count, len(indices))

            metrics.append(SubgroupMetric(
                metric=FairnessMetric.DEMOGRAPHIC_PARITY,
                value=rate,
                sample_size=len(indices),
                confidence_interval_lower=ci[0],
                confidence_interval_upper=ci[1],
            ))

        return metrics

    def compute_equal_opportunity(
        self,
        predictions: List[bool],
        labels: List[bool],
        subgroup_labels: List[str],
    ) -> List[SubgroupMetric]:
        """
        Compute equal opportunity per subgroup.

        Equal opportunity: P(Ŷ=1 | Y=1, G=g) should be equal across groups.
        Only considers positive-label samples (true positive rate).
        """
        if not (len(predictions) == len(labels) == len(subgroup_labels)):
            raise ValueError("All input lists must have same length")
        if not predictions:
            return []

        groups = self._group_by(subgroup_labels)
        metrics = []

        for group_name, indices in groups.items():
            # Filter to positive labels only
            positive_indices = [i for i in indices if i < len(labels) and labels[i]]
            if not positive_indices:
                continue

            true_positives = sum(
                1 for i in positive_indices
                if i < len(predictions) and predictions[i]
            )
            tpr = true_positives / len(positive_indices)
            ci = self._wilson_ci(true_positives, len(positive_indices))

            metrics.append(SubgroupMetric(
                metric=FairnessMetric.EQUAL_OPPORTUNITY,
                value=tpr,
                sample_size=len(positive_indices),
                confidence_interval_lower=ci[0],
                confidence_interval_upper=ci[1],
            ))

        return metrics

    def compute_equalized_odds(
        self,
        predictions: List[bool],
        labels: List[bool],
        subgroup_labels: List[str],
    ) -> List[SubgroupMetric]:
        """
        Compute equalized odds per subgroup.

        Equalized odds: both TPR and FPR should be equal across groups.
        Returns the average of TPR and FPR per group.
        """
        if not (len(predictions) == len(labels) == len(subgroup_labels)):
            raise ValueError("All input lists must have same length")
        if not predictions:
            return []

        groups = self._group_by(subgroup_labels)
        metrics = []

        for group_name, indices in groups.items():
            positive_label_idx = [i for i in indices if i < len(labels) and labels[i]]
            negative_label_idx = [i for i in indices if i < len(labels) and not labels[i]]

            # TPR
            tpr = 0.0
            if positive_label_idx:
                tp = sum(1 for i in positive_label_idx if predictions[i])
                tpr = tp / len(positive_label_idx)

            # FPR
            fpr = 0.0
            if negative_label_idx:
                fp = sum(1 for i in negative_label_idx if predictions[i])
                fpr = fp / len(negative_label_idx)

            # Equalized odds = average of TPR and FPR
            combined = (tpr + fpr) / 2.0
            ci = self._wilson_ci(
                int(combined * len(indices)),
                len(indices),
            )

            metrics.append(SubgroupMetric(
                metric=FairnessMetric.EQUALIZED_ODDS,
                value=combined,
                sample_size=len(indices),
                confidence_interval_lower=ci[0],
                confidence_interval_upper=ci[1],
            ))

        return metrics

    def compute_disparate_impact(
        self,
        predictions: List[bool],
        subgroup_labels: List[str],
    ) -> List[SubgroupMetric]:
        """
        Compute disparate impact ratio per subgroup pair.

        Disparate impact: P(Ŷ=1 | G=g1) / P(Ŷ=1 | G=g2) >= 0.8 (4/5ths rule)
        Returns ratio for each subgroup relative to the majority group.
        """
        dp_metrics = self.compute_demographic_parity(predictions, subgroup_labels)
        if len(dp_metrics) < 2:
            return dp_metrics

        # Find the group with highest positive rate as reference
        max_rate = max(m.value for m in dp_metrics)
        if max_rate == 0:
            return dp_metrics

        return [
            SubgroupMetric(
                metric=FairnessMetric.DISPARATE_IMPACT,
                value=m.value / max_rate,
                sample_size=m.sample_size,
                confidence_interval_lower=m.confidence_interval_lower / max_rate if max_rate > 0 else 0.0,
                confidence_interval_upper=m.confidence_interval_upper / max_rate if max_rate > 0 else 0.0,
            )
            for m in dp_metrics
        ]

    def compute_per_subgroup_accuracy(
        self,
        predictions: List[bool],
        labels: List[bool],
        subgroup_labels: List[str],
    ) -> List[SubgroupMetric]:
        """
        Compute accuracy per subgroup.

        This is a custom metric: per-group accuracy to detect
        performance disparities across demographic groups.
        """
        if not (len(predictions) == len(labels) == len(subgroup_labels)):
            raise ValueError("All input lists must have same length")
        if not predictions:
            return []

        groups = self._group_by(subgroup_labels)
        metrics = []

        for group_name, indices in groups.items():
            correct = sum(
                1 for i in indices
                if i < len(predictions) and i < len(labels)
                and predictions[i] == labels[i]
            )
            accuracy = correct / len(indices) if indices else 0.0
            ci = self._wilson_ci(correct, len(indices))

            metrics.append(SubgroupMetric(
                metric=FairnessMetric.CALIBRATION,  # using calibration slot for accuracy
                value=accuracy,
                sample_size=len(indices),
                confidence_interval_lower=ci[0],
                confidence_interval_upper=ci[1],
            ))

        return metrics

    def analyze_session(
        self,
        predictions: List[bool],
        labels: List[bool],
        subgroup_labels: List[str],
        protected_attribute: Subgroup,
        system_id: str = "",
        dataset_name: str = "",
        model_name: str = "",
    ) -> FairnessReport:
        """
        Run complete fairness analysis across all subgroups.

        Returns a full FairnessReport with all metrics computed.
        """
        if not (len(predictions) == len(labels) == len(subgroup_labels)):
            raise ValueError("All input lists must have same length")

        report = FairnessReport(
            system_id=system_id,
            dataset_name=dataset_name,
            model_name=model_name,
            methodology="Statistical fairness analysis",
        )

        # Compute all fairness metrics
        dp_metrics = self.compute_demographic_parity(predictions, subgroup_labels)
        eo_metrics = self.compute_equal_opportunity(predictions, labels, subgroup_labels)
        eq_metrics = self.compute_equalized_odds(predictions, labels, subgroup_labels)
        di_metrics = self.compute_disparate_impact(predictions, subgroup_labels)
        acc_metrics = self.compute_per_subgroup_accuracy(predictions, labels, subgroup_labels)

        # Build subgroup analyses
        groups = self._group_by(subgroup_labels)
        group_names = sorted(groups.keys())

        # Merge metrics per group
        for idx, group_name in enumerate(group_names):
            analysis = SubgroupAnalysis(
                subgroup_name=group_name,
                protected_attribute=protected_attribute,
                sample_size=len(groups[group_name]),
            )

            # Assign metrics for this group
            if idx < len(dp_metrics):
                analysis.metrics.append(dp_metrics[idx])
            if idx < len(eo_metrics):
                analysis.metrics.append(eo_metrics[idx])
            if idx < len(eq_metrics):
                analysis.metrics.append(eq_metrics[idx])
            if idx < len(di_metrics):
                analysis.metrics.append(di_metrics[idx])
            if idx < len(acc_metrics):
                analysis.metrics.append(acc_metrics[idx])

            analysis.compute_fairness()
            report.add_subgroup_analysis(analysis)

        report.compute_overall_fairness()
        return report

    def create_session(
        self,
        predictions: List[bool],
        labels: List[bool],
        subgroup_labels: List[str],
        protected_attribute: Subgroup,
        name: str = "",
        system_id: str = "",
        dataset_name: str = "",
        model_name: str = "",
    ) -> BiasTestSession:
        """
        Create and run a complete bias test session.

        Convenience method that creates a session, runs analysis,
        and returns the completed session with report.
        """
        session = BiasTestSession(
            name=name,
            system_id=system_id,
            dataset_name=dataset_name,
            model_name=model_name,
        )

        try:
            report = self.analyze_session(
                predictions=predictions,
                labels=labels,
                subgroup_labels=subgroup_labels,
                protected_attribute=protected_attribute,
                system_id=system_id,
                dataset_name=dataset_name,
                model_name=model_name,
            )

            session.analyses = report.subgroup_analyses
            session.report = report
            session.complete(status=BiasTestStatus.COMPLETED)

        except Exception as e:
            session.complete(status=BiasTestStatus.FAILED, error=str(e))

        return session

    # -- Private helpers --

    @staticmethod
    def _group_by(values: List[str]) -> dict[str, list[int]]:
        """Group indices by value."""
        groups: dict[str, list[int]] = {}
        for idx, val in enumerate(values):
            groups.setdefault(val, []).append(idx)
        return groups

    @staticmethod
    def _wilson_ci(successes: int, trials: int, z: float = 1.96) -> Tuple[float, float]:
        """
        Wilson score confidence interval for a binomial proportion.

        Args:
            successes: Number of successes
            trials: Total number of trials
            z: Z-score for desired confidence level (1.96 = 95%)

        Returns:
            Tuple of (lower_bound, upper_bound)
        """
        if trials == 0:
            return (0.0, 1.0)

        p = successes / trials
        denominator = 1 + z**2 / trials
        center = (p + z**2 / (2 * trials)) / denominator
        spread = z * math.sqrt((p * (1 - p) + z**2 / (4 * trials)) / trials) / denominator

        lower = max(0.0, center - spread)
        upper = min(1.0, center + spread)

        return (lower, upper)
