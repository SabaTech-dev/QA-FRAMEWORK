"""
Unit Tests for Self-Healing Infrastructure

Tests for selector healer, confidence scorer, and related implementations.
"""

from datetime import datetime, timezone
from unittest.mock import Mock

import pytest

from src.domain.self_healing.entities import Selector
from src.domain.self_healing.value_objects import (
    HealingContext,
    HealingStatus,
    SelectorMetadata,
    SelectorType,
)
from src.infrastructure.self_healing.confidence_scorer import AIConfidenceScorer, ConfidenceScorer
from src.infrastructure.self_healing.selector_generator import SelectorGenerator
from src.infrastructure.self_healing.selector_healer import SelectorHealer
from src.infrastructure.self_healing.selector_repository import InMemorySelectorRepository


class TestConfidenceScorer:
    """Tests for ConfidenceScorer."""

    @pytest.fixture
    def scorer(self):
        """Create a confidence scorer instance."""
        return ConfidenceScorer()

    @pytest.fixture
    def context(self):
        """Create a healing context."""
        return HealingContext(
            page_url="https://example.com",
            page_title="Test Page",
            screenshot_path=None,
            html_snapshot=None,
            surrounding_text="Submit",
            element_attributes={"id": "submit-btn", "class": "button primary"},
            parent_selector=".form",
            sibling_selectors=[],
        )

    def test_score_id_selector(self, scorer, context):
        """Test scoring an ID selector."""
        selector = Selector(
            value="#submit-btn",
            selector_type=SelectorType.ID,
        )

        score = scorer.score(selector, context)

        # ID selectors should score high
        assert score >= 0.8

    def test_score_class_selector(self, scorer, context):
        """Test scoring a class selector."""
        selector = Selector(
            value=".button",
            selector_type=SelectorType.CLASS,
        )

        score = scorer.score(selector, context)

        # Class selectors should have moderate score
        assert 0.3 <= score <= 0.8

    def test_score_data_attribute_selector(self, scorer, context):
        """Test scoring a data attribute selector."""
        context_with_data = HealingContext(
            page_url="https://example.com",
            page_title="Test Page",
            screenshot_path=None,
            html_snapshot=None,
            surrounding_text=None,
            element_attributes={"data-testid": "submit-button"},
            parent_selector=None,
            sibling_selectors=[],
        )

        selector = Selector(
            value="[data-testid='submit-button']",
            selector_type=SelectorType.DATA_ATTRIBUTE,
        )

        score = scorer.score(selector, context_with_data)

        # Data attributes should score high
        assert score >= 0.7

    def test_score_with_historical_success(self, scorer, context):
        """Test scoring with historical success data."""
        selector = Selector(
            value=".button",
            selector_type=SelectorType.CLASS,
            metadata=SelectorMetadata(
                created_at=datetime.now(timezone.utc),
                updated_at=None,
                usage_count=100,
                success_rate=0.95,
                last_successful=datetime.now(timezone.utc),
                source="manual",
            ),
        )

        score = scorer.score(selector, context)

        # High historical success should boost score (class selector + good history)
        assert score >= 0.5

    def test_score_with_historical_failure(self, scorer, context):
        """Test scoring with historical failure data."""
        selector = Selector(
            value=".button",
            selector_type=SelectorType.CLASS,
            metadata=SelectorMetadata(
                created_at=datetime.now(timezone.utc),
                updated_at=None,
                usage_count=100,
                success_rate=0.2,
                last_successful=None,
                source="manual",
            ),
        )

        score = scorer.score(selector, context)

        # Low historical success should reduce score
        assert score < 0.5

    def test_score_candidates(self, scorer, context):
        """Test scoring multiple candidates."""
        selectors = [
            Selector(value="#submit-btn", selector_type=SelectorType.ID),
            Selector(value=".button", selector_type=SelectorType.CLASS),
            Selector(value="//button", selector_type=SelectorType.XPATH),
        ]

        scored = scorer.score_candidates(selectors, context)

        # Should return all selectors with scores
        assert len(scored) == 3

        # Should be sorted by score descending
        for i in range(len(scored) - 1):
            assert scored[i][1] >= scored[i + 1][1]

    def test_score_specificity_long_selector(self, scorer, context):
        """Test that very long selectors are penalized."""
        long_selector = Selector(
            value=".very > .long > .nested > .selector > .that > .goes > .on > .forever",
            selector_type=SelectorType.CSS,
        )

        short_selector = Selector(
            value="#submit",
            selector_type=SelectorType.ID,
        )

        long_score = scorer.score(long_selector, context)
        short_score = scorer.score(short_selector, context)

        assert short_score > long_score


