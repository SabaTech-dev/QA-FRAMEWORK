"""
AI Act Compliance Domain Module

Generates compliance evidence in EU AI Act Annex IV format
and SARIF 2.1.0 for CI/CD integration.

Provides:
- Annex IV technical documentation export
- SARIF 2.1.0 results export
- Compliance evidence aggregation from accuracy testing sessions
"""

from .value_objects import (
    SystemType,
    RiskTier,
    ComplianceStatus,
    AnnexIVSection,
    SARIFLevel,
    SARIFResultKind,
    validate_system_id,
    validate_provider_name,
    MAX_SYSTEM_ID_LENGTH,
    MAX_PROVIDER_NAME_LENGTH,
)
from .entities import (
    SystemDescription,
    TestingMethodology,
    ComplianceEvidence,
    AnnexIVReport,
    SARIFRun,
    SARIFReport,
)
from .interfaces import (
    IAnnexIVExporter,
    ISARIFExporter,
    IComplianceRepository,
)

__all__ = [
    # Value Objects
    "SystemType",
    "RiskTier",
    "ComplianceStatus",
    "AnnexIVSection",
    "SARIFLevel",
    "SARIFResultKind",
    "validate_system_id",
    "validate_provider_name",
    "MAX_SYSTEM_ID_LENGTH",
    "MAX_PROVIDER_NAME_LENGTH",
    # Entities
    "SystemDescription",
    "TestingMethodology",
    "ComplianceEvidence",
    "AnnexIVReport",
    "SARIFRun",
    "SARIFReport",
    # Interfaces
    "IAnnexIVExporter",
    "ISARIFExporter",
    "IComplianceRepository",
]
