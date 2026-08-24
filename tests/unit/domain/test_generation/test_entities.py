"""
Unit tests for test generation entities.
"""

import pytest

from src.domain.test_generation.entities import (
    EdgeCase,
    GeneratedTest,
    TestGenerationSession,
    TestScenario,
)
from src.domain.test_generation.value_objects import (
    ConfidenceLevel,
    GenerationStatus,
    GenerationType,
    RequirementSource,
    TestCaseMetadata,
    TestFramework,
    TestPriority,
)


class TestTestScenario:
    """Tests for TestScenario entity."""

    def test_create_scenario(self):
        """Test creating a test scenario."""
        scenario = TestScenario(
            name="User Login",
            description="Test user login functionality",
            preconditions=["User exists", "User is logged out"],
            steps=["Navigate to login page", "Enter credentials", "Click login"],
            expected_results=["User is logged in", "Redirect to dashboard"],
            priority=TestPriority.HIGH,
            tags=["auth", "login"],
        )

        assert scenario.name == "User Login"
        assert scenario.step_count == 3
        assert scenario.has_preconditions is True
        assert len(scenario.tags) == 2

    def test_scenario_without_preconditions(self):
        """Test scenario without preconditions."""
        scenario = TestScenario(
            name="Simple Test",
            description="Simple test scenario",
        )

        assert scenario.has_preconditions is False
        assert scenario.step_count == 0

    def test_scenario_to_dict(self):
        """Test scenario serialization."""
        scenario = TestScenario(
            name="Test",
            description="Description",
            steps=["Step 1"],
        )

        data = scenario.to_dict()

        assert data["name"] == "Test"
        assert data["step_count"] == 1
        assert "id" in data


class TestGeneratedTest:
    """Tests for GeneratedTest entity."""

    def test_create_generated_test(self):
        """Test creating a generated test."""
        test = GeneratedTest(
            name="test_user_login",
            test_code="def test_user_login(): assert True",
            framework=TestFramework.PYTEST,
            generation_type=GenerationType.FROM_REQUIREMENTS,
            confidence_score=0.85,
            confidence_level=ConfidenceLevel.HIGH,
            priority=TestPriority.HIGH,
            imports=["import pytest"],
            test_function="def test_user_login():",
            fixtures=["client"],
            assertions=["assert response.status_code == 200"],
            tags=["auth", "login"],
        )

        assert test.name == "test_user_login"
        assert test.framework == TestFramework.PYTEST
        assert test.is_high_confidence is True
        assert test.assertion_count == 1

    def test_test_validity(self):
        """Test test validity check."""
        test = GeneratedTest(
            name="test_valid",
            test_code="def test_valid(): assert True",
            metadata=TestCaseMetadata.create_empty().with_validation([]),
        )

        assert test.is_valid is True

    def test_test_invalid_with_errors(self):
        """Test test with validation errors."""
        test = GeneratedTest(
            name="test_invalid",
            test_code="def test_invalid(): pass",
            metadata=TestCaseMetadata.create_empty().with_validation(["No assertions"]),
        )

        assert test.is_valid is False

    def test_test_without_metadata(self):
        """Test without metadata."""
        test = GeneratedTest(
            name="test_no_meta",
            test_code="def test(): pass",
        )

        assert test.is_valid is False

    def test_generated_test_to_dict(self):
        """Test generated test serialization."""
        test = GeneratedTest(
            name="test",
            test_code="code",
            framework=TestFramework.PYTEST,
        )

        data = test.to_dict()

        assert data["name"] == "test"
        assert data["framework"] == "pytest"
        assert "created_at" in data


