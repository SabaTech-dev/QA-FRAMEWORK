"""
Unit tests for graceful shutdown functionality
"""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock

import pytest

from src.infrastructure.shutdown.connection_tracker import ConnectionTracker
from src.infrastructure.shutdown.models import (
    ConnectionInfo,
    ResourceType,
    ShutdownConfig,
    ShutdownPhase,
    ShutdownProgress,
    ShutdownStatus,
)
from src.infrastructure.shutdown.shutdown_manager import ShutdownManager
from src.infrastructure.shutdown.standalone import BackgroundTaskManager, StandaloneShutdown

# Fixtures


@pytest.fixture
def config():
    """Create test configuration"""
    return ShutdownConfig(
        graceful_timeout=5.0,
        drain_timeout=2.0,
        resource_close_timeout=1.0,
        drain_check_interval=0.1,
        force_after_timeout=True,
        log_progress=False,
        raise_on_error=False,
    )


@pytest.fixture
def connection_tracker(config):
    """Create connection tracker instance"""
    return ConnectionTracker(config)


@pytest.fixture
def shutdown_manager(config):
    """Create shutdown manager instance"""
    # Reset singleton before each test
    ShutdownManager.reset()
    manager = ShutdownManager(config)
    yield manager
    # Cleanup after test
    ShutdownManager.reset()


# ConnectionInfo Tests


class TestConnectionInfo:
    """Tests for ConnectionInfo model"""

    def test_create_connection_info(self):
        """Test creating connection info"""
        info = ConnectionInfo(
            connection_id="conn_123",
            resource_type=ResourceType.DATABASE,
            created_at=datetime.now(),
            metadata={"host": "localhost"},
            request_count=5,
        )

        assert info.connection_id == "conn_123"
        assert info.resource_type == ResourceType.DATABASE
        assert info.is_active is True
        assert info.request_count == 5

    def test_connection_info_defaults(self):
        """Test connection info default values"""
        info = ConnectionInfo(
            connection_id="conn_456", resource_type=ResourceType.REDIS, created_at=datetime.now()
        )

        assert info.metadata == {}
        assert info.request_count == 0
        assert info.is_active is True


# ShutdownProgress Tests


class TestShutdownProgress:
    """Tests for ShutdownProgress model"""

    def test_duration_seconds_no_start(self):
        """Test duration when not started"""
        progress = ShutdownProgress()
        assert progress.duration_seconds is None

    def test_duration_seconds_in_progress(self):
        """Test duration while in progress"""
        progress = ShutdownProgress(
            phase=ShutdownPhase.DRAINING_CONNECTIONS,
            started_at=datetime.now() - timedelta(seconds=5),
        )

        duration = progress.duration_seconds
        assert duration is not None
        assert 4.9 <= duration <= 5.1

    def test_duration_seconds_completed(self):
        """Test duration when completed"""
        progress = ShutdownProgress(
            phase=ShutdownPhase.COMPLETED,
            started_at=datetime.now() - timedelta(seconds=10),
            completed_at=datetime.now(),
        )

        duration = progress.duration_seconds
        assert duration is not None
        assert 9.9 <= duration <= 10.1

    def test_is_complete(self):
        """Test is_complete property"""
        progress = ShutdownProgress(phase=ShutdownPhase.NONE)
        assert not progress.is_complete

        progress.phase = ShutdownPhase.INITIATED
        assert not progress.is_complete

        progress.phase = ShutdownPhase.COMPLETED
        assert progress.is_complete

        progress.phase = ShutdownPhase.FORCED
        assert progress.is_complete


# ConnectionTracker Tests


