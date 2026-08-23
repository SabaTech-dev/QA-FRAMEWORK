"""
Unit tests for test generation use cases.
"""

from unittest.mock import Mock

import pytest

from src.domain.test_generation.entities import GeneratedTest
from src.domain.test_generation.use_cases.generate_edge_cases import (
    GenerateEdgeCases,
    GenerateEdgeCasesInput,
)
from src.domain.test_generation.use_cases.generate_from_requirements import (
    GenerateFromRequirements,
    GenerateFromRequirementsInput,
)
from src.domain.test_generation.use_cases.generate_from_ui import (
    GenerateFromUI,
    GenerateFromUIInput,
)
from src.domain.test_generation.value_objects import (
    GenerationStatus,
    RequirementSource,
    TestFramework,
)


class TestGenerateFromRequirements:
    """Tests for GenerateFromRequirements use case."""

    @pytest.fixture
    def mock_parser(self):
        """Mock requirement parser."""
        parser = Mock()
        parser.parse.return_value = [
            {
                "id": "req-001",
                "title": "User Login",
                "description": "Test user login",
                "preconditions": ["User exists"],
                "steps": ["Enter credentials"],
                "expected_results": ["User logged in"],
                "priority": "high",
                "tags": ["auth"],
            }
        ]
        return parser

    @pytest.fixture
    def mock_llm(self):
        """Mock LLM adapter."""
        llm = Mock()
        llm.generate_test.return_value = GeneratedTest(
            name="test_user_login",
            test_code="def test_user_login(): assert True",
            framework=TestFramework.PYTEST,
        )
        llm.estimate_confidence.return_value = 0.85
        return llm

    def test_execute_success(self, mock_parser, mock_llm):
        """Test successful execution."""
        # Mock test with validation
        from src.domain.test_generation.value_objects import TestCaseMetadata

        mock_llm.generate_test.return_value = GeneratedTest(
            name="test_user_login",
            test_code="def test_user_login(): assert True",
            framework=TestFramework.PYTEST,
            metadata=TestCaseMetadata.create_empty().with_validation([]),  # Valid test
        )

        use_case = GenerateFromRequirements(
            requirement_parser=mock_parser,
            llm_adapter=mock_llm,
        )

        input_data = GenerateFromRequirementsInput(
            content="# Requirements\n## User Login\nDescription here",
            source_type=RequirementSource.MARKDOWN,
            framework=TestFramework.PYTEST,
        )

        output = use_case.execute(input_data)

        assert output.success is True
        assert len(output.tests) == 1
        assert len(output.scenarios) == 1
        assert output.session.status in [GenerationStatus.COMPLETED, GenerationStatus.PARTIAL]

    def test_execute_with_min_confidence(self, mock_parser, mock_llm):
        """Test with minimum confidence filter."""
        mock_llm.estimate_confidence.return_value = 0.3  # Low confidence

        use_case = GenerateFromRequirements(
            requirement_parser=mock_parser,
            llm_adapter=mock_llm,
        )

        input_data = GenerateFromRequirementsInput(
            content="# Requirements",
            min_confidence=0.5,
        )

        output = use_case.execute(input_data)

        assert output.success is True
        assert len(output.tests) == 0  # Filtered out due to low confidence

    def test_execute_with_error(self, mock_parser, mock_llm):
        """Test execution with error."""
        mock_parser.parse.side_effect = Exception("Parse error")

        use_case = GenerateFromRequirements(
            requirement_parser=mock_parser,
            llm_adapter=mock_llm,
        )

        input_data = GenerateFromRequirementsInput(content="Invalid content")

        output = use_case.execute(input_data)

        assert output.success is False
        assert output.error_message == "Parse error"
        assert output.session.status == GenerationStatus.FAILED


