"""
Generate Edge Cases Use Case

Analyzes requirements and generates edge case test scenarios.
"""

from dataclasses import dataclass
from typing import List, Optional, Protocol

from ..entities import EdgeCase, GeneratedTest, TestGenerationSession
from ..value_objects import GenerationStatus, TestFramework


class EdgeCaseGenerator(Protocol):
    """Protocol for generating edge cases."""

    def generate_from_requirement(self, requirement: dict) -> List[EdgeCase]:
        """Generate edge cases from a requirement."""
        ...

    def categorize_edge_case(self, edge_case: EdgeCase) -> str:
        """Categorize an edge case."""
        ...


class LLMAdapter(Protocol):
    """Protocol for LLM-based test generation."""

    def generate_test_for_edge_case(
        self,
        edge_case: EdgeCase,
        framework: TestFramework,
    ) -> GeneratedTest:
        """Generate a test for an edge case."""
        ...

    def estimate_risk(self, edge_case: EdgeCase) -> str:
        """Estimate risk level for an edge case."""
        ...


@dataclass
class GenerateEdgeCasesInput:
    """Input for the GenerateEdgeCases use case."""

    requirements: List[dict]
    framework: TestFramework = TestFramework.PYTEST
    tenant_id: Optional[str] = None
    categories: List[str] = None  # None = all categories
    max_per_requirement: int = 5
    generate_tests: bool = True
    min_risk_level: str = "medium"


@dataclass
class GenerateEdgeCasesOutput:
    """Output from the GenerateEdgeCases use case."""

    session: TestGenerationSession
    edge_cases: List[EdgeCase]
    tests: List[GeneratedTest]
    by_category: dict
    high_risk_count: int
    success: bool
    error_message: Optional[str] = None


class GenerateEdgeCases:
    """
    Use case for generating edge case test scenarios.

    Takes requirements and generates comprehensive edge cases
    covering boundary conditions, negative scenarios, etc.
    """

    # Default categories to consider
    DEFAULT_CATEGORIES = [
        "boundary",
        "negative",
        "security",
        "performance",
        "data_validation",
        "concurrency",
        "error_handling",
    ]

    def __init__(
        self,
        edge_case_generator: EdgeCaseGenerator,
        llm_adapter: LLMAdapter,
    ):
        self.edge_case_generator = edge_case_generator
        self.llm_adapter = llm_adapter

    def execute(self, input_data: GenerateEdgeCasesInput) -> GenerateEdgeCasesOutput:
        """Execute the use case."""
        session = TestGenerationSession(
            tenant_id=input_data.tenant_id,
            source_type=TestFramework.PYTEST,  # Placeholder
        )

        categories = input_data.categories or self.DEFAULT_CATEGORIES

        try:
            all_edge_cases = []
            all_tests = []
            by_category = {cat: [] for cat in categories}

            # Generate edge cases for each requirement
            for requirement in input_data.requirements:
                edge_cases = self.edge_case_generator.generate_from_requirement(requirement)

                # Filter by category and limit
                filtered_cases = [ec for ec in edge_cases if ec.category in categories][
                    : input_data.max_per_requirement
                ]

                # Estimate risk and generate tests
                for edge_case in filtered_cases:
                    # Estimate risk level
                    risk = self.llm_adapter.estimate_risk(edge_case)
                    edge_case = EdgeCase(
                        id=edge_case.id,
                        name=edge_case.name,
                        description=edge_case.description,
                        category=edge_case.category,
                        input_values=edge_case.input_values,
                        expected_behavior=edge_case.expected_behavior,
                        risk_level=risk,
                        source_requirement=str(requirement.get("id", "")),
                        tenant_id=edge_case.tenant_id,
                    )

                    # Filter by minimum risk level
                    if self._risk_meets_threshold(risk, input_data.min_risk_level):
                        # Generate test if requested
                        if input_data.generate_tests:
                            test = self.llm_adapter.generate_test_for_edge_case(
                                edge_case=edge_case,
                                framework=input_data.framework,
                            )
                            edge_case = EdgeCase(
                                id=edge_case.id,
                                name=edge_case.name,
                                description=edge_case.description,
                                category=edge_case.category,
                                input_values=edge_case.input_values,
                                expected_behavior=edge_case.expected_behavior,
                                risk_level=risk,
                                generated_test=test,
                                source_requirement=edge_case.source_requirement,
                                tenant_id=edge_case.tenant_id,
                            )
                            all_tests.append(test)
                            session = session.add_test(test)

                        all_edge_cases.append(edge_case)
                        session = session.add_edge_case(edge_case)

                        # Categorize
                        if edge_case.category in by_category:
                            by_category[edge_case.category].append(edge_case)

            # Complete session
            session = session.complete()

            high_risk_count = sum(1 for ec in all_edge_cases if ec.is_high_risk)

            return GenerateEdgeCasesOutput(
                session=session,
                edge_cases=all_edge_cases,
                tests=all_tests,
                by_category=by_category,
                high_risk_count=high_risk_count,
                success=True,
            )

        except Exception as e:
            session = session.complete(
                status=GenerationStatus.FAILED,
                error=str(e),
            )

            return GenerateEdgeCasesOutput(
                session=session,
                edge_cases=[],
                tests=[],
                by_category={},
                high_risk_count=0,
                success=False,
                error_message=str(e),
            )

    def _risk_meets_threshold(self, risk: str, min_risk: str) -> bool:
        """Check if risk level meets minimum threshold."""
        risk_levels = ["low", "medium", "high", "critical"]
        risk_idx = risk_levels.index(risk) if risk in risk_levels else 0
        min_idx = risk_levels.index(min_risk) if min_risk in risk_levels else 0
        return risk_idx >= min_idx
