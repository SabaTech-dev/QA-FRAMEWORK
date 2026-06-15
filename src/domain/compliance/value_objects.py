"""
Value Objects for AI Act Compliance Domain

Core types for EU AI Act compliance evidence generation,
including Annex IV section identifiers and SARIF 2.1.0 types.
"""

from enum import Enum
import re
from dataclasses import dataclass
from typing import Optional, List

# Security: input length limits to prevent resource exhaustion
MAX_SYSTEM_ID_LENGTH = 200
MAX_PROVIDER_NAME_LENGTH = 500


class RiskTier(str, Enum):
    """AI Act risk classification (Art. 6)."""
    PROHIBITED = "prohibited"          # Art. 5 — banned practices
    HIGH_RISK = "high_risk"            # Art. 6 — strict requirements
    LIMITED_RISK = "limited_risk"      # Art. 50 — transparency obligations
    MINIMAL_RISK = "minimal_risk"      # No specific obligations


class SystemType(str, Enum):
    """Type of AI system for Annex IV documentation."""
    STANDALONE = "standalone"
    EMBEDDED = "embedded"
    COMPONENT = "component"
    GPAI = "gpai"                      # General-purpose AI model


class ComplianceStatus(str, Enum):
    """Compliance evaluation status."""
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    PARTIALLY_COMPLIANT = "partially_compliant"
    PENDING_REVIEW = "pending_review"


class AnnexIVSection(str, Enum):
    """
    Annex IV technical documentation sections.

    Reference: EU AI Act, Annex IV — Technical documentation
    for high-risk AI systems.
    """
    SYSTEM_DESCRIPTION = "1"           # Description of the AI system
    INTENDED_PURPOSE = "2"             # Intended purpose
    PERSONS_AFFECTED = "3"             # Persons likely affected
    ACTORS_ROLES = "4"                 # Actors in operation/use
    TRAINING_VALIDATION_TESTING = "5"  # Datasets and data governance
    TRAINING_METRICS = "6"             # Relevant training/validation metrics
    VALIDATION_TESTING = "7"           # Pre-determined testing methodology
    DESIGN_SPECS = "8"                 # Design specifications of system
    SYSTEM_ARCHITECTURE = "9"          # System architecture
    HUMAN_OVERSIGHT = "10"             # Human oversight measures
    ACCURACY_ROBUSTNESS = "11"         # Accuracy and robustness
    CYBERSECURITY = "12"               # Cybersecurity measures
    QUALITY_MANAGEMENT = "13"          # Quality management system
    TECHNICAL_LOGS = "14"              # Technical logs
    EU_DECLARATION = "15"              # EU declaration of conformity ref
    POST_MARKET = "16"                 # Post-market monitoring plan


class SARIFLevel(str, Enum):
    """SARIF 2.1.0 result severity levels (§3.27.10)."""
    NONE = "none"
    NOTE = "note"
    WARNING = "warning"
    ERROR = "error"


class SARIFResultKind(str, Enum):
    """SARIF 2.1.0 result kinds (§3.27.22)."""
    PASS = "pass"            # Test passed
    FAIL = "fail"            # Test failed
    REVIEW = "review"        # Needs manual review
    OPEN = "open"            # Not yet evaluated
    INFORMATIONAL = "informational"
    NOT_APPLICABLE = "notApplicable"


# Validation patterns (security: strict format to prevent injection)
_SYSTEM_ID_PATTERN = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9._:-]{0,199}$')
_PROVIDER_SAFE_CHARS = re.compile(r'^[^\n\r\t<>{}|\\^~\[\]`]+$')


def validate_system_id(value: str) -> str:
    """
    Validate AI system identifier.

    Must start with alphanumeric, followed by alphanumeric/dots/dashes/colons.
    Max MAX_SYSTEM_ID_LENGTH chars.
    """
    if not value or not isinstance(value, str):
        raise ValueError("system_id must be a non-empty string")
    if len(value) > MAX_SYSTEM_ID_LENGTH:
        raise ValueError(
            f"system_id exceeds max length {MAX_SYSTEM_ID_LENGTH}, got {len(value)}"
        )
    if not _SYSTEM_ID_PATTERN.match(value):
        raise ValueError(
            "system_id must start with alphanumeric and contain only "
            "[a-zA-Z0-9._:-] characters"
        )
    return value


def validate_provider_name(value: str) -> str:
    """
    Validate provider/system name for Annex IV reports.

    Rejects control characters and common markup injection vectors.
    Max MAX_PROVIDER_NAME_LENGTH chars.
    """
    if not value or not isinstance(value, str):
        raise ValueError("provider name must be a non-empty string")
    if len(value) > MAX_PROVIDER_NAME_LENGTH:
        raise ValueError(
            f"provider name exceeds max length {MAX_PROVIDER_NAME_LENGTH}, got {len(value)}"
        )
    if not _PROVIDER_SAFE_CHARS.match(value):
        raise ValueError(
            "provider name contains forbidden characters "
            "(control chars, angle brackets, etc.)"
        )
    return value


@dataclass
class AnnexIVRequirement:
    """
    A single Annex IV documentation requirement.

    Represents one item the technical documentation must address.
    """
    section: AnnexIVSection
    title: str
    description: str
    is_satisfied: bool = False
    evidence_ref: Optional[str] = None  # reference to evidence artifact
    gap_description: Optional[str] = None

    def __post_init__(self):
        if not self.title or len(self.title) > 300:
            raise ValueError("title must be 1-300 chars")
        if len(self.description) > 5000:
            raise ValueError("description exceeds 5000 chars")

    @property
    def status(self) -> str:
        """Human-readable compliance status for this requirement."""
        return "satisfied" if self.is_satisfied else (
            "gap: " + (self.gap_description or "not documented")
            if self.gap_description else "not documented"
        )

    def to_dict(self) -> dict:
        return {
            "section": self.section.value,
            "title": self.title,
            "description": self.description,
            "is_satisfied": self.is_satisfied,
            "evidence_ref": self.evidence_ref,
            "gap_description": self.gap_description,
            "status": self.status,
        }
