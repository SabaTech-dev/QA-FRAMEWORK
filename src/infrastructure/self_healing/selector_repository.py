"""
Selector Repository Implementation

In-memory implementation of the selector repository for development/testing.
"""

from src.domain.self_healing.entities import Selector
from src.domain.self_healing.interfaces import ISelectorRepository
from src.domain.self_healing.value_objects import SelectorType


class InMemorySelectorRepository(ISelectorRepository):
    """
    In-memory implementation of selector repository.

    Suitable for development, testing, and small-scale deployments.
    For production, use a database-backed implementation.
    """

    def __init__(self):
        self._selectors: dict[str, Selector] = {}
        self._alternatives: dict[str, list[Selector]] = {}
        self._by_value: dict[tuple, str] = {}  # (value, type) -> id

    async def get_by_id(self, selector_id: str) -> Selector | None:
        """Retrieve a selector by ID."""
        return self._selectors.get(selector_id)

    async def get_by_value(
        self,
        value: str,
        selector_type: SelectorType,
    ) -> Selector | None:
        """Retrieve a selector by its value and type."""
        key = (value, selector_type)
        selector_id = self._by_value.get(key)
        if selector_id:
            return self._selectors.get(selector_id)
        return None

    async def get_alternatives(self, selector_id: str) -> list[Selector]:
        """Get alternative selectors for a given selector."""
        return self._alternatives.get(selector_id, [])

    async def save(self, selector: Selector) -> Selector:
        """Save a selector (create or update)."""
        self._selectors[selector.id] = selector

        # Index by value and type
        key = (selector.value, selector.selector_type)
        self._by_value[key] = selector.id

        return selector

    async def save_alternative(
        self,
        parent_id: str,
        alternative: Selector,
    ) -> None:
        """Save an alternative selector for a parent."""
        # Save the alternative selector
        await self.save(alternative)

        # Add to alternatives list
        if parent_id not in self._alternatives:
            self._alternatives[parent_id] = []

        self._alternatives[parent_id].append(alternative)

    async def get_low_confidence(
        self,
        tenant_id: str,
        threshold: float = 0.5,
        limit: int = 100,
    ) -> list[Selector]:
        """Get selectors with confidence below threshold."""
        low_confidence = []

        for selector in self._selectors.values():
            if selector.tenant_id != tenant_id:
                continue

            if selector.confidence_score < threshold:
                low_confidence.append(selector)

                if len(low_confidence) >= limit:
                    break

        # Sort by confidence ascending
        low_confidence.sort(key=lambda s: s.confidence_score)

        return low_confidence

    async def record_usage(
        self,
        selector_id: str,
        success: bool,
    ) -> None:
        """Record a usage event for a selector."""
        selector = self._selectors.get(selector_id)
        if selector:
            updated = selector.record_usage(success)
            self._selectors[selector_id] = updated

    def clear(self) -> None:
        """Clear all data (useful for testing)."""
        self._selectors.clear()
        self._alternatives.clear()
        self._by_value.clear()


class DatabaseSelectorRepository(ISelectorRepository):
    """
    Database-backed implementation of selector repository.

    This is a placeholder that shows the interface for a real
    database implementation. In production, this would use
    SQLAlchemy, asyncpg, or similar.
    """

    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        # In a real implementation, initialize database connection here

    async def get_by_id(self, selector_id: str) -> Selector | None:
        """Retrieve a selector by ID from database."""
        # Placeholder - implement with actual database query
        raise NotImplementedError("Database implementation required")

    async def get_by_value(
        self,
        value: str,
        selector_type: SelectorType,
    ) -> Selector | None:
        """Retrieve a selector by value and type from database."""
        raise NotImplementedError("Database implementation required")

    async def get_alternatives(self, selector_id: str) -> list[Selector]:
        """Get alternatives from database."""
        raise NotImplementedError("Database implementation required")

    async def save(self, selector: Selector) -> Selector:
        """Save selector to database."""
        raise NotImplementedError("Database implementation required")

    async def save_alternative(
        self,
        parent_id: str,
        alternative: Selector,
    ) -> None:
        """Save alternative to database."""
        raise NotImplementedError("Database implementation required")

    async def get_low_confidence(
        self,
        tenant_id: str,
        threshold: float = 0.5,
        limit: int = 100,
    ) -> list[Selector]:
        """Query low confidence selectors from database."""
        raise NotImplementedError("Database implementation required")

    async def record_usage(
        self,
        selector_id: str,
        success: bool,
    ) -> None:
        """Record usage in database."""
        raise NotImplementedError("Database implementation required")
