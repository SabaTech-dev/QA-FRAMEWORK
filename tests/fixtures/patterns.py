"""
Advanced Test Patterns for QA Framework.

Implements sophisticated testing patterns:
- AAA Pattern (Arrange-Act-Assert)
- Given-When-Then (BDD style)
- Table-Driven Tests
- Parametrized Test Builders
- Test Isolation Patterns
"""

import functools
import time
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, TypeVar
from unittest.mock import MagicMock

import pytest

T = TypeVar("T")
R = TypeVar("R")


@dataclass
class TestStep:
    """Represents a single step in a test scenario."""

    name: str
    action: Callable[..., Any]
    description: str = ""
    expected_result: Any | None = None


@dataclass
class TestScenario:
    """Represents a complete test scenario with multiple steps."""

    name: str
    description: str
    steps: list[TestStep] = field(default_factory=list)
    setup: Callable[..., Any] | None = None
    teardown: Callable[..., Any] | None = None
    tags: list[str] = field(default_factory=list)


class AAAPattern:
    """
    Arrange-Act-Assert pattern implementation.
    Provides structured way to organize tests.
    """

    def __init__(self, test_name: str = ""):
        self.test_name = test_name
        self._arranged_data: dict[str, Any] = {}
        self._action_result: Any = None
        self._assertions: list[dict[str, Any]] = []

    def arrange(self, **kwargs: Any) -> "AAAPattern":
        """
        Arrange phase - Set up test preconditions and inputs.
        """
        self._arranged_data.update(kwargs)
        return self

    def act(self, action: Callable[..., R], *args: Any, **kwargs: Any) -> "AAAPattern":
        """
        Act phase - Execute the action being tested.
        """
        self._action_result = action(*args, **kwargs)
        return self

    def assert_that(self, condition: bool, message: str = "") -> "AAAPattern":
        """
        Assert phase - Verify expected outcomes.
        """
        self._assertions.append({"condition": condition, "message": message, "passed": condition})

        if not condition:
            raise AssertionError(message or "Assertion failed")

        return self

    def assert_equals(self, expected: Any, actual: Any, message: str = "") -> "AAAPattern":
        """Assert that expected equals actual."""
        msg = message or f"Expected {expected} but got {actual}"
        return self.assert_that(expected == actual, msg)

    def assert_not_none(self, value: Any, message: str = "") -> "AAAPattern":
        """Assert that value is not None."""
        msg = message or "Expected value to not be None"
        return self.assert_that(value is not None, msg)

    def assert_raises(
        self, exception_type: type, callable_obj: Callable, *args: Any, **kwargs: Any
    ) -> "AAAPattern":
        """Assert that callable raises specific exception."""
        try:
            callable_obj(*args, **kwargs)
            raise AssertionError(f"Expected {exception_type.__name__} to be raised")
        except exception_type:
            return self

    def get_result(self) -> Any:
        """Get the result from act phase."""
        return self._action_result

    def get_arranged(self, key: str) -> Any:
        """Get arranged data by key."""
        return self._arranged_data.get(key)


