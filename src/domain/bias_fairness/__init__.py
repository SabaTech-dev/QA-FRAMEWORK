"""
Bias/Fairness Testing Domain Module

Evaluates AI system fairness across demographic subgroups,
providing statistical evidence for EU AI Act Art. 10 compliance.

Provides:
- Demographic parity analysis
- Equal opportunity testing
- Disparate impact measurement
- Per-subgroup accuracy breakdown
"""

from .value_objects import (
    FairnessMetric,
    Subgroup,
    BiasTestStatus,
    FairnessLevel,
    SubgroupMetric,
    validate_group_name,
    validate_metric_value,
    MAX_GROUP_NAME_LENGTH,
    MAX_SUBGROUPS,
)
from .entities import (
    SubgroupAnalysis,
    FairnessReport,
    BiasTestSession,
)
from .interfaces import (
    IFairnessAnalyzer,
    IDatasetProvider,
)

__all__ = [
    # Value Objects
    "FairnessMetric",
    "Subgroup",
    "BiasTestStatus",
    "FairnessLevel",
    "validate_group_name",
    "validate_metric_value",
    "MAX_GROUP_NAME_LENGTH",
    "MAX_SUBGROUPS",
    # Entities
    "SubgroupAnalysis",
    "FairnessReport",
    "BiasTestSession",
    # Interfaces
    "IFairnessAnalyzer",
    "IDatasetProvider",
]
