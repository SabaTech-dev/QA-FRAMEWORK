"""
Edge Case Generator

Generates edge case scenarios from requirements.
"""

from uuid import uuid4

from src.domain.test_generation.entities import EdgeCase


class EdgeCaseGeneratorImpl:
    """
    Implementation of edge case generation.

    Generates comprehensive edge cases covering various categories.
    """

    # Edge case templates by category
    EDGE_CASE_TEMPLATES = {
        "boundary": [
            {
                "name": "Minimum value",
                "description": "Test with minimum allowed value",
                "input_template": {"value": "MIN"},
                "expected_behavior": "System accepts minimum value",
            },
            {
                "name": "Maximum value",
                "description": "Test with maximum allowed value",
                "input_template": {"value": "MAX"},
                "expected_behavior": "System accepts maximum value",
            },
            {
                "name": "Empty value",
                "description": "Test with empty/null value",
                "input_template": {"value": ""},
                "expected_behavior": "System handles empty value appropriately",
            },
        ],
        "negative": [
            {
                "name": "Invalid input",
                "description": "Test with invalid input data",
                "input_template": {"value": "INVALID"},
                "expected_behavior": "System rejects invalid input with error",
            },
            {
                "name": "Unauthorized access",
                "description": "Test without proper authorization",
                "input_template": {"auth": None},
                "expected_behavior": "System denies access",
            },
            {
                "name": "Missing required field",
                "description": "Test with missing required field",
                "input_template": {"required_field": None},
                "expected_behavior": "System validates and returns error",
            },
        ],
        "security": [
            {
                "name": "SQL injection attempt",
                "description": "Test for SQL injection vulnerability",
                "input_template": {"value": "'; DROP TABLE users; --"},
                "expected_behavior": "System sanitizes input and prevents injection",
            },
            {
                "name": "XSS attempt",
                "description": "Test for cross-site scripting",
                "input_template": {"value": '<script>alert("XSS")</script>'},
                "expected_behavior": "System escapes malicious script",
            },
            {
                "name": "Path traversal attempt",
                "description": "Test for path traversal vulnerability",
                "input_template": {"path": "../../../etc/passwd"},
                "expected_behavior": "System prevents path traversal",
            },
        ],
        "performance": [
            {
                "name": "Large input data",
                "description": "Test with large amount of data",
                "input_template": {"data_size": "LARGE"},
                "expected_behavior": "System handles large data within time limit",
            },
            {
                "name": "Concurrent requests",
                "description": "Test with multiple simultaneous requests",
                "input_template": {"concurrent_users": 100},
                "expected_behavior": "System handles concurrent load",
            },
            {
                "name": "Slow network",
                "description": "Test with slow network conditions",
                "input_template": {"network_speed": "SLOW"},
                "expected_behavior": "System handles slow connection gracefully",
            },
        ],
        "data_validation": [
            {
                "name": "Invalid email format",
                "description": "Test with malformed email address",
                "input_template": {"email": "invalid-email"},
                "expected_behavior": "System validates and rejects invalid email",
            },
            {
                "name": "Invalid date format",
                "description": "Test with invalid date",
                "input_template": {"date": "99/99/9999"},
                "expected_behavior": "System validates and rejects invalid date",
            },
            {
                "name": "Special characters",
                "description": "Test with special characters",
                "input_template": {"value": "!@#$%^&*()"},
                "expected_behavior": "System handles special characters",
            },
        ],
        "concurrency": [
            {
                "name": "Race condition",
                "description": "Test for race condition",
                "input_template": {"concurrent_ops": True},
                "expected_behavior": "System prevents race conditions",
            },
            {
                "name": "Deadlock scenario",
                "description": "Test for potential deadlock",
                "input_template": {"locks": "MULTIPLE"},
                "expected_behavior": "System avoids deadlock",
            },
        ],
        "error_handling": [
            {
                "name": "Network timeout",
                "description": "Test with network timeout",
                "input_template": {"timeout": True},
                "expected_behavior": "System handles timeout gracefully",
            },
            {
                "name": "Service unavailable",
                "description": "Test when dependent service is down",
                "input_template": {"service_status": "DOWN"},
                "expected_behavior": "System handles service failure gracefully",
            },
            {
                "name": "Database connection lost",
                "description": "Test with lost database connection",
                "input_template": {"db_connection": "LOST"},
                "expected_behavior": "System handles database failure",
            },
        ],
    }

    def generate_from_requirement(self, requirement: dict) -> list[EdgeCase]:
        """Generate edge cases from a requirement."""
        edge_cases = []

        # Determine applicable categories based on requirement
        categories = self._determine_categories(requirement)

        for category in categories:
            templates = self.EDGE_CASE_TEMPLATES.get(category, [])

            for template in templates:
                edge_case = EdgeCase(
                    id=str(uuid4()),
                    name=f"{template['name']} - {requirement.get('title', 'Unknown')}",
                    description=template["description"],
                    category=category,
                    input_values=self._populate_template(template["input_template"], requirement),
                    expected_behavior=template["expected_behavior"],
                    risk_level=self._estimate_risk(category),
                    source_requirement=requirement.get("id"),
                )
                edge_cases.append(edge_case)

        return edge_cases

    def categorize_edge_case(self, edge_case: EdgeCase) -> str:
        """Categorize an edge case."""
        return edge_case.category

    def _determine_categories(self, requirement: dict) -> list[str]:
        """Determine which edge case categories apply."""
        categories = ["boundary", "negative"]  # Always include these

        description = requirement.get("description", "").lower()
        tags = [t.lower() for t in requirement.get("tags", [])]

        # Add security tests for authentication/authorization
        if any(word in description for word in ["auth", "login", "password", "permission"]):
            categories.append("security")

        # Add performance tests for high-load scenarios
        if any(word in description for word in ["load", "performance", "scale", "concurrent"]):
            categories.extend(["performance", "concurrency"])

        # Add data validation tests for forms/input
        if any(word in description for word in ["form", "input", "field", "validate"]):
            categories.append("data_validation")

        # Add error handling tests for integrations
        if any(word in description for word in ["api", "service", "external", "integration"]):
            categories.append("error_handling")

        # Check tags
        if "security" in tags:
            categories.append("security")
        if "performance" in tags:
            categories.append("performance")

        return list(set(categories))

    def _populate_template(self, template: dict, requirement: dict) -> dict:
        """Populate template with requirement-specific values."""
        populated = {}

        for key, value in template.items():
            if value == "MIN":
                # Try to extract minimum from requirement
                populated[key] = requirement.get("min_value", 0)
            elif value == "MAX":
                # Try to extract maximum from requirement
                populated[key] = requirement.get("max_value", 1000)
            elif value == "INVALID":
                populated[key] = "INVALID_DATA"
            elif value == "LARGE":
                populated[key] = "X" * 10000  # Large string
            else:
                populated[key] = value

        return populated

    def _estimate_risk(self, category: str) -> str:
        """Estimate risk level for a category."""
        high_risk = ["security", "concurrency"]
        medium_risk = ["performance", "error_handling"]

        if category in high_risk:
            return "high"
        elif category in medium_risk:
            return "medium"
        else:
            return "low"