class TestConnectionTracker:
    """Tests for ConnectionTracker"""

    @pytest.mark.asyncio
    async def test_register_connection(self, connection_tracker):
        """Test registering a connection"""
        conn_id = await connection_tracker.register_connection(
            resource_type=ResourceType.DATABASE, metadata={"host": "localhost"}
        )

        assert conn_id is not None
        assert conn_id.startswith("database_")

        stats = connection_tracker.get_stats()
        assert stats["total_connections"] == 1
        assert stats["active_connections"] == 1

    @pytest.mark.asyncio
    async def test_register_connection_custom_id(self, connection_tracker):
        """Test registering connection with custom ID"""
        conn_id = await connection_tracker.register_connection(
            resource_type=ResourceType.REDIS, connection_id="custom_conn_123"
        )

        assert conn_id == "custom_conn_123"

    @pytest.mark.asyncio
    async def test_register_connection_when_shutting_down(self, connection_tracker):
        """Test that registration fails during shutdown"""
        connection_tracker.stop_accepting_new()

        with pytest.raises(RuntimeError, match="Not accepting new connections"):
            await connection_tracker.register_connection(resource_type=ResourceType.DATABASE)

    @pytest.mark.asyncio
    async def test_deregister_connection(self, connection_tracker):
        """Test deregistering a connection"""
        conn_id = await connection_tracker.register_connection(resource_type=ResourceType.DATABASE)

        result = await connection_tracker.deregister_connection(conn_id)
        assert result is True

        stats = connection_tracker.get_stats()
        assert stats["total_connections"] == 0

    @pytest.mark.asyncio
    async def test_deregister_unknown_connection(self, connection_tracker):
        """Test deregistering non-existent connection"""
        result = await connection_tracker.deregister_connection("unknown_id")
        assert result is False

    @pytest.mark.asyncio
    async def test_request_tracking(self, connection_tracker):
        """Test tracking requests on a connection"""
        conn_id = await connection_tracker.register_connection(
            resource_type=ResourceType.HTTP_CLIENT
        )

        # Start requests
        await connection_tracker.start_request(conn_id)
        await connection_tracker.start_request(conn_id)
        await connection_tracker.start_request(conn_id)

        in_flight = await connection_tracker.get_in_flight_requests_count()
        assert in_flight == 3

        # End requests
        await connection_tracker.end_request(conn_id)
        await connection_tracker.end_request(conn_id)

        in_flight = await connection_tracker.get_in_flight_requests_count()
        assert in_flight == 1

    @pytest.mark.asyncio
    async def test_request_tracking_unknown_connection(self, connection_tracker):
        """Test tracking requests on unknown connection"""
        result = await connection_tracker.start_request("unknown")
        assert result is False

        result = await connection_tracker.end_request("unknown")
        assert result is False

    @pytest.mark.asyncio
    async def test_get_connections_by_type(self, connection_tracker):
        """Test getting connections by type"""
        await connection_tracker.register_connection(ResourceType.DATABASE)
        await connection_tracker.register_connection(ResourceType.DATABASE)
        await connection_tracker.register_connection(ResourceType.REDIS)

        db_conns = await connection_tracker.get_connections_by_type(ResourceType.DATABASE)
        assert len(db_conns) == 2

        redis_conns = await connection_tracker.get_connections_by_type(ResourceType.REDIS)
        assert len(redis_conns) == 1

        http_conns = await connection_tracker.get_connections_by_type(ResourceType.HTTP_CLIENT)
        assert len(http_conns) == 0

    @pytest.mark.asyncio
    async def test_drain_connections_immediate(self, connection_tracker):
        """Test draining connections with no active requests"""
        await connection_tracker.register_connection(ResourceType.DATABASE)
        await connection_tracker.register_connection(ResourceType.REDIS)

        result = await connection_tracker.drain_connections(timeout=1.0)

        assert result["drained_connections"] == 2
        assert result["remaining_requests"] == 0
        assert connection_tracker.is_accepting_new() is False

    @pytest.mark.asyncio
    async def test_drain_connections_with_timeout(self, connection_tracker):
        """Test draining connections with timeout"""
        conn_id = await connection_tracker.register_connection(ResourceType.HTTP_CLIENT)
        await connection_tracker.start_request(conn_id)

        result = await connection_tracker.drain_connections(timeout=0.5)

        # Should timeout since request is still in flight
        assert result["remaining_requests"] == 1
        assert connection_tracker.is_accepting_new() is False

    @pytest.mark.asyncio
    async def test_force_close_all(self, connection_tracker):
        """Test force closing all connections"""
        await connection_tracker.register_connection(ResourceType.DATABASE)
        await connection_tracker.register_connection(ResourceType.REDIS)
        await connection_tracker.register_connection(ResourceType.HTTP_CLIENT)

        count = await connection_tracker.force_close_all()
        assert count == 3

        stats = connection_tracker.get_stats()
        assert stats["total_connections"] == 0


# ShutdownManager Tests


