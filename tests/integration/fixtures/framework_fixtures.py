"""
Fixtures for QA Framework core integration testing.

Provides fixtures for the framework core components including test runners,
adapters, and result entities.
"""

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from src.core.entities.test_result import TestResult, TestStatus
from src.core.use_cases.test_runner import TestRunner

# =============================================================================
# Core Entity Fixtures
# =============================================================================


@pytest.fixture
def test_result_factory():
    """Factory for creating TestResult entities."""

    def _factory(**kwargs):
        return TestResult(
            test_id=kwargs.get("test_id", "test_001"),
            test_name=kwargs.get("test_name", "Example Test"),
            status=kwargs.get("status", TestStatus.PASSED),
            duration=kwargs.get("duration", 1.5),
            error_message=kwargs.get("error_message", None),
            metadata=kwargs.get("metadata", {}),
            timestamp=kwargs.get("timestamp", datetime.now(UTC)),
            suite_id=kwargs.get("suite_id", 1),
            case_id=kwargs.get("case_id", 1),
        )

    return _factory


@pytest.fixture
def multiple_test_results(test_result_factory):
    """Create a list of test results with various statuses."""
    return [
        test_result_factory(status=TestStatus.PASSED, test_id="test_001"),
        test_result_factory(status=TestStatus.PASSED, test_id="test_002"),
        test_result_factory(
            status=TestStatus.FAILED, test_id="test_003", error_message="Assertion failed"
        ),
        test_result_factory(status=TestStatus.SKIPPED, test_id="test_004"),
        test_result_factory(
            status=TestStatus.ERROR, test_id="test_005", error_message="Runtime error"
        ),
    ]


@pytest.fixture
def test_status_variations():
    """Provide all test status variations for testing."""
    return {
        "passed": TestStatus.PASSED,
        "failed": TestStatus.FAILED,
        "skipped": TestStatus.SKIPPED,
        "error": TestStatus.ERROR,
        "in_progress": TestStatus.IN_PROGRESS,
    }


# =============================================================================
# Test Runner Fixtures
# =============================================================================


@pytest.fixture
def test_runner():
    """Provide a configured TestRunner instance."""
    return TestRunner(max_retries=1, timeout=30.0, parallel=False)


@pytest_asyncio.fixture
async def async_test_runner():
    """Provide an async-configured TestRunner."""
    runner = TestRunner(max_retries=1, timeout=30.0, parallel=True)
    yield runner


@pytest.fixture
def mock_test_runner():
    """Provide a mocked TestRunner for controlled testing."""
    mock_runner = MagicMock(spec=TestRunner)
    mock_runner.run_test = AsyncMock()
    mock_runner.run_tests = AsyncMock()
    return mock_runner


# =============================================================================
# Adapter Fixtures
# =============================================================================


@pytest.fixture
def mock_http_adapter():
    """Mock HTTP adapter for testing."""
    with patch("src.adapters.http.httpx_client.HTTPXClient") as mock:
        instance = mock.return_value
        instance.request = AsyncMock(
            return_value={"status_code": 200, "json": {"success": True}, "text": "OK"}
        )
        instance.get = AsyncMock(return_value={"status_code": 200, "json": dict})
        instance.post = AsyncMock(return_value={"status_code": 201, "json": lambda: {"id": 1}})
        instance.close = AsyncMock()
        yield instance


@pytest.fixture
def mock_ui_adapter():
    """Mock UI adapter (Playwright) for testing."""
    with patch("src.adapters.ui.playwright_page.PlaywrightPage") as mock:
        instance = mock.return_value
        instance.goto = AsyncMock()
        instance.click = AsyncMock()
        instance.fill = AsyncMock()
        instance.screenshot = AsyncMock(return_value=b"screenshot_bytes")
        instance.close = AsyncMock()
        instance.get_text = AsyncMock(return_value="Sample text")
        yield instance


@pytest.fixture
def mock_database_adapter():
    """Mock database adapter for testing."""
    with patch("src.adapters.database.sqlalchemy_adapter.SQLAlchemyAdapter") as mock:
        instance = mock.return_value
        instance.execute = AsyncMock(return_value=[{"id": 1, "name": "test"}])
        instance.insert = AsyncMock(return_value=1)
        instance.update = AsyncMock(return_value=True)
        instance.delete = AsyncMock(return_value=True)
        instance.query = AsyncMock(return_value=[])
        instance.close = AsyncMock()
        yield instance


# =============================================================================
# Result Reporter Fixtures
# =============================================================================


@pytest.fixture
def mock_allure_reporter():
    """Mock Allure reporter for testing."""
    with patch("src.adapters.reporting.allure_reporter.AllureReporter") as mock:
        instance = mock.return_value
        instance.start_test = MagicMock()
        instance.stop_test = MagicMock()
        instance.attach_screenshot = MagicMock()
        instance.attach_log = MagicMock()
        instance.generate_report = MagicMock(return_value="/path/to/report")
        yield instance


@pytest.fixture
def mock_html_reporter():
    """Mock HTML reporter for testing."""
    with patch("src.adapters.reporting.html_reporter.HTMLReporter") as mock:
        instance = mock.return_value
        instance.add_result = MagicMock()
        instance.generate = MagicMock(return_value="/path/to/report.html")
        yield instance


# =============================================================================
# Test Configuration Fixtures
# =============================================================================


@pytest.fixture
def framework_config():
    """Provide framework configuration for tests."""
    return {
        "test": {"timeout": 300, "retry_count": 1, "parallel_workers": 2},
        "reporting": {
            "enabled": True,
            "output_dir": "/tmp/test_reports",
            "formats": ["json", "html", "allure"],
        },
        "adapters": {
            "http": {"timeout": 30, "retries": 3},
            "ui": {"headless": True, "browser": "chromium"},
            "database": {"pool_size": 5, "max_overflow": 10},
        },
    }


@pytest.fixture
def test_artifacts_dir(tmp_path):
    """Provide a temporary directory for test artifacts."""
    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir()
    return str(artifacts_dir)


@pytest.fixture
def sample_test_code():
    """Provide sample test code for testing."""
    return """
def test_example_pass():
    assert True

def test_example_fail():
    assert False, "Intentional failure"

def test_example_error():
    raise RuntimeError("Intentional error")

@pytest.mark.skip
def test_example_skip():
    pass
"""


# =============================================================================
# Execution Context Fixtures
# =============================================================================


@pytest.fixture
def execution_context():
    """Provide a test execution context."""
    return {
        "execution_id": "exec_001",
        "suite_id": 1,
        "environment": "test",
        "start_time": datetime.now(UTC),
        "user_id": "user_001",
        "parameters": {"parallel": False, "timeout": 300},
    }


@pytest.fixture
def framework_event_stream():
    """Provide a mock event stream for framework events."""
    events = []

    class EventStream:
        def __init__(self):
            self.events = events

        def add_event(self, event_type: str, data: dict[str, Any]):
            self.events.append(
                {
                    "type": event_type,
                    "data": data,
                    "timestamp": datetime.now(UTC).isoformat(),
                }
            )

        def get_events(self) -> list[dict]:
            return self.events

        def clear(self):
            self.events.clear()

    return EventStream()


# =============================================================================
# Cleanup Fixtures
# =============================================================================


@pytest.fixture(autouse=True)
def cleanup_framework_state():
    """Cleanup framework state after each test."""
    yield
    # Cleanup any global state
