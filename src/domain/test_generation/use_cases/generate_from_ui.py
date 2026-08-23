"""
Generate Tests from UI Use Case

Analyzes UI automation code and generates additional test cases.
"""

from dataclasses import dataclass
from typing import List, Optional, Protocol

from ..entities import GeneratedTest, TestGenerationSession, TestScenario
from ..value_objects import (
    ConfidenceLevel,
    GenerationStatus,
    GenerationType,
    TestCaseMetadata,
    TestFramework,
    TestPriority,
)


class UIAnalyzer(Protocol):
    """Protocol for analyzing UI automation code."""

    def analyze(self, code: str, framework: TestFramework) -> dict:
        """Analyze UI automation code."""
        ...

    def extract_selectors(self, code: str) -> List[str]:
        """Extract selectors from UI code."""
        ...

    def extract_flows(self, code: str) -> List[dict]:
        """Extract user flows from UI code."""
        ...


class LLMAdapter(Protocol):
    """Protocol for LLM-based test generation."""

    def generate_test(
        self,
        flow: dict,
        framework: TestFramework,
        context: dict,
    ) -> GeneratedTest:
        """Generate a test from a UI flow."""
        ...

    def suggest_improvements(self, test_code: str) -> List[str]:
        """Suggest improvements to test code."""
        ...

    def estimate_confidence(self, flow: dict, test_code: str) -> float:
        """Estimate confidence score for generated test."""
        ...


@dataclass
class GenerateFromUIInput:
    """Input for the GenerateFromUI use case."""

    ui_code: str
    framework: TestFramework = TestFramework.PLAYWRIGHT
    tenant_id: Optional[str] = None
    generate_missing_tests: bool = True
    improve_existing: bool = False
    min_confidence: float = 0.5


@dataclass
class GenerateFromUIOutput:
    """Output from the GenerateFromUI use case."""

    session: TestGenerationSession
    tests: List[GeneratedTest]
    flows_detected: int
    selectors_found: int
    success: bool
    error_message: Optional[str] = None


class GenerateFromUI:
    """
    Use case for generating tests from UI automation code.

    Analyzes existing Playwright/Cypress code and generates
    additional test cases or improvements.
    """

    def __init__(
        self,
        ui_analyzer: UIAnalyzer,
        llm_adapter: LLMAdapter,
    ):
        self.ui_analyzer = ui_analyzer
        self.llm_adapter = llm_adapter

    def execute(self, input_data: GenerateFromUIInput) -> GenerateFromUIOutput:
        """Execute the use case."""
        session = TestGenerationSession(
            tenant_id=input_data.tenant_id,
            source_type=(
                TestFramework.PLAYWRIGHT
                if input_data.framework == TestFramework.PLAYWRIGHT
                else TestFramework.CYPRESS
            ),
        )

        try:
            # Analyze UI code
            _analysis = self.ui_analyzer.analyze(
                code=input_data.ui_code,
                framework=input_data.framework,
            )

            # Extract flows
            flows = self.ui_analyzer.extract_flows(input_data.ui_code)
            selectors = self.ui_analyzer.extract_selectors(input_data.ui_code)

            session = TestGenerationSession(
                id=session.id,
                tenant_id=session.tenant_id,
                source_type=session.source_type,
                total_requirements=len(flows),
                status=GenerationStatus.ANALYZING,
            )

            # Generate tests for each flow
            generated_tests = []

            for flow in flows:
                if input_data.generate_missing_tests:
                    test = self._generate_test_for_flow(
                        flow=flow,
                        framework=input_data.framework,
                        session_id=session.id,
                    )

                    if test.confidence_score >= input_data.min_confidence:
                        generated_tests.append(test)
                        session = session.add_test(test)

            # Complete session
            session = session.complete()

            return GenerateFromUIOutput(
                session=session,
                tests=generated_tests,
                flows_detected=len(flows),
                selectors_found=len(selectors),
                success=True,
            )

        except Exception as e:
            session = session.complete(
                status=GenerationStatus.FAILED,
                error=str(e),
            )

            return GenerateFromUIOutput(
                session=session,
                tests=[],
                flows_detected=0,
                selectors_found=0,
                success=False,
                error_message=str(e),
            )

    def _generate_test_for_flow(
        self,
        flow: dict,
        framework: TestFramework,
        session_id: str,
    ) -> GeneratedTest:
        """Generate a test for a UI flow."""
        # Generate test code
        test = self.llm_adapter.generate_test(
            flow=flow,
            framework=framework,
            context={"session_id": session_id},
        )

        # Estimate confidence
        confidence = self.llm_adapter.estimate_confidence(
            flow=flow,
            test_code=test.test_code,
        )

        # Create scenario from flow
        scenario = TestScenario(
            name=flow.get("name", "UI Flow"),
            description=flow.get("description", ""),
            steps=flow.get("steps", []),
            expected_results=flow.get("expected_results", []),
            priority=self._map_priority(flow.get("priority", "medium")),
            tags=flow.get("tags", ["ui", "automation"]),
        )

        return GeneratedTest(
            id=test.id,
            name=test.name,
            scenario=scenario,
            test_code=test.test_code,
            framework=framework,
            generation_type=GenerationType.FROM_UI,
            confidence_score=confidence,
            confidence_level=ConfidenceLevel.from_score(confidence),
            priority=self._map_priority(flow.get("priority", "medium")),
            metadata=TestCaseMetadata.create_empty(),
            imports=test.imports,
            test_function=test.test_function,
            fixtures=test.fixtures,
            assertions=test.assertions,
            tags=test.tags + ["ui", "generated"],
            tenant_id=test.tenant_id,
        )

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
