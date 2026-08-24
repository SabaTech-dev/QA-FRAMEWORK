"""
Unit Tests for Self-Healing Domain

Tests for entities, value objects, and interfaces in the self-healing module.
"""

from datetime import UTC, datetime, timedelta

import pytest

from src.domain.self_healing.entities import HealingResult, HealingSession, Selector
from src.domain.self_healing.value_objects import (
    ConfidenceLevel,
    HealingContext,
    HealingStatus,
    SelectorMetadata,
    SelectorType,
)


class TestSelectorMetadata:
    """Tests for SelectorMetadata value object."""

    def test_create_metadata(self):
        """Test creating selector metadata."""
        now = datetime.now(UTC)
        metadata = SelectorMetadata(
            created_at=now,
            updated_at=None,
            usage_count=0,
            success_rate=1.0,
            last_successful=now,
            source="manual",
        )

        assert metadata.created_at == now
        assert metadata.usage_count == 0
        assert metadata.success_rate == 1.0
        assert metadata.source == "manual"

    def test_with_update_success(self):
        """Test updating metadata with successful usage."""
        now = datetime.now(UTC)
        metadata = SelectorMetadata(
            created_at=now - timedelta(days=1),
            updated_at=now,
            usage_count=10,
            success_rate=0.8,
            last_successful=now,
            source="manual",
        )

        updated = metadata.with_update(success=True)

        assert updated.usage_count == 11
        assert updated.success_rate > 0.8  # Should increase
        assert updated.last_successful is not None
        assert updated.updated_at is not None

    def test_with_update_failure(self):
        """Test updating metadata with failed usage."""
        now = datetime.now(UTC)
        metadata = SelectorMetadata(
            created_at=now - timedelta(days=1),
            updated_at=now,
            usage_count=10,
            success_rate=0.8,
            last_successful=now,
            source="manual",
        )

        updated = metadata.with_update(success=False)

        assert updated.usage_count == 11
        assert updated.success_rate < 0.8  # Should decrease


class TestHealingContext:
    """Tests for HealingContext value object."""

    def test_create_minimal_context(self):
        """Test creating minimal healing context."""
        context = HealingContext.create_minimal("https://example.com")

        assert context.page_url == "https://example.com"
        assert context.page_title is None
        assert context.screenshot_path is None
        assert context.element_attributes == {}

    def test_create_full_context(self):
        """Test creating full healing context."""
        context = HealingContext(
            page_url="https://example.com/page",
            page_title="Test Page",
            screenshot_path="/tmp/screenshot.png",
            html_snapshot="<html>...</html>",
            surrounding_text="Click here",
            element_attributes={"id": "btn", "class": "button"},
            parent_selector=".container",
            sibling_selectors=[".sibling1", ".sibling2"],
        )

        assert context.page_url == "https://example.com/page"
        assert context.page_title == "Test Page"
        assert context.element_attributes == {"id": "btn", "class": "button"}


class TestSelector:
    """Tests for Selector entity."""

    def test_create_selector(self):
        """Test creating a selector."""
        selector = Selector(
            value="#submit-button",
            selector_type=SelectorType.ID,
            description="Submit button",
        )

        assert selector.value == "#submit-button"
        assert selector.selector_type == SelectorType.ID
        assert selector.description == "Submit button"
        assert selector.is_active is True
        assert selector.id is not None

    def test_selector_auto_metadata(self):
        """Test that selector auto-creates metadata."""
        selector = Selector(value=".button")

        assert selector.metadata is not None
        assert selector.metadata.source == "manual"
        assert selector.metadata.usage_count == 0

    def test_confidence_score(self):
        """Test confidence score calculation."""
        selector = Selector(
            value=".button",
            metadata=SelectorMetadata(
                created_at=datetime.now(UTC),
                updated_at=None,
                usage_count=10,
                success_rate=0.9,
                last_successful=datetime.now(UTC),
                source="manual",
            ),
        )

        assert selector.confidence_score == 0.9
        assert selector.confidence_level == ConfidenceLevel.HIGH

    def test_confidence_level_from_score(self):
        """Test confidence level categorization."""
        assert ConfidenceLevel.from_score(0.9) == ConfidenceLevel.HIGH
        assert ConfidenceLevel.from_score(0.7) == ConfidenceLevel.MEDIUM
        assert ConfidenceLevel.from_score(0.4) == ConfidenceLevel.LOW
        assert ConfidenceLevel.from_score(0.1) == ConfidenceLevel.VERY_LOW

    def test_record_usage_success(self):
        """Test recording successful usage."""
        selector = Selector(value=".button")
        updated = selector.record_usage(success=True)

        assert updated.metadata.usage_count == 1
        assert updated.metadata.success_rate == 1.0

    def test_record_usage_failure(self):
        """Test recording failed usage."""
        selector = Selector(value=".button")
        updated = selector.record_usage(success=False)

        assert updated.metadata.usage_count == 1
        assert updated.metadata.success_rate == 0.0

    def test_add_alternative(self):
        """Test adding alternative selector."""
        selector = Selector(value="#old-selector")
        alternative = Selector(value=".new-selector")

        updated = selector.add_alternative(alternative)

        assert len(updated.alternatives) == 1
        assert updated.alternatives[0].value == ".new-selector"


