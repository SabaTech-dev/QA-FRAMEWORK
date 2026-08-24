"""
Advanced Test Fixtures Organization.

Provides organized fixtures by architectural layers:
- Core fixtures (entities, configuration)
- Infrastructure fixtures (database, cache, messaging)
- Adapter fixtures (HTTP, UI, API clients)
- Test Data fixtures (factories, builders, object mothers)
"""

import asyncio
import os
import shutil
import tempfile
import threading
import uuid
from collections.abc import AsyncGenerator, Callable, Generator
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from multiprocessing import Queue
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from faker import Faker

from tests.fixtures.factories import (
    APIRequestFactory,
    ObjectMother,
    OrderFactory,
    ProductFactory,
    TestScenarioBuilder,
    UserFactory,
)
from tests.fixtures.patterns import (
    AAAPattern,
    GivenWhenThen,
    RetryPattern,
    TestIsolationManager,
    create_test_table,
)

# ============================================================================
# CORE LAYER FIXTURES
# ============================================================================


@pytest.fixture(scope="session")
def session_id() -> str:
    """Unique session identifier for test isolation."""
    return str(uuid.uuid4())


@pytest.fixture(scope="session")
def test_run_timestamp() -> datetime:
    """Timestamp when test run started."""
    return datetime.now()


@pytest.fixture(scope="session")
def test_config() -> dict[str, Any]:
    """Test configuration loaded from environment or defaults."""
    return {
        "environment": os.getenv("TEST_ENV", "development"),
        "debug": os.getenv("TEST_DEBUG", "false").lower() == "true",
        "parallel_workers": int(os.getenv("TEST_WORKERS", "4")),
        "timeout": int(os.getenv("TEST_TIMEOUT", "30")),
        "retries": int(os.getenv("TEST_RETRIES", "3")),
    }


@pytest.fixture(scope="session")
def faker_instance(worker_id: str) -> Faker:
    """Faker instance seeded for reproducibility."""
    fake = Faker()
    # Seed with worker_id to ensure different workers get different sequences
    seed_value = hash(worker_id) % 10000 if worker_id != "master" else 0
    fake.seed_instance(seed_value)
    return fake


@pytest.fixture(scope="function")
def isolated_event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Isolated event loop for async tests."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop

    # Cleanup
    pending = asyncio.all_tasks(loop)
    for task in pending:
        task.cancel()

    loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
    loop.close()


# ============================================================================
# INFRASTRUCTURE LAYER FIXTURES
# ============================================================================


@pytest.fixture(scope="session")
def thread_pool() -> Generator[ThreadPoolExecutor, None, None]:
    """Thread pool for parallel test execution."""
    pool = ThreadPoolExecutor(max_workers=4)
    yield pool
    pool.shutdown(wait=True)


@pytest.fixture(scope="session")
def shared_message_queue() -> Queue:
    """Shared message queue for inter-test communication."""
    return Queue()


@pytest.fixture(scope="function")
def resource_lock() -> threading.Lock:
    """Thread-safe lock for shared resources."""
    return threading.Lock()


@pytest.fixture(scope="function")
def temp_directory() -> Generator[str, None, None]:
    """Temporary directory isolated per test."""
    temp_dir = tempfile.mkdtemp(prefix="test_")
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture(scope="session")
def worker_temp_dir(worker_id: str) -> Generator[str, None, None]:
    """Temporary directory isolated per worker."""
    temp_dir = tempfile.mkdtemp(prefix=f"worker_{worker_id}_")
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture(scope="function")
def mock_database() -> Generator[MagicMock, None, None]:
    """Mock database for unit tests."""
    db = MagicMock()
    db.connect = MagicMock(return_value=True)
    db.disconnect = MagicMock(return_value=True)
    db.execute = MagicMock(return_value=[])
    db.query = MagicMock(return_value=[])
    yield db


@pytest.fixture(scope="function")
def mock_cache() -> Generator[MagicMock, None, None]:
    """Mock cache for unit tests."""
    cache = MagicMock()
    cache.get = MagicMock(return_value=None)
    cache.set = MagicMock(return_value=True)
    cache.delete = MagicMock(return_value=True)
    cache.clear = MagicMock(return_value=True)
    yield cache


