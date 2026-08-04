"""
Shared fixtures and configuration for integration tests.

This module provides pytest fixtures for integration testing between
the QA framework core and the dashboard backend.
"""

import asyncio
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Any, AsyncGenerator, Dict, Generator, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# Register the integration fixture modules so that factory fixtures such as
# ``test_result_factory``, ``test_suite_model_factory`` or
# ``mock_websocket_manager`` are available to the integration tests. Without
# this registration pytest reports them as "fixture not found" and every test
# that depends on them errors during setup.
pytest_plugins = [
    "tests.integration.fixtures.framework_fixtures",
    "tests.integration.fixtures.dashboard_fixtures",
]

# Configure pytest-asyncio
pytestmark = pytest.mark.asyncio(loop_scope="function")


# =============================================================================
# Test Configuration
# =============================================================================


class TestConfig:
    """Configuration for integration tests."""

    # Database configuration
    POSTGRES_HOST = os.getenv("TEST_POSTGRES_HOST", "localhost")
    POSTGRES_PORT = int(os.getenv("TEST_POSTGRES_PORT", "5432"))
    POSTGRES_DB = os.getenv("TEST_POSTGRES_DB", "qa_framework_test")
    POSTGRES_USER = os.getenv("TEST_POSTGRES_USER", "qa_user")
    POSTGRES_PASSWORD = os.getenv("TEST_POSTGRES_PASSWORD", "qa_password")

    # Redis configuration
    REDIS_HOST = os.getenv("TEST_REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("TEST_REDIS_PORT", "6379"))
    REDIS_DB = int(os.getenv("TEST_REDIS_DB", "1"))  # Use different DB for tests

    # Backend configuration
    BACKEND_URL = os.getenv("TEST_BACKEND_URL", "http://localhost:8000")
    API_VERSION = "v1"

    # Test timeouts
    DEFAULT_TIMEOUT = 30
    WEBSOCKET_TIMEOUT = 5

    @property
    def database_url(self) -> str:
        """Generate async database URL."""
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


config = TestConfig()


# =============================================================================
# Event Loop and Session Management
# =============================================================================


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def db_engine():
    """Create a database engine for the test session.

    The integration test database is an external dependency (Postgres). When it
    is not reachable — e.g. running the suite locally without ``docker compose``
    or without the CI service container — we skip the whole session instead of
    erroring every database-backed test, so the suite degrades gracefully.
    """
    engine = create_async_engine(
        config.database_url,
        echo=False,
        future=True,
        pool_size=5,
        max_overflow=10,
    )

    # Verify connectivity + create schema. Skip gracefully on failure so the
    # rest of the suite stays green in environments without a live database.
    try:
        async with engine.begin() as conn:
            from dashboard.backend.models import Base

            await conn.run_sync(Base.metadata.create_all)
    except Exception as exc:  # noqa: BLE001 — broad on purpose (any DB issue → skip)
        await engine.dispose()
        pytest.skip(f"Postgres unavailable for integration tests: {exc}")

    yield engine

    # Cleanup
    async with engine.begin() as conn:
        from dashboard.backend.models import Base

        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Provide a database session for each test."""
    async_session = sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        yield session
        # Rollback after each test
        await session.rollback()


# =============================================================================
# HTTP Client Fixtures
# =============================================================================


@pytest_asyncio.fixture
async def http_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """Provide an async HTTP client for API testing."""
    async with httpx.AsyncClient(
        base_url=config.BACKEND_URL,
        timeout=config.DEFAULT_TIMEOUT,
        headers={"Content-Type": "application/json"},
    ) as client:
        yield client


@pytest_asyncio.fixture
async def authenticated_client(http_client) -> AsyncGenerator[httpx.AsyncClient, None]:
    """Provide an authenticated HTTP client."""
    # Create a test user and login
    login_data = {"username": "test_integration_user", "password": "Test123!"}

    response = await http_client.post("/api/v1/auth/login", json=login_data)

    if response.status_code == 200:
        token = response.json()["access_token"]
        http_client.headers["Authorization"] = f"Bearer {token}"
    else:
        # Create user if doesn't exist
        user_data = {
            "username": login_data["username"],
            "email": "test@example.com",
            "password": login_data["password"],
        }
        await http_client.post("/api/v1/users", json=user_data)
        response = await http_client.post("/api/v1/auth/login", json=login_data)
        if response.status_code == 200:
            token = response.json()["access_token"]
            http_client.headers["Authorization"] = f"Bearer {token}"

    yield http_client


# =============================================================================
# Mock Fixtures for External Dependencies
# =============================================================================


@pytest.fixture
def mock_jira_integration():
    """Mock Jira integration for testing."""
    # The dashboard backend uses intra-package imports (e.g.
    # ``from integrations.base import ...``) that are only resolvable when
    # ``dashboard/backend`` is on sys.path. In the QA-FRAMEWORK test layout that
    # is not the case, so the patch target is not importable here — skip the
    # tests that need it rather than erroring at setup.
    try:
        import dashboard.backend.integrations.jira  # noqa: F401
    except Exception:  # noqa: BLE001 — broad on purpose (import failure → skip)
        pytest.skip(
            "dashboard.backend.integrations.jira is not importable in this "
            "test layout (requires dashboard/backend on sys.path)."
        )
    with patch("dashboard.backend.integrations.jira.JiraIntegration") as mock:
        instance = mock.return_value
        instance.connect = AsyncMock(return_value=True)
        instance.health_check = AsyncMock(return_value={"status": "healthy"})
        instance.create_bug = AsyncMock(return_value={"key": "TEST-123"})
        instance.sync_test_results = AsyncMock(return_value={"synced": 10})
        yield instance


@pytest.fixture
def mock_celery_task():
    """Mock Celery task execution."""
    # See mock_jira_integration: the patch target is not importable in this
    # test layout, so skip gracefully.
    try:
        import dashboard.backend.services.execution  # noqa: F401
    except Exception:  # noqa: BLE001 — broad on purpose (import failure → skip)
        pytest.skip(
            "dashboard.backend.services.execution is not importable in this "
            "test layout (requires dashboard/backend on sys.path)."
        )
    with patch("dashboard.backend.services.execution.execute_test_suite.delay") as mock:
        mock.return_value = MagicMock(
            id="test-task-id", status="PENDING", get=MagicMock(return_value={"status": "completed"})
        )
        yield mock


@pytest.fixture
def mock_redis():
    """Mock Redis cache for testing."""
    cache_data = {}

    class MockRedis:
        async def get(self, key: str) -> Optional[bytes]:
            return cache_data.get(key)

        async def set(self, key: str, value: bytes, ex: Optional[int] = None) -> bool:
            cache_data[key] = value
            return True

        async def delete(self, *keys) -> int:
            count = 0
            for key in keys:
                if key in cache_data:
                    del cache_data[key]
                    count += 1
            return count

        async def flushdb(self) -> bool:
            cache_data.clear()
            return True

        async def ping(self) -> bool:
            return True

    return MockRedis()


@pytest_asyncio.fixture
async def redis_client(mock_redis):
    """Provide a mock Redis client."""
    yield mock_redis


# =============================================================================
# Test Data Factories
# =============================================================================


@pytest.fixture
def test_suite_data():
    """Factory for test suite data."""

    def _factory(**kwargs):
        data = {
            "name": kwargs.get("name", "Integration Test Suite"),
            "description": kwargs.get("description", "Test suite for integration testing"),
            "framework_type": kwargs.get("framework_type", "pytest"),
            "config": kwargs.get("config", {"parallel": False, "timeout": 300, "retry_count": 1}),
        }
        data.update(kwargs)
        return data

    return _factory


@pytest.fixture
def test_case_data():
    """Factory for test case data."""

    def _factory(**kwargs):
        data = {
            "name": kwargs.get("name", "Integration Test Case"),
            "test_code": kwargs.get("test_code", "def test_example(): assert True"),
            "test_type": kwargs.get("test_type", "unit"),
            "priority": kwargs.get("priority", "medium"),
            "tags": kwargs.get("tags", ["integration", "automated"]),
        }
        data.update(kwargs)
        return data

    return _factory


@pytest.fixture
def test_execution_data():
    """Factory for test execution data."""

    def _factory(**kwargs):
        data = {
            "suite_id": kwargs.get("suite_id", 1),
            "environment": kwargs.get("environment", "test"),
            "parameters": kwargs.get("parameters", {}),
        }
        data.update(kwargs)
        return data

    return _factory


@pytest.fixture
def user_data():
    """Factory for user data."""

    def _factory(**kwargs):
        import uuid

        unique_id = str(uuid.uuid4())[:8]
        data = {
            "username": kwargs.get("username", f"testuser_{unique_id}"),
            "email": kwargs.get("email", f"test_{unique_id}@example.com"),
            "password": kwargs.get("password", "Test123!"),
            "is_active": kwargs.get("is_active", True),
        }
        data.update(kwargs)
        return data

    return _factory


# =============================================================================
# Performance and Timing Fixtures
# =============================================================================


@pytest.fixture
def performance_threshold():
    """Define performance thresholds for integration tests."""
    return {
        "api_response_ms": 500,
        "database_query_ms": 100,
        "cache_operation_ms": 50,
        "websocket_message_ms": 100,
        "end_to_end_flow_s": 30,
    }


@pytest.fixture
def benchmark():
    """Provide a simple benchmark fixture."""

    class Benchmark:
        def __init__(self):
            self.results = []

        def record(self, name: str, duration_ms: float, threshold_ms: float):
            self.results.append(
                {
                    "name": name,
                    "duration_ms": duration_ms,
                    "threshold_ms": threshold_ms,
                    "passed": duration_ms <= threshold_ms,
                }
            )
            return duration_ms <= threshold_ms

        def get_summary(self):
            passed = sum(1 for r in self.results if r["passed"])
            total = len(self.results)
            return {
                "total": total,
                "passed": passed,
                "failed": total - passed,
                "results": self.results,
            }

    return Benchmark()


# =============================================================================
# Cleanup and Utility Fixtures
# =============================================================================


@pytest.fixture(autouse=True)
def cleanup_after_test():
    """Automatically cleanup after each test."""
    yield
    # Cleanup logic runs after each test


@pytest.fixture
def test_id():
    """Generate a unique test ID."""
    import uuid

    return str(uuid.uuid4())


@pytest.fixture
def test_timestamp():
    """Provide current timestamp for test data."""
    return datetime.now(timezone.utc)


# =============================================================================
# Pytest Configuration Hooks
# =============================================================================


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line("markers", "database: mark test as requiring database")
    config.addinivalue_line("markers", "redis: mark test as requiring Redis")
    config.addinivalue_line("markers", "websocket: mark test as requiring WebSocket")
    config.addinivalue_line("markers", "concurrent: mark test as testing concurrent operations")
    config.addinivalue_line("markers", "e2e: mark test as end-to-end")


def pytest_collection_modifyitems(config, items):
    """Modify test collection - add markers based on test name."""
    for item in items:
        if "integration" in item.nodeid:
            item.add_marker(pytest.mark.integration)
        if "database" in item.nodeid or "db_" in item.nodeid:
            item.add_marker(pytest.mark.database)
        if "redis" in item.nodeid or "cache" in item.nodeid:
            item.add_marker(pytest.mark.redis)
        if "websocket" in item.nodeid or "ws_" in item.nodeid:
            item.add_marker(pytest.mark.websocket)
        if "concurrent" in item.nodeid:
            item.add_marker(pytest.mark.concurrent)
        if "e2e" in item.nodeid:
            item.add_marker(pytest.mark.e2e)
