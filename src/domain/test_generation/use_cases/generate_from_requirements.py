"""
Generate Tests from Requirements Use Case

Analyzes requirements documents and generates test cases.
"""

from dataclasses import dataclass
from typing import Protocol

from ..entities import GeneratedTest, TestGenerationSession, TestScenario
from ..value_objects import (
    ConfidenceLevel,
    GenerationStatus,
    GenerationType,
    RequirementSource,
    TestCaseMetadata,
    TestFramework,
    TestPriority,
)


class RequirementParser(Protocol):
    """Protocol for parsing requirements documents."""

    def parse(self, content: str) -> list[dict]:
        """Parse requirements content into structured format."""
        ...


class LLMAdapter(Protocol):
    """Protocol for LLM-based test generation."""

    def generate_test(
        self,
        requirement: dict,
        framework: TestFramework,
        context: dict,
    ) -> GeneratedTest:
        """Generate a test from a requirement."""
        ...

    def estimate_confidence(self, requirement: dict, test_code: str) -> float:
        """Estimate confidence score for generated test."""
        ...


@dataclass
class GenerateFromRequirementsInput:
    """Input for the GenerateFromRequirements use case."""

    content: str
    source_type: RequirementSource = RequirementSource.MARKDOWN
    framework: TestFramework = TestFramework.PYTEST
    tenant_id: str | None = None
    generate_edge_cases: bool = True
    min_confidence: float = 0.5


@dataclass
class GenerateFromRequirementsOutput:
    """Output from the GenerateFromRequirements use case."""

    session: TestGenerationSession
    tests: list[GeneratedTest]
    scenarios: list[TestScenario]
    success: bool
    error_message: str | None = None


class GenerateFromRequirements:
    """
    Use case for generating tests from requirements documents.

    Takes a requirements document (markdown, JIRA, etc.) and
    generates comprehensive test cases.
    """

    def __init__(
        self,
        requirement_parser: RequirementParser,
        llm_adapter: LLMAdapter,
    ):
        self.requirement_parser = requirement_parser
        self.llm_adapter = llm_adapter

    def execute(self, input_data: GenerateFromRequirementsInput) -> GenerateFromRequirementsOutput:
        """Execute the use case."""
        session = TestGenerationSession(
            tenant_id=input_data.tenant_id,
            source_type=input_data.source_type,
            source_content=input_data.content[:500],  # Store first 500 chars
        )

        try:
            # Parse requirements
            requirements = self.requirement_parser.parse(input_data.content)
            session = TestGenerationSession(
                id=session.id,
                tenant_id=session.tenant_id,
                source_type=session.source_type,
                source_content=session.source_content,
                total_requirements=len(requirements),
                status=GenerationStatus.ANALYZING,
            )

            # Generate tests for each requirement
            generated_tests = []
            for req in requirements:
                test = self._generate_single_test(
                    requirement=req,
                    framework=input_data.framework,
                    session_id=session.id,
                )

                if test.confidence_score >= input_data.min_confidence:
                    generated_tests.append(test)
                    session = session.add_test(test)

            # Create scenarios
            scenarios = self._create_scenarios(requirements)
            for scenario in scenarios:
                session = session.add_scenario(scenario)

            # Complete session
            session = session.complete()

            return GenerateFromRequirementsOutput(
                session=session,
                tests=generated_tests,
                scenarios=scenarios,
                success=True,
            )

        except Exception as e:
            session = session.complete(
                status=GenerationStatus.FAILED,
                error=str(e),
            )

            return GenerateFromRequirementsOutput(
                session=session,
                tests=[],
                scenarios=[],
                success=False,
                error_message=str(e),
            )

    def _generate_single_test(
        self,
        requirement: dict,
        framework: TestFramework,
        session_id: str,
    ) -> GeneratedTest:
        """Generate a single test from a requirement."""
        # Generate test code
        test = self.llm_adapter.generate_test(
            requirement=requirement,
            framework=framework,
            context={"session_id": session_id},
        )

        # Estimate confidence
        confidence = self.llm_adapter.estimate_confidence(
            requirement=requirement,
            test_code=test.test_code,
        )

        # Update test with confidence
        return GeneratedTest(
            id=test.id,
            name=test.name,
            scenario=test.scenario,
            test_code=test.test_code,
            framework=framework,
            generation_type=GenerationType.FROM_REQUIREMENTS,
            confidence_score=confidence,
            confidence_level=ConfidenceLevel.from_score(confidence),
            priority=self._map_priority(requirement.get("priority", "medium")),
            metadata=TestCaseMetadata.create_empty(),
            imports=test.imports,
            test_function=test.test_function,
            fixtures=test.fixtures,
            assertions=test.assertions,
            tags=test.tags,
            tenant_id=test.tenant_id,
        )

    def _create_scenarios(self, requirements: list[dict]) -> list[TestScenario]:
        """Create test scenarios from requirements."""
        scenarios = []

        for req in requirements:
            scenario = TestScenario(
                name=req.get("title", "Untitled Scenario"),
                description=req.get("description", ""),
                preconditions=req.get("preconditions", []),
                steps=req.get("steps", []),
                expected_results=req.get("expected_results", []),
                priority=self._map_priority(req.get("priority", "medium")),
                tags=req.get("tags", []),
                source_requirement=req.get("id"),
            )
            scenarios.append(scenario)

        return scenarios

    def _map_priority(self, priority: str) -> TestPriority:
        """Map string priority to TestPriority enum."""
        mapping = {
            "critical": TestPriority.CRITICAL,
            "high": TestPriority.HIGH,
            "medium": TestPriority.MEDIUM,
            "low": TestPriority.LOW,
            "smoke": TestPriority.SMOKE,
        }
        return mapping.get(priority.lower(), TestPriority.MEDIUM)
