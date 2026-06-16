"""
LLM Adapter for Test Generation

Integrates with LLM providers (OpenAI, Gemini) for generating tests.
All LLM calls are traced via Langfuse for observability.
"""

from typing import Optional, List
import json

from src.domain.test_generation.entities import GeneratedTest, TestScenario
from src.domain.test_generation.value_objects import (
    TestFramework,
    TestCaseMetadata,
)
from src.infrastructure.observability import get_tracer


class LLMTestGenerator:
    """
    Adapter for LLM-based test generation.
    
    Supports OpenAI and Gemini APIs for generating test code.
    All generation calls are automatically traced via Langfuse.
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
        self._tracer = get_tracer()
    
    def generate_test(
        self,
        requirement: dict,
        framework: TestFramework,
        context: dict,
    ) -> GeneratedTest:
        """Generate a test from a requirement."""
        trace_meta = {
            "operation": "generate_test",
            "provider": self.provider,
            "model": self.model,
            "framework": framework.value,
            "requirement_title": requirement.get("title", "unknown"),
        }

        with self._tracer.trace_generation(
            name=f"generate_test:{requirement.get('title', 'unknown')}",
            metadata=trace_meta,
        ) as ctx:
            prompt = self._build_requirement_prompt(requirement, framework)
            ctx.set_input({"prompt": prompt, "requirement": requirement, "framework": framework.value})
            
            # Mock implementation - in production, would call LLM API
            test_code = self._generate_mock_test(requirement, framework)
            
            result = GeneratedTest(
                name=f"test_{requirement.get('title', 'unknown').lower().replace(' ', '_')}",
                test_code=test_code,
                framework=framework,
                imports=self._get_framework_imports(framework),
                test_function=self._extract_function_name(test_code),
                assertions=["assert result is not None"],
                tags=requirement.get("tags", []),
            )
            
            ctx.set_output({
                "test_name": result.name,
                "test_code": test_code,
                "framework": framework.value,
            })
            ctx.set_metadata("model", self.model)
            ctx.set_metadata("provider", self.provider)
            
            return result
    
    def generate_test_for_edge_case(
        self,
        edge_case,
        framework: TestFramework,
    ) -> GeneratedTest:
        """Generate a test for an edge case."""
        trace_meta = {
            "operation": "generate_edge_case_test",
            "provider": self.provider,
            "model": self.model,
            "framework": framework.value,
            "edge_case_name": edge_case.name,
            "edge_case_category": getattr(edge_case, "category", "unknown"),
        }

        with self._tracer.trace_generation(
            name=f"generate_edge_case:{edge_case.name}",
            metadata=trace_meta,
        ) as ctx:
            ctx.set_input({
                "edge_case": {
                    "name": edge_case.name,
                    "description": getattr(edge_case, "description", ""),
                    "category": getattr(edge_case, "category", ""),
                    "risk_level": getattr(edge_case, "risk_level", ""),
                    "input_values": getattr(edge_case, "input_values", {}),
                    "expected_behavior": getattr(edge_case, "expected_behavior", ""),
                },
                "framework": framework.value,
            })

            test_code = self._generate_edge_case_test(edge_case, framework)
            
            result = GeneratedTest(
                name=f"test_edge_{edge_case.name.lower().replace(' ', '_')}",
                test_code=test_code,
                framework=framework,
                generation_type="edge_case",
                imports=self._get_framework_imports(framework),
                test_function=self._extract_function_name(test_code),
                assertions=[f"assert {edge_case.expected_behavior}"],
                tags=["edge-case", edge_case.category],
            )

            ctx.set_output({
                "test_name": result.name,
                "test_code": test_code,
            })
            
            return result
    
    def estimate_confidence(self, requirement: dict, test_code: str) -> float:
        """Estimate confidence score for generated test."""
        with self._tracer.trace_generation(
            name="estimate_confidence",
            metadata={"operation": "estimate_confidence", "model": self.model},
        ) as ctx:
            ctx.set_input({
                "requirement_title": requirement.get("title", "unknown"),
                "test_code_length": len(test_code),
            })
            
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
            
            score = min(base_score, 1.0)
            
            ctx.set_output({"confidence_score": score})
            
            # Record score in Langfuse
            self._tracer.record_score(
                trace_id=ctx.trace_id,
                name="confidence",
                value=score,
                comment=f"Auto-estimated confidence for {requirement.get('title', 'test')}",
            )
            
            return score
    
    def suggest_improvements(self, test_code: str) -> List[str]:
        """Suggest improvements to test code."""
        with self._tracer.trace_generation(
            name="suggest_improvements",
            metadata={"operation": "suggest_improvements", "model": self.model},
        ) as ctx:
            ctx.set_input({"test_code_length": len(test_code)})
            
            suggestions = []
            
            if "assert" not in test_code:
                suggestions.append("Add assertions to validate expected behavior")
            
            if "try" not in test_code and "except" not in test_code:
                suggestions.append("Consider adding error handling")
            
            if "TODO" in test_code or "FIXME" in test_code:
                suggestions.append("Remove placeholder comments")
            
            ctx.set_output({"suggestions_count": len(suggestions), "suggestions": suggestions})
            
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
        title = requirement.get('title', 'unknown').lower().replace(' ', '_')
        
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
        name = edge_case.name.lower().replace(' ', '_')
        
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
            TestFramework.CYPRESS: ["/// <reference types=\"cypress\" />"],
            TestFramework.SELENIUM: ["from selenium import webdriver", "from selenium.webdriver.common.by import By"],
            TestFramework.JEST: ["import { describe, test, expect } from '@jest/globals'"],
            TestFramework.JUNIT: ["import org.junit.Test;", "import static org.junit.Assert.*"],
        }
        return imports.get(framework, [])
    
    def _extract_function_name(self, test_code: str) -> str:
        """Extract test function name from code."""
        for line in test_code.split('\n'):
            if 'def test_' in line or 'it("' in line or 'test("' in line:
                return line.strip()
        return "test_unknown"
