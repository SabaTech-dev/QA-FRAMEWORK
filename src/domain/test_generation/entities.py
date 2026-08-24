"""
Entities for AI Test Generation Domain

Core entities that represent generated tests, scenarios, edge cases, and sessions.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from .value_objects import (
    ConfidenceLevel,
    GenerationStatus,
    GenerationType,
    RequirementSource,
    TestCaseMetadata,
    TestFramework,
    TestPriority,
)


@dataclass
class TestScenario:
    """
    A test scenario derived from requirements.

    Represents a high-level test case that can be converted
    to actual test code.
    """

    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    preconditions: List[str] = field(default_factory=list)
    steps: List[str] = field(default_factory=list)
    expected_results: List[str] = field(default_factory=list)
    priority: TestPriority = TestPriority.MEDIUM
    tags: List[str] = field(default_factory=list)
    source_requirement: Optional[str] = None
    tenant_id: Optional[str] = None

    @property
    def step_count(self) -> int:
        """Number of steps in the scenario."""
        return len(self.steps)

    @property
    def has_preconditions(self) -> bool:
        """Check if scenario has preconditions."""
        return len(self.preconditions) > 0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "preconditions": self.preconditions,
            "steps": self.steps,
            "expected_results": self.expected_results,
            "priority": self.priority.value,
            "tags": self.tags,
            "step_count": self.step_count,
        }


@dataclass
class GeneratedTest:
    """
    A generated test case with code.

    Contains the actual test code and metadata about
    the generation process.
    """

    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    scenario: Optional[TestScenario] = None
    test_code: str = ""
    framework: TestFramework = TestFramework.PYTEST
    generation_type: GenerationType = GenerationType.FROM_REQUIREMENTS
    confidence_score: float = 0.0
    confidence_level: ConfidenceLevel = ConfidenceLevel.VERY_LOW
    priority: TestPriority = TestPriority.MEDIUM
    metadata: Optional[TestCaseMetadata] = None

    # Test structure
    imports: List[str] = field(default_factory=list)
    test_function: str = ""
    fixtures: List[str] = field(default_factory=list)
    assertions: List[str] = field(default_factory=list)

    # Categorization
    tags: List[str] = field(default_factory=list)
    file_path: Optional[str] = None

    tenant_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def is_high_confidence(self) -> bool:
        """Check if test has high confidence."""
        return self.confidence_level == ConfidenceLevel.HIGH

    @property
    def assertion_count(self) -> int:
        """Number of assertions in the test."""
        return len(self.assertions)

    @property
    def is_valid(self) -> bool:
        """Check if test passed validation."""
        if self.metadata is None:
            return False
        return self.metadata.validated and len(self.metadata.validation_errors) == 0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "test_code": self.test_code,
            "framework": self.framework.value,
            "generation_type": self.generation_type.value,
            "confidence_score": self.confidence_score,
            "confidence_level": self.confidence_level.value,
            "priority": self.priority.value,
            "imports": self.imports,
            "test_function": self.test_function,
            "fixtures": self.fixtures,
            "assertions": self.assertions,
            "assertion_count": self.assertion_count,
            "tags": self.tags,
            "file_path": self.file_path,
            "is_valid": self.is_valid,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class EdgeCase:
    """
    An edge case scenario for testing.

    Represents unusual or boundary conditions that
    should be tested.
    """

    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    category: str = "general"  # boundary, negative, security, performance
    input_values: Dict[str, Any] = field(default_factory=dict)
    expected_behavior: str = ""
    risk_level: str = "medium"  # low, medium, high, critical
    generated_test: Optional[GeneratedTest] = None

    source_requirement: Optional[str] = None
    tenant_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def has_test(self) -> bool:
        """Check if edge case has a generated test."""
        return self.generated_test is not None

    @property
    def is_high_risk(self) -> bool:
        """Check if edge case is high risk."""
        return self.risk_level in ["high", "critical"]

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "input_values": self.input_values,
            "expected_behavior": self.expected_behavior,
            "risk_level": self.risk_level,
            "has_test": self.has_test,
            "is_high_risk": self.is_high_risk,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class TestGenerationSession:
    """
    A session containing multiple test generation operations.

    Tracks the overall progress and statistics of a batch
    generation operation.
    """

    id: str = field(default_factory=lambda: str(uuid4()))
    tenant_id: Optional[str] = None

    # Input
    source_type: RequirementSource = RequirementSource.MARKDOWN
    source_content: Optional[str] = None
    source_url: Optional[str] = None

    # Results
    scenarios: List[TestScenario] = field(default_factory=list)
    generated_tests: List[GeneratedTest] = field(default_factory=list)
    edge_cases: List[EdgeCase] = field(default_factory=list)

    # Statistics
    total_requirements: int = 0
    scenarios_created: int = 0
    tests_generated: int = 0
    edge_cases_identified: int = 0

    # Timing
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    generation_time_ms: int = 0

    status: GenerationStatus = GenerationStatus.PENDING
    error_message: Optional[str] = None

    @property
    def total_items(self) -> int:
        """Total number of generated items."""
        return len(self.scenarios) + len(self.generated_tests) + len(self.edge_cases)

    @property
    def high_confidence_tests(self) -> int:
        """Number of high confidence tests."""
        return sum(1 for t in self.generated_tests if t.is_high_confidence)

    @property
    def valid_tests(self) -> int:
        """Number of valid tests."""
        return sum(1 for t in self.generated_tests if t.is_valid)

    @property
    def high_risk_edge_cases(self) -> int:
        """Number of high risk edge cases."""
        return sum(1 for e in self.edge_cases if e.is_high_risk)

    @property
    def average_confidence(self) -> float:
        """Average confidence score of generated tests."""
        if not self.generated_tests:
            return 0.0
        return sum(t.confidence_score for t in self.generated_tests) / len(self.generated_tests)

    @property
    def success_rate(self) -> float:
        """Calculate generation success rate."""
        if self.total_requirements == 0:
            return 0.0
        return self.tests_generated / self.total_requirements

    @property
    def is_completed(self) -> bool:
        """Check if session is completed."""
        return self.status in [
            GenerationStatus.COMPLETED,
            GenerationStatus.FAILED,
            GenerationStatus.PARTIAL,
        ]

    def add_scenario(self, scenario: TestScenario) -> "TestGenerationSession":
        """Add a scenario to the session."""
        new_scenarios = self.scenarios + [scenario]
        return TestGenerationSession(
            id=self.id,
            tenant_id=self.tenant_id,
            source_type=self.source_type,
            source_content=self.source_content,
            source_url=self.source_url,
            scenarios=new_scenarios,
            generated_tests=self.generated_tests,
            edge_cases=self.edge_cases,
            total_requirements=self.total_requirements,
            scenarios_created=len(new_scenarios),
            tests_generated=self.tests_generated,
            edge_cases_identified=self.edge_cases_identified,
            started_at=self.started_at,
            completed_at=self.completed_at,
            generation_time_ms=self.generation_time_ms,
            status=self.status,
            error_message=self.error_message,
        )

    def add_test(self, test: GeneratedTest) -> "TestGenerationSession":
        """Add a generated test to the session."""
        new_tests = self.generated_tests + [test]
        return TestGenerationSession(
            id=self.id,
            tenant_id=self.tenant_id,
            source_type=self.source_type,
            source_content=self.source_content,
            source_url=self.source_url,
            scenarios=self.scenarios,
            generated_tests=new_tests,
            edge_cases=self.edge_cases,
            total_requirements=self.total_requirements,
            scenarios_created=self.scenarios_created,
            tests_generated=len(new_tests),
            edge_cases_identified=self.edge_cases_identified,
            started_at=self.started_at,
            completed_at=self.completed_at,
            generation_time_ms=self.generation_time_ms,
            status=self.status,
            error_message=self.error_message,
        )

    def add_edge_case(self, edge_case: EdgeCase) -> "TestGenerationSession":
        """Add an edge case to the session."""
        new_edge_cases = self.edge_cases + [edge_case]
        return TestGenerationSession(
            id=self.id,
            tenant_id=self.tenant_id,
            source_type=self.source_type,
            source_content=self.source_content,
            source_url=self.source_url,
            scenarios=self.scenarios,
            generated_tests=self.generated_tests,
            edge_cases=new_edge_cases,
            total_requirements=self.total_requirements,
            scenarios_created=self.scenarios_created,
            tests_generated=self.tests_generated,
            edge_cases_identified=len(new_edge_cases),
            started_at=self.started_at,
            completed_at=self.completed_at,
            generation_time_ms=self.generation_time_ms,
            status=self.status,
            error_message=self.error_message,
        )

    def complete(
        self, status: GenerationStatus = None, error: str = None
    ) -> "TestGenerationSession":
        """Mark session as completed."""
        final_status = status or (
            GenerationStatus.COMPLETED
            if self.tests_generated > 0 and self.valid_tests == self.tests_generated
            else GenerationStatus.PARTIAL if self.tests_generated > 0 else GenerationStatus.FAILED
        )

        generation_time = int((datetime.now(timezone.utc) - self.started_at).total_seconds() * 1000)

        return TestGenerationSession(
            id=self.id,
            tenant_id=self.tenant_id,
            source_type=self.source_type,
            source_content=self.source_content,
            source_url=self.source_url,
            scenarios=self.scenarios,
            generated_tests=self.generated_tests,
            edge_cases=self.edge_cases,
            total_requirements=self.total_requirements,
            scenarios_created=self.scenarios_created,
            tests_generated=self.tests_generated,
            edge_cases_identified=self.edge_cases_identified,
            started_at=self.started_at,
            completed_at=datetime.now(timezone.utc),
            generation_time_ms=generation_time,
            status=final_status,
            error_message=error or self.error_message,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "source_type": self.source_type.value,
            "total_requirements": self.total_requirements,
            "scenarios_created": self.scenarios_created,
            "tests_generated": self.tests_generated,
            "edge_cases_identified": self.edge_cases_identified,
            "high_confidence_tests": self.high_confidence_tests,
            "valid_tests": self.valid_tests,
            "high_risk_edge_cases": self.high_risk_edge_cases,
            "average_confidence": self.average_confidence,
            "success_rate": self.success_rate,
            "generation_time_ms": self.generation_time_ms,
            "status": self.status.value,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "scenarios": [s.to_dict() for s in self.scenarios],
            "generated_tests": [t.to_dict() for t in self.generated_tests],
            "edge_cases": [e.to_dict() for e in self.edge_cases],
        }