class TestHealingResult:
    """Tests for HealingResult entity."""

    def test_create_healing_result(self):
        """Test creating a healing result."""
        result = HealingResult(
            status=HealingStatus.SUCCESS,
            confidence_score=0.85,
        )

        assert result.status == HealingStatus.SUCCESS
        assert result.confidence_score == 0.85
        assert result.id is not None

    def test_is_successful(self):
        """Test is_successful property."""
        selector = Selector(value=".healed")

        result = HealingResult(
            status=HealingStatus.SUCCESS,
            healed_selector=selector,
            confidence_score=0.9,
        )

        assert result.is_successful is True

    def test_is_not_successful_no_selector(self):
        """Test is_successful is False when no selector."""
        result = HealingResult(
            status=HealingStatus.SUCCESS,
            healed_selector=None,
            confidence_score=0.9,
        )

        assert result.is_successful is False

    def test_is_not_successful_failed_status(self):
        """Test is_successful is False when status is FAILED."""
        result = HealingResult(
            status=HealingStatus.FAILED,
            healed_selector=Selector(value=".healed"),
            confidence_score=0.9,
        )

        assert result.is_successful is False

    def test_is_high_confidence(self):
        """Test is_high_confidence property."""
        result = HealingResult(
            confidence_score=0.85,
            confidence_level=ConfidenceLevel.HIGH,
        )

        assert result.is_high_confidence is True

    def test_to_dict(self):
        """Test serialization to dictionary."""
        original = Selector(value="#original")
        healed = Selector(value=".healed")

        result = HealingResult(
            original_selector=original,
            healed_selector=healed,
            status=HealingStatus.SUCCESS,
            confidence_score=0.85,
            healing_time_ms=150,
            attempts=3,
        )

        data = result.to_dict()

        assert data["original_selector_value"] == "#original"
        assert data["healed_selector_value"] == ".healed"
        assert data["status"] == "success"
        assert data["confidence_score"] == 0.85
        assert data["healing_time_ms"] == 150


