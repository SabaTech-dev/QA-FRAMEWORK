"""
Entities for AI Act Compliance Domain

Core entities for Annex IV reports, SARIF 2.1.0 outputs,
and compliance evidence aggregation.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from uuid import uuid4
import json

from .value_objects import (
    RiskTier,
    SystemType,
    ComplianceStatus,
    AnnexIVSection,
    SARIFLevel,
    SARIFResultKind,
    AnnexIVRequirement,
    validate_system_id,
    validate_provider_name,
)


@dataclass
class SystemDescription:
    """
    Annex IV §1 — Description of the AI system.

    Captures identity, purpose, and metadata about the AI system
    under compliance evaluation.
    """
    system_id: str = ""
    name: str = ""
    provider_name: str = ""
    system_type: SystemType = SystemType.STANDALONE
    risk_tier: RiskTier = RiskTier.HIGH_RISK
    version: str = ""
    description: str = ""
    intended_purpose: str = ""           # Annex IV §2
    target_users: str = ""               # Annex IV §3
    likely_affected_persons: str = ""    # Annex IV §3

    def __post_init__(self):
        if self.system_id:
            validate_system_id(self.system_id)
        if self.provider_name:
            validate_provider_name(self.provider_name)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "system_id": self.system_id,
            "name": self.name,
            "provider_name": self.provider_name,
            "system_type": self.system_type.value,
            "risk_tier": self.risk_tier.value,
            "version": self.version,
            "description": self.description,
            "intended_purpose": self.intended_purpose,
            "target_users": self.target_users,
            "likely_affected_persons": self.likely_affected_persons,
        }


@dataclass
class TestingMethodology:
    """
    Annex IV §7 — Pre-determined testing methodology.

    Describes how the AI system was tested for accuracy,
    robustness, and cybersecurity (Art. 15).
    """
    methodology_name: str = ""
    description: str = ""
    test_categories: List[str] = field(default_factory=list)
    benchmarks_used: List[str] = field(default_factory=list)
    evaluation_metrics: List[str] = field(default_factory=list)
    passing_threshold: float = 0.6
    environment: str = ""

    def __post_init__(self):
        if not 0.0 <= self.passing_threshold <= 1.0:
            raise ValueError(
                f"passing_threshold must be in [0.0, 1.0], got {self.passing_threshold}"
            )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "methodology_name": self.methodology_name,
            "description": self.description,
            "test_categories": self.test_categories,
            "benchmarks_used": self.benchmarks_used,
            "evaluation_metrics": self.evaluation_metrics,
            "passing_threshold": self.passing_threshold,
            "environment": self.environment,
        }


@dataclass
class ComplianceEvidence:
    """
    Evidence artifact linking testing results to Annex IV requirements.

    Each evidence item maps a test result or measurement to
    a specific Annex IV section, providing traceability.
    """
    id: str = field(default_factory=lambda: str(uuid4()))
    annex_section: AnnexIVSection = AnnexIVSection.ACCURACY_ROBUSTNESS
    evidence_type: str = ""       # "accuracy_test", "robustness_test", "security_audit"
    title: str = ""
    description: str = ""
    source_session_id: Optional[str] = None  # links to AccuracyTestSession
    metric_name: str = ""
    metric_value: float = 0.0
    metric_target: float = 0.0
    passed: bool = False
    artifact_data: Dict[str, Any] = field(default_factory=dict)
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def meets_target(self) -> bool:
        """Check if metric meets or exceeds target."""
        return self.metric_value >= self.metric_target

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "annex_section": self.annex_section.value,
            "evidence_type": self.evidence_type,
            "title": self.title,
            "description": self.description,
            "source_session_id": self.source_session_id,
            "metric_name": self.metric_name,
            "metric_value": self.metric_value,
            "metric_target": self.metric_target,
            "passed": self.passed,
            "meets_target": self.meets_target,
            "artifact_data": self.artifact_data,
            "generated_at": self.generated_at.isoformat(),
        }


@dataclass
class AnnexIVReport:
    """
    Complete Annex IV technical documentation report.

    Aggregates system description, testing methodology, and evidence
    into a structured document compliant with EU AI Act Annex IV.

    This is the primary export artifact for AI Act compliance.
    """
    id: str = field(default_factory=lambda: str(uuid4()))
    system: SystemDescription = field(default_factory=SystemDescription)
    methodology: TestingMethodology = field(default_factory=TestingMethodology)
    evidence: List[ComplianceEvidence] = field(default_factory=list)
    requirements: List[AnnexIVRequirement] = field(default_factory=list)

    # Aggregate metrics (from testing sessions)
    overall_accuracy_score: float = 0.0
    overall_pass_rate: float = 0.0
    total_evaluations: int = 0
    evaluations_passed: int = 0
    hallucination_count: int = 0

    # Compliance determination
    compliance_status: ComplianceStatus = ComplianceStatus.PENDING_REVIEW
    assessment_date: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    assessor: str = ""
    notes: List[str] = field(default_factory=list)
    tenant_id: Optional[str] = None

    def add_evidence(self, evidence: ComplianceEvidence) -> None:
        """Add an evidence item to the report."""
        self.evidence.append(evidence)

    def compute_compliance(self) -> ComplianceStatus:
        """
        Determine compliance status based on evidence and requirements.

        Returns the computed status. Also updates self.compliance_status.
        """
        if not self.evidence and not self.requirements:
            self.compliance_status = ComplianceStatus.PENDING_REVIEW
            return self.compliance_status

        # Check requirements
        requirements_satisfied = sum(1 for r in self.requirements if r.is_satisfied)
        requirements_total = len(self.requirements)

        # Check evidence
        evidence_passed = sum(1 for e in self.evidence if e.passed)
        evidence_total = len(self.evidence)

        if requirements_total == 0 and evidence_total == 0:
            self.compliance_status = ComplianceStatus.PENDING_REVIEW
        elif (
            requirements_total > 0
            and requirements_satisfied == requirements_total
            and evidence_total > 0
            and evidence_passed == evidence_total
        ):
            self.compliance_status = ComplianceStatus.COMPLIANT
        elif (
            requirements_total > 0
            and requirements_satisfied < requirements_total * 0.5
        ):
            self.compliance_status = ComplianceStatus.NON_COMPLIANT
        else:
            self.compliance_status = ComplianceStatus.PARTIALLY_COMPLIANT

        return self.compliance_status

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary (excludes tenant_id for public view)."""
        return {
            "id": self.id,
            "generated_at": self.assessment_date.isoformat(),
            "system": self.system.to_dict(),
            "methodology": self.methodology.to_dict(),
            "evidence": [e.to_dict() for e in self.evidence],
            "requirements": [r.to_dict() for r in self.requirements],
            "aggregate_metrics": {
                "overall_accuracy_score": self.overall_accuracy_score,
                "overall_pass_rate": self.overall_pass_rate,
                "total_evaluations": self.total_evaluations,
                "evaluations_passed": self.evaluations_passed,
                "hallucination_count": self.hallucination_count,
            },
            "compliance_status": self.compliance_status.value,
            "assessor": self.assessor,
            "notes": self.notes,
        }

    def to_json(self, indent: int = 2) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