class TestGenerateFromUI:
    """Tests for GenerateFromUI use case."""

    @pytest.fixture
    def mock_analyzer(self):
        """Mock UI analyzer."""
        analyzer = Mock()
        analyzer.analyze.return_value = {
            "framework": "playwright",
            "test_count": 2,
        }
        analyzer.extract_flows.return_value = [
            {
                "name": "Login Flow",
                "steps": ["Navigate", "Enter credentials"],
                "expected_results": ["User logged in"],
            }
        ]
        analyzer.extract_selectors.return_value = ["#username", "#password"]
        return analyzer

    @pytest.fixture
    def mock_llm(self):
        """Mock LLM adapter."""
        llm = Mock()
        llm.generate_test.return_value = GeneratedTest(
            name="test_login_flow",
            test_code="def test_login_flow(): pass",
            framework=TestFramework.PLAYWRIGHT,
        )
        llm.estimate_confidence.return_value = 0.9
        return llm

    def test_execute_success(self, mock_analyzer, mock_llm):
        """Test successful execution."""
        use_case = GenerateFromUI(
            ui_analyzer=mock_analyzer,
            llm_adapter=mock_llm,
        )

        input_data = GenerateFromUIInput(
            ui_code="test('login', () => { page.goto('/login'); });",
            framework=TestFramework.PLAYWRIGHT,
        )

        output = use_case.execute(input_data)

        assert output.success is True
        assert output.flows_detected == 1
        assert output.selectors_found == 2
        assert len(output.tests) == 1

    def test_execute_without_generation(self, mock_analyzer, mock_llm):
        """Test execution without generating tests."""
        use_case = GenerateFromUI(
            ui_analyzer=mock_analyzer,
            llm_adapter=mock_llm,
        )

        input_data = GenerateFromUIInput(
            ui_code="test code",
            generate_missing_tests=False,
        )

        output = use_case.execute(input_data)

        assert output.success is True
        assert len(output.tests) == 0


class TestGenerateEdgeCases:
    """Tests for GenerateEdgeCases use case."""

    @pytest.fixture
    def mock_generator(self):
        """Mock edge case generator."""
        from src.domain.test_generation.entities import EdgeCase

        generator = Mock()
        generator.generate_from_requirement.return_value = [
            EdgeCase(
                name="Boundary Case",
                description="Test boundary",
                category="boundary",
                risk_level="medium",
            ),
            EdgeCase(
                name="Security Case",
                description="Test security",
                category="security",
                risk_level="critical",
            ),
        ]
        generator.categorize_edge_case.side_effect = lambda ec: ec.category
        return generator

    @pytest.fixture
    def mock_llm(self):
        """Mock LLM adapter."""
        llm = Mock()
        llm.generate_test_for_edge_case.return_value = GeneratedTest(
            name="test_edge_case",
            test_code="def test_edge(): pass",
        )
        llm.estimate_risk.return_value = "high"
        return llm

    def test_execute_success(self, mock_generator, mock_llm):
        """Test successful execution."""
        use_case = GenerateEdgeCases(
            edge_case_generator=mock_generator,
            llm_adapter=mock_llm,
        )

        input_data = GenerateEdgeCasesInput(
            requirements=[{"id": "req-001", "title": "Feature"}],
            framework=TestFramework.PYTEST,
        )

        output = use_case.execute(input_data)

        assert output.success is True
        assert len(output.edge_cases) == 2
        assert len(output.tests) == 2
        assert output.high_risk_count >= 0

    def test_execute_with_risk_filter(self, mock_generator, mock_llm):
        """Test with risk level filtering."""
        mock_llm.estimate_risk.return_value = "low"

        use_case = GenerateEdgeCases(
            edge_case_generator=mock_generator,
            llm_adapter=mock_llm,
        )

        input_data = GenerateEdgeCasesInput(
            requirements=[{"id": "req-001"}],
            min_risk_level="high",
        )

        output = use_case.execute(input_data)

        assert output.success is True
        # Should filter out low risk cases

    def test_execute_without_tests(self, mock_generator, mock_llm):
        """Test without generating tests."""
        use_case = GenerateEdgeCases(
            edge_case_generator=mock_generator,
            llm_adapter=mock_llm,
        )

        input_data = GenerateEdgeCasesInput(
            requirements=[{"id": "req-001"}],
            generate_tests=False,
        )

        output = use_case.execute(input_data)

        assert output.success is True
        assert len(output.edge_cases) == 2
        assert len(output.tests) == 0

    def test_by_category_grouping(self, mock_generator, mock_llm):
        """Test grouping by category."""
        use_case = GenerateEdgeCases(
            edge_case_generator=mock_generator,
            llm_adapter=mock_llm,
        )

        input_data = GenerateEdgeCasesInput(
            requirements=[{"id": "req-001"}],
            categories=["boundary", "security"],
        )

        output = use_case.execute(input_data)

        assert "boundary" in output.by_category
        assert "security" in output.by_category