class TestShutdownManager:
    """Tests for ShutdownManager"""

    def test_singleton_pattern(self, config):
        """Test that ShutdownManager follows singleton pattern"""
        ShutdownManager.reset()

        manager1 = ShutdownManager(config)
        manager2 = ShutdownManager(config)

        assert manager1 is manager2

        ShutdownManager.reset()

    def test_register_resource(self, shutdown_manager):
        """Test registering a resource"""
        mock_db = Mock()
        mock_db.close = Mock()

        shutdown_manager.register_resource(
            name="database",
            resource_type=ResourceType.DATABASE,
            instance=mock_db,
            close_handler="close",
            priority=100,
        )

        assert "database" in shutdown_manager._resources
        assert len(shutdown_manager._resources) == 1

    def test_unregister_resource(self, shutdown_manager):
        """Test unregistering a resource"""
        mock_db = Mock()

        shutdown_manager.register_resource(
            name="database", resource_type=ResourceType.DATABASE, instance=mock_db
        )

        result = shutdown_manager.unregister_resource("database")
        assert result is True
        assert "database" not in shutdown_manager._resources

    def test_unregister_unknown_resource(self, shutdown_manager):
        """Test unregistering non-existent resource"""
        result = shutdown_manager.unregister_resource("unknown")
        assert result is False

    def test_resource_priority_sorting(self, shutdown_manager):
        """Test that resources are sorted by priority"""
        mock1 = Mock()
        mock2 = Mock()
        mock3 = Mock()

        shutdown_manager.register_resource("redis", ResourceType.REDIS, mock2, priority=90)
        shutdown_manager.register_resource("db", ResourceType.DATABASE, mock1, priority=100)
        shutdown_manager.register_resource("http", ResourceType.HTTP_CLIENT, mock3, priority=80)

        # Should be sorted: http (80), redis (90), db (100)
        assert shutdown_manager._resources_by_priority == ["http", "redis", "db"]

    def test_add_hooks(self, shutdown_manager):
        """Test adding shutdown hooks"""
        pre_hook = Mock()
        post_hook = Mock()

        shutdown_manager.add_pre_shutdown_hook(pre_hook)
        shutdown_manager.add_post_shutdown_hook(post_hook)

        assert pre_hook in shutdown_manager._pre_shutdown_hooks
        assert post_hook in shutdown_manager._post_shutdown_hooks

    @pytest.mark.asyncio
    async def test_shutdown_basic(self, shutdown_manager):
        """Test basic shutdown flow"""
        mock_db = Mock()
        mock_db.close = Mock()

        shutdown_manager.register_resource(
            name="database",
            resource_type=ResourceType.DATABASE,
            instance=mock_db,
            close_handler="close",
        )

        result = await shutdown_manager.shutdown(reason="Test shutdown")

        assert result.status == ShutdownStatus.SUCCESSFUL
        assert result.progress.phase == ShutdownPhase.COMPLETED
        assert mock_db.close.called

    @pytest.mark.asyncio
    async def test_shutdown_with_async_close(self, shutdown_manager):
        """Test shutdown with async close method"""
        mock_db = Mock()
        mock_db.close = AsyncMock()

        shutdown_manager.register_resource(
            name="database",
            resource_type=ResourceType.DATABASE,
            instance=mock_db,
            close_handler="close",
        )

        result = await shutdown_manager.shutdown(reason="Test shutdown")

        assert result.status == ShutdownStatus.SUCCESSFUL
        assert mock_db.close.called

    @pytest.mark.asyncio
    async def test_shutdown_auto_detect_close_method(self, shutdown_manager):
        """Test automatic detection of close method"""
        mock_resource = Mock()
        mock_resource.dispose = Mock()

        shutdown_manager.register_resource(
            name="resource",
            resource_type=ResourceType.CUSTOM,
            instance=mock_resource,
            close_handler="dispose",
        )

        result = await shutdown_manager.shutdown(reason="Test shutdown")

        assert result.status == ShutdownStatus.SUCCESSFUL
        assert mock_resource.dispose.called

    @pytest.mark.asyncio
    async def test_shutdown_with_error(self, shutdown_manager):
        """Test shutdown with error in close method"""
        mock_db = Mock()
        mock_db.close = Mock(side_effect=Exception("Close failed"))

        shutdown_manager.register_resource(
            name="database",
            resource_type=ResourceType.DATABASE,
            instance=mock_db,
            close_handler="close",
        )

        result = await shutdown_manager.shutdown(reason="Test shutdown")

        assert result.status == ShutdownStatus.SUCCESSFUL  # Still successful even with errors
        assert len(result.progress.errors) > 0
        assert "Close failed" in result.progress.errors[0]

    @pytest.mark.asyncio
    async def test_shutdown_already_in_progress(self, shutdown_manager):
        """Test calling shutdown when already in progress"""
        # Start first shutdown
        task1 = asyncio.create_task(shutdown_manager.shutdown(reason="First"))

        # Give it a moment to start
        await asyncio.sleep(0.1)

        # Try second shutdown
        result = await shutdown_manager.shutdown(reason="Second")

        assert result.status == ShutdownStatus.IN_PROGRESS
        assert "already in progress" in result.message

        # Wait for first to complete
        await task1

    @pytest.mark.asyncio
    async def test_shutdown_with_hooks(self, shutdown_manager):
        """Test shutdown with pre and post hooks"""
        pre_hook = Mock()
        post_hook = Mock()

        shutdown_manager.add_pre_shutdown_hook(pre_hook)
        shutdown_manager.add_post_shutdown_hook(post_hook)

        await shutdown_manager.shutdown(reason="Test shutdown")

        assert pre_hook.called
        assert post_hook.called

    @pytest.mark.asyncio
    async def test_shutdown_connection_draining(self, shutdown_manager):
        """Test that connections are drained during shutdown"""
        # Register a connection
        _conn_id = await shutdown_manager.connection_tracker.register_connection(
            resource_type=ResourceType.DATABASE
        )

        result = await shutdown_manager.shutdown(reason="Test shutdown")

        assert result.status == ShutdownStatus.SUCCESSFUL
        assert result.progress.drained_connections == 1

    @pytest.mark.asyncio
    async def test_is_shutting_down(self, shutdown_manager):
        """Test is_shutting_down flag"""
        assert not shutdown_manager.is_shutting_down()

        # Start shutdown in background
        task = asyncio.create_task(shutdown_manager.shutdown(reason="Test", timeout=0.1))

        # Give it a moment
        await asyncio.sleep(0.05)

        assert shutdown_manager.is_shutting_down()

        # Wait for completion
        await task


