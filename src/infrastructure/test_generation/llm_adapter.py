"""
LLM Adapter for Test Generation

Integrates with LLM providers (OpenAI, Gemini) for generating tests.
"""

from typing import List, Optional

from src.domain.test_generation.entities import GeneratedTest
from src.domain.test_generation.value_objects import TestFramework


class LLMTestGenerator:
    """
    Adapter for LLM-based test generation.

    Supports OpenAI and Gemini APIs for generating test code.
    """

    def __init__(
        self,
        provider: str = "openai",
        api_key: Optional[str] = None,
        model: str = "gpt-4",
    ):
        self.provider = provider
        self.api_key = api_key
        self.model = model
        self._client = None

    def generate_test(
        self,
        requirement: dict,
        framework: TestFramework,
        context: dict,
    ) -> GeneratedTest:
        """Generate a test from a requirement."""
        _prompt = self._build_requirement_prompt(requirement, framework)

        # Mock implementation - in production, would call LLM API
        test_code = self._generate_mock_test(requirement, framework)

        return GeneratedTest(
            name=f"test_{requirement.get('title', 'unknown').lower().replace(' ', '_')}",
            test_code=test_code,
            framework=framework,
            imports=self._get_framework_imports(framework),
            test_function=self._extract_function_name(test_code),
            assertions=["assert result is not None"],
            tags=requirement.get("tags", []),
        )

    def generate_test_for_edge_case(
        self,
        edge_case,
        framework: TestFramework,
    ) -> GeneratedTest:
        """Generate a test for an edge case."""
        test_code = self._generate_edge_case_test(edge_case, framework)

        return GeneratedTest(
            name=f"test_edge_{edge_case.name.lower().replace(' ', '_')}",
            test_code=test_code,
            framework=framework,
            generation_type="edge_case",
            imports=self._get_framework_imports(framework),
            test_function=self._extract_function_name(test_code),
            assertions=[f"assert {edge_case.expected_behavior}"],
            tags=["edge-case", edge_case.category],
        )

    def estimate_confidence(self, requirement: dict, test_code: str) -> float:
        """Estimate confidence score for generated test."""
        # Mock confidence estimation
        # In production, would use LLM to evaluate test quality
        base_score = 0.7

        # Adjust based on test characteristics
        if "assert" in test_code:
            base_score += 0.1
        if "setup" in test_code.lower() or "teardown" in test_code.lower():
            base_score += 0.05
        if len(test_code.split("\n")) > 10:
            base_score += 0.05

        return min(base_score, 1.0)

    def suggest_improvements(self, test_code: str) -> List[str]:
        """Suggest improvements to test code."""
        suggestions = []

        if "assert" not in test_code:
            suggestions.append("Add assertions to validate expected behavior")

        if "try" not in test_code and "except" not in test_code:
            suggestions.append("Consider adding error handling")

        if "TODO" in test_code or "FIXME" in test_code:
            suggestions.append("Remove placeholder comments")

        return suggestions

    def _build_requirement_prompt(self, requirement: dict, framework: TestFramework) -> str:
        """Build prompt for LLM."""
        return f"""
Generate a {framework.value} test for the following requirement:

Title: {requirement.get('title', 'N/A')}
Description: {requirement.get('description', 'N/A')}
Preconditions: {requirement.get('preconditions', [])}
Steps: {requirement.get('steps', [])}
Expected Results: {requirement.get('expected_results', [])}

Generate a complete, runnable test with proper imports, setup, and assertions.
"""

    def _generate_mock_test(self, requirement: dict, framework: TestFramework) -> str:
        """Generate mock test code."""
        title = requirement.get("title", "unknown").lower().replace(" ", "_")

        if framework == TestFramework.PYTEST:
            return f'''
def test_{title}():
    """Test for: {requirement.get('title', 'Unknown')}"""
    # Setup
    # {requirement.get('preconditions', ['No preconditions'])[0] if requirement.get('preconditions') else 'No preconditions'}
    
    # Execute steps
    # {requirement.get('steps', ['No steps'])[0] if requirement.get('steps') else 'No steps'}
    
    # Assert expected results
    # {requirement.get('expected_results', ['No expected results'])[0] if requirement.get('expected_results') else 'No expected results'}
    assert True
'''
        elif framework == TestFramework.PLAYWRIGHT:
            return f'''
def test_{title}(page):
    """Test for: {requirement.get('title', 'Unknown')}"""
    # Navigate and setup
    # {requirement.get('preconditions', ['No preconditions'])[0] if requirement.get('preconditions') else 'No preconditions'}
    
    # Execute steps
    # {requirement.get('steps', ['No steps'])[0] if requirement.get('steps') else 'No steps'}
    
    # Assert expected results
    # {requirement.get('expected_results', ['No expected results'])[0] if requirement.get('expected_results') else 'No expected results'}
    assert True
'''
        else:
            return f"// Test for {title} - {framework.value} framework"

    def _generate_edge_case_test(self, edge_case, framework: TestFramework) -> str:
        """Generate test for edge case."""
        name = edge_case.name.lower().replace(" ", "_")

        if framework == TestFramework.PYTEST:
            return f'''
def test_edge_{name}():
    """Edge case: {edge_case.description}"""
    # Category: {edge_case.category}
    # Risk Level: {edge_case.risk_level}
    
    # Test input values
    input_values = {edge_case.input_values}
    
    # Expected behavior: {edge_case.expected_behavior}
    assert True
'''
        return f"// Edge case test for {name}"

    def _get_framework_imports(self, framework: TestFramework) -> List[str]:
        """Get standard imports for framework."""
        imports = {
            TestFramework.PYTEST: ["import pytest", "from unittest.mock import Mock"],
            TestFramework.PLAYWRIGHT: ["from playwright.sync_api import Page, expect"],
            TestFramework.CYPRESS: ['/// <reference types="cypress" />'],
            TestFramework.SELENIUM: [
                "from selenium import webdriver",
                "from selenium.webdriver.common.by import By",
            ],
            TestFramework.JEST: ["import { describe, test, expect } from '@jest/globals'"],
            TestFramework.JUNIT: ["import org.junit.Test;", "import static org.junit.Assert.*"],
        }
        return imports.get(framework, [])

    def _extract_function_name(self, test_code: str) -> str:
        """Extract test function name from code."""
        for line in test_code.split("\n"):
            if "def test_" in line or 'it("' in line or 'test("' in line:
                return line.strip()
        return "test_unknown"
