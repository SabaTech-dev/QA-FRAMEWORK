"""Pydantic models for the QA Visual module.

The QAAnalysis contract mirrors the exact JSON structure the vision model
is prompted to return (validated in Fase A: 5/5 literal texts, 0 hallucinations).
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, model_validator


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class IssueCategory(str, Enum):
    CONTRAST = "contrast"
    ALIGNMENT = "alignment"
    OVERFLOW = "overflow"
    MISSING = "missing"
    TEXT = "text"
    SPACING = "spacing"
    OTHER = "other"


class QAIssue(BaseModel):
    """A single QA issue detected on the screenshot."""

    severity: Severity = Severity.INFO
    category: IssueCategory = IssueCategory.OTHER
    description: str = ""
    element: Optional[str] = None


class LayoutInfo(BaseModel):
    description: str = ""
    colors: Optional[Dict[str, str]] = None


class Accessibility(BaseModel):
    contrast_issues: List[str] = Field(default_factory=list)
    missing_alt: bool = False
    missing_labels: List[str] = Field(default_factory=list)


class VisualRegression(BaseModel):
    """Regression flags reported by the vision model."""

    unexpected_whitespace: bool = False
    overlapping_elements: bool = False
    cut_off_content: bool = False
    misaligned: bool = False

    def has_any(self) -> bool:
        return any(
            (
                self.unexpected_whitespace,
                self.overlapping_elements,
                self.cut_off_content,
                self.misaligned,
            )
        )


class QAAnalysis(BaseModel):
    """Structured result the vision model must return for one screenshot."""

    page_title: Optional[str] = None
    visible_texts: List[str] = Field(default_factory=list)
    layout: Optional[LayoutInfo] = None
    qa_issues: List[QAIssue] = Field(default_factory=list)
    accessibility: Accessibility = Field(default_factory=Accessibility)
    visual_regression: VisualRegression = Field(default_factory=VisualRegression)
    overall_score: int = Field(ge=0, le=100)
    summary: str = ""


class AnalyzeResponse(BaseModel):
    """Full analysis report returned by the endpoint and persisted."""

    report_id: str
    target: str
    analysis: QAAnalysis
    passed: bool
    score: int
    threshold: int
    cost_usd: float
    latency_s: float
    model: str
    regression_detected: bool = False
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TrendPoint(BaseModel):
    """One point in the score history of a target."""

    report_id: str
    target: str
    timestamp: Optional[datetime] = None
    score: int
    cost_usd: float = 0.0
    passed: Optional[bool] = None


class TrendAlert(BaseModel):
    """Alert raised from the trend analysis (e.g. score degradation)."""

    type: str
    target: str
    message: str
    current_score: Optional[int] = None
    previous_score: Optional[int] = None

    @model_validator(mode="after")
    def _validate_degradation_scores(self) -> "TrendAlert":
        if self.type == "degradation" and (
            self.current_score is None or self.previous_score is None
        ):
            raise ValueError("degradation alerts require current_score and previous_score")
        return self