# StandaloneShutdown Tests


class TestStandaloneShutdown:
    """Tests for StandaloneShutdown wrapper"""

    def test_setup(self):
        """Test setup method"""
        shutdown = StandaloneShutdown()
        shutdown.setup(install_signal_handlers=False)

        # Should not raise
        assert shutdown.manager is not None

    def test_register_database(self):
        """Test registering database"""
        shutdown = StandaloneShutdown()
        mock_db = Mock()

        shutdown.register_database(mock_db)

        assert "database" in shutdown.manager._resources

    def test_register_redis(self):
        """Test registering redis"""
        shutdown = StandaloneShutdown()
        mock_redis = Mock()

        shutdown.register_redis(mock_redis)

        assert "redis" in shutdown.manager._resources

    @pytest.mark.asyncio
    async def test_is_shutting_down(self):
        """Test is_shutting_down method"""
        shutdown = StandaloneShutdown()
        assert not shutdown.is_shutting_down()

    @pytest.mark.asyncio
    async def test_trigger_shutdown(self):
        """Test manually triggering shutdown"""
        shutdown = StandaloneShutdown()

        await shutdown.trigger_shutdown(reason="Test")

        assert shutdown._cleanup_done
        assert shutdown.manager.is_shutting_down()


# BackgroundTaskManager Tests


class TestBackgroundTaskManager:
    """Tests for BackgroundTaskManager"""

    @pytest.mark.asyncio
    async def test_start_task(self):
        """Test starting a background task"""
        manager = BackgroundTaskManager()

        async def task_func():
            await asyncio.sleep(0.1)
            return "done"

        await manager.start_task("test_task", lambda: task_func())

        assert "test_task" in manager._tasks
        assert not manager._tasks["test_task"].done()

        # Wait for completion
        await asyncio.sleep(0.2)
        assert manager._tasks["test_task"].done()

    @pytest.mark.asyncio
    async def test_stop_task(self):
        """Test stopping a task"""
        manager = BackgroundTaskManager()

        async def long_task():
            await asyncio.sleep(10)

        await manager.start_task("long_task", lambda: long_task())

        result = await manager.stop_task("long_task", timeout=0.5)

        assert result is True
        assert manager._tasks["long_task"].done()

    @pytest.mark.asyncio
    async def test_stop_all(self):
        """Test stopping all tasks"""
        manager = BackgroundTaskManager()

        async def task_func():
            await asyncio.sleep(10)

        await manager.start_task("task1", lambda: task_func())
        await manager.start_task("task2", lambda: task_func())
        await manager.start_task("task3", lambda: task_func())

        await manager.stop_all(timeout=0.5)

        assert len(manager._tasks) == 0


