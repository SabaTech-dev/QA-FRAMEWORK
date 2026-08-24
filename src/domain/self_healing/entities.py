"""
Entities for Self-Healing Tests Domain

Core entities that represent selectors, healing results, and sessions.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from .value_objects import (
    ConfidenceLevel,
    HealingContext,
    HealingStatus,
    SelectorMetadata,
    SelectorType,
)


@dataclass
class Selector:
    """
    Represents a UI selector that can be used to locate elements.

    Selectors are the core unit of the self-healing system. They track
    their own success rate and can suggest alternatives when broken.
    """

    id: str = field(default_factory=lambda: str(uuid4()))
    value: str = ""
    selector_type: SelectorType = SelectorType.CSS
    description: Optional[str] = None
    metadata: Optional[SelectorMetadata] = None
    alternatives: List["Selector"] = field(default_factory=list)
    is_active: bool = True
    tenant_id: Optional[str] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = SelectorMetadata(
                created_at=datetime.now(timezone.utc),
                updated_at=None,
                usage_count=0,
                success_rate=1.0,
                last_successful=datetime.now(timezone.utc),
                source="manual",
            )

    @property
    def confidence_score(self) -> float:
        """Calculate confidence score based on historical data."""
        if self.metadata is None:
            return 0.5
        return self.metadata.success_rate

    @property
    def confidence_level(self) -> ConfidenceLevel:
        """Get confidence level category."""
        return ConfidenceLevel.from_score(self.confidence_score)

    def record_usage(self, success: bool) -> "Selector":
        """Record a usage event and return updated selector."""
        updated_metadata = self.metadata.with_update(success) if self.metadata else None
        return Selector(
            id=self.id,
            value=self.value,
            selector_type=self.selector_type,
            description=self.description,
            metadata=updated_metadata,
            alternatives=self.alternatives,
            is_active=self.is_active,
            tenant_id=self.tenant_id,
        )

    def add_alternative(self, alternative: "Selector") -> "Selector":
        """Add an alternative selector."""
        new_alternatives = self.alternatives + [alternative]
        return Selector(
            id=self.id,
            value=self.value,
            selector_type=self.selector_type,
            description=self.description,
            metadata=self.metadata,
            alternatives=new_alternatives,
            is_active=self.is_active,
            tenant_id=self.tenant_id,
        )


@dataclass
class HealingResult:
    """
    Result of a healing operation.

    Contains the healed selector, confidence score, and metadata about
    the healing process.
    """

    id: str = field(default_factory=lambda: str(uuid4()))
    original_selector: Optional[Selector] = None
    healed_selector: Optional[Selector] = None
    status: HealingStatus = HealingStatus.PENDING
    confidence_score: float = 0.0
    confidence_level: ConfidenceLevel = ConfidenceLevel.VERY_LOW
    healing_time_ms: int = 0
    attempts: int = 0
    candidates_evaluated: int = 0
    error_message: Optional[str] = None
    context: Optional[HealingContext] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_successful(self) -> bool:
        """Check if healing was successful."""
        return self.status == HealingStatus.SUCCESS and self.healed_selector is not None

    @property
    def is_high_confidence(self) -> bool:
        """Check if result has high confidence."""
        return self.confidence_level == ConfidenceLevel.HIGH

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "original_selector_value": (
                self.original_selector.value if self.original_selector else None
            ),
            "healed_selector_value": self.healed_selector.value if self.healed_selector else None,
            "status": self.status.value,
            "confidence_score": self.confidence_score,
            "confidence_level": self.confidence_level.value,
            "healing_time_ms": self.healing_time_ms,
            "attempts": self.attempts,
            "candidates_evaluated": self.candidates_evaluated,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class HealingSession:
    """
    A session containing multiple healing operations.

    Tracks the overall progress and statistics of a batch healing operation.
    """

    id: str = field(default_factory=lambda: str(uuid4()))
    test_run_id: Optional[str] = None
    tenant_id: Optional[str] = None
    results: List[HealingResult] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    status: HealingStatus = HealingStatus.PENDING

    @property
    def total_selectors(self) -> int:
        """Total number of selectors in session."""
        return len(self.results)

    @property
    def successful_heals(self) -> int:
        """Number of successful heals."""
        return sum(1 for r in self.results if r.is_successful)

    @property
    def failed_heals(self) -> int:
        """Number of failed heals."""
        return sum(1 for r in self.results if r.status == HealingStatus.FAILED)

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if not self.results:
            return 0.0
        return self.successful_heals / len(self.results)

    @property
    def average_confidence(self) -> float:
        """Calculate average confidence score."""
        if not self.results:
            return 0.0
        return sum(r.confidence_score for r in self.results) / len(self.results)

    def add_result(self, result: HealingResult) -> "HealingSession":
        """Add a healing result to the session."""
        new_results = self.results + [result]
        return HealingSession(
            id=self.id,
            test_run_id=self.test_run_id,
            tenant_id=self.tenant_id,
            results=new_results,
            started_at=self.started_at,
            completed_at=self.completed_at,
            status=self.status,
        )

    def complete(self) -> "HealingSession":
        """Mark session as completed."""
        final_status = (
            HealingStatus.SUCCESS
            if self.success_rate >= 0.8
            else HealingStatus.PARTIAL if self.success_rate > 0 else HealingStatus.FAILED
        )
        return HealingSession(
            id=self.id,
            test_run_id=self.test_run_id,
            tenant_id=self.tenant_id,
            results=self.results,
            started_at=self.started_at,
            completed_at=datetime.now(timezone.utc),
            status=final_status,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "test_run_id": self.test_run_id,
            "tenant_id": self.tenant_id,
            "total_selectors": self.total_selectors,
            "successful_heals": self.successful_heals,
            "failed_heals": self.failed_heals,
            "success_rate": self.success_rate,
            "average_confidence": self.average_confidence,
            "status": self.status.value,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "results": [r.to_dict() for r in self.results],
        }