class GivenWhenThen:
    """
    BDD-style Given-When-Then pattern.
    Makes tests more readable and business-focused.
    """

    def __init__(self, scenario_name: str = ""):
        self.scenario_name = scenario_name
        self._context: dict[str, Any] = {}
        self._given_statements: list[str] = []
        self._when_statements: list[str] = []
        self._then_statements: list[str] = []

    def given(self, description: str, **context: Any) -> "GivenWhenThen":
        """
        Given phase - Set up preconditions.
        """
        self._given_statements.append(description)
        self._context.update(context)
        return self

    def when(
        self,
        description: str,
        action: Callable[..., Any] | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> "GivenWhenThen":
        """
        When phase - Execute action.
        """
        self._when_statements.append(description)

        if action:
            result = action(*args, **kwargs)
            self._context["result"] = result

        return self

    def then(
        self,
        description: str,
        assertion: Callable[..., bool] | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> "GivenWhenThen":
        """
        Then phase - Verify outcomes.
        """
        self._then_statements.append(description)

        if assertion:
            if not assertion(*args, **kwargs):
                raise AssertionError(f"Then failed: {description}")

        return self

    def and_(self, description: str) -> "GivenWhenThen":
        """Additional step (and)."""
        return self.then(description)

    def get_context(self) -> dict[str, Any]:
        """Get the test context."""
        return self._context.copy()

    def get_scenario_description(self) -> str:
        """Get full scenario description."""
        lines = [f"Scenario: {self.scenario_name}"]

        for stmt in self._given_statements:
            lines.append(f"  Given {stmt}")

        for stmt in self._when_statements:
            lines.append(f"  When {stmt}")

        for stmt in self._then_statements:
            lines.append(f"  Then {stmt}")

        return "\n".join(lines)


@dataclass
class TestCase:
    """Represents a single test case for table-driven testing."""

    name: str
    input_data: Any
    expected: Any
    description: str = ""
    should_raise: type | None = None
    tags: list[str] = field(default_factory=list)


class TableDrivenTests:
    """
    Table-Driven Test pattern.
    Allows defining multiple test cases in a table format.
    """

    def __init__(self):
        self._test_cases: list[TestCase] = []

    def add_case(
        self,
        name: str,
        input_data: Any,
        expected: Any,
        description: str = "",
        should_raise: type | None = None,
        tags: list[str] | None = None,
    ) -> "TableDrivenTests":
        """Add a test case."""
        self._test_cases.append(
            TestCase(
                name=name,
                input_data=input_data,
                expected=expected,
                description=description,
                should_raise=should_raise,
                tags=tags or [],
            )
        )
        return self

    def run(self, test_function: Callable[[Any], Any]) -> list[dict[str, Any]]:
        """
        Run all test cases against the test function.
        Returns results for each case.
        """
        results = []

        for case in self._test_cases:
            result = {"name": case.name, "passed": False, "error": None, "duration": 0.0}

            start_time = time.time()

            try:
                if case.should_raise:
                    try:
                        test_function(case.input_data)
                        result["error"] = f"Expected {case.should_raise.__name__} to be raised"
                    except case.should_raise:
                        result["passed"] = True
                else:
                    actual = test_function(case.input_data)
                    if actual == case.expected:
                        result["passed"] = True
                    else:
                        result["error"] = f"Expected {case.expected} but got {actual}"
            except Exception as e:
                result["error"] = str(e)

            result["duration"] = time.time() - start_time
            results.append(result)

        return results

    def to_pytest_params(self) -> list[tuple]:
        """Convert test cases to pytest parametrize format."""
        return [
            pytest.param(
                case.input_data,
                case.expected,
                case.should_raise,
                id=case.name,
                marks=[getattr(pytest.mark, tag) for tag in case.tags if hasattr(pytest.mark, tag)],
            )
            for case in self._test_cases
        ]


class TestDataTable:
    """
    Data Table pattern for organizing test inputs.
    Similar to Cucumber data tables.
    """

    def __init__(self, headers: list[str] | None = None):
        self.headers = headers or []
        self.rows: list[dict[str, Any]] = []

    def add_row(self, **values: Any) -> "TestDataTable":
        """Add a row to the table."""
        if not self.headers:
            self.headers = list(values.keys())

        row = {k: values.get(k) for k in self.headers}
        self.rows.append(row)
        return self

    def add_rows(self, *rows: dict[str, Any]) -> "TestDataTable":
        """Add multiple rows."""
        for row in rows:
            self.add_row(**row)
        return self

    def get_row(self, index: int) -> dict[str, Any]:
        """Get row by index."""
        return self.rows[index]

    def get_column(self, header: str) -> list[Any]:
        """Get all values for a column."""
        return [row.get(header) for row in self.rows]

    def filter(self, **conditions: Any) -> list[dict[str, Any]]:
        """Filter rows by conditions."""
        return [row for row in self.rows if all(row.get(k) == v for k, v in conditions.items())]

    def to_list(self) -> list[dict[str, Any]]:
        """Convert table to list of dictionaries."""
        return self.rows.copy()


class TestIsolationManager:
    """
    Manages test isolation and cleanup.
    Ensures tests don't interfere with each other.
    """

    def __init__(self):
        self._setup_hooks: list[Callable[..., Any]] = []
        self._teardown_hooks: list[Callable[..., Any]] = []
        self._resources: list[Any] = []

    def on_setup(self, hook: Callable[..., Any]) -> "TestIsolationManager":
        """Register setup hook."""
        self._setup_hooks.append(hook)
        return self

    def on_teardown(self, hook: Callable[..., Any]) -> "TestIsolationManager":
        """Register teardown hook."""
        self._teardown_hooks.append(hook)
        return self

    def setup(self) -> None:
        """Run all setup hooks."""
        for hook in self._setup_hooks:
            hook()

    def teardown(self) -> None:
        """Run all teardown hooks."""
        for hook in reversed(self._teardown_hooks):
            try:
                hook()
            except Exception:
                pass  # Ensure all cleanup runs

    @contextmanager
    def isolated_context(self):
        """Context manager for isolated test execution."""
        try:
            self.setup()
            yield self
        finally:
            self.teardown()


class RetryPattern:
    """
    Retry pattern for flaky tests.
    Implements exponential backoff and configurable retry logic.
    """

    def __init__(
        self,
        max_retries: int = 3,
        delay: float = 1.0,
        backoff: float = 2.0,
        exceptions: tuple = (Exception,),
    ):
        self.max_retries = max_retries
        self.delay = delay
        self.backoff = backoff
        self.exceptions = exceptions

    def execute(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """
        Execute function with retry logic.
        """
        current_delay = self.delay
        last_exception: Exception | None = None

        for attempt in range(self.max_retries + 1):
            try:
                return func(*args, **kwargs)
            except self.exceptions as e:
                last_exception = e

                if attempt < self.max_retries:
                    time.sleep(current_delay)
                    current_delay *= self.backoff

        raise last_exception or Exception("Max retries exceeded")

    def decorator(self, func: Callable[..., T]) -> Callable[..., T]:
        """Decorator for adding retry logic to functions."""

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            return self.execute(func, *args, **kwargs)

        return wrapper


class TestDoubleFactory:
    """
    Factory for creating test doubles (mocks, stubs, fakes, spies).
    """

    @staticmethod
    def mock(**methods: Any) -> MagicMock:
        """Create a mock object with specified methods."""
        mock_obj = MagicMock()
        for name, return_value in methods.items():
            setattr(mock_obj, name, MagicMock(return_value=return_value))
        return mock_obj

    @staticmethod
    def stub(return_value: Any) -> Callable[..., Any]:
        """Create a stub function."""
        return lambda *args, **kwargs: return_value

    @staticmethod
    def spy(func: Callable[..., T]) -> tuple:
        """Create a spy that wraps a function."""
        calls: list[tuple] = []

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            calls.append((args, kwargs))
            return func(*args, **kwargs)

        return wrapper, calls


class ParameterizedTestBuilder:
    """
    Builder for creating parameterized tests.
    Simplifies creating multiple test variations.
    """

    def __init__(self):
        self._parameters: list[tuple] = []
        self._ids: list[str] = []
        self._marks: list[list[Any]] = []

    def add_case(
        self, *args: Any, id: str | None = None, marks: list[Any] | None = None
    ) -> "ParameterizedTestBuilder":
        """Add a test case."""
        self._parameters.append(args)
        self._ids.append(id or f"case_{len(self._parameters)}")
        self._marks.append(marks or [])
        return self

    def build(self) -> tuple:
        """Build pytest.mark.parametrize arguments."""
        param_list = []
        for params, id_val, marks in zip(self._parameters, self._ids, self._marks):
            param = pytest.param(*params, id=id_val)
            for mark in marks:
                param = param.pytestmark + [mark]
            param_list.append(param)

        return param_list


class TestSuiteBuilder:
    """
    Builder for creating test suites dynamically.
    """

    def __init__(self, name: str = ""):
        self.name = name
        self._tests: list[Callable[..., Any]] = []
        self._setup: Callable[..., Any] | None = None
        self._teardown: Callable[..., Any] | None = None

    def add_test(self, test_func: Callable[..., Any]) -> "TestSuiteBuilder":
        """Add a test to the suite."""
        self._tests.append(test_func)
        return self

    def set_setup(self, setup_func: Callable[..., Any]) -> "TestSuiteBuilder":
        """Set setup function for the suite."""
        self._setup = setup_func
        return self

    def set_teardown(self, teardown_func: Callable[..., Any]) -> "TestSuiteBuilder":
        """Set teardown function for the suite."""
        self._teardown = teardown_func
        return self

    def run(self) -> dict[str, Any]:
        """Run all tests in the suite."""
        results = {
            "suite_name": self.name,
            "total": len(self._tests),
            "passed": 0,
            "failed": 0,
            "errors": [],
            "duration": 0.0,
        }

        start_time = time.time()

        try:
            if self._setup:
                self._setup()

            for test in self._tests:
                try:
                    test()
                    results["passed"] += 1
                except AssertionError as e:
                    results["failed"] += 1
                    results["errors"].append(str(e))
                except Exception as e:
                    results["failed"] += 1
                    results["errors"].append(f"Unexpected error: {e}")
        finally:
            if self._teardown:
                try:
                    self._teardown()
                except Exception as e:
                    results["errors"].append(f"Teardown error: {e}")

        results["duration"] = time.time() - start_time
        return results


def using_aaa(test_name: str = "") -> AAAPattern:
    """Factory function for AAA pattern."""
    return AAAPattern(test_name)


def using_bdd(scenario_name: str = "") -> GivenWhenThen:
    """Factory function for BDD pattern."""
    return GivenWhenThen(scenario_name)


def create_test_table(headers: list[str] | None = None) -> TestDataTable:
    """Factory function for test data table."""
    return TestDataTable(headers)


def create_isolation_manager() -> TestIsolationManager:
    """Factory function for isolation manager."""
    return TestIsolationManager()


def with_retry(max_retries: int = 3, delay: float = 1.0) -> RetryPattern:
    """Factory function for retry pattern."""
    return RetryPattern(max_retries=max_retries, delay=delay)
