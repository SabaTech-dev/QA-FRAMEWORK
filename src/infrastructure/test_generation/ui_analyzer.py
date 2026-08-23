"""
UI Analyzer

Analyzes UI automation code (Playwright/Cypress) for test generation.
"""

import re
from typing import List


class PlaywrightAnalyzer:
    """Analyzer for Playwright test code."""

    def analyze(self, code: str, framework) -> dict:
        """Analyze Playwright code."""
        return {
            "framework": "playwright",
            "test_count": self._count_tests(code),
            "selectors": self.extract_selectors(code),
            "flows": self.extract_flows(code),
            "has_page_objects": self._has_page_objects(code),
            "has_fixtures": self._has_fixtures(code),
        }

    def extract_selectors(self, code: str) -> List[str]:
        """Extract selectors from Playwright code."""
        selectors = []

        # Match page.locator(), page.getBy*(), $(), $$()
        patterns = [
            r'page\.locator\(["\']([^"\']+)["\']',
            r'page\.getBy\w+\(["\']([^"\']+)["\']',
            r'\$\(["\']([^"\']+)["\']',
            r'\$\$\(["\']([^"\']+)["\']',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, code)
            selectors.extend(matches)

        return list(set(selectors))

    def extract_flows(self, code: str) -> List[dict]:
        """Extract user flows from Playwright code."""
        flows = []

        # Find test functions
        test_pattern = r'(?:test|it)\s*\(\s*["\']([^"\']+)["\']'
        test_names = re.findall(test_pattern, code)

        for name in test_names:
            # Extract test body (simplified)
            flow = {
                "name": name,
                "description": f"User flow: {name}",
                "steps": self._extract_test_steps(code, name),
                "expected_results": ["Test passes"],
                "priority": "medium",
                "tags": ["playwright", "ui"],
            }
            flows.append(flow)

        return flows

    def _count_tests(self, code: str) -> int:
        """Count number of tests."""
        return len(re.findall(r"(?:test|it)\s*\(", code))

    def _has_page_objects(self, code: str) -> bool:
        """Check if code uses page objects."""
        return "Page" in code and "class" in code

    def _has_fixtures(self, code: str) -> bool:
        """Check if code uses fixtures."""
        return "fixture" in code or "@pytest.fixture" in code

    def _extract_test_steps(self, code: str, test_name: str) -> List[str]:
        """Extract steps from a test."""
        # Simplified extraction
        steps = []

        # Find common Playwright actions
        actions = [
            (r'page\.goto\(["\']([^"\']+)["\']', "Navigate to {}"),
            (r'page\.click\(["\']([^"\']+)["\']', "Click on {}"),
            (r'page\.fill\(["\']([^"\']+)["\']', "Fill in {}"),
            (r'page\.type\(["\']([^"\']+)["\']', "Type into {}"),
            (r'page\.waitForSelector\(["\']([^"\']+)["\']', "Wait for {}"),
        ]

        for pattern, template in actions:
            matches = re.findall(pattern, code)
            for match in matches:
                steps.append(template.format(match))

        return steps


class CypressAnalyzer:
    """Analyzer for Cypress test code."""

    def analyze(self, code: str, framework) -> dict:
        """Analyze Cypress code."""
        return {
            "framework": "cypress",
            "test_count": self._count_tests(code),
            "selectors": self.extract_selectors(code),
            "flows": self.extract_flows(code),
            "has_custom_commands": self._has_custom_commands(code),
        }

    def extract_selectors(self, code: str) -> List[str]:
        """Extract selectors from Cypress code."""
        selectors = []

        # Match cy.get(), cy.contains()
        patterns = [
            r'cy\.get\(["\']([^"\']+)["\']',
            r'cy\.contains\(["\']([^"\']+)["\']',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, code)
            selectors.extend(matches)

        return list(set(selectors))

    def extract_flows(self, code: str) -> List[dict]:
        """Extract user flows from Cypress code."""
        flows = []

        # Find describe/it blocks
        describe_pattern = r'describe\s*\(\s*["\']([^"\']+)["\']'
        it_pattern = r'it\s*\(\s*["\']([^"\']+)["\']'

        _describes = re.findall(describe_pattern, code)
        its = re.findall(it_pattern, code)

        for name in its:
            flow = {
                "name": name,
                "description": f"User flow: {name}",
                "steps": self._extract_cypress_steps(code),
                "expected_results": ["Test passes"],
                "priority": "medium",
                "tags": ["cypress", "ui"],
            }
            flows.append(flow)

        return flows

    def _count_tests(self, code: str) -> int:
        """Count number of tests."""
        return len(re.findall(r"it\s*\(", code))

    def _has_custom_commands(self, code: str) -> bool:
        """Check if code uses custom commands."""
        return "Cypress.Commands.add" in code

    def _extract_cypress_steps(self, code: str) -> List[str]:
        """Extract steps from Cypress code."""
        steps = []

        # Find common Cypress actions
        actions = [
            (r'cy\.visit\(["\']([^"\']+)["\']', "Visit {}"),
            (r"cy\.click\(\)", "Click element"),
            (r'cy\.type\(["\']([^"\']+)["\']', "Type {}"),
            (r"cy\.wait\((\d+)\)", "Wait {} ms"),
        ]

        for pattern, template in actions:
            matches = re.findall(pattern, code)
            for match in matches:
                steps.append(template.format(match))

        return steps