@pytest.fixture(scope="function")
def mock_message_broker() -> Generator[MagicMock, None, None]:
    """Mock message broker for unit tests."""
    broker = MagicMock()
    broker.publish = MagicMock(return_value=True)
    broker.subscribe = MagicMock(return_value=True)
    broker.consume = MagicMock(return_value=[])
    yield broker


# ============================================================================
# ADAPTER LAYER FIXTURES
# ============================================================================


@pytest.fixture(scope="function")
def mock_http_client() -> Generator[MagicMock, None, None]:
    """Mock HTTP client for unit tests."""
    client = MagicMock()
    client.get = MagicMock(return_value=MagicMock(status_code=200, json=dict))
    client.post = MagicMock(return_value=MagicMock(status_code=201, json=dict))
    client.put = MagicMock(return_value=MagicMock(status_code=200, json=dict))
    client.delete = MagicMock(return_value=MagicMock(status_code=204))
    client.close = MagicMock()
    yield client


@pytest.fixture(scope="function")
def mock_async_http_client() -> Generator[AsyncMock, None, None]:
    """Mock async HTTP client for unit tests."""
    client = AsyncMock()

    response_mock = AsyncMock()
    response_mock.status_code = 200
    response_mock.json = AsyncMock(return_value={})
    response_mock.text = AsyncMock(return_value="")
    response_mock.headers = {}

    client.get = AsyncMock(return_value=response_mock)
    client.post = AsyncMock(return_value=response_mock)
    client.put = AsyncMock(return_value=response_mock)
    client.delete = AsyncMock(return_value=response_mock)
    client.close = AsyncMock()

    yield client


@pytest.fixture(scope="function")
def mock_ui_driver() -> Generator[MagicMock, None, None]:
    """Mock UI driver for unit tests."""
    driver = MagicMock()
    driver.goto = MagicMock()
    driver.click = MagicMock()
    driver.fill = MagicMock()
    driver.screenshot = MagicMock(return_value=b"fake_screenshot")
    driver.close = MagicMock()
    yield driver


@pytest.fixture(scope="function")
def mock_api_client() -> Generator[MagicMock, None, None]:
    """Mock API client with predefined responses."""
    client = MagicMock()
    client.base_url = "https://api.example.com"
    client.headers = {"Authorization": "Bearer test_token"}

    client.request = MagicMock(
        return_value=MagicMock(status_code=200, json=lambda: {"data": [], "meta": {"total": 0}})
    )

    yield client


# ============================================================================
# TEST DATA FACTORIES FIXTURES
# ============================================================================


@pytest.fixture(scope="function")
def user_factory(faker_instance: Faker) -> UserFactory:
    """User factory for generating test users."""
    return UserFactory(faker_instance)


@pytest.fixture(scope="function")
def product_factory(faker_instance: Faker) -> ProductFactory:
    """Product factory for generating test products."""
    return ProductFactory(faker_instance)


@pytest.fixture(scope="function")
def order_factory(faker_instance: Faker) -> OrderFactory:
    """Order factory for generating test orders."""
    return OrderFactory(faker_instance)


@pytest.fixture(scope="function")
def api_request_factory(faker_instance: Faker) -> APIRequestFactory:
    """API request factory for generating test requests."""
    return APIRequestFactory(faker_instance)


@pytest.fixture(scope="function")
def object_mother(faker_instance: Faker) -> ObjectMother:
    """Object mother for common test scenarios."""
    return ObjectMother(faker_instance)


@pytest.fixture(scope="function")
def scenario_builder(faker_instance: Faker) -> TestScenarioBuilder:
    """Scenario builder for complex test setups."""
    return TestScenarioBuilder(faker_instance)


# ============================================================================
# TEST PATTERN FIXTURES
# ============================================================================


@pytest.fixture(scope="function")
def aaa_pattern(request: pytest.FixtureRequest) -> AAAPattern:
    """AAA pattern helper for structured tests."""
    return AAAPattern(test_name=request.node.name)


@pytest.fixture(scope="function")
def bdd_scenario(request: pytest.FixtureRequest) -> GivenWhenThen:
    """BDD pattern helper for behavior-driven tests."""
    return GivenWhenThen(scenario_name=request.node.name)


@pytest.fixture(scope="function")
def test_isolation() -> Generator[TestIsolationManager, None, None]:
    """Test isolation manager for setup/teardown."""
    manager = TestIsolationManager()
    yield manager
    manager.teardown()


