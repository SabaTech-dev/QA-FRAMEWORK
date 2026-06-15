"""
Interfaces for Bias/Fairness Testing Domain

Abstract interfaces defining contracts for fairness analysis.
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Protocol

from .entities import SubgroupAnalysis, FairnessReport, BiasTestSession
from .value_objects import FairnessMetric, Subgroup


class IFairnessAnalyzer(Protocol):
    """Protocol for analyzing fairness across subgroups."""

    def analyze(
        self,
        predictions: List[bool],
        labels: List[bool],
        subgroup_values: List[str],
        protected_attribute: Subgroup,
        metric: FairnessMetric = FairnessMetric.DEMOGRAPHIC_PARITY,
    ) -> SubgroupAnalysis:
        """
        Analyze fairness for a single subgroup.

        Args:
            predictions: Model predictions (True = positive outcome)
            labels: Ground truth labels
            subgroup_values: Subgroup membership for each sample
            protected_attribute: Which protected attribute is being analyzed
            metric: Which fairness metric to compute

        Returns:
            SubgroupAnalysis with computed metrics
        """
        ...


class IDatasetProvider(Protocol):
    """Protocol for providing dataset information for fairness testing."""

    def get_subgroup_samples(
        self,
        dataset_id: str,
        protected_attribute: Subgroup,
        subgroup_name: str,
    ) -> tuple[List[bool], List[bool]]:
        """
        Get predictions and labels for a specific subgroup.

        Args:
            dataset_id: Identifier for the dataset
            protected_attribute: Which attribute to filter by
            subgroup_name: Specific subgroup value

        Returns:
            Tuple of (predictions, labels) for the subgroup
        """
        ...

    def get_available_subgroups(
        self,
        dataset_id: str,
        protected_attribute: Subgroup,
    ) -> List[str]:
        """
        Get list of available subgroup values for a protected attribute.

        Args:
            dataset_id: Identifier for the dataset
            protected_attribute: Which attribute to enumerate

        Returns:
            List of subgroup name strings
        """
        ...
