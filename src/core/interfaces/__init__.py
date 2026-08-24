"""Interfaces - Contracts for core components (SOLID DIP)"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from src.core.entities.test_result import TestResult


class ITestRunner(ABC):
    """Interface for test runner (Dependency Inversion Principle)"""

    @abstractmethod
    async def run_test(self, test_func: Any, *args: Any, **kwargs: Any) -> TestResult:
        """
        Run a test function.

        Args:
            test_func: Test function to execute
            *args: Positional arguments for test function
            **kwargs: Keyword arguments for test function

        Returns:
            TestResult object with execution details
        """

    @abstractmethod
    async def cleanup(self) -> None:
        """Cleanup resources after test execution"""


class IHTTPClient(ABC):
    """Interface for HTTP client adapters"""

    @abstractmethod
    async def get(self, url: str, **kwargs: Any) -> Any:
        """Perform GET request"""

    @abstractmethod
    async def post(self, url: str, data: dict[str, Any] | None = None, **kwargs: Any) -> Any:
        """Perform POST request"""

    @abstractmethod
    async def put(self, url: str, data: dict[str, Any] | None = None, **kwargs: Any) -> Any:
        """Perform PUT request"""

    @abstractmethod
    async def delete(self, url: str, **kwargs: Any) -> Any:
        """Perform DELETE request"""


class IUIPage(ABC):
    """
    Interface for UI page objects (Single Responsibility Principle).

    This interface defines the contract for all UI page adapters,
    following the Interface Segregation Principle (ISP) from SOLID.
    """

    @abstractmethod
    async def goto(self, url: str) -> None:
        """
        Navigate to a URL.

        Args:
            url: URL to navigate to
        """

    @abstractmethod
    async def click(self, selector: str) -> None:
        """
        Click on an element.

        Args:
            selector: CSS selector for the element
        """

    @abstractmethod
    async def fill(self, selector: str, value: str) -> None:
        """
        Fill an input field with a value.

        Args:
            selector: CSS selector for the input
            value: Value to fill
        """

    @abstractmethod
    async def wait_for_selector(self, selector: str, timeout: int = 30000) -> None:
        """
        Wait for an element to appear.

        Args:
            selector: CSS selector for the element
            timeout: Timeout in milliseconds (default: 30000)
        """

    @abstractmethod
    async def get_text(self, selector: str) -> str:
        """
        Get text content of an element.

        Args:
            selector: CSS selector for the element

        Returns:
            Text content of the element
        """

    @abstractmethod
    async def is_visible(self, selector: str) -> bool:
        """
        Check if an element is visible.

        Args:
            selector: CSS selector for the element

        Returns:
            True if visible, False otherwise
        """

    @abstractmethod
    async def screenshot(self, path: str) -> None:
        """
        Take a screenshot of the current page.

        Args:
            path: Path to save the screenshot
        """

    @abstractmethod
    async def close(self) -> None:
        """Close the browser/page."""


class IAssertion(ABC):
    """Interface for assertions (Interface Segregation Principle)"""

    @abstractmethod
    def assert_equal(self, actual: Any, expected: Any, message: str | None = None) -> None:
        """Assert two values are equal"""

    @abstractmethod
    def assert_true(self, condition: bool, message: str | None = None) -> None:
        """Assert condition is true"""

    @abstractmethod
    def assert_status_code(self, response: Any, expected: int) -> None:
        """Assert HTTP status code"""


class IReporter(ABC):
    """
    Interface for test reporters (Interface Segregation Principle).

    This interface defines the contract for all reporting adapters,
    following Dependency Inversion Principle (DIP) from SOLID.
    Supports multiple output formats: HTML, JSON, XML.
    """

    @abstractmethod
    def start_test(self, test_name: str, description: str | None = None) -> None:
        """
        Start reporting for a test case.

        Args:
            test_name: Name of the test case
            description: Optional test description
        """

    @abstractmethod
    def end_test(self, status: str, message: str | None = None) -> None:
        """
        End reporting for current test case.

        Args:
            status: Test status (passed, failed, skipped, broken)
            message: Optional status message or error details
        """

    @abstractmethod
    def add_step(self, step_name: str, status: str | None = None) -> None:
        """
        Add a step to the current test.

        Args:
            step_name: Name of the step
            status: Optional step status
        """

    @abstractmethod
    def attach_screenshot(self, screenshot_path: str, name: str | None = None) -> None:
        """
        Attach a screenshot to the current test report.

        Args:
            screenshot_path: Path to the screenshot file
            name: Optional name for the attachment
        """

    @abstractmethod
    def attach_text(self, content: str, name: str) -> None:
        """
        Attach text content to the current test report.

        Args:
            content: Text content to attach
            name: Name of the attachment
        """

    @abstractmethod
    def attach_json(self, data: dict[str, Any], name: str) -> None:
        """
        Attach JSON data to the current test report.

        Args:
            data: Dictionary to serialize as JSON
            name: Name of the attachment
        """

    @abstractmethod
    def add_tag(self, tag: str) -> None:
        """
        Add a tag/label to the current test.

        Args:
            tag: Tag to add
        """

    @abstractmethod
    def add_severity(self, level: str) -> None:
        """
        Set severity level for the current test.

        Args:
            level: Severity level (blocker, critical, normal, minor, trivial)
        """

    @abstractmethod
    def generate_report(self, output_dir: str, report_format: str = "html") -> str:
        """
        Generate the final report in specified format.

        Args:
            output_dir: Directory to save the report
            report_format: Report format (html, json, xml)

        Returns:
            Path to the generated report
        """

    @abstractmethod
    def cleanup(self) -> None:
        """Cleanup resources and close reporter"""


class IPerformanceClient(ABC):
    """
    Interface for performance/load testing clients (Interface Segregation Principle).

    This interface defines the contract for all performance testing adapters,
    supporting load testing tools like locust, k6, and Apache Bench.
    """

    @abstractmethod
    async def load_test(
        self, target_url: str, users: int, duration: int, ramp_up: int = 0
    ) -> dict[str, Any]:
        """
        Execute a load test against a target URL.

        Args:
            target_url: URL to test
            users: Number of concurrent users
            duration: Test duration in seconds
            ramp_up: Ramp-up time in seconds (default: 0)

        Returns:
            Dictionary with load test results including metrics
        """

    @abstractmethod
    async def benchmark(self, target_url: str, requests: int) -> dict[str, Any]:
        """
        Execute a benchmark test with fixed number of requests.

        Args:
            target_url: URL to test
            requests: Number of requests to send

        Returns:
            Dictionary with benchmark results
        """

    @abstractmethod
    async def stress_test(
        self, target_url: str, start_users: int, max_users: int, step_users: int, step_duration: int
    ) -> dict[str, Any]:
        """
        Execute a stress test with gradually increasing load.

        Args:
            target_url: URL to test
            start_users: Initial number of users
            max_users: Maximum number of users
            step_users: User increment per step
            step_duration: Duration of each step in seconds

        Returns:
            Dictionary with stress test results
        """

    @abstractmethod
    async def close(self) -> None:
        """Close the performance client and cleanup resources."""


class IMetricsCollector(ABC):
    """
    Interface for collecting performance metrics (Interface Segregation Principle).

    This interface defines the contract for metrics collection during
    performance testing, following Single Responsibility Principle.
    """

    @abstractmethod
    def start_collection(self) -> None:
        """Start collecting metrics."""

    @abstractmethod
    def record_response_time(self, response_time_ms: float) -> None:
        """
        Record a response time measurement.

        Args:
            response_time_ms: Response time in milliseconds
        """

    @abstractmethod
    def record_error(self, error_type: str, error_message: str) -> None:
        """
        Record an error occurrence.

        Args:
            error_type: Type of error (e.g., 'timeout', 'connection_error')
            error_message: Error message or description
        """

    @abstractmethod
    def record_throughput(self, requests_count: int, time_window_ms: float) -> None:
        """
        Record throughput metrics.

        Args:
            requests_count: Number of requests in the time window
            time_window_ms: Time window in milliseconds
        """

    @abstractmethod
    def get_metrics(self) -> dict[str, Any]:
        """
        Get collected metrics.

        Returns:
            Dictionary with all collected metrics including:
            - response_times: Statistics about response times
            - throughput: Requests per second
            - error_rate: Percentage of failed requests
            - total_requests: Total number of requests
        """

    @abstractmethod
    def reset(self) -> None:
        """Reset all collected metrics."""


class ISecurityClient(ABC):
    """
    Interface for security testing clients (Interface Segregation Principle).

    This interface defines the contract for security testing adapters,
    supporting vulnerability testing like SQL injection, XSS, and auth testing.
    """

    @abstractmethod
    async def test_sql_injection(
        self, target_url: str, parameter: str, method: str = "GET"
    ) -> dict[str, Any]:
        """
        Test for SQL injection vulnerabilities.

        Args:
            target_url: URL to test
            parameter: Parameter name to test
            method: HTTP method (GET or POST)

        Returns:
            Dictionary with test results including vulnerabilities found
        """

    @abstractmethod
    async def test_xss(
        self, target_url: str, parameter: str, method: str = "GET"
    ) -> dict[str, Any]:
        """
        Test for Cross-Site Scripting (XSS) vulnerabilities.

        Args:
            target_url: URL to test
            parameter: Parameter name to test
            method: HTTP method (GET or POST)

        Returns:
            Dictionary with test results including vulnerabilities found
        """

    @abstractmethod
    async def test_authentication(self, target_url: str, test_cases: list) -> dict[str, Any]:
        """
        Test authentication mechanisms.

        Args:
            target_url: URL to test
            test_cases: List of authentication test cases

        Returns:
            Dictionary with authentication test results
        """

    @abstractmethod
    async def test_rate_limiting(
        self, target_url: str, requests_count: int, time_window: int
    ) -> dict[str, Any]:
        """
        Test rate limiting implementation.

        Args:
            target_url: URL to test
            requests_count: Number of requests to send
            time_window: Time window in seconds

        Returns:
            Dictionary with rate limiting test results
        """

    @abstractmethod
    async def test_security_headers(self, target_url: str) -> dict[str, Any]:
        """
        Test for security headers presence and configuration.

        Args:
            target_url: URL to test

        Returns:
            Dictionary with security headers analysis
        """

    @abstractmethod
    async def close(self) -> None:
        """Close the security client and cleanup resources."""


class IDatabaseClient(ABC):
    """
    Interface for database testing clients (Interface Segregation Principle).

    This interface defines the contract for database testing adapters,
    supporting SQL validation, data integrity testing, and migration testing.
    """

    @abstractmethod
    async def connect(self) -> None:
        """Establish database connection."""

    @abstractmethod
    async def disconnect(self) -> None:
        """Close database connection."""

    @abstractmethod
    async def execute_query(self, query: str, params: dict | None = None) -> Any:
        """
        Execute a SQL query.

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            Query results
        """

    @abstractmethod
    async def validate_query(self, query: str) -> dict[str, Any]:
        """
        Validate a SQL query for syntax and performance issues.

        Args:
            query: SQL query to validate

        Returns:
            Dictionary with validation results
        """

    @abstractmethod
    async def test_data_integrity(self, table: str, constraints: list[Any]) -> dict[str, Any]:
        """
        Test data integrity constraints.

        Args:
            table: Table name to test
            constraints: List of constraints to validate

        Returns:
            Dictionary with integrity test results
        """

    @abstractmethod
    async def test_migration(
        self, migration_script: str, rollback_script: str | None = None
    ) -> dict[str, Any]:
        """
        Test database migration script.

        Args:
            migration_script: Path to migration script or SQL content
            rollback_script: Optional path to rollback script

        Returns:
            Dictionary with migration test results
        """

    @abstractmethod
    async def get_schema_info(self) -> dict[str, Any]:
        """
        Get database schema information.

        Returns:
            Dictionary with schema details including tables, columns, indexes
        """


class ISQLValidator(ABC):
    """
    Interface for SQL validation (Interface Segregation Principle).

    This interface defines the contract for SQL query validation,
    checking syntax, performance, and security issues.
    """

    @abstractmethod
    def validate_syntax(self, query: str) -> dict[str, Any]:
        """
        Validate SQL query syntax.

        Args:
            query: SQL query to validate

        Returns:
            Dictionary with syntax validation results
        """

    @abstractmethod
    def check_performance_issues(self, query: str) -> dict[str, Any]:
        """
        Check for common SQL performance issues.

        Args:
            query: SQL query to analyze

        Returns:
            Dictionary with performance issues found
        """

    @abstractmethod
    def check_security_issues(self, query: str) -> dict[str, Any]:
        """
        Check for SQL security issues like injection vulnerabilities.

        Args:
            query: SQL query to analyze

        Returns:
            Dictionary with security issues found
        """

    @abstractmethod
    def analyze_query_plan(self, query: str) -> dict[str, Any]:
        """
        Analyze query execution plan.

        Args:
            query: SQL query to analyze

        Returns:
            Dictionary with query plan analysis
        """
