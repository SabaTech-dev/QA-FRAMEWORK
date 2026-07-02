"""
Unit tests for buffer flushing in the shutdown manager (Phase 4).

Covers the ShutdownManager.flush_buffers() method and its integration into
the _phase_flush_buffers() shutdown phase.
"""

import logging
from unittest.mock import AsyncMock, Mock

import pytest

from src.infrastructure.shutdown.models import ResourceType, ShutdownConfig, ShutdownPhase
from src.infrastructure.shutdown.shutdown_manager import ShutdownManager


# Fixtures


@pytest.fixture
def config():
    """Create a fast test configuration."""
    return ShutdownConfig(
        graceful_timeout=5.0,
        drain_timeout=1.0,
        resource_close_timeout=1.0,
        drain_check_interval=0.1,
        force_after_timeout=True,
        log_progress=False,
        raise_on_error=False,
    )


@pytest.fixture
def shutdown_manager(config):
    """Create an isolated ShutdownManager instance (reset singleton)."""
    ShutdownManager.reset()
    manager = ShutdownManager(config)
    yield manager
    ShutdownManager.reset()


# Tests


class TestFlushBuffers:
    """Tests for ShutdownManager.flush_buffers()."""

    @pytest.mark.asyncio
    async def test_resources_with_flush_are_flushed(self, shutdown_manager):
        """Resources exposing a flush() method should be flushed."""
        flushable = Mock()
        flushable.flush = Mock()

        shutdown_manager.register_resource(
            name="buffer_a",
            resource_type=ResourceType.CUSTOM,
            instance=flushable,
        )

        count = await shutdown_manager.flush_buffers()

        assert count == 1
        assert flushable.flush.called

    @pytest.mark.asyncio
    async def test_resources_without_flush_are_skipped(self, shutdown_manager):
        """Resources without a flush() method must be skipped gracefully."""
        # spec=[] => Mock that does NOT auto-create attributes, so no flush().
        no_flush = Mock(spec=[])

        flushable = Mock()
        flushable.flush = Mock()

        shutdown_manager.register_resource(
            name="no_flush",
            resource_type=ResourceType.CUSTOM,
            instance=no_flush,
        )
        shutdown_manager.register_resource(
            name="flushable",
            resource_type=ResourceType.CUSTOM,
            instance=flushable,
        )

        count = await shutdown_manager.flush_buffers()

        # Only the flushable resource counts.
        assert count == 1
        assert flushable.flush.called

    @pytest.mark.asyncio
    async def test_flush_errors_are_caught_and_logged(self, shutdown_manager, caplog):
        """flush() errors must be caught, logged and not stop the shutdown."""
        failing = Mock()
        failing.flush = Mock(side_effect=RuntimeError("flush boom"))

        ok = Mock()
        ok.flush = Mock()

        shutdown_manager.register_resource(
            name="failing",
            resource_type=ResourceType.CUSTOM,
            instance=failing,
        )
        shutdown_manager.register_resource(
            name="ok",
            resource_type=ResourceType.CUSTOM,
            instance=ok,
        )

        with caplog.at_level(
            logging.ERROR,
            logger="src.infrastructure.shutdown.shutdown_manager",
        ):
            count = await shutdown_manager.flush_buffers()

        # The failing resource did not count, but the ok one still flushed.
        assert count == 1
        assert ok.flush.called

        # Error was logged.
        assert any("flush boom" in record.message for record in caplog.records)

        # No exception propagated: recorded as a warning in progress.
        assert any("failing" in w for w in shutdown_manager._progress.warnings)

    @pytest.mark.asyncio
    async def test_empty_resources_list(self, shutdown_manager):
        """Flushing with no registered resources returns 0 and does not raise."""
        count = await shutdown_manager.flush_buffers()

        assert count == 0
        assert shutdown_manager._progress.warnings == []

    @pytest.mark.asyncio
    async def test_async_flush_is_awaited(self, shutdown_manager):
        """Async flush() coroutines should be awaited correctly."""
        async_flushable = Mock()
        async_flushable.flush = AsyncMock()

        shutdown_manager.register_resource(
            name="async_buffer",
            resource_type=ResourceType.CUSTOM,
            instance=async_flushable,
        )

        count = await shutdown_manager.flush_buffers()

        assert count == 1
        assert async_flushable.flush.called

    @pytest.mark.asyncio
    async def test_non_callable_flush_attribute_is_skipped(self, shutdown_manager):
        """A non-callable `flush` attribute must be skipped gracefully."""
        weird = Mock()
        weird.flush = "not-a-method"  # attribute exists but is not callable

        flushable = Mock()
        flushable.flush = Mock()

        shutdown_manager.register_resource(
            name="weird",
            resource_type=ResourceType.CUSTOM,
            instance=weird,
        )
        shutdown_manager.register_resource(
            name="flushable",
            resource_type=ResourceType.CUSTOM,
            instance=flushable,
        )

        count = await shutdown_manager.flush_buffers()

        assert count == 1


class TestFlushBuffersPhaseIntegration:
    """Tests for the integration of flush_buffers() into the Phase 4 method."""

    @pytest.mark.asyncio
    async def test_phase_flush_buffers_sets_phase_and_logs(self, shutdown_manager, caplog):
        """Phase 4 must set the FLUSHING_BUFFERS phase and delegate to flush_buffers()."""
        flushable = Mock()
        flushable.flush = Mock()

        shutdown_manager.register_resource(
            name="buffer",
            resource_type=ResourceType.CUSTOM,
            instance=flushable,
        )

        with caplog.at_level(
            logging.INFO,
            logger="src.infrastructure.shutdown.shutdown_manager",
        ):
            await shutdown_manager._phase_flush_buffers()

        assert shutdown_manager._progress.phase == ShutdownPhase.FLUSHING_BUFFERS
        assert flushable.flush.called
        assert any("Flushing buffers" in r.message for r in caplog.records)

    @pytest.mark.asyncio
    async def test_full_shutdown_invokes_flush(self, shutdown_manager):
        """A complete shutdown must flush buffers of registered resources."""
        flushable = Mock()
        flushable.flush = Mock()
        # Provide a close method so Phase 3 doesn't warn.
        flushable.close = Mock()

        shutdown_manager.register_resource(
            name="buffer",
            resource_type=ResourceType.CUSTOM,
            instance=flushable,
            close_handler="close",
        )

        result = await shutdown_manager.shutdown(reason="flush integration")

        assert result.success
        assert flushable.flush.called


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
