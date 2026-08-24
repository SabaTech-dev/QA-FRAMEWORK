"""
Contract Testing Fixtures for Pytest.

Provides fixtures for API contract testing:
- OpenAPI spec loading
- Contract validator instances
- Coverage tracking
- Auto-validation hooks
"""

from collections.abc import Generator
from typing import Any

import pytest

from src.adapters.api_contract.contract_validator import (
    ContractCoverageChecker,
    ContractValidator,
    OpenAPIParser,
)


@pytest.fixture(scope="session")
def openapi_spec_path() -> str:
    """Path to OpenAPI specification file."""
    return "openapi.yaml"


@pytest.fixture(scope="session")
def openapi_parser(openapi_spec_path: str) -> OpenAPIParser:
    """OpenAPI parser instance."""
    return OpenAPIParser(openapi_spec_path)


@pytest.fixture(scope="session")
def contract_validator(openapi_spec_path: str) -> ContractValidator:
    """Contract validator instance."""
    return ContractValidator(openapi_spec_path)


@pytest.fixture(scope="session")
def coverage_checker(openapi_spec_path: str) -> ContractCoverageChecker:
    """Contract coverage checker instance."""
    return ContractCoverageChecker(openapi_spec_path)


@pytest.fixture(scope="function")
def contract_validation_context() -> Generator[dict[str, Any], None, None]:
    """Context for contract validation within a test."""
    context = {
        "validated_responses": [],
        "violations": [],
    }
    yield context


# Custom markers
def pytest_configure(config: pytest.Config) -> None:
    """Configure contract testing markers."""
    config.addinivalue_line("markers", "contract(path, method): mark test with contract endpoint")
    config.addinivalue_line("markers", "contract_test: mark test as contract test")
    config.addinivalue_line("markers", "validate_response: auto-validate API responses")


def pytest_runtest_setup(item: pytest.Item) -> None:
    """Setup for contract tests."""
    contract_marker = item.get_closest_marker("contract")
    if contract_marker:
        # Store contract info on test item
        item._contract_path = contract_marker.kwargs.get("path")
        item._contract_method = contract_marker.kwargs.get("method")


def pytest_runtest_teardown(item: pytest.Item) -> None:
    """Teardown for contract tests - track coverage."""
    if hasattr(item, "_contract_path") and hasattr(item, "_contract_method"):
        # Coverage tracking would happen here
        pass
