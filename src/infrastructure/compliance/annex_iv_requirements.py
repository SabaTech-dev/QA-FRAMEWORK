"""
Annex IV Requirements — EU AI Act compliance definitions.

Defines the structured fields required by Annex IV of the EU AI Act
for high-risk AI system technical documentation.
"""

from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class RiskLevel(str, Enum):
    """Risk levels per EU AI Act."""
    minimal = "minimal"
    limited = "limited"
    high = "high"
    unacceptable = "unacceptable"


class SystemDescription(BaseModel):
    """Annex IV §1 — System description."""
    name: str = Field(..., description="Name of the AI system")
    version: str = Field(..., description="Version identifier")
    purpose: str = Field(..., description="Intended purpose of the system")
    intended_users: List[str] = Field(default_factory=list, description="Target user groups")
    deployment_context: str = Field(..., description="Deployment environment")
    interaction_mode: str = Field(default="api", description="How users interact (api, gui, batch)")


class SystemCapabilities(BaseModel):
    """Annex IV §2 — Capabilities and limitations."""
    capabilities: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
    performance_metrics: dict = Field(default_factory=dict, description="Key performance indicators")
    known_biases: List[str] = Field(default_factory=list)


class DataTrainingSummary(BaseModel):
    """Annex IV §3 — Data training summary."""
    datasets_used: List[str] = Field(default_factory=list, description="Dataset names/IDs")
    data_provenance: str = Field(default="N/A", description="Source and provenance")
    data_characteristics: str = Field(default="N/A", description="Size, demographics, features")
    data_cleaning: Optional[str] = Field(default=None, description="Preprocessing steps")
    data_splits: Optional[dict] = Field(default=None, description="Train/val/test split ratios")


class RiskAssessment(BaseModel):
    """Annex IV §4 — Risk assessment."""
    identified_risks: List[str] = Field(default_factory=list)
    mitigation_measures: List[str] = Field(default_factory=list)
    residual_risk_level: RiskLevel = Field(default=RiskLevel.minimal)
    risk_assessment_date: Optional[datetime] = None


class EvaluationResult(BaseModel):
    """Annex IV §5 — Evaluation metrics."""
    metric_name: str
    metric_value: float
    metric_description: Optional[str] = None


class HumanOversight(BaseModel):
    """Annex IV §6 — Human oversight measures."""
    oversight_mechanisms: List[str] = Field(default_factory=list)
    override_capabilities: List[str] = Field(default_factory=list)
    alert_thresholds: Optional[dict] = Field(default=None)


class TransparencyInfo(BaseModel):
    """Annex IV §7 — Transparency obligations."""
    user_notification: str = Field(default="Users are informed they are interacting with an AI system")
    explainability: str = Field(default="Decisions can be traced to test execution data")
    documentation_url: Optional[str] = None


class AnnexIVDocument(BaseModel):
    """Complete Annex IV technical documentation."""
    system_description: SystemDescription
    capabilities: SystemCapabilities
    data_training: DataTrainingSummary
    risk_assessment: RiskAssessment
    evaluation_results: List[EvaluationResult] = Field(default_factory=list)
    human_oversight: HumanOversight
    transparency: TransparencyInfo
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    schema_version: str = Field(default="1.0.0", description="Annex IV schema version")


# Default QA-FRAMEWORK Annex IV template
QA_FRAMEWORK_DEFAULTS = {
    "system_description": {
        "name": "QA-FRAMEWORK",
        "version": "0.1.0-beta",
        "purpose": "Automated QA testing platform with AI-powered test generation, self-healing tests, and security scanning",
        "intended_users": ["QA engineers", "DevOps teams", "Security analysts"],
        "deployment_context": "Self-hosted or cloud deployment for enterprise QA teams",
        "interaction_mode": "api",
    },
    "capabilities": {
        "capabilities": [
            "AI test case generation",
            "Self-healing test maintenance",
            "Security vulnerability scanning (ZAP, Nuclei)",
            "OWASP API Top 10 compliance checking",
            "Multi-framework support (pytest, playwright)",
        ],
        "limitations": [
            "Requires manual test suite configuration",
            "Self-healing limited to deterministic selectors",
            "Security scanning requires external tools (ZAP, Nuclei)",
        ],
        "performance_metrics": {},
        "known_biases": [
            "Test generation quality depends on LLM model used",
            "Security scanning limited to known vulnerability patterns",
        ],
    },
    "data_training": {
        "datasets_used": ["N/A — uses external LLM APIs"],
        "data_provenance": "No training data — system orchestrates external AI models",
        "data_characteristics": "Not applicable — system does not train models directly",
    },
    "risk_assessment": {
        "identified_risks": [
            "False positives in security scanning",
            "Test generation may produce non-deterministic results",
            "LLM API dependency for AI features",
        ],
        "mitigation_measures": [
            "Manual review of security findings before action",
            "Test versioning and review workflow",
            "Fallback to manual test creation if AI unavailable",
        ],
        "residual_risk_level": "limited",
    },
    "human_oversight": {
        "oversight_mechanisms": [
            "All AI-generated tests require human approval before execution",
            "Security findings reviewed by security analyst",
            "Dashboard provides full visibility of all automated actions",
        ],
        "override_capabilities": [
            "Manual test override",
            "Execution stop/pause controls",
            "Rate limiting and quota management",
        ],
    },
    "transparency": {
        "user_notification": "Dashboard clearly labels AI-generated content",
        "explainability": "All test executions logged with full traceability",
        "documentation_url": "https://github.com/SabaTech-dev/QA-FRAMEWORK",
    },
}
