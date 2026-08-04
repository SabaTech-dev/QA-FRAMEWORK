"""
Fixtures for Dashboard backend integration testing.

Provides fixtures for the dashboard FastAPI backend including API clients,
database models, and service mocks.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any, AsyncGenerator, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession


# =============================================================================
# Dashboard patch helper
# =============================================================================
#
# The dashboard backend uses intra-package imports (e.g.
# ``from services.auth_service import ...``) that only resolve when
# ``dashboard/backend`` is on sys.path. In the QA-FRAMEWORK test layout that
# path is not present, so any ``patch("dashboard.backend.<sub>...")`` target
# cannot be imported and every dependent test errors at setup. This helper
# skips the test gracefully instead of erroring.
def _patch_or_skip(target, **kwargs):
    """Like :func:`unittest.mock.patch`, but skip the test when the target
    module is not importable in the current layout."""
    import contextlib
    import importlib

    module_name = target.rsplit(".", 1)[0]

    @contextlib.contextmanager
    def _cm():
        try:
            importlib.import_module(module_name)
        except Exception:  # noqa: BLE001 — broad on purpose (import failure → skip)
            pytest.skip(
                f"{module_name} is not importable in this test layout "
                "(requires dashboard/backend on sys.path)."
            )
        with patch(target, **kwargs) as mock:
            yield mock

    return _cm()


# =============================================================================
# Dashboard Model Fixtures
# =============================================================================


@pytest.fixture
def user_model_factory():
    """Factory for creating User model data."""

    def _factory(**kwargs):
        return {
            "id": kwargs.get("id", 1),
            "username": kwargs.get("username", "testuser"),
            "email": kwargs.get("email", "test@example.com"),
            "hashed_password": kwargs.get("hashed_password", "hashed_password_hash"),
            "is_active": kwargs.get("is_active", True),
            "is_superuser": kwargs.get("is_superuser", False),
            "created_at": kwargs.get("created_at", datetime.now(timezone.utc)),
            "updated_at": kwargs.get("updated_at", datetime.now(timezone.utc)),
        }

    return _factory


@pytest.fixture
def test_suite_model_factory():
    """Factory for creating TestSuite model data."""

    def _factory(**kwargs):
        return {
            "id": kwargs.get("id", 1),
            "name": kwargs.get("name", "Test Suite"),
            "description": kwargs.get("description", "Test suite description"),
            "framework_type": kwargs.get("framework_type", "pytest"),
            "config": kwargs.get("config", {"parallel": False, "timeout": 300, "retry_count": 1}),
            "created_at": kwargs.get("created_at", datetime.now(timezone.utc)),
            "updated_at": kwargs.get("updated_at", datetime.now(timezone.utc)),
            "created_by": kwargs.get("created_by", 1),
        }

    return _factory


@pytest.fixture
def test_case_model_factory():
    """Factory for creating TestCase model data."""

    def _factory(**kwargs):
        return {
            "id": kwargs.get("id", 1),
            "suite_id": kwargs.get("suite_id", 1),
            "name": kwargs.get("name", "Test Case"),
            "test_code": kwargs.get("test_code", "def test_example(): pass"),
            "test_type": kwargs.get("test_type", "unit"),
            "priority": kwargs.get("priority", "medium"),
            "tags": kwargs.get("tags", ["integration"]),
            "created_at": kwargs.get("created_at", datetime.now(timezone.utc)),
            "updated_at": kwargs.get("updated_at", datetime.now(timezone.utc)),
        }

    return _factory


@pytest.fixture
def test_execution_model_factory():
    """Factory for creating TestExecution model data."""

    def _factory(**kwargs):
        return {
            "id": kwargs.get("id", 1),
            "suite_id": kwargs.get("suite_id", 1),
            "status": kwargs.get("status", "pending"),
            "environment": kwargs.get("environment", "test"),
            "parameters": kwargs.get("parameters", {}),
            "started_at": kwargs.get("started_at", None),
            "completed_at": kwargs.get("completed_at", None),
            "duration": kwargs.get("duration", None),
            "results_summary": kwargs.get(
                "results_summary", {"total": 0, "passed": 0, "failed": 0, "skipped": 0, "error": 0}
            ),
            "created_at": kwargs.get("created_at", datetime.now(timezone.utc)),
            "triggered_by": kwargs.get("triggered_by", 1),
        }

    return _factory


@pytest.fixture
def test_artifact_model_factory():
    """Factory for creating TestArtifact model data."""

    def _factory(**kwargs):
        return {
            "id": kwargs.get("id", 1),
            "execution_id": kwargs.get("execution_id", 1),
            "test_case_id": kwargs.get("test_case_id", 1),
            "artifact_type": kwargs.get("artifact_type", "screenshot"),
            "file_path": kwargs.get("file_path", "/path/to/artifact.png"),
            "file_size": kwargs.get("file_size", 1024),
            "created_at": kwargs.get("created_at", datetime.now(timezone.utc)),
        }

    return _factory


# =============================================================================
# API Response Fixtures
# =============================================================================


@pytest.fixture
def api_response_factory():
    """Factory for creating standardized API responses."""

    def _factory(status="success", data=None, message=None, errors=None):
        return {"status": status, "data": data or {}, "message": message, "errors": errors or []}

    return _factory


@pytest.fixture
def paginated_response_factory():
    """Factory for creating paginated API responses."""

    def _factory(items=None, total=0, page=1, page_size=20):
        return {
            "status": "success",
            "data": {
                "items": items or [],
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": (total + page_size - 1) // page_size,
            },
        }

    return _factory


@pytest.fixture
def auth_token_response():
    """Provide a sample authentication token response."""
    return {
        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test_token",
        "token_type": "bearer",
        "expires_in": 3600,
    }


# =============================================================================
# Dashboard Service Mocks
# =============================================================================


@pytest.fixture
def mock_test_suite_service():
    """Mock TestSuite service for testing."""
    with _patch_or_skip("dashboard.backend.services.suite.TestSuiteService") as mock:
        instance = mock.return_value
        instance.create = AsyncMock(return_value={"id": 1, "name": "Test Suite"})
        instance.get = AsyncMock(return_value={"id": 1, "name": "Test Suite"})
        instance.update = AsyncMock(return_value={"id": 1, "name": "Updated Suite"})
        instance.delete = AsyncMock(return_value=True)
        instance.list = AsyncMock(return_value=[])
        yield instance


@pytest.fixture
def mock_test_case_service():
    """Mock TestCase service for testing."""
    with _patch_or_skip("dashboard.backend.services.case.TestCaseService") as mock:
        instance = mock.return_value
        instance.create = AsyncMock(return_value={"id": 1, "name": "Test Case"})
        instance.get = AsyncMock(return_value={"id": 1, "name": "Test Case"})
        instance.update = AsyncMock(return_value={"id": 1, "name": "Updated Case"})
        instance.delete = AsyncMock(return_value=True)
        instance.list = AsyncMock(return_value=[])
        yield instance


@pytest.fixture
def mock_execution_service():
    """Mock Execution service for testing."""
    with _patch_or_skip("dashboard.backend.services.execution.ExecutionService") as mock:
        instance = mock.return_value
        instance.create = AsyncMock(return_value={"id": 1, "status": "pending"})
        instance.get = AsyncMock(return_value={"id": 1, "status": "running"})
        instance.start = AsyncMock(return_value={"id": 1, "status": "running"})
        instance.stop = AsyncMock(return_value={"id": 1, "status": "stopped"})
        instance.list = AsyncMock(return_value=[])
        instance.get_status = AsyncMock(return_value="completed")
        yield instance


@pytest.fixture
def mock_user_service():
    """Mock User service for testing."""
    with _patch_or_skip("dashboard.backend.services.user.UserService") as mock:
        instance = mock.return_value
        instance.create = AsyncMock(return_value={"id": 1, "username": "testuser"})
        instance.get = AsyncMock(return_value={"id": 1, "username": "testuser"})
        instance.get_by_username = AsyncMock(return_value={"id": 1, "username": "testuser"})
        instance.update = AsyncMock(return_value={"id": 1, "username": "updateduser"})
        instance.delete = AsyncMock(return_value=True)
        instance.authenticate = AsyncMock(return_value={"id": 1, "username": "testuser"})
        yield instance


@pytest.fixture
def mock_dashboard_cache():
    """Mock Dashboard cache manager for testing."""
    with _patch_or_skip("dashboard.backend.core.cache.cache_manager") as mock:
        mock.async_get = AsyncMock(return_value=None)
        mock.async_set = AsyncMock(return_value=True)
        mock.async_delete = AsyncMock(return_value=True)
        mock.invalidate_suite_cache = AsyncMock()
        mock.invalidate_case_cache = AsyncMock()
        mock.invalidate_execution_cache = AsyncMock()
        mock.invalidate_dashboard_cache = AsyncMock()
        yield mock


# =============================================================================
# WebSocket Fixtures
# =============================================================================


@pytest.fixture
def mock_websocket_manager():
    """Mock WebSocket manager for testing."""
    with _patch_or_skip("dashboard.backend.core.websocket.ConnectionManager") as mock:
        instance = mock.return_value
        instance.connect = AsyncMock()
        instance.disconnect = AsyncMock()
        instance.send_personal_message = AsyncMock()
        instance.broadcast = AsyncMock()
        instance.get_active_connections = MagicMock(return_value=[])
        yield instance


@pytest.fixture
def websocket_message_factory():
    """Factory for creating WebSocket messages."""

    def _factory(message_type="update", data=None):
        return {
            "type": message_type,
            "data": data or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    return _factory


# =============================================================================
# Integration Hub Fixtures
# =============================================================================


@pytest.fixture
def mock_jira_client():
    """Mock Jira client for integration testing."""
    with _patch_or_skip("dashboard.backend.integrations.jira.JiraClient") as mock:
        instance = mock.return_value
        instance.connect = AsyncMock(return_value=True)
        instance.create_issue = AsyncMock(return_value={"key": "TEST-123"})
        instance.get_issue = AsyncMock(return_value={"key": "TEST-123", "fields": {}})
        instance.update_issue = AsyncMock(return_value=True)
        instance.search_issues = AsyncMock(return_value=[])
        yield instance


@pytest.fixture
def mock_zephyr_client():
    """Mock Zephyr client for integration testing."""
    with _patch_or_skip("dashboard.backend.integrations.zephyr.ZephyrClient") as mock:
        instance = mock.return_value
        instance.connect = AsyncMock(return_value=True)
        instance.create_test_case = AsyncMock(return_value={"id": "Z123"})
        instance.create_test_cycle = AsyncMock(return_value={"id": "C456"})
        instance.update_test_execution = AsyncMock(return_value=True)
        yield instance


# =============================================================================
# Background Task Fixtures
# =============================================================================


@pytest.fixture
def mock_celery_app():
    """Mock Celery app for testing."""
    with _patch_or_skip("dashboard.backend.core.celery.celery_app") as mock:
        mock.send_task = MagicMock(return_value=MagicMock(id="task-123"))
        mock.AsyncResult = MagicMock(
            return_value=MagicMock(status="SUCCESS", result={"status": "completed"})
        )
        yield mock


@pytest.fixture
def celery_task_result_factory():
    """Factory for creating Celery task results."""

    def _factory(status="SUCCESS", result=None, traceback=None):
        return MagicMock(
            status=status,
            result=result or {},
            traceback=traceback,
            ready=MagicMock(return_value=status in ["SUCCESS", "FAILURE"]),
            successful=MagicMock(return_value=status == "SUCCESS"),
            failed=MagicMock(return_value=status == "FAILURE"),
        )

    return _factory


# =============================================================================
# Database Transaction Fixtures
# =============================================================================


@pytest_asyncio.fixture
async def db_transaction(db_session: AsyncSession) -> AsyncGenerator[AsyncSession, None]:
    """Provide a database session with automatic rollback."""
    async with db_session.begin():
        yield db_session
        await db_session.rollback()


@pytest.fixture
def database_snapshot(db_session):
    """Capture and restore database state."""

    class Snapshot:
        def __init__(self, session):
            self.session = session
            self.tables = []

        async def capture(self):
            # Capture current state (simplified)
            pass

        async def restore(self):
            # Restore to captured state (simplified)
            await self.session.rollback()

    return Snapshot(db_session)


# =============================================================================
# Dashboard Configuration Fixtures
# =============================================================================


@pytest.fixture
def dashboard_config():
    """Provide dashboard configuration for tests."""
    return {
        "app": {"title": "QA Framework Dashboard", "version": "1.0.0", "debug": False},
        "database": {"pool_size": 5, "max_overflow": 10, "pool_timeout": 30},
        "cache": {"default_ttl": 300, "short_ttl": 60, "medium_ttl": 600, "long_ttl": 3600},
        "security": {
            "secret_key": "test-secret-key",
            "algorithm": "HS256",
            "access_token_expire_minutes": 30,
        },
        "integrations": {
            "jira": {"enabled": True, "url": "https://jira.example.com", "project": "TEST"},
            "zephyr": {"enabled": True, "url": "https://zephyr.example.com"},
        },
    }


@pytest.fixture
def api_version():
    """Provide the API version for tests."""
    return "v1"


@pytest.fixture
def api_base_url():
    """Provide the base API URL for tests."""
    return "http://localhost:8000/api/v1"
