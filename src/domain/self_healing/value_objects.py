"""
Value Objects for Self-Healing Tests Domain

Defines the core value objects used in the self-healing system.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum


class SelectorType(str, Enum):
    """Types of selectors supported by the self-healing system."""

    CSS = "css"
    XPATH = "xpath"
    ID = "id"
    NAME = "name"
    CLASS = "class"
    TAG = "tag"
    ATTRIBUTE = "attribute"
    TEXT = "text"
    ARIA = "aria"
    DATA_ATTRIBUTE = "data_attribute"
    COMPOSITE = "composite"


class HealingStatus(str, Enum):
    """Status of a healing operation."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"
    SKIPPED = "skipped"


class ConfidenceLevel(str, Enum):
    """Confidence level categories for healed selectors."""

    HIGH = "high"  # 80-100%
    MEDIUM = "medium"  # 50-79%
    LOW = "low"  # 20-49%
    VERY_LOW = "very_low"  # 0-19%

    @classmethod
    def from_score(cls, score: float) -> "ConfidenceLevel":
        """Convert a numerical score to a confidence level."""
        if score >= 0.8:
            return cls.HIGH
        elif score >= 0.5:
            return cls.MEDIUM
        elif score >= 0.2:
            return cls.LOW
        return cls.VERY_LOW


@dataclass(frozen=True)
class SelectorMetadata:
    """Immutable metadata about a selector."""

    created_at: datetime
    updated_at: datetime | None
    usage_count: int
    success_rate: float
    last_successful: datetime | None
    source: str  # 'manual', 'generated', 'healed'

    def with_update(self, success: bool) -> "SelectorMetadata":
        """Create new metadata with updated stats."""
        new_count = self.usage_count + 1
        new_success_rate = (
            self.success_rate * self.usage_count + (1.0 if success else 0.0)
        ) / new_count
        return SelectorMetadata(
            created_at=self.created_at,
            updated_at=datetime.now(UTC),
            usage_count=new_count,
            success_rate=new_success_rate,
            last_successful=datetime.now(UTC) if success else self.last_successful,
            source=self.source,
        )


@dataclass(frozen=True)
class HealingContext:
    """Context information for a healing operation."""

    page_url: str
    page_title: str | None
    screenshot_path: str | None
    html_snapshot: str | None
    surrounding_text: str | None
    element_attributes: dict
    parent_selector: str | None
    sibling_selectors: list

    @classmethod
    def create_minimal(cls, page_url: str) -> "HealingContext":
        """Create minimal context with just URL."""
        return cls(
            page_url=page_url,
            page_title=None,
            screenshot_path=None,
            html_snapshot=None,
            surrounding_text=None,
            element_attributes={},
            parent_selector=None,
            sibling_selectors=[],
        )
