"""
Tests for FastAPI shutdown integration
"""

import asyncio
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.infrastructure.shutdown import (
    ResourceType,
    ShutdownManager,
    ShutdownMiddleware,
    register_database_connection,
    register_redis_connection,
    setup_fastapi_shutdown,
)
from src.infrastructure.shutdown.fastapi_integration import RequestTracker, get_request_tracker

# Fixtures


@pytest.fixture
def shutdown_manager():
    """Create fresh shutdown manager for each test"""
    ShutdownManager.reset()
    manager = ShutdownManager()
    yield manager
    ShutdownManager.reset()


@pytest.fixture
def app_with_shutdown(shutdown_manager):
    """Create FastAPI app with shutdown middleware"""
    app = FastAPI()

    # Add shutdown middleware
    app.add_middleware(ShutdownMiddleware, manager=shutdown_manager)

    @app.get("/test")
    async def test_endpoint():
        return {"status": "ok"}

    @app.get("/health")
    async def health():
        return {"healthy": True}

    return app


# ShutdownMiddleware Tests


class TestShutdownMiddleware:
    """Tests for ShutdownMiddleware"""

    def test_normal_request(self, app_with_shutdown):
        """Test normal request when not shutting down"""
        client = TestClient(app_with_shutdown)

        response = client.get("/test")

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_request_during_shutdown(self, app_with_shutdown, shutdown_manager):
        """Test request rejection during shutdown"""
        # Trigger shutdown
        asyncio.run(shutdown_manager.shutdown(reason="Test shutdown"))

        client = TestClient(app_with_shutdown)
        response = client.get("/test")

        assert response.status_code == 503
        assert "shutting down" in response.json()["error"].lower()
        assert "retry-after" in response.headers

    def test_request_when_not_accepting_new(self, app_with_shutdown, shutdown_manager):
        """Test request rejection when not accepting new connections"""
        # Stop accepting new connections
        shutdown_manager.connection_tracker.stop_accepting_new()

        client = TestClient(app_with_shutdown)
        response = client.get("/test")

        assert response.status_code == 503
        assert "not accepting" in response.json()["error"].lower()

    def test_request_tracking(self, app_with_shutdown, shutdown_manager):
        """Test that requests are tracked"""
        initial_stats = shutdown_manager.connection_tracker.get_stats()
        initial_count = initial_stats["total_connections"]

        client = TestClient(app_with_shutdown)
        response = client.get("/test")

        assert response.status_code == 200

        # Connection should be tracked during request but cleaned up after
        final_stats = shutdown_manager.connection_tracker.get_stats()
        assert final_stats["total_connections"] == initial_count


# setup_fastapi_shutdown Tests


class TestSetupFastapiShutdown:
    """Tests for setup_fastapi_shutdown function"""

    def test_setup_adds_middleware(self, shutdown_manager):
        """Test that setup adds shutdown middleware"""
        app = FastAPI()

        setup_fastapi_shutdown(app, manager=shutdown_manager, setup_signal_handlers=False)

        # Check that middleware was added
        assert any(hasattr(m, "cls") and m.cls == ShutdownMiddleware for m in app.user_middleware)

    def test_setup_registers_events(self, shutdown_manager):
        """Test that setup uses lifespan pattern (modern FastAPI)"""
        # Modern FastAPI uses lifespan pattern, not on_startup/on_shutdown
        # The deprecated setup_fastapi_shutdown only adds middleware now
        # For full lifecycle management, use create_shutdown_lifespan()
        app = FastAPI()

        setup_fastapi_shutdown(app, manager=shutdown_manager, setup_signal_handlers=False)

        # Verify middleware was added (this is what the deprecated function does)
        assert len(app.user_middleware) > 0
        assert any(hasattr(m, "cls") and m.cls == ShutdownMiddleware for m in app.user_middleware)

    @pytest.mark.asyncio
    async def test_shutdown_event_triggers_manager(self, shutdown_manager):
        """Test that FastAPI shutdown event triggers shutdown manager (lifespan pattern)"""
        from contextlib import asynccontextmanager

        # Use modern lifespan pattern
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            # Startup
            shutdown_manager.setup_signal_handlers()
            yield
            # Shutdown
            await shutdown_manager.shutdown(reason="Test shutdown")

        app = FastAPI(lifespan=lifespan)

        # Trigger shutdown via lifespan
        async with lifespan(app):
            pass  # Normal operation

        # After context exits, shutdown should have been triggered
        assert shutdown_manager.is_shutting_down()


# Resource Registration Tests


