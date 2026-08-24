"""Benchmark tests for QA-FRAMEWORK core components.

These tests use pytest-benchmark to measure performance of critical operations.
Run with: pytest tests/performance -v -m performance --benchmark-only
"""

import time

import pytest


class TestCorePerformance:
    """Performance tests for core framework components."""

    @pytest.mark.performance
    def test_import_time(self, benchmark):
        """Benchmark import time of core module."""

        def import_core():
            import src.core.entities.test_result  # noqa: F401

            return True

        result = benchmark(import_core)
        assert result is True

    @pytest.mark.performance
    def test_test_result_creation(self, benchmark):
        """Benchmark TestResult entity creation."""
        from src.core.entities.test_result import TestResult, TestStatus

        def create_result():
            return TestResult(
                test_id="perf-test-001",
                name="Performance Test",
                status=TestStatus.PASSED,
                duration_ms=100.0,
                message="Benchmark test",
            )

        result = benchmark(create_result)
        assert result.test_id == "perf-test-001"

    @pytest.mark.performance
    def test_test_result_serialization(self, benchmark):
        """Benchmark TestResult serialization to dict."""
        from src.core.entities.test_result import TestResult, TestStatus

        test_result = TestResult(
            test_id="perf-test-002",
            name="Serialization Benchmark",
            status=TestStatus.PASSED,
            duration_ms=50.0,
        )

        result = benchmark(lambda: test_result.to_dict())
        assert isinstance(result, dict)

    @pytest.mark.performance
    def test_logger_performance(self, benchmark):
        """Benchmark QALogger write operations."""
        from src.core.interfaces.logger import LogLevel, QALogger

        logger = QALogger(name="benchmark-logger")

        def log_message():
            logger.log(
                level=LogLevel.INFO,
                message="Benchmark log message",
                context={"test": "performance"},
            )
            return True

        result = benchmark(log_message)
        assert result is True


class TestAdapterPerformance:
    """Performance tests for adapters."""

    @pytest.mark.performance
    def test_http_adapter_instantiation(self, benchmark):
        """Benchmark HTTP adapter creation."""
        from src.adapters.http.http_client import HTTPClient

        def create_client():
            return HTTPClient(base_url="http://localhost")

        result = benchmark(create_client)
        assert result is not None

    @pytest.mark.performance
    def test_database_adapter_instantiation(self, benchmark):
        """Benchmark database adapter creation."""
        from src.adapters.database.database_client import DatabaseClient

        def create_client():
            return DatabaseClient(connection_string="sqlite:///:memory:")

        result = benchmark(create_client)
        assert result is not None


class TestReportPerformance:
    """Performance tests for reporting."""

    @pytest.mark.performance
    def test_html_report_generation(self, benchmark):
        """Benchmark HTML report generation."""
        from src.adapters.reporting.html_reporter import HTMLReporter
        from src.core.entities.test_result import TestResult, TestStatus

        results = [
            TestResult(
                test_id=f"test-{i}",
                name=f"Test {i}",
                status=TestStatus.PASSED if i % 2 == 0 else TestStatus.FAILED,
                duration_ms=float(i * 10),
            )
            for i in range(100)
        ]

        reporter = HTMLReporter()

        result = benchmark(lambda: reporter.generate(results))
        assert result is not None

    @pytest.mark.performance
    def test_json_report_generation(self, benchmark):
        """Benchmark JSON report generation."""
        from src.adapters.reporting.json_reporter import JSONReporter
        from src.core.entities.test_result import TestResult, TestStatus

        results = [
            TestResult(
                test_id=f"test-{i}",
                name=f"Test {i}",
                status=TestStatus.PASSED if i % 2 == 0 else TestStatus.FAILED,
                duration_ms=float(i * 10),
            )
            for i in range(100)
        ]

        reporter = JSONReporter()

        result = benchmark(lambda: reporter.generate(results))
        assert result is not None


class TestConcurrencyPerformance:
    """Performance tests for concurrent operations."""

    @pytest.mark.performance
    def test_concurrent_test_execution(self, benchmark):
        """Benchmark concurrent test execution simulation."""
        import concurrent.futures

        def simulate_test(test_id):
            time.sleep(0.001)  # Simulate test execution
            return f"test-{test_id}"

        def run_concurrent():
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(simulate_test, i) for i in range(50)]
                return [f.result() for f in concurrent.futures.as_completed(futures)]

        results = benchmark(run_concurrent)
        assert len(results) == 50


# Smoke test to verify benchmark fixture works
@pytest.mark.performance
def test_benchmark_fixture_works(benchmark):
    """Verify benchmark fixture is working correctly."""

    def simple_operation():
        return 1 + 1

    result = benchmark(simple_operation)
    assert result == 2