# Integration Tests


class TestIntegration:
    """Integration tests for shutdown system"""

    @pytest.mark.asyncio
    async def test_full_shutdown_flow(self, shutdown_manager):
        """Test complete shutdown flow with multiple resources"""
        # Create mock resources
        mock_db = Mock()
        mock_db.dispose = AsyncMock()

        mock_redis = Mock()
        mock_redis.close = Mock()

        # Register resources
        shutdown_manager.register_resource(
            name="database",
            resource_type=ResourceType.DATABASE,
            instance=mock_db,
            close_handler="dispose",
            priority=100,
        )

        shutdown_manager.register_resource(
            name="redis",
            resource_type=ResourceType.REDIS,
            instance=mock_redis,
            close_handler="close",
            priority=90,
        )

        # Register connections
        await shutdown_manager.connection_tracker.register_connection(
            resource_type=ResourceType.DATABASE
        )

        # Execute shutdown
        result = await shutdown_manager.shutdown(reason="Integration test")

        # Verify
        assert result.status == ShutdownStatus.SUCCESSFUL
        assert result.progress.phase == ShutdownPhase.COMPLETED
        assert result.progress.closed_resources == 2
        assert result.progress.drained_connections == 1

        # Verify close methods called in order (redis first, then db)
        assert mock_redis.close.called
        assert mock_db.dispose.called

    @pytest.mark.asyncio
    async def test_shutdown_with_active_requests(self, shutdown_manager):
        """Test shutdown with active in-flight requests"""
        # Register connection with active request
        conn_id = await shutdown_manager.connection_tracker.register_connection(
            resource_type=ResourceType.HTTP_CLIENT
        )
        await shutdown_manager.connection_tracker.start_request(conn_id)

        # Start shutdown in background
        task = asyncio.create_task(shutdown_manager.shutdown(reason="Test with requests"))

        # Wait for draining to start
        await asyncio.sleep(0.2)

        # Complete the request
        await shutdown_manager.connection_tracker.end_request(conn_id)

        # Wait for shutdown to complete
        result = await task

        assert result.status == ShutdownStatus.SUCCESSFUL


# Edge Cases


class TestEdgeCases:
    """Tests for edge cases and error conditions"""

    @pytest.mark.asyncio
    async def test_shutdown_no_resources(self, shutdown_manager):
        """Test shutdown with no registered resources"""
        result = await shutdown_manager.shutdown(reason="No resources")

        assert result.status == ShutdownStatus.SUCCESSFUL
        assert result.progress.total_resources == 0

    @pytest.mark.asyncio
    async def test_shutdown_resource_no_close_method(self, shutdown_manager):
        """Test shutdown with resource that has no close method"""
        mock_resource = Mock(spec=[])  # No methods

        shutdown_manager.register_resource(
            name="no_close", resource_type=ResourceType.CUSTOM, instance=mock_resource
        )

        result = await shutdown_manager.shutdown(reason="No close method")

        # Should complete but not close the resource
        assert result.status == ShutdownStatus.SUCCESSFUL
        assert result.progress.closed_resources == 0

    @pytest.mark.asyncio
    async def test_shutdown_with_timeout(self, config):
        """Test shutdown timeout behavior"""
        config.graceful_timeout = 0.5
        config.drain_timeout = 1.0  # Longer than graceful timeout

        ShutdownManager.reset()
        shutdown_manager = ShutdownManager(config)

        # Register connection with active request
        conn_id = await shutdown_manager.connection_tracker.register_connection(
            resource_type=ResourceType.HTTP_CLIENT
        )
        await shutdown_manager.connection_tracker.start_request(conn_id)

        # Shutdown should timeout
        result = await shutdown_manager.shutdown(reason="Timeout test")

        # Shutdown completes successfully but with warnings about in-flight requests
        assert result.status == ShutdownStatus.SUCCESSFUL
        assert result.progress.warnings  # Should have warnings about in-flight requests


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