@pytest.fixture(scope="function")
def retry_handler() -> RetryPattern:
    """Retry pattern handler for flaky tests."""
    return RetryPattern(max_retries=3, delay=0.1)


@pytest.fixture(scope="function")
def test_data_table() -> Callable[..., Any]:
    """Factory for test data tables."""
    return create_test_table


# ============================================================================
# UTILITY FIXTURES
# ============================================================================


@pytest.fixture(scope="function")
def timer() -> Generator[dict[str, Any], None, None]:
    """Timer fixture for performance measurement."""
    timer_data = {"start": None, "end": None, "duration": None}
    timer_data["start"] = datetime.now()
    yield timer_data
    timer_data["end"] = datetime.now()
    timer_data["duration"] = (timer_data["end"] - timer_data["start"]).total_seconds()


@pytest.fixture(scope="function")
def execution_context() -> dict[str, Any]:
    """Execution context with thread and process info."""
    import os
    import threading

    return {
        "pid": os.getpid(),
        "thread_id": threading.current_thread().ident,
        "thread_name": threading.current_thread().name,
    }


@pytest.fixture(scope="function")
def test_data_container() -> dict[str, Any]:
    """Container for test data that needs to be shared within a test."""
    return {}


@pytest.fixture(scope="function")
def unique_test_id(request: pytest.FixtureRequest) -> str:
    """Generate unique test ID."""
    return f"{request.node.name}_{uuid.uuid4().hex[:8]}"


@pytest.fixture(scope="function")
def isolated_test_data(worker_id: str, unique_test_id: str) -> dict[str, Any]:
    """Isolated test data container per test."""
    return {
        "worker_id": worker_id,
        "test_id": unique_test_id,
        "created_at": datetime.now().isoformat(),
        "data": {},
    }


# ============================================================================
# ASYNC FIXTURES
# ============================================================================


@pytest_asyncio.fixture(scope="function")
async def async_timer() -> AsyncGenerator[dict[str, Any], None]:
    """Async timer fixture."""
    timer_data = {"start": datetime.now(), "end": None, "duration": None}
    yield timer_data
    timer_data["end"] = datetime.now()
    timer_data["duration"] = (timer_data["end"] - timer_data["start"]).total_seconds()


@pytest_asyncio.fixture(scope="function")
async def async_resource_pool() -> AsyncGenerator[dict[str, Any], None]:
    """Async resource pool for async tests."""
    pool = {"resources": [], "max_size": 10}
    yield pool
    # Cleanup
    pool["resources"].clear()


# ============================================================================
# CUSTOMIZATION HOOKS
# ============================================================================


def pytest_configure(config: pytest.Config) -> None:
    """Configure pytest with custom markers and options."""
    # Add custom markers
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "e2e: End-to-end tests")
    config.addinivalue_line("markers", "api: API tests")
    config.addinivalue_line("markers", "ui: UI tests")
    config.addinivalue_line("markers", "performance: Performance tests")
    config.addinivalue_line("markers", "security: Security tests")
    config.addinivalue_line("markers", "flaky: Flaky tests that may need retries")
    config.addinivalue_line("markers", "serial: Tests that must run serially")
    config.addinivalue_line("markers", "parallel_safe: Tests safe for parallel execution")
    config.addinivalue_line("markers", "isolated: Tests requiring complete isolation")


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Modify test collection - automatically add markers based on path."""
    for item in items:
        # Auto-mark based on directory
        if "/unit/" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "/integration/" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "/e2e/" in str(item.fspath):
            item.add_marker(pytest.mark.e2e)
        elif "/performance/" in str(item.fspath):
            item.add_marker(pytest.mark.performance)
        elif "/security/" in str(item.fspath):
            item.add_marker(pytest.mark.security)


@pytest.fixture(scope="session", autouse=True)
def log_test_session_start(request: pytest.FixtureRequest) -> Generator[None, None, None]:
    """Log when test session starts and ends."""
    print(f"\n{'=' * 60}")
    print(f"Starting test session: {request.config.invocation_params.args}")
    print(f"Workers: {request.config.getoption('numprocesses', '1')}")
    print(f"{'=' * 60}\n")
    yield
    print(f"\n{'=' * 60}")
    print("Test session completed")
    print(f"{'=' * 60}\n")