class TestAIConfidenceScorer:
    """Tests for AI-powered confidence scorer."""

    @pytest.fixture
    def scorer(self):
        """Create an AI confidence scorer instance."""
        return AIConfidenceScorer()

    @pytest.fixture
    def context(self):
        """Create a healing context."""
        return HealingContext.create_minimal("https://example.com")

    def test_record_outcome(self, scorer, context):
        """Test recording healing outcomes."""
        selector = Selector(value=".button", selector_type=SelectorType.CLASS)

        # Record some outcomes
        scorer.record_outcome(selector, 0.7, True)
        scorer.record_outcome(selector, 0.7, True)
        scorer.record_outcome(selector, 0.7, False)

        # Should have learning data
        assert len(scorer._learning_data) == 1

    def test_calibration_adjustment(self, scorer, context):
        """Test calibration adjustment calculation."""
        selector = Selector(value=".button", selector_type=SelectorType.CLASS)

        # Record outcomes that show overconfidence
        for _ in range(10):
            scorer.record_outcome(selector, 0.8, False)

        adjustment = scorer.get_calibration_adjustment(selector)

        # Should suggest lowering confidence
        assert adjustment < 0

    def test_calibration_insufficient_data(self, scorer, context):
        """Test calibration with insufficient data."""
        selector = Selector(value=".button", selector_type=SelectorType.CLASS)

        # Only 2 observations - not enough for calibration
        scorer.record_outcome(selector, 0.8, True)
        scorer.record_outcome(selector, 0.8, False)

        adjustment = scorer.get_calibration_adjustment(selector)

        # Should return 0 (no adjustment) with insufficient data
        assert adjustment == 0.0


class TestSelectorGenerator:
    """Tests for SelectorGenerator."""

    @pytest.fixture
    def generator(self):
        """Create a selector generator instance."""
        return SelectorGenerator()

    def test_generate_from_id(self, generator):
        """Test generating selector from ID attribute."""
        attributes = {"id": "submit-button"}

        selectors = generator.generate_from_attributes(attributes)

        assert len(selectors) > 0
        assert any(s.value == "#submit-button" for s in selectors)

    def test_generate_from_data_attribute(self, generator):
        """Test generating selector from data attribute."""
        attributes = {"data-testid": "submit-btn"}

        selectors = generator.generate_from_attributes(attributes)

        assert any("[data-testid" in s.value for s in selectors)

    def test_generate_from_classes(self, generator):
        """Test generating selector from classes."""
        attributes = {"class": "button primary large"}

        selectors = generator.generate_from_attributes(attributes)

        # Should generate individual class selectors
        class_selectors = [s for s in selectors if s.selector_type == SelectorType.CLASS]
        assert len(class_selectors) > 0

    def test_generate_from_name(self, generator):
        """Test generating selector from name attribute."""
        attributes = {"name": "email"}

        selectors = generator.generate_from_attributes(attributes)

        assert any("[name=" in s.value for s in selectors)

    def test_generate_from_aria(self, generator):
        """Test generating selector from ARIA attributes."""
        attributes = {"aria-label": "Submit form"}

        selectors = generator.generate_from_attributes(attributes)

        aria_selectors = [s for s in selectors if s.selector_type == SelectorType.ARIA]
        assert len(aria_selectors) > 0

    def test_generate_from_text(self, generator):
        """Test generating text-based selectors."""
        attributes = {"tagName": "button"}
        text = "Click here to submit"

        selectors = generator.generate_from_attributes(attributes, element_text=text)

        # Should generate XPath text selectors
        xpath_selectors = [s for s in selectors if s.selector_type == SelectorType.XPATH]
        assert len(xpath_selectors) > 0

    def test_generate_from_context(self, generator):
        """Test generating selectors from context."""
        context = HealingContext(
            page_url="https://example.com",
            page_title=None,
            screenshot_path=None,
            html_snapshot=None,
            surrounding_text="Submit",
            element_attributes={"tagName": "button", "class": "btn"},
            parent_selector=".form-container",
            sibling_selectors=[".prev-btn"],
        )

        selectors = generator.generate_from_context(context)

        # Should generate context-based selectors
        assert len(selectors) > 0

    def test_generate_composite(self, generator):
        """Test generating composite selectors."""
        base_selectors = [
            Selector(value=".primary", selector_type=SelectorType.CLASS),
            Selector(value=".large", selector_type=SelectorType.CLASS),
        ]

        composites = generator.generate_composite(base_selectors)

        # Should combine class selectors
        assert len(composites) > 0
        # Combined class selector
        assert any(".primary.large" in s.value or ".primary" in s.value for s in composites)

    def test_avoid_indexed_classes(self):
        """Test that indexed classes are avoided."""
        generator = SelectorGenerator(avoid_indexed_selectors=True)

        attributes = {"class": "item-12345 button active-999"}

        selectors = generator.generate_from_attributes(attributes)

        # Should not include heavily indexed classes
        for s in selectors:
            assert "12345" not in s.value
            assert "999" not in s.value


