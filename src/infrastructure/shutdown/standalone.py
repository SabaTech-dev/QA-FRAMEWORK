"""
Standalone usage helpers for graceful shutdown

This module provides utilities for using the shutdown manager
in standalone applications (not FastAPI).
"""

import asyncio
from contextlib import contextmanager
from typing import Any, Callable, Optional

from src.infrastructure.logger.logger import QALogger
from src.infrastructure.shutdown.models import ResourceType, ShutdownConfig
from src.infrastructure.shutdown.shutdown_manager import ShutdownManager, shutdown_manager

logger = QALogger.get_logger(__name__)


class StandaloneShutdown:
    """
    Wrapper for standalone applications.

    Provides simple interface for non-FastAPI applications.

    Example:
        from src.infrastructure.shutdown.standalone import StandaloneShutdown

        # Create shutdown handler
        shutdown = StandaloneShutdown()
        shutdown.setup()

        # Register resources
        shutdown.register_database(engine)
        shutdown.register_redis(redis_client)

        # Main application loop
        while not shutdown.is_shutting_down():
            # Do work
            await process_request()

        # Cleanup
        await shutdown.wait_and_cleanup()
    """

    def __init__(self, config: Optional[ShutdownConfig] = None):
        self.manager = ShutdownManager(config)
        self._cleanup_done = False

    def setup(self, install_signal_handlers: bool = True) -> None:
        """
        Setup shutdown handling.

        Args:
            install_signal_handlers: Whether to install signal handlers
        """
        if install_signal_handlers:
            self.manager.setup_signal_handlers()

        logger.info("Standalone shutdown handler setup complete")

    def register_database(self, engine: Any, priority: int = 100) -> None:
        """Register database engine for shutdown"""
        self.manager.register_resource(
            name="database",
            resource_type=ResourceType.DATABASE,
            instance=engine,
            close_handler="dispose",
            priority=priority,
        )
        logger.info("Database registered for shutdown")

    def register_redis(self, client: Any, priority: int = 90) -> None:
        """Register Redis client for shutdown"""
        self.manager.register_resource(
            name="redis",
            resource_type=ResourceType.REDIS,
            instance=client,
            close_handler="close",
            priority=priority,
        )
        logger.info("Redis registered for shutdown")

    def register_resource(
        self,
        name: str,
        instance: Any,
        resource_type: ResourceType = ResourceType.CUSTOM,
        close_handler: Optional[str] = None,
        priority: int = 100,
    ) -> None:
        """
        Register a custom resource for shutdown.

        Args:
            name: Resource name
            instance: Resource instance
            resource_type: Type of resource
            close_handler: Method name to call for closing
            priority: Shutdown priority (lower = closed first)
        """
        self.manager.register_resource(
            name=name,
            resource_type=resource_type,
            instance=instance,
            close_handler=close_handler,
            priority=priority,
        )
        logger.info(f"Custom resource registered: name={name}")

    def is_shutting_down(self) -> bool:
        """Check if shutdown is in progress"""
        return self.manager.is_shutting_down()

    def should_stop(self) -> bool:
        """Alias for is_shutting_down() for clarity"""
        return self.is_shutting_down()

    async def wait_and_cleanup(
        self, timeout: Optional[float] = None, reason: str = "Application shutdown"
    ) -> None:
        """
        Wait for shutdown signal and cleanup.

        This is typically called at the end of your application.

        Args:
            timeout: Maximum time to wait for shutdown
            reason: Reason for shutdown
        """
        if self._cleanup_done:
            return

        # Wait for shutdown to be triggered
        if not self.is_shutting_down():
            logger.info("Waiting for shutdown signal...")
            await self.manager.wait_for_shutdown(timeout=timeout)

        # Execute shutdown
        await self.manager.shutdown(reason=reason)

        self._cleanup_done = True
        logger.info("Standalone application cleanup complete")

    async def trigger_shutdown(self, reason: str = "Manual trigger") -> None:
        """
        Manually trigger shutdown.

        Args:
            reason: Reason for shutdown
        """
        logger.info(f"Shutdown triggered manually: reason={reason}")
        await self.manager.shutdown(reason=reason)
        self._cleanup_done = True


@contextmanager
def shutdown_context(setup_signals: bool = True, manager: Optional[ShutdownManager] = None):
    """
    Context manager for shutdown handling.

    Automatically sets up signal handlers and ensures cleanup.

    Example:
        from src.infrastructure.shutdown.standalone import shutdown_context

        with shutdown_context() as shutdown:
            shutdown.register_database(engine)

            while not shutdown.is_shutting_down():
                # Do work
                pass

        # Cleanup happens automatically
    """
    manager = manager or shutdown_manager
    shutdown = StandaloneShutdown()
    shutdown.manager = manager

    try:
        shutdown.setup(install_signal_handlers=setup_signals)
        yield shutdown
    finally:
        # Ensure cleanup on exit
        if not shutdown._cleanup_done:
            logger.info("Context manager ensuring cleanup")
            # Run cleanup in event loop if one exists
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(manager.shutdown(reason="Context exit"))
                else:
                    loop.run_until_complete(manager.shutdown(reason="Context exit"))
            except RuntimeError:
                # No event loop, create one for cleanup
                asyncio.run(manager.shutdown(reason="Context exit"))

        shutdown._cleanup_done = True