class TestHealingSession:
    """Tests for HealingSession entity."""

    def test_create_session(self):
        """Test creating a healing session."""
        session = HealingSession()

        assert session.id is not None
        assert session.status == HealingStatus.PENDING
        assert len(session.results) == 0

    def test_total_selectors(self):
        """Test total_selectors property."""
        session = HealingSession()

        assert session.total_selectors == 0

        session.results.append(HealingResult())
        session.results.append(HealingResult())

        assert session.total_selectors == 2

    def test_successful_heals(self):
        """Test successful_heals property."""
        session = HealingSession(
            results=[
                HealingResult(status=HealingStatus.SUCCESS, healed_selector=Selector(value=".a")),
                HealingResult(status=HealingStatus.FAILED),
                HealingResult(status=HealingStatus.SUCCESS, healed_selector=Selector(value=".b")),
            ]
        )

        assert session.successful_heals == 2

    def test_failed_heals(self):
        """Test failed_heals property."""
        session = HealingSession(
            results=[
                HealingResult(status=HealingStatus.SUCCESS, healed_selector=Selector(value=".a")),
                HealingResult(status=HealingStatus.FAILED),
                HealingResult(status=HealingStatus.FAILED),
            ]
        )

        assert session.failed_heals == 2

    def test_success_rate(self):
        """Test success_rate calculation."""
        session = HealingSession(
            results=[
                HealingResult(status=HealingStatus.SUCCESS, healed_selector=Selector(value=".a")),
                HealingResult(status=HealingStatus.FAILED),
                HealingResult(status=HealingStatus.SUCCESS, healed_selector=Selector(value=".b")),
                HealingResult(status=HealingStatus.SUCCESS, healed_selector=Selector(value=".c")),
            ]
        )

        assert session.success_rate == 0.75

    def test_average_confidence(self):
        """Test average_confidence calculation."""
        session = HealingSession(
            results=[
                HealingResult(confidence_score=0.8),
                HealingResult(confidence_score=0.6),
                HealingResult(confidence_score=0.9),
            ]
        )

        assert session.average_confidence == pytest.approx(0.767, rel=0.01)

    def test_add_result(self):
        """Test adding a result to session."""
        session = HealingSession()
        result = HealingResult(confidence_score=0.9)

        updated = session.add_result(result)

        assert len(updated.results) == 1
        assert updated.results[0].confidence_score == 0.9

    def test_complete_success(self):
        """Test completing session with high success rate."""
        session = HealingSession(
            results=[
                HealingResult(status=HealingStatus.SUCCESS, healed_selector=Selector(value=".a")),
                HealingResult(status=HealingStatus.SUCCESS, healed_selector=Selector(value=".b")),
                HealingResult(status=HealingStatus.SUCCESS, healed_selector=Selector(value=".c")),
            ]
        )

        completed = session.complete()

        assert completed.status == HealingStatus.SUCCESS
        assert completed.completed_at is not None

    def test_complete_partial(self):
        """Test completing session with partial success."""
        session = HealingSession(
            results=[
                HealingResult(status=HealingStatus.SUCCESS, healed_selector=Selector(value=".a")),
                HealingResult(status=HealingStatus.FAILED),
                HealingResult(status=HealingStatus.FAILED),
            ]
        )

        completed = session.complete()

        assert completed.status == HealingStatus.PARTIAL

    def test_complete_failed(self):
        """Test completing session with all failures."""
        session = HealingSession(
            results=[
                HealingResult(status=HealingStatus.FAILED),
                HealingResult(status=HealingStatus.FAILED),
            ]
        )

        completed = session.complete()

        assert completed.status == HealingStatus.FAILED

    def test_to_dict(self):
        """Test session serialization."""
        session = HealingSession(
            test_run_id="run-123",
            tenant_id="tenant-456",
            results=[
                HealingResult(
                    status=HealingStatus.SUCCESS,
                    confidence_score=0.9,
                    healed_selector=Selector(value=".a"),
                ),
            ],
        )

        data = session.to_dict()

        assert data["test_run_id"] == "run-123"
        assert data["tenant_id"] == "tenant-456"
        assert data["total_selectors"] == 1
        assert data["successful_heals"] == 1
        assert data["success_rate"] == 1.0
        assert len(data["results"]) == 1


class TestSelectorType:
    """Tests for SelectorType enum."""

    def test_all_types_exist(self):
        """Test all expected selector types exist."""
        expected_types = [
            "css",
            "xpath",
            "id",
            "name",
            "class",
            "tag",
            "attribute",
            "text",
            "aria",
            "data_attribute",
            "composite",
        ]

        for type_name in expected_types:
            assert SelectorType(type_name) is not None


class TestHealingStatus:
    """Tests for HealingStatus enum."""

    def test_all_statuses_exist(self):
        """Test all expected statuses exist."""
        expected_statuses = ["pending", "in_progress", "success", "failed", "partial", "skipped"]

        for status_name in expected_statuses:
            assert HealingStatus(status_name) is not None


class TestConfidenceLevel:
    """Tests for ConfidenceLevel enum."""

    def test_from_score_boundaries(self):
        """Test confidence level boundaries."""
        # High: 80-100%
        assert ConfidenceLevel.from_score(1.0) == ConfidenceLevel.HIGH
        assert ConfidenceLevel.from_score(0.8) == ConfidenceLevel.HIGH
        assert ConfidenceLevel.from_score(0.79) == ConfidenceLevel.MEDIUM

        # Medium: 50-79%
        assert ConfidenceLevel.from_score(0.5) == ConfidenceLevel.MEDIUM
        assert ConfidenceLevel.from_score(0.49) == ConfidenceLevel.LOW

        # Low: 20-49%
        assert ConfidenceLevel.from_score(0.2) == ConfidenceLevel.LOW
        assert ConfidenceLevel.from_score(0.19) == ConfidenceLevel.VERY_LOW

        # Very low: 0-19%
        assert ConfidenceLevel.from_score(0.0) == ConfidenceLevel.VERY_LOW