class TestInMemorySelectorRepository:
    """Tests for InMemorySelectorRepository."""

    @pytest.fixture
    def repository(self):
        """Create a repository instance."""
        return InMemorySelectorRepository()

    @pytest.mark.asyncio
    async def test_save_and_get(self, repository):
        """Test saving and retrieving a selector."""
        selector = Selector(
            value="#submit",
            selector_type=SelectorType.ID,
        )

        saved = await repository.save(selector)
        retrieved = await repository.get_by_id(saved.id)

        assert retrieved is not None
        assert retrieved.value == "#submit"

    @pytest.mark.asyncio
    async def test_get_by_value(self, repository):
        """Test retrieving selector by value."""
        selector = Selector(
            value="#submit",
            selector_type=SelectorType.ID,
        )

        await repository.save(selector)
        retrieved = await repository.get_by_value("#submit", SelectorType.ID)

        assert retrieved is not None
        assert retrieved.value == "#submit"

    @pytest.mark.asyncio
    async def test_save_alternative(self, repository):
        """Test saving alternative selector."""
        parent = Selector(value="#old", selector_type=SelectorType.ID)
        alternative = Selector(value=".new", selector_type=SelectorType.CLASS)

        await repository.save(parent)
        await repository.save_alternative(parent.id, alternative)

        alternatives = await repository.get_alternatives(parent.id)

        assert len(alternatives) == 1
        assert alternatives[0].value == ".new"

    @pytest.mark.asyncio
    async def test_record_usage(self, repository):
        """Test recording selector usage."""
        selector = Selector(value=".button", selector_type=SelectorType.CLASS)

        saved = await repository.save(selector)
        await repository.record_usage(saved.id, success=True)

        updated = await repository.get_by_id(saved.id)

        assert updated.metadata.usage_count == 1
        assert updated.metadata.success_rate == 1.0

    @pytest.mark.asyncio
    async def test_get_low_confidence(self, repository):
        """Test retrieving low confidence selectors."""
        # Create selectors with different success rates
        high_conf = Selector(
            value="#high",
            selector_type=SelectorType.ID,
            tenant_id="tenant-1",
            metadata=SelectorMetadata(
                created_at=datetime.now(timezone.utc),
                updated_at=None,
                usage_count=10,
                success_rate=0.9,
                last_successful=datetime.now(timezone.utc),
                source="manual",
            ),
        )

        low_conf = Selector(
            value="#low",
            selector_type=SelectorType.ID,
            tenant_id="tenant-1",
            metadata=SelectorMetadata(
                created_at=datetime.now(timezone.utc),
                updated_at=None,
                usage_count=10,
                success_rate=0.3,
                last_successful=None,
                source="manual",
            ),
        )

        await repository.save(high_conf)
        await repository.save(low_conf)

        low_confidence = await repository.get_low_confidence("tenant-1", threshold=0.5)

        assert len(low_confidence) == 1
        assert low_confidence[0].value == "#low"

    @pytest.mark.asyncio
    async def test_clear(self, repository):
        """Test clearing repository."""
        selector = Selector(value=".test", selector_type=SelectorType.CLASS)
        await repository.save(selector)

        repository.clear()

        all_selectors = await repository.get_low_confidence("any", threshold=1.0, limit=1000)
        assert len(all_selectors) == 0