class TestResourceRegistration:
    """Tests for resource registration helpers"""

    @pytest.mark.asyncio
    async def test_register_database_connection(self, shutdown_manager):
        """Test registering database connection"""
        mock_engine = Mock()
        mock_engine.dispose = Mock()

        await register_database_connection(mock_engine, manager=shutdown_manager)

        assert "database_engine" in shutdown_manager._resources
        resource = shutdown_manager._resources["database_engine"]
        assert resource.resource_type == ResourceType.DATABASE
        assert resource.close_handler == "dispose"

    @pytest.mark.asyncio
    async def test_register_database_with_session_factory(self, shutdown_manager):
        """Test registering database with session factory"""
        mock_engine = Mock()
        mock_engine.dispose = Mock()
        mock_session_factory = Mock()

        await register_database_connection(
            mock_engine, session_factory=mock_session_factory, manager=shutdown_manager
        )

        assert "database_engine" in shutdown_manager._resources

    @pytest.mark.asyncio
    async def test_register_redis_connection(self, shutdown_manager):
        """Test registering Redis connection"""
        mock_redis = Mock()
        mock_redis.close = Mock()

        await register_redis_connection(mock_redis, manager=shutdown_manager)

        assert "redis" in shutdown_manager._resources
        resource = shutdown_manager._resources["redis"]
        assert resource.resource_type == ResourceType.REDIS
        assert resource.close_handler == "close"

    @pytest.mark.asyncio
    async def test_register_redis_custom_name(self, shutdown_manager):
        """Test registering Redis with custom name"""
        mock_redis = Mock()
        mock_redis.close = Mock()

        await register_redis_connection(mock_redis, name="cache_redis", manager=shutdown_manager)

        assert "cache_redis" in shutdown_manager._resources


# RequestTracker Tests


class TestRequestTracker:
    """Tests for RequestTracker"""

    @pytest.mark.asyncio
    async def test_request_tracker_context(self, shutdown_manager):
        """Test request tracker as context manager"""
        tracker = RequestTracker(manager=shutdown_manager)

        initial_stats = shutdown_manager.connection_tracker.get_stats()
        initial_count = initial_stats["total_connections"]

        async with tracker:
            # Connection should be registered
            assert tracker.connection_id is not None

            stats = shutdown_manager.connection_tracker.get_stats()
            assert stats["total_connections"] == initial_count + 1

        # After context, connection should be cleaned up
        final_stats = shutdown_manager.connection_tracker.get_stats()
        assert final_stats["total_connections"] == initial_count

    @pytest.mark.asyncio
    async def test_request_tracker_during_shutdown(self, shutdown_manager):
        """Test request tracker during shutdown"""
        # Trigger shutdown
        await shutdown_manager.shutdown(reason="Test")

        tracker = RequestTracker(manager=shutdown_manager)

        async with tracker:
            # Should not register connection during shutdown
            assert tracker.connection_id is None

    def test_get_request_tracker_dependency(self):
        """Test FastAPI dependency for request tracker"""
        tracker = get_request_tracker()

        assert isinstance(tracker, RequestTracker)


# Integration Tests


class TestFastAPIIntegration:
    """Integration tests for FastAPI shutdown"""

    @pytest.mark.asyncio
    async def test_full_fastapi_shutdown_flow(self):
        """Test complete FastAPI shutdown flow with modern lifespan pattern"""
        from contextlib import asynccontextmanager

        ShutdownManager.reset()
        manager = ShutdownManager()

        # Create mock resources
        mock_db = Mock()
        mock_db.dispose = AsyncMock()

        mock_redis = Mock()
        mock_redis.close = Mock()

        # Create lifespan with resource registration
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            # Startup
            manager.setup_signal_handlers()
            await register_database_connection(mock_db, manager=manager)
            await register_redis_connection(mock_redis, manager=manager)
            yield
            # Shutdown
            await manager.shutdown(reason="Application shutdown")

        # Create app with lifespan
        app = FastAPI(lifespan=lifespan)

        # Add middleware
        app.add_middleware(ShutdownMiddleware, manager=manager)

        # Run the lifespan to trigger shutdown
        async with lifespan(app):
            # Normal operation phase
            assert "database_engine" in manager._resources
            assert "redis" in manager._resources

        # Verify resources were closed after lifespan exit
        assert mock_db.dispose.called
        assert mock_redis.close.called
        assert manager.is_shutting_down()

        ShutdownManager.reset()

    @pytest.mark.asyncio
    async def test_concurrent_requests_during_shutdown(self):
        """Test handling concurrent requests during shutdown"""
        ShutdownManager.reset()
        manager = ShutdownManager()

        app = FastAPI()

        # Add middleware
        app.add_middleware(ShutdownMiddleware, manager=manager)

        request_count = 0

        @app.get("/slow")
        async def slow_endpoint():
            nonlocal request_count
            request_count += 1
            await asyncio.sleep(0.2)
            return {"count": request_count}

        # Start shutdown in background
        shutdown_task = asyncio.create_task(manager.shutdown(reason="Test", timeout=0.5))

        # Wait a bit for shutdown to start
        await asyncio.sleep(0.1)

        # Try to make request (should be rejected)
        client = TestClient(app)
        response = client.get("/slow")

        assert response.status_code == 503

        # Wait for shutdown to complete
        await shutdown_task

        ShutdownManager.reset()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
