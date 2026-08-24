"""
Interfaces for Self-Healing Tests Domain

Abstract interfaces defining contracts for the self-healing system.
"""

from abc import ABC, abstractmethod
from typing import Protocol

from .entities import HealingResult, HealingSession, Selector
from .value_objects import HealingContext, SelectorType


class ISelectorHealer(Protocol):
    """Protocol for selector healing implementations."""

    def heal(
        self,
        broken_selector: Selector,
        context: HealingContext,
    ) -> HealingResult:
        """
        Attempt to heal a broken selector.

        Args:
            broken_selector: The selector that failed
            context: Context about the page and element

        Returns:
            HealingResult with the healed selector and confidence score
        """
        ...


class IConfidenceScorer(Protocol):
    """Protocol for confidence scoring implementations."""

    def score(
        self,
        selector: Selector,
        context: HealingContext,
    ) -> float:
        """
        Calculate confidence score for a selector.

        Args:
            selector: The selector to score
            context: Context about the page and element

        Returns:
            Confidence score between 0.0 and 1.0
        """
        ...

    def score_candidates(
        self,
        selectors: list[Selector],
        context: HealingContext,
    ) -> list[tuple]:
        """
        Score multiple candidate selectors.

        Args:
            selectors: List of selectors to score
            context: Context about the page and element

        Returns:
            List of (selector, score) tuples sorted by score descending
        """
        ...


class ISelectorRepository(ABC):
    """Abstract repository for selector persistence."""

    @abstractmethod
    async def get_by_id(self, selector_id: str) -> Selector | None:
        """Retrieve a selector by ID."""

    @abstractmethod
    async def get_by_value(
        self,
        value: str,
        selector_type: SelectorType,
    ) -> Selector | None:
        """Retrieve a selector by its value and type."""

    @abstractmethod
    async def get_alternatives(
        self,
        selector_id: str,
    ) -> list[Selector]:
        """Get alternative selectors for a given selector."""

    @abstractmethod
    async def save(self, selector: Selector) -> Selector:
        """Save a selector (create or update)."""

    @abstractmethod
    async def save_alternative(
        self,
        parent_id: str,
        alternative: Selector,
    ) -> None:
        """Save an alternative selector for a parent."""

    @abstractmethod
    async def get_low_confidence(
        self,
        tenant_id: str,
        threshold: float = 0.5,
        limit: int = 100,
    ) -> list[Selector]:
        """Get selectors with confidence below threshold."""

    @abstractmethod
    async def record_usage(
        self,
        selector_id: str,
        success: bool,
    ) -> None:
        """Record a usage event for a selector."""


class IHealingSessionRepository(ABC):
    """Abstract repository for healing session persistence."""

    @abstractmethod
    async def get_by_id(self, session_id: str) -> HealingSession | None:
        """Retrieve a healing session by ID."""

    @abstractmethod
    async def get_by_test_run(
        self,
        test_run_id: str,
    ) -> HealingSession | None:
        """Retrieve a healing session by test run ID."""

    @abstractmethod
    async def save(self, session: HealingSession) -> HealingSession:
        """Save a healing session."""

    @abstractmethod
    async def get_recent(
        self,
        tenant_id: str,
        limit: int = 10,
    ) -> list[HealingSession]:
        """Get recent healing sessions for a tenant."""


class ISelectorGenerator(Protocol):
    """Protocol for generating new selectors."""

    def generate_from_attributes(
        self,
        attributes: dict,
        element_text: str | None,
    ) -> list[Selector]:
        """Generate candidate selectors from element attributes."""
        ...

    def generate_from_context(
        self,
        context: HealingContext,
    ) -> list[Selector]:
        """Generate candidate selectors from page context."""
        ...

    def generate_composite(
        self,
        selectors: list[Selector],
    ) -> list[Selector]:
        """Generate composite selectors from multiple candidates."""
        ...


class IPageAnalyzer(Protocol):
    """Protocol for analyzing page structure."""

    def get_element_at_selector(
        self,
        selector: Selector,
    ) -> dict | None:
        """Get element info at the given selector."""
        ...

    def find_similar_elements(
        self,
        context: HealingContext,
    ) -> list[dict]:
        """Find elements similar to the target element."""
        ...

    def validate_selector(
        self,
        selector: Selector,
    ) -> bool:
        """Validate that a selector finds exactly one element."""
        ...

    def get_page_structure(
        self,
        url: str,
    ) -> dict:
        """Get the structural analysis of a page."""
        ...
