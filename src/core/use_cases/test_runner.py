"""Test Runner Use Case - Execute tests with error handling"""

import time
import traceback
from collections.abc import Callable
from typing import Any

from src.core.entities.test_result import TestResult, TestStatus
from src.core.interfaces import ITestRunner


class TestRunner(ITestRunner):
    """
    Test runner implementation.

    This class follows Single Responsibility Principle (SRP) by only
    handling test execution and error handling.
    """

    def __init__(self, max_retries: int = 0):
        """
        Initialize test runner.

        Args:
            max_retries: Maximum number of retries for failed tests
        """
        self.max_retries = max_retries
        self._results: list[TestResult] = []

    async def run_test(
        self, test_func: Callable[..., Any], *args: Any, **kwargs: Any
    ) -> TestResult:
        """
        Run a test function with error handling and retry logic.

        Args:
            test_func: Test function to execute
            *args: Positional arguments for test function
            **kwargs: Keyword arguments for test function

        Returns:
            TestResult object with execution details
        """
        test_name = test_func.__name__
        start_time = time.time()

        for attempt in range(self.max_retries + 1):
            try:
                # Execute test function
                if hasattr(test_func, "__call__"):
                    result = test_func(*args, **kwargs)
                    if result and hasattr(result, "__await__"):
                        result = await result

                execution_time = time.time() - start_time

                # Test passed
                test_result = TestResult(
                    test_name=test_name, status=TestStatus.PASSED, execution_time=execution_time
                )

                self._results.append(test_result)
                return test_result

            except AssertionError as e:
                # Test failed
                execution_time = time.time() - start_time
                error_msg = f"Assertion failed: {e!s}"

                test_result = TestResult(
                    test_name=test_name,
                    status=TestStatus.FAILED,
                    execution_time=execution_time,
                    error_message=error_msg,
                )

                self._results.append(test_result)
                return test_result

            except Exception as e:
                # Test error
                execution_time = time.time() - start_time
                error_msg = f"Error: {e!s}\n{traceback.format_exc()}"

                test_result = TestResult(
                    test_name=test_name,
                    status=TestStatus.ERROR,
                    execution_time=execution_time,
                    error_message=error_msg,
                )

                self._results.append(test_result)
                return test_result

        # This should never be reached, but satisfies mypy
        # The loop always executes at least once (max_retries + 1 >= 1)
        raise RuntimeError("Test execution failed to return a result")

    async def cleanup(self) -> None:
        """Cleanup resources after test execution"""
        self._results.clear()

    def get_results(self) -> list[TestResult]:
        """Get all test results"""
        return self._results.copy()