class TestEdgeCase:
    """Tests for EdgeCase entity."""

    def test_create_edge_case(self):
        """Test creating an edge case."""
        edge_case = EdgeCase(
            name="SQL Injection",
            description="Test for SQL injection vulnerability",
            category="security",
            input_values={"username": "'; DROP TABLE users; --"},
            expected_behavior="Input sanitized",
            risk_level="critical",
        )

        assert edge_case.name == "SQL Injection"
        assert edge_case.category == "security"
        assert edge_case.is_high_risk is True
        assert edge_case.has_test is False

    def test_edge_case_with_test(self):
        """Test edge case with generated test."""
        test = GeneratedTest(name="test_sql_injection", test_code="def test(): pass")
        edge_case = EdgeCase(
            name="Edge Case",
            description="Description",
            generated_test=test,
        )

        assert edge_case.has_test is True

    def test_edge_case_risk_levels(self):
        """Test different risk levels."""
        high_risk = EdgeCase(name="High", risk_level="high")
        critical_risk = EdgeCase(name="Critical", risk_level="critical")
        medium_risk = EdgeCase(name="Medium", risk_level="medium")
        low_risk = EdgeCase(name="Low", risk_level="low")

        assert high_risk.is_high_risk is True
        assert critical_risk.is_high_risk is True
        assert medium_risk.is_high_risk is False
        assert low_risk.is_high_risk is False

    def test_edge_case_to_dict(self):
        """Test edge case serialization."""
        edge_case = EdgeCase(
            name="Test",
            description="Desc",
            category="boundary",
        )

        data = edge_case.to_dict()

        assert data["name"] == "Test"
        assert data["category"] == "boundary"
        assert "created_at" in data


class TestTestGenerationSession:
    """Tests for TestGenerationSession entity."""

    def test_create_session(self):
        """Test creating a generation session."""
        session = TestGenerationSession(
            tenant_id="tenant-001",
            source_type=RequirementSource.MARKDOWN,
            total_requirements=5,
        )

        assert session.tenant_id == "tenant-001"
        assert session.total_requirements == 5
        assert session.status == GenerationStatus.PENDING
        assert session.total_items == 0

    def test_add_test_to_session(self):
        """Test adding test to session."""
        session = TestGenerationSession()
        test = GeneratedTest(name="test_1", test_code="def test_1(): pass")

        updated = session.add_test(test)

        assert updated.tests_generated == 1
        assert len(updated.generated_tests) == 1
        assert updated.total_items == 1

    def test_add_scenario_to_session(self):
        """Test adding scenario to session."""
        session = TestGenerationSession()
        scenario = TestScenario(name="Scenario 1")

        updated = session.add_scenario(scenario)

        assert updated.scenarios_created == 1
        assert len(updated.scenarios) == 1

    def test_add_edge_case_to_session(self):
        """Test adding edge case to session."""
        session = TestGenerationSession()
        edge_case = EdgeCase(name="Edge Case 1")

        updated = session.add_edge_case(edge_case)

        assert updated.edge_cases_identified == 1
        assert len(updated.edge_cases) == 1

    def test_session_statistics(self):
        """Test session statistics."""
        session = TestGenerationSession(total_requirements=10)

        # Add tests with different confidence levels
        high_conf = GeneratedTest(
            name="test_1",
            confidence_score=0.9,
            confidence_level=ConfidenceLevel.HIGH,
            metadata=TestCaseMetadata.create_empty().with_validation([]),
        )
        medium_conf = GeneratedTest(
            name="test_2",
            confidence_score=0.6,
            confidence_level=ConfidenceLevel.MEDIUM,
        )

        session = session.add_test(high_conf)
        session = session.add_test(medium_conf)

        assert session.high_confidence_tests == 1
        assert session.valid_tests == 1
        assert session.average_confidence == pytest.approx(0.75, 0.01)
        assert session.success_rate == pytest.approx(0.2, 0.01)

    def test_complete_session(self):
        """Test completing a session."""
        session = TestGenerationSession(total_requirements=5)
        test = GeneratedTest(name="test", test_code="code")
        session = session.add_test(test)

        completed = session.complete()

        assert completed.is_completed is True
        assert completed.completed_at is not None
        assert completed.generation_time_ms >= 0  # Can be 0 if very fast

    def test_session_with_edge_cases(self):
        """Test session with high risk edge cases."""
        session = TestGenerationSession()

        high_risk = EdgeCase(name="High", risk_level="critical")
        low_risk = EdgeCase(name="Low", risk_level="low")

        session = session.add_edge_case(high_risk)
        session = session.add_edge_case(low_risk)

        assert session.high_risk_edge_cases == 1

    def test_session_to_dict(self):
        """Test session serialization."""
        session = TestGenerationSession(
            tenant_id="tenant-001",
            total_requirements=5,
        )
        test = GeneratedTest(name="test", test_code="code")
        session = session.add_test(test)

        data = session.to_dict()

        assert data["tenant_id"] == "tenant-001"
        assert data["total_requirements"] == 5
        assert data["tests_generated"] == 1
        assert "started_at" in data