@dataclass
class SARIFRun:
    """
    SARIF 2.1.0 run object (§3.14).

    A run represents a single invocation of a tool that produced
    a set of results.
    """
    tool_name: str = "qa-framework"
    tool_version: str = "1.0.0"
    tool_information_uri: str = ""
    results: List[Dict[str, Any]] = field(default_factory=list)
    invocations: List[Dict[str, Any]] = field(default_factory=list)
    taxonomy: List[Dict[str, Any]] = field(default_factory=list)

    def add_result(
        self,
        rule_id: str,
        level: SARIFLevel,
        kind: SARIFResultKind,
        message: str,
        locations: Optional[List[Dict[str, Any]]] = None,
        partial_fingerprints: Optional[Dict[str, str]] = None,
        properties: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Add a result entry to this run."""
        result: Dict[str, Any] = {
            "ruleId": rule_id,
            "level": level.value,
            "kind": kind.value,
            "message": {"text": message},
        }
        if locations:
            result["locations"] = locations
        if partial_fingerprints:
            result["partialFingerprints"] = partial_fingerprints
        if properties:
            result["properties"] = properties
        self.results.append(result)

    def to_dict(self) -> Dict[str, Any]:
        tool: Dict[str, Any] = {
            "driver": {
                "name": self.tool_name,
                "version": self.tool_version,
            }
        }
        if self.tool_information_uri:
            tool["driver"]["informationUri"] = self.tool_information_uri
        if self.taxonomy:
            tool["driver"]["rules"] = self.taxonomy

        return {
            "tool": tool,
            "results": self.results,
            "invocations": self.invocations,
        }


@dataclass
class SARIFReport:
    """
    SARIF 2.1.0 report (top-level object, §3.13).

    The complete SARIF log file, ready for CI/CD consumption.
    """
    version: str = "2.1.0"
    schema_uri: str = "https://docs.oasis-open.org/sarif/sarif/v2.1.0/cs01/schemas/sarif-schema-2.1.0.json"
    runs: List[SARIFRun] = field(default_factory=list)
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    tenant_id: Optional[str] = None

    def add_run(self, run: SARIFRun) -> None:
        """Add a run to the report."""
        self.runs.append(run)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to SARIF-compliant dictionary (excludes tenant_id)."""
        return {
            "version": self.version,
            "$schema": self.schema_uri,
            "runs": [r.to_dict() for r in self.runs],
            "properties": {
                "generatedAt": self.generated_at.isoformat(),
            },
        }

    def to_json(self, indent: int = 2) -> str:
        """Serialize to SARIF JSON string."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)
