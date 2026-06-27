"""
Self-Healing Pydantic schemas.

Field names are aligned with the frontend TypeScript interfaces in
``SelfHealing.tsx`` so the API payload maps 1:1.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


class SelectorType(str, Enum):
    css = "css"
    xpath = "xpath"
    id = "id"
    data_attribute = "data_attribute"


class ConfidenceLevel(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"


class HealingStatus(str, Enum):
    success = "success"
    partial = "partial"
    failed = "failed"
    skipped = "skipped"
    running = "running"


# ==================== Selector ====================
class HealingSelectorBase(BaseModel):
    value: str = Field(..., min_length=1, description="Selector string")
    selector_type: SelectorType = SelectorType.css
    description: Optional[str] = None
    confidence_score: float = Field(0.5, ge=0.0, le=1.0)
    confidence_level: ConfidenceLevel = ConfidenceLevel.medium
    is_active: bool = True
    usage_count: int = 0
    success_rate: float = Field(0.0, ge=0.0, le=1.0)


class HealingSelectorCreate(HealingSelectorBase):
    pass


class HealingSelectorUpdate(BaseModel):
    value: Optional[str] = Field(default=None, min_length=1)
    selector_type: Optional[SelectorType] = None
    description: Optional[str] = None
    confidence_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    confidence_level: Optional[ConfidenceLevel] = None
    is_active: Optional[bool] = None
    success_rate: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class HealingSelectorResponse(HealingSelectorBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ==================== Session ====================
class HealingSessionResponse(BaseModel):
    id: int
    status: str
    total_selectors: int = 0
    successful_heals: int = 0
    failed_heals: int = 0
    success_rate: float = 0.0
    average_confidence: float = 0.0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ==================== Result ====================
class HealingResultResponse(BaseModel):
    id: int
    session_id: Optional[int] = None
    selector_id: Optional[int] = None
    original_selector_value: str
    healed_selector_value: Optional[str] = None
    status: str
    confidence_score: float = 0.0
    confidence_level: str = "low"
    healing_time_ms: int = 0
    attempts: int = 1
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ==================== Heal action ====================
class HealResponse(HealingResultResponse):
    """Response for POST /healing/selectors/{id}/heal — a single result."""

    pass
