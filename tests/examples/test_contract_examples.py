"""
API Contract Testing Examples.

Demonstrates usage of contract testing with OpenAPI specifications.
"""

import pytest

from src.adapters.api_contract.contract_validator import (
    ContractCoverageChecker,
    ContractValidator,
    contract_test,
    validate_api_response,
)


@pytest.mark.contract_test
class TestContractValidation:
    """Examples of API contract validation."""

    def test_validate_get_user_response(self, contract_validator: ContractValidator) -> None:
        """Example: Validate GET /users/{id} response."""
        # Mock API response
        response_body = {
            "id": 123,
            "username": "johndoe",
            "email": "john@example.com",
            "firstName": "John",
            "lastName": "Doe",
        }

        # Validate against contract
        violations = contract_validator.validate_response(
            endpoint_path="/users/{id}", method="GET", status_code=200, response_body=response_body
        )

        # Assert no violations
        assert len(violations) == 0, f"Contract violations: {violations}"

    def test_validate_create_user_request(self, contract_validator: ContractValidator) -> None:
        """Example: Validate POST /users request body."""
        request_body = {
            "username": "newuser",
            "email": "new@example.com",
            "password": "securepassword123",
        }

        violations = contract_validator.validate_request(
            endpoint_path="/users", method="POST", request_body=request_body
        )

        assert len(violations) == 0, f"Contract violations: {violations}"

    def test_validate_error_response(self, contract_validator: ContractValidator) -> None:
        """Example: Validate error response structure."""
        error_response = {"error": "User not found", "code": "USER_NOT_FOUND", "status": 404}

        violations = contract_validator.validate_response(
            endpoint_path="/users/{id}", method="GET", status_code=404, response_body=error_response
        )

        assert len(violations) == 0


class TestContractCoverage:
    """Examples of contract coverage checking."""

    def test_coverage_tracking(self, coverage_checker: ContractCoverageChecker) -> None:
        """Example: Track which endpoints are tested."""
        # Mark endpoints as tested
        coverage_checker.mark_tested("/users", "GET")
        coverage_checker.mark_tested("/users", "POST")
        coverage_checker.mark_tested("/users/{id}", "GET")

        # Get coverage report
        coverage = coverage_checker.get_coverage()

        print(f"Coverage: {coverage['coverage_percentage']}%")
        print(f"Tested: {coverage['tested_endpoints']} endpoints")
        print(f"Untested: {coverage['untested_endpoints']} endpoints")

        # Assert minimum coverage
        assert coverage["coverage_percentage"] >= 40.0, "Coverage below 40%"

    def test_generate_coverage_report(
        self, coverage_checker: ContractCoverageChecker, tmp_path
    ) -> None:
        """Example: Generate coverage report."""
        # Mark some endpoints
        coverage_checker.mark_tested("/users", "GET")
        coverage_checker.mark_tested("/products", "GET")

        # Generate report
        report_path = tmp_path / "coverage_report.md"
        report = coverage_checker.generate_report(str(report_path))

        # Verify report was created
        assert report_path.exists()
        assert "API Contract Coverage Report" in report


class TestConvenienceFunctions:
    """Examples using convenience functions."""

    def test_validate_with_convenience_function(self) -> None:
        """Example: Use convenience function for quick validation."""
        response_body = {"id": 1, "name": "Product A", "price": 29.99}

        # Quick validation
        violations = validate_api_response(
            spec_path="openapi.yaml",
            endpoint_path="/products/{id}",
            method="GET",
            status_code=200,
            response_body=response_body,
        )

        # In a real test, you'd check the violations
        # This is just demonstrating the API
        print(f"Found {len(violations)} violations")


# Using decorator to mark contract tests
@contract_test("/users", "GET", spec_path="openapi.yaml")
class TestWithDecorator:
    """Examples using contract test decorator."""

    def test_decorated_contract(self) -> None:
        """Test marked with contract decorator."""
        # The decorator marks this test as covering GET /users


# Real-world example: Integration with HTTP client testing
@pytest.mark.contract_test
class TestAPIWithContractValidation:
    """Real-world example: Testing API with contract validation."""

    def test_api_integration(self, contract_validator: ContractValidator, mock_http_client) -> None:
        """
        Example: Test API call and validate response against contract.

        In real usage, this would use actual HTTP calls.
        """
        # Simulate API call (would be real call in practice)
        mock_response = {"id": 123, "username": "testuser", "email": "test@example.com"}

        # Validate response matches contract
        violations = contract_validator.validate_response(
            endpoint_path="/users/{id}",
            method="GET",
            status_code=200,
            response_body=mock_response,
            headers={"Content-Type": "application/json"},
        )

        # Assert contract compliance
        assert (
            len(violations) == 0
        ), f"API response violates contract: {[v.message for v in violations]}"
