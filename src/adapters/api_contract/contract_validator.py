"""
API Contract Testing using OpenAPI/Swagger specifications.

Validates API implementations against OpenAPI 3.0 specifications:
- Schema validation for requests and responses
- Endpoint coverage checking
- Response code validation
- Header validation
- Example validation

Clean Architecture: Adapter layer
SOLID Principles:
    - SRP: Each validator has single responsibility
    - OCP: Extensible validation rules
    - DIP: Depends on abstractions
"""

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import yaml


class ValidationSeverity(Enum):
    """Validation severity levels."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationResult:
    """Result of a validation check."""

    passed: bool
    message: str
    severity: ValidationSeverity = ValidationSeverity.ERROR
    path: str = ""
    expected: Any = None
    actual: Any = None


@dataclass
class ContractViolation:
    """Represents a contract violation."""

    rule: str
    message: str
    path: str
    severity: ValidationSeverity
    expected: Any = None
    actual: Any = None


@dataclass
class EndpointContract:
    """Contract definition for an API endpoint."""

    path: str
    method: str
    operation_id: str | None = None
    summary: str | None = None
    parameters: list[dict[str, Any]] = field(default_factory=list)
    request_body: dict[str, Any] | None = None
    responses: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    deprecated: bool = False


class ISchemaValidator(ABC):
    """Interface for schema validators."""

    @abstractmethod
    def validate(self, data: Any, schema: dict[str, Any]) -> ValidationResult:
        """Validate data against schema."""


class JSONSchemaValidator(ISchemaValidator):
    """
    JSON Schema validator for OpenAPI schemas.
    """

    def validate(self, data: Any, schema: dict[str, Any]) -> ValidationResult:
        """Validate data against JSON schema."""
        try:
            from jsonschema import ValidationError, validate

            validate(instance=data, schema=schema)
            return ValidationResult(
                passed=True, message="Validation passed", severity=ValidationSeverity.INFO
            )
        except ImportError:
            # Fallback to basic validation
            return self._basic_validation(data, schema)
        except ValidationError as e:
            return ValidationResult(
                passed=False,
                message=str(e.message),
                severity=ValidationSeverity.ERROR,
                path=str(e.path),
                expected=e.validator_value,
                actual=e.instance,
            )

    def _basic_validation(self, data: Any, schema: dict[str, Any]) -> ValidationResult:
        """Basic validation without jsonschema library."""
        schema_type = schema.get("type")

        if schema_type == "object" and not isinstance(data, dict):
            return ValidationResult(
                passed=False,
                message=f"Expected object, got {type(data).__name__}",
                severity=ValidationSeverity.ERROR,
            )

        if schema_type == "array" and not isinstance(data, list):
            return ValidationResult(
                passed=False,
                message=f"Expected array, got {type(data).__name__}",
                severity=ValidationSeverity.ERROR,
            )

        if schema_type == "string" and not isinstance(data, str):
            return ValidationResult(
                passed=False,
                message=f"Expected string, got {type(data).__name__}",
                severity=ValidationSeverity.ERROR,
            )

        return ValidationResult(
            passed=True, message="Basic validation passed", severity=ValidationSeverity.INFO
        )


class OpenAPIParser:
    """
    Parser for OpenAPI 3.0 specifications.
    Extracts contract information from OpenAPI specs.
    """

    def __init__(self, spec_path: str | Path):
        self.spec_path = Path(spec_path)
        self._spec: dict[str, Any] | None = None
        self._endpoints: list[EndpointContract] = []

    def parse(self) -> dict[str, Any]:
        """Parse OpenAPI specification file."""
        if self._spec is not None:
            return self._spec

        with open(self.spec_path, "r") as f:
            content = f.read()

        # Determine format from extension or content
        if self.spec_path.suffix in [".yaml", ".yml"]:
            self._spec = yaml.safe_load(content)
        else:
            self._spec = json.loads(content)

        return self._spec

    def get_endpoints(self) -> list[EndpointContract]:
        """Extract all endpoint contracts from spec."""
        if self._endpoints:
            return self._endpoints

        spec = self.parse()
        paths = spec.get("paths", {})

        for path, path_item in paths.items():
            for method in ["get", "post", "put", "patch", "delete", "head", "options"]:
                if method in path_item:
                    operation = path_item[method]
                    contract = EndpointContract(
                        path=path,
                        method=method.upper(),
                        operation_id=operation.get("operationId"),
                        summary=operation.get("summary"),
                        parameters=operation.get("parameters", []),
                        request_body=operation.get("requestBody"),
                        responses=operation.get("responses", {}),
                        tags=operation.get("tags", []),
                        deprecated=operation.get("deprecated", False),
                    )
                    self._endpoints.append(contract)

        return self._endpoints

    def get_endpoint(self, path: str, method: str) -> EndpointContract | None:
        """Get contract for specific endpoint."""
        endpoints = self.get_endpoints()
        for endpoint in endpoints:
            if endpoint.path == path and endpoint.method == method.upper():
                return endpoint
        return None

    def get_schemas(self) -> dict[str, Any]:
        """Get all schemas defined in components."""
        spec = self.parse()
        components = spec.get("components", {})
        if isinstance(components, dict):
            schemas = components.get("schemas", {})
            return schemas if isinstance(schemas, dict) else {}
        return {}

    def get_schema(self, schema_name: str) -> dict[str, Any] | None:
        """Get specific schema by name."""
        schemas = self.get_schemas()
        return schemas.get(schema_name)

    def resolve_schema(self, schema_ref: str) -> dict[str, Any] | None:
        """Resolve schema reference (e.g., #/components/schemas/User)."""
        if not schema_ref.startswith("#/"):
            return None

        parts = schema_ref[2:].split("/")
        spec = self.parse()

        current = spec
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None

        return current


class ContractValidator:
    """
    Validates API responses against OpenAPI contracts.
    """

    def __init__(self, spec_path: str | Path):
        self.parser = OpenAPIParser(spec_path)
        self.schema_validator = JSONSchemaValidator()
        self.violations: list[ContractViolation] = []

    def validate_response(
        self,
        endpoint_path: str,
        method: str,
        status_code: int,
        response_body: Any,
        headers: dict[str, str] | None = None,
    ) -> list[ContractViolation]:
        """
        Validate an API response against the contract.

        Args:
            endpoint_path: API endpoint path (e.g., "/users/{id}")
            method: HTTP method (GET, POST, etc.)
            status_code: HTTP status code
            response_body: Response body data
            headers: Response headers

        Returns:
            List of contract violations (empty if valid)
        """
        self.violations = []

        # Get endpoint contract
        contract = self.parser.get_endpoint(endpoint_path, method)
        if not contract:
            self.violations.append(
                ContractViolation(
                    rule="endpoint_exists",
                    message=f"Endpoint {method} {endpoint_path} not found in contract",
                    path=f"{method} {endpoint_path}",
                    severity=ValidationSeverity.ERROR,
                )
            )
            return self.violations

        # Validate status code
        self._validate_status_code(contract, status_code)

        # Validate response body schema
        if response_body is not None:
            self._validate_response_body(contract, status_code, response_body)

        # Validate headers if provided
        if headers:
            self._validate_headers(contract, status_code, headers)

        return self.violations

    def _validate_status_code(self, contract: EndpointContract, status_code: int) -> None:
        """Validate that status code is defined in contract."""
        status_str = str(status_code)

        # Check exact match
        if status_str in contract.responses:
            return

        # Check default
        if "default" in contract.responses:
            return

        # Check wildcards (e.g., 2XX, 4XX)
        status_prefix = status_str[0] + "XX"
        if status_prefix in contract.responses:
            return

        # Not found - violation
        allowed_codes = list(contract.responses.keys())
        self.violations.append(
            ContractViolation(
                rule="status_code",
                message=f"Status code {status_code} not defined in contract",
                path=f"{contract.method} {contract.path}",
                severity=ValidationSeverity.ERROR,
                expected=allowed_codes,
                actual=status_code,
            )
        )

    def _validate_response_body(
        self, contract: EndpointContract, status_code: int, response_body: Any
    ) -> None:
        """Validate response body against schema."""
        status_str = str(status_code)
        response_spec = contract.responses.get(status_str)

        if not response_spec:
            # Try wildcard
            status_prefix = status_str[0] + "XX"
            response_spec = contract.responses.get(status_prefix)

        if not response_spec:
            response_spec = contract.responses.get("default", {})

        content = response_spec.get("content", {})

        # Check if response should have body
        if not content and response_body:
            self.violations.append(
                ContractViolation(
                    rule="unexpected_body",
                    message=f"Response should not have a body for status {status_code}",
                    path=f"{contract.method} {contract.path}",
                    severity=ValidationSeverity.WARNING,
                )
            )
            return

        # Validate against schema
        json_content = content.get("application/json", {})
        schema = json_content.get("schema", {})

        if schema:
            # Resolve schema reference if needed
            if "$ref" in schema:
                schema = self.parser.resolve_schema(schema["$ref"]) or schema

            result = self.schema_validator.validate(response_body, schema)

            if not result.passed:
                self.violations.append(
                    ContractViolation(
                        rule="schema_validation",
                        message=result.message,
                        path=f"{contract.method} {contract.path}",
                        severity=result.severity,
                        expected=result.expected,
                        actual=result.actual,
                    )
                )

    def _validate_headers(
        self, contract: EndpointContract, status_code: int, headers: dict[str, str]
    ) -> None:
        """Validate response headers."""
        status_str = str(status_code)
        response_spec = contract.responses.get(status_str, {})

        if not response_spec:
            status_prefix = status_str[0] + "XX"
            response_spec = contract.responses.get(status_prefix, {})

        expected_headers = response_spec.get("headers", {})

        # Check required headers
        for header_name, header_spec in expected_headers.items():
            if header_spec.get("required", False):
                if header_name.lower() not in [h.lower() for h in headers]:
                    self.violations.append(
                        ContractViolation(
                            rule="required_header",
                            message=f"Required header '{header_name}' missing",
                            path=f"{contract.method} {contract.path}",
                            severity=ValidationSeverity.ERROR,
                            expected=header_name,
                        )
                    )

    def validate_request(
        self,
        endpoint_path: str,
        method: str,
        request_body: Any | None = None,
        query_params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> list[ContractViolation]:
        """Validate an API request against the contract."""
        self.violations = []

        contract = self.parser.get_endpoint(endpoint_path, method)
        if not contract:
            self.violations.append(
                ContractViolation(
                    rule="endpoint_exists",
                    message=f"Endpoint {method} {endpoint_path} not found in contract",
                    path=f"{method} {endpoint_path}",
                    severity=ValidationSeverity.ERROR,
                )
            )
            return self.violations

        # Validate request body
        if request_body and contract.request_body:
            self._validate_request_body(contract, request_body)

        # Validate query parameters
        if query_params:
            self._validate_query_params(contract, query_params)

        return self.violations

    def _validate_request_body(self, contract: EndpointContract, request_body: Any) -> None:
        """Validate request body against schema."""
        if not contract.request_body:
            return

        content = contract.request_body.get("content", {})
        json_content = content.get("application/json", {})
        schema = json_content.get("schema", {})

        if schema:
            if "$ref" in schema:
                schema = self.parser.resolve_schema(schema["$ref"]) or schema

            result = self.schema_validator.validate(request_body, schema)

            if not result.passed:
                self.violations.append(
                    ContractViolation(
                        rule="request_body_validation",
                        message=result.message,
                        path=f"{contract.method} {contract.path}",
                        severity=result.severity,
                        expected=result.expected,
                        actual=result.actual,
                    )
                )

    def _validate_query_params(
        self, contract: EndpointContract, query_params: dict[str, Any]
    ) -> None:
        """Validate query parameters."""
        param_specs = {p["name"]: p for p in contract.parameters if p.get("in") == "query"}

        # Check required params
        for name, spec in param_specs.items():
            if spec.get("required", False) and name not in query_params:
                self.violations.append(
                    ContractViolation(
                        rule="required_parameter",
                        message=f"Required query parameter '{name}' missing",
                        path=f"{contract.method} {contract.path}",
                        severity=ValidationSeverity.ERROR,
                        expected=name,
                    )
                )

        # Check for unknown params
        for param_name in query_params:
            if param_name not in param_specs:
                self.violations.append(
                    ContractViolation(
                        rule="unknown_parameter",
                        message=f"Unknown query parameter '{param_name}'",
                        path=f"{contract.method} {contract.path}",
                        severity=ValidationSeverity.WARNING,
                        actual=param_name,
                    )
                )


class ContractCoverageChecker:
    """
    Checks API test coverage against OpenAPI contract.
    """

    def __init__(self, spec_path: str | Path):
        self.parser = OpenAPIParser(spec_path)
        self.tested_endpoints: set[tuple[str, str]] = set()

    def mark_tested(self, path: str, method: str) -> None:
        """Mark an endpoint as tested."""
        self.tested_endpoints.add((path, method.upper()))

    def get_coverage(self) -> dict[str, Any]:
        """
        Get contract coverage report.

        Returns:
            Dictionary with coverage statistics
        """
        all_endpoints = self.parser.get_endpoints()
        all_contracts = {(e.path, e.method) for e in all_endpoints}

        tested = self.tested_endpoints
        untested = all_contracts - tested

        coverage_percentage = (len(tested) / len(all_contracts) * 100) if all_contracts else 0

        return {
            "total_endpoints": len(all_contracts),
            "tested_endpoints": len(tested),
            "untested_endpoints": len(untested),
            "coverage_percentage": round(coverage_percentage, 2),
            "tested": sorted(list(tested)),
            "untested": sorted(list(untested)),
        }

    def generate_report(self, output_path: str | None = None) -> str:
        """Generate coverage report in markdown format."""
        coverage = self.get_coverage()

        report = f"""# API Contract Coverage Report

## Summary

- **Total Endpoints**: {coverage['total_endpoints']}
- **Tested Endpoints**: {coverage['tested_endpoints']}
- **Untested Endpoints**: {coverage['untested_endpoints']}
- **Coverage**: {coverage['coverage_percentage']}%

## Tested Endpoints

"""

        for path, method in coverage["tested"]:
            report += f"- ✅ `{method}` {path}\n"

        report += "\n## Untested Endpoints\n\n"

        for path, method in coverage["untested"]:
            report += f"- ❌ `{method}` {path}\n"

        if output_path:
            with open(output_path, "w") as f:
                f.write(report)

        return report


class ContractTestDecorator:
    """
    Decorator for marking tests with contract information.

    Usage:
        @contract_test("/users", "GET")
        def test_get_users():
            pass
    """

    def __init__(self, path: str, method: str, spec_path: str | None = None) -> None:
        self.path = path
        self.method = method
        self.spec_path = spec_path

    def __call__(self, func: Any) -> Any:
        """Apply decorator to test function."""
        func._contract_path = self.path
        func._contract_method = self.method
        func._spec_path = self.spec_path
        return func


def contract_test(path: str, method: str, spec_path: str | None = None) -> ContractTestDecorator:
    """Factory function for contract test decorator."""
    return ContractTestDecorator(path, method, spec_path)


# Convenience functions


def validate_api_response(
    spec_path: str | Path,
    endpoint_path: str,
    method: str,
    status_code: int,
    response_body: Any,
    headers: dict[str, str] | None = None,
) -> list[ContractViolation]:
    """Convenience function to validate an API response."""
    validator = ContractValidator(spec_path)
    return validator.validate_response(endpoint_path, method, status_code, response_body, headers)


def check_contract_coverage(
    spec_path: str | Path, tested_endpoints: list[tuple[str, str]]
) -> dict[str, Any]:
    """Check coverage of tested endpoints against contract."""
    checker = ContractCoverageChecker(spec_path)
    for path, method in tested_endpoints:
        checker.mark_tested(path, method)
    return checker.get_coverage()