class TestSelectorHealer:
    """Tests for SelectorHealer."""

    @pytest.fixture
    def mock_scorer(self):
        """Create mock confidence scorer."""
        scorer = Mock()
        scorer.score = Mock(return_value=0.8)
        scorer.score_candidates = Mock(
            return_value=[
                (Selector(value="#new", selector_type=SelectorType.ID), 0.8),
                (Selector(value=".alt", selector_type=SelectorType.CLASS), 0.6),
            ]
        )
        return scorer

    @pytest.fixture
    def mock_generator(self):
        """Create mock selector generator."""
        generator = Mock()
        generator.generate_from_attributes = Mock(
            return_value=[
                Selector(value="#new", selector_type=SelectorType.ID),
            ]
        )
        generator.generate_from_context = Mock(return_value=[])
        generator.generate_composite = Mock(return_value=[])
        return generator

    @pytest.fixture
    def mock_page_analyzer(self):
        """Create mock page analyzer."""
        analyzer = Mock()
        analyzer.validate_selector = Mock(return_value=True)
        analyzer.find_similar_elements = Mock(return_value=[])
        return analyzer

    @pytest.fixture
    def healer(self, mock_scorer, mock_generator, mock_page_analyzer):
        """Create a selector healer instance."""
        return SelectorHealer(
            confidence_scorer=mock_scorer,
            selector_generator=mock_generator,
            page_analyzer=mock_page_analyzer,
            min_confidence=0.5,
        )

    @pytest.fixture
    def context(self):
        """Create a healing context."""
        return HealingContext(
            page_url="https://example.com",
            page_title="Test",
            screenshot_path=None,
            html_snapshot=None,
            surrounding_text=None,
            element_attributes={"id": "submit"},
            parent_selector=None,
            sibling_selectors=[],
        )

    def test_heal_success(self, healer, context):
        """Test successful healing."""
        broken = Selector(
            value="#broken",
            selector_type=SelectorType.ID,
            alternatives=[
                Selector(value="#working", selector_type=SelectorType.ID),
            ],
        )

        result = healer.heal(broken, context)

        assert result.status == HealingStatus.SUCCESS
        assert result.healed_selector is not None
        assert result.confidence_score >= 0.5

    def test_heal_failure(self, mock_scorer, mock_generator, mock_page_analyzer, context):
        """Test failed healing."""
        # Configure mocks to fail
        mock_scorer.score = Mock(return_value=0.3)  # Below threshold
        mock_scorer.score_candidates = Mock(return_value=[])
        mock_page_analyzer.validate_selector = Mock(return_value=False)

        healer = SelectorHealer(
            confidence_scorer=mock_scorer,
            selector_generator=mock_generator,
            page_analyzer=mock_page_analyzer,
            min_confidence=0.5,
        )

        broken = Selector(value="#broken", selector_type=SelectorType.ID)

        result = healer.heal(broken, context)

        assert result.status == HealingStatus.FAILED

    def test_heal_tracks_timing(self, healer, context):
        """Test that healing tracks timing."""
        broken = Selector(
            value="#broken",
            selector_type=SelectorType.ID,
            alternatives=[Selector(value="#alt", selector_type=SelectorType.ID)],
        )

        result = healer.heal(broken, context)

        assert result.healing_time_ms >= 0

    def test_batch_heal(self, healer, context):
        """Test batch healing."""
        selectors = [
            Selector(value="#a", selector_type=SelectorType.ID),
            Selector(value="#b", selector_type=SelectorType.ID),
        ]

        def context_factory(s):
            return context

        results = healer.batch_heal(selectors, context_factory)

        assert len(results) == 2