class BackgroundTaskManager:
    """
    Manager for background tasks with graceful shutdown support.

    Example:
        from src.infrastructure.shutdown.standalone import BackgroundTaskManager

        task_manager = BackgroundTaskManager()

        # Start background tasks
        task_manager.start_task("worker1", worker_func)
        task_manager.start_task("worker2", another_worker)

        # When shutting down
        await task_manager.stop_all(timeout=10.0)
    """

    def __init__(self):
        self._tasks: dict[str, asyncio.Task] = {}
        self._lock = asyncio.Lock()

    async def start_task(
        self, name: str, coro_factory: Callable[[], Any], restart_on_failure: bool = False
    ) -> None:
        """
        Start a background task.

        Args:
            name: Task name
            coro_factory: Function that creates the coroutine
            restart_on_failure: Whether to restart task on failure
        """
        async with self._lock:
            if name in self._tasks and not self._tasks[name].done():
                logger.warning(f"Task already running: name={name}")
                return

            async def wrapper():
                while True:
                    try:
                        await coro_factory()
                        break  # Task completed normally
                    except asyncio.CancelledError:
                        logger.info(f"Task cancelled: name={name}")
                        break
                    except Exception as e:
                        logger.error(f"Task failed: name={name}, error={str(e)}")
                        if not restart_on_failure:
                            raise
                        logger.info(f"Restarting task: name={name}")
                        await asyncio.sleep(1)

            task = asyncio.create_task(wrapper())
            self._tasks[name] = task

            logger.info(f"Background task started: name={name}")

    async def stop_task(self, name: str, timeout: float = 5.0) -> bool:
        """
        Stop a specific task.

        Args:
            name: Task name
            timeout: Maximum time to wait for task to stop

        Returns:
            True if task stopped successfully
        """
        async with self._lock:
            task = self._tasks.get(name)
            if not task:
                return True

            if task.done():
                return True

            task.cancel()

            try:
                await asyncio.wait_for(task, timeout=timeout)
                return True
            except asyncio.TimeoutError:
                logger.warning(f"Task stop timeout: name={name}, timeout={timeout}")
                return False
            except asyncio.CancelledError:
                return True

    async def stop_all(self, timeout: float = 10.0) -> None:
        """
        Stop all background tasks.

        Args:
            timeout: Maximum time to wait per task
        """
        logger.info(f"Stopping all background tasks: count={len(self._tasks)}")

        for name in list(self._tasks.keys()):
            await self.stop_task(name, timeout=timeout)

        self._tasks.clear()
        logger.info("All background tasks stopped")


def create_shutdown_decorator(manager: Optional[ShutdownManager] = None):
    """
    Create a decorator for functions that should be aware of shutdown.

    Example:
        from src.infrastructure.shutdown.standalone import create_shutdown_decorator

        shutdown_aware = create_shutdown_decorator()

        @shutdown_aware
        async def long_running_task():
            # Check if shutdown is requested
            if shutdown_aware.is_shutting_down():
                return
            # Do work
    """
    manager = manager or shutdown_manager

    def decorator(func):
        async def wrapper(*args, **kwargs):
            if manager.is_shutting_down():
                logger.info(f"Skipping function - shutdown in progress: function={func.__name__}")
                return None

            try:
                return await func(*args, **kwargs)
            except asyncio.CancelledError:
                logger.info(f"Function cancelled during shutdown: function={func.__name__}")
                raise

        # Add shutdown check method
        wrapper.is_shutting_down = manager.is_shutting_down

        return wrapper

    return decorator


# Convenience functions for common patterns


async def run_with_shutdown(
    coro: Any, manager: Optional[ShutdownManager] = None, shutdown_timeout: float = 30.0
) -> Any:
    """
    Run a coroutine with shutdown handling.

    If shutdown is triggered while the coroutine is running,
    it will be cancelled and cleanup will be performed.

    Args:
        coro: Coroutine to run
        manager: ShutdownManager instance
        shutdown_timeout: Timeout for cleanup

    Returns:
        Result of the coroutine

    Raises:
        asyncio.CancelledError: If shutdown was triggered
    """
    manager = manager or shutdown_manager

    try:
        return await coro
    except asyncio.CancelledError:
        logger.info("Coroutine cancelled - performing cleanup")
        await manager.shutdown(reason="Coroutine cancelled", timeout=shutdown_timeout)
        raise


def install_signal_handler(callback: Callable[[], None]) -> None:
    """
    Install a simple signal handler for non-async applications.

    Args:
        callback: Function to call when shutdown signal is received

    Example:
        from src.infrastructure.shutdown.standalone import install_signal_handler

        def on_shutdown():
            print("Shutting down...")
            # Cleanup

        install_signal_handler(on_shutdown)
    """
    import signal

    def handler(signum, frame):
        logger.info(f"Received shutdown signal: signal={signum}")
        callback()

    signal.signal(signal.SIGTERM, handler)
    signal.signal(signal.SIGINT, handler)

    logger.info("Signal handlers installed")
