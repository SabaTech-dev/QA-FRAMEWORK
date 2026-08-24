"""
Value Objects for AI Test Generation Domain

Defines the core value objects used in the test generation system.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum


class GenerationType(str, Enum):
    """Types of test generation methods."""

    FROM_REQUIREMENTS = "from_requirements"
    FROM_UI = "from_ui"
    FROM_CODE = "from_code"
    EDGE_CASES = "edge_cases"
    REGRESSION = "regression"
    INTEGRATION = "integration"


class TestFramework(str, Enum):
    """Supported test frameworks."""

    PYTEST = "pytest"
    PLAYWRIGHT = "playwright"
    CYPRESS = "cypress"
    SELENIUM = "selenium"
    JEST = "jest"
    JUNIT = "junit"
    ROBOT = "robot"


class TestPriority(str, Enum):
    """Priority levels for generated tests."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    SMOKE = "smoke"


class GenerationStatus(str, Enum):
    """Status of a test generation operation."""

    PENDING = "pending"
    ANALYZING = "analyzing"
    GENERATING = "generating"
    VALIDATING = "validating"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


class ConfidenceLevel(str, Enum):
    """Confidence level for generated tests."""

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


class RequirementSource(str, Enum):
    """Source of requirements for test generation."""

    MARKDOWN = "markdown"
    JIRA = "jira"
    CONFLUENCE = "confluence"
    USER_STORY = "user_story"
    DOCUMENTATION = "documentation"
    CODE_COMMENTS = "code_comments"
    API_SPEC = "api_spec"


@dataclass(frozen=True)
class TestCaseMetadata:
    """Immutable metadata about a generated test case."""

    generated_at: datetime
    generator_version: str
    llm_model: str | None
    source_type: RequirementSource
    source_id: str | None
    tokens_used: int
    generation_time_ms: int
    validated: bool
    validation_errors: list[str]

    @classmethod
    def create_empty(cls) -> "TestCaseMetadata":
        """Create empty metadata."""
        return cls(
            generated_at=datetime.now(UTC),
            generator_version="1.0.0",
            llm_model=None,
            source_type=RequirementSource.MARKDOWN,
            source_id=None,
            tokens_used=0,
            generation_time_ms=0,
            validated=False,
            validation_errors=[],
        )

    def with_validation(self, errors: list[str]) -> "TestCaseMetadata":
        """Create metadata with validation results."""
        return TestCaseMetadata(
            generated_at=self.generated_at,
            generator_version=self.generator_version,
            llm_model=self.llm_model,
            source_type=self.source_type,
            source_id=self.source_id,
            tokens_used=self.tokens_used,
            generation_time_ms=self.generation_time_ms,
            validated=True,
            validation_errors=errors,
        )
