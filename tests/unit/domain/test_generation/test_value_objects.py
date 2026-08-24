"""
Unit tests for test generation value objects.
"""

from datetime import UTC, datetime

import pytest

from src.domain.test_generation.value_objects import (
    ConfidenceLevel,
    GenerationStatus,
    GenerationType,
    RequirementSource,
    TestCaseMetadata,
    TestFramework,
    TestPriority,
)


class TestGenerationType:
    """Tests for GenerationType enum."""

    def test_generation_types_exist(self):
        """Test all generation types are defined."""
        assert GenerationType.FROM_REQUIREMENTS
        assert GenerationType.FROM_UI
        assert GenerationType.FROM_CODE
        assert GenerationType.EDGE_CASES
        assert GenerationType.REGRESSION
        assert GenerationType.INTEGRATION

    def test_generation_type_values(self):
        """Test generation type values."""
        assert GenerationType.FROM_REQUIREMENTS.value == "from_requirements"
        assert GenerationType.FROM_UI.value == "from_ui"


class TestTestFramework:
    """Tests for TestFramework enum."""

    def test_frameworks_exist(self):
        """Test all frameworks are defined."""
        assert TestFramework.PYTEST
        assert TestFramework.PLAYWRIGHT
        assert TestFramework.CYPRESS
        assert TestFramework.SELENIUM
        assert TestFramework.JEST
        assert TestFramework.JUNIT
        assert TestFramework.ROBOT

    def test_framework_values(self):
        """Test framework values."""
        assert TestFramework.PYTEST.value == "pytest"
        assert TestFramework.PLAYWRIGHT.value == "playwright"


class TestTestPriority:
    """Tests for TestPriority enum."""

    def test_priorities_exist(self):
        """Test all priorities are defined."""
        assert TestPriority.CRITICAL
        assert TestPriority.HIGH
        assert TestPriority.MEDIUM
        assert TestPriority.LOW
        assert TestPriority.SMOKE


class TestGenerationStatus:
    """Tests for GenerationStatus enum."""

    def test_statuses_exist(self):
        """Test all statuses are defined."""
        assert GenerationStatus.PENDING
        assert GenerationStatus.ANALYZING
        assert GenerationStatus.GENERATING
        assert GenerationStatus.VALIDATING
        assert GenerationStatus.COMPLETED
        assert GenerationStatus.FAILED
        assert GenerationStatus.PARTIAL


class TestConfidenceLevel:
    """Tests for ConfidenceLevel enum."""

    def test_confidence_levels_exist(self):
        """Test all confidence levels are defined."""
        assert ConfidenceLevel.HIGH
        assert ConfidenceLevel.MEDIUM
        assert ConfidenceLevel.LOW
        assert ConfidenceLevel.VERY_LOW

    def test_from_score_high(self):
        """Test high confidence from score."""
        level = ConfidenceLevel.from_score(0.85)
        assert level == ConfidenceLevel.HIGH

    def test_from_score_medium(self):
        """Test medium confidence from score."""
        level = ConfidenceLevel.from_score(0.65)
        assert level == ConfidenceLevel.MEDIUM

    def test_from_score_low(self):
        """Test low confidence from score."""
        level = ConfidenceLevel.from_score(0.35)
        assert level == ConfidenceLevel.LOW

    def test_from_score_very_low(self):
        """Test very low confidence from score."""
        level = ConfidenceLevel.from_score(0.15)
        assert level == ConfidenceLevel.VERY_LOW

    def test_from_score_boundary_high(self):
        """Test boundary score for high confidence."""
        level = ConfidenceLevel.from_score(0.8)
        assert level == ConfidenceLevel.HIGH

    def test_from_score_boundary_medium(self):
        """Test boundary score for medium confidence."""
        level = ConfidenceLevel.from_score(0.5)
        assert level == ConfidenceLevel.MEDIUM


class TestRequirementSource:
    """Tests for RequirementSource enum."""

    def test_sources_exist(self):
        """Test all sources are defined."""
        assert RequirementSource.MARKDOWN
        assert RequirementSource.JIRA
        assert RequirementSource.CONFLUENCE
        assert RequirementSource.USER_STORY
        assert RequirementSource.DOCUMENTATION
        assert RequirementSource.CODE_COMMENTS
        assert RequirementSource.API_SPEC


class TestTestCaseMetadata:
    """Tests for TestCaseMetadata value object."""

    def test_create_metadata(self):
        """Test creating metadata."""
        metadata = TestCaseMetadata(
            generated_at=datetime.now(UTC),
            generator_version="1.0.0",
            llm_model="gpt-4",
            source_type=RequirementSource.MARKDOWN,
            source_id="req-001",
            tokens_used=100,
            generation_time_ms=500,
            validated=False,
            validation_errors=[],
        )

        assert metadata.generator_version == "1.0.0"
        assert metadata.llm_model == "gpt-4"
        assert metadata.tokens_used == 100
        assert metadata.validated is False

    def test_create_empty(self):
        """Test creating empty metadata."""
        metadata = TestCaseMetadata.create_empty()

        assert metadata.generator_version == "1.0.0"
        assert metadata.llm_model is None
        assert metadata.tokens_used == 0
        assert metadata.validated is False
        assert len(metadata.validation_errors) == 0

    def test_with_validation_success(self):
        """Test metadata with successful validation."""
        metadata = TestCaseMetadata.create_empty()
        validated = metadata.with_validation(errors=[])

        assert validated.validated is True
        assert len(validated.validation_errors) == 0

    def test_with_validation_errors(self):
        """Test metadata with validation errors."""
        metadata = TestCaseMetadata.create_empty()
        validated = metadata.with_validation(errors=["Missing assertion"])

        assert validated.validated is True
        assert len(validated.validation_errors) == 1
        assert "Missing assertion" in validated.validation_errors

    def test_metadata_is_immutable(self):
        """Test metadata is immutable (frozen)."""
        metadata = TestCaseMetadata.create_empty()

        with pytest.raises(AttributeError):
            metadata.tokens_used = 200
