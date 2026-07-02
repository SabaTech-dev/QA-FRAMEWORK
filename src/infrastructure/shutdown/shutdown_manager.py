"""
Main Shutdown Manager for graceful shutdown of QA-FRAMEWORK services
"""

import asyncio
import signal
import sys
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Union

from src.infrastructure.shutdown.models import (
    ConnectionInfo,
    ResourceInfo,
    ResourceType,
    ShutdownConfig,
    ShutdownPhase,
    ShutdownProgress,
    ShutdownResult,
    ShutdownStatus,
)
from src.infrastructure.shutdown.connection_tracker import ConnectionTracker
from src.infrastructure.logger.logger import QALogger


logger = QALogger.get_logger(__name__)


class ShutdownManager:
    """
    Manages graceful shutdown of QA-FRAMEWORK services.
    
    Features:
    - Signal handling (SIGTERM, SIGINT)
    - Connection tracking and draining
    - Resource cleanup (DB, Redis, file handles, etc.)
    - Configurable timeouts
    - Progress logging
    - Both FastAPI and standalone usage
    
    Example:
        manager = ShutdownManager()
        
        # Register resources
        manager.register_resource("db", ResourceType.DATABASE, db_engine)
        manager.register_resource("redis", ResourceType.REDIS, redis_client)
        
        # Setup signal handlers
        manager.setup_signal_handlers()
        
        # In FastAPI:
        @app.on_event("shutdown")
        async def shutdown_event():
            await manager.shutdown()
    """
    
    _instance: Optional['ShutdownManager'] = None
    
    def __new__(cls, config: Optional[ShutdownConfig] = None):
        """Singleton pattern for global shutdown manager"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, config: Optional[ShutdownConfig] = None):
        """Initialize shutdown manager"""
        if self._initialized:
            return
        
        self.config = config or ShutdownConfig()
        self.connection_tracker = ConnectionTracker(self.config)
        
        # Resources to manage
        self._resources: Dict[str, ResourceInfo] = {}
        self._resources_by_priority: List[str] = []
        
        # Shutdown state
        self._progress = ShutdownProgress()
        self._is_shutting_down = False
        self._shutdown_complete = asyncio.Event()
        
        # Hooks
        self._pre_shutdown_hooks: List[Callable] = []
        self._post_shutdown_hooks: List[Callable] = []
        
        # Signal handlers
        self._original_handlers: Dict[signal.Signals, Any] = {}
        self._signal_handlers_installed = False
        
        self._initialized = True
        
        logger.info("Shutdown manager initialized")
    
    @classmethod
    def reset(cls):
        """Reset singleton instance (useful for testing)"""
        if cls._instance is not None:
            cls._instance = None
    
    def register_resource(
        self,
        name: str,
        resource_type: ResourceType,
        instance: Any,
        close_handler: Optional[str] = None,
        priority: int = 100,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Register a resource to be closed during shutdown.
        
        Args:
            name: Unique name for the resource
            resource_type: Type of resource
            instance: The resource instance (e.g., database engine, redis client)
            close_handler: Name of method to call for closing (e.g., "close", "disconnect")
                          If None, will try common methods: close, disconnect, shutdown
            priority: Priority for closing (lower = closed first)
            metadata: Optional metadata
        """
        resource_info = ResourceInfo(
            name=name,
            resource_type=resource_type,
            instance=instance,
            close_handler=close_handler,
            priority=priority,
            metadata=metadata or {}
        )
        
        self._resources[name] = resource_info
        
        # Update priority list
        self._resources_by_priority = sorted(
            self._resources.keys(),
            key=lambda n: self._resources[n].priority
        )
        
        logger.info(f"Resource registered: name={name}, resource_type={resource_type.value}, priority={priority}")
    
    def unregister_resource(self, name: str) -> bool:
        """
        Unregister a resource.
        
        Args:
            name: Resource name
            
        Returns:
            True if resource was unregistered, False if not found
        """
        if name in self._resources:
            del self._resources[name]
            self._resources_by_priority = sorted(
                self._resources.keys(),
                key=lambda n: self._resources[n].priority
            )
            logger.info(f"Resource unregistered: name={name}")
            return True
        return False
    
    def add_pre_shutdown_hook(self, hook: Callable) -> None:
        """Add a hook to run before shutdown starts"""
        self._pre_shutdown_hooks.append(hook)
        hook_name = hook.__name__ if hasattr(hook, '__name__') else str(hook)
        logger.debug(f"Pre-shutdown hook added: hook={hook_name}")
    
    def add_post_shutdown_hook(self, hook: Callable) -> None:
        """Add a hook to run after shutdown completes"""
        self._post_shutdown_hooks.append(hook)
        hook_name = hook.__name__ if hasattr(hook, '__name__') else str(hook)
        logger.debug(f"Post-shutdown hook added: hook={hook_name}")
    
    def setup_signal_handlers(self) -> None:
        """
        Setup signal handlers for SIGTERM and SIGINT.
        
        This allows graceful shutdown when process receives termination signal.
        """
        if self._signal_handlers_installed:
            logger.warning("Signal handlers already installed")
            return
        
        loop = asyncio.get_event_loop()
        
        def handle_signal(sig: signal.Signals):
            """Signal handler callback"""
            logger.info(f"Received shutdown signal: signal={sig.name}")
            
            # Create shutdown task
            if not self._is_shutting_down:
                asyncio.create_task(self.shutdown(reason=f"Signal {sig.name}"))
        
        # Setup handlers for SIGTERM and SIGINT
        for sig in (signal.SIGTERM, signal.SIGINT):
            self._original_handlers[sig] = signal.getsignal(sig)
            
            try:
                # For asyncio, use loop.add_signal_handler
                loop.add_signal_handler(
                    sig,
                    lambda s=sig: handle_signal(s)
                )
            except (NotImplementedError, RuntimeError):
                # Fallback for Windows or when event loop doesn't support it
                signal.signal(sig, lambda s, f: handle_signal(s))
        
        self._signal_handlers_installed = True
        logger.info("Signal handlers installed for SIGTERM and SIGINT")
    
    def restore_signal_handlers(self) -> None:
        """Restore original signal handlers"""
        if not self._signal_handlers_installed:
            return
        
        loop = asyncio.get_event_loop()
        
        for sig in (signal.SIGTERM, signal.SIGINT):
            try:
                loop.remove_signal_handler(sig)
            except (NotImplementedError, RuntimeError):
                pass
            
            if sig in self._original_handlers:
                signal.signal(sig, self._original_handlers[sig])
        
        self._signal_handlers_installed = False
        logger.info("Signal handlers restored")
    
    async def shutdown(
        self,
        reason: str = "Manual shutdown",
        timeout: Optional[float] = None
    ) -> ShutdownResult:
        """
        Execute graceful shutdown.
        
        Args:
            reason: Reason for shutdown
            timeout: Optional timeout override
            
        Returns:
            ShutdownResult with status and progress
        """
        if self._is_shutting_down:
            logger.warning("Shutdown already in progress")
            return ShutdownResult(
                status=ShutdownStatus.IN_PROGRESS,
                progress=self._progress,
                message="Shutdown already in progress"
            )
        
        self._is_shutting_down = True
        timeout = timeout or self.config.graceful_timeout
        
        # Initialize progress
        self._progress = ShutdownProgress(
            phase=ShutdownPhase.INITIATED,
            started_at=datetime.now()
        )
        
        logger.info(f"Shutdown initiated: reason={reason}, timeout_seconds={timeout}")
        
        try:
            # Run pre-shutdown hooks
            await self._run_hooks(self._pre_shutdown_hooks, "pre-shutdown")
            
            # Phase 1: Stop accepting new connections
            await self._phase_stop_new_connections()
            
            # Phase 2: Drain existing connections
            drained = await self._phase_drain_connections()
            
            # Phase 3: Close resources
            closed = await self._phase_close_resources()
            
            # Phase 4: Flush buffers
            await self._phase_flush_buffers()
            
            # Phase 5: Complete
            self._progress.phase = ShutdownPhase.COMPLETED
            self._progress.completed_at = datetime.now()
            
            # Run post-shutdown hooks
            await self._run_hooks(self._post_shutdown_hooks, "post-shutdown")
            
            duration = self._progress.duration_seconds
            logger.info(f"Shutdown completed successfully: duration_seconds={duration}, drained_connections={drained}, closed_resources={closed}")
            
            self._shutdown_complete.set()
            
            return ShutdownResult(
                status=ShutdownStatus.SUCCESSFUL,
                progress=self._progress,
                message=f"Shutdown completed in {duration:.2f}s"
            )
            
        except asyncio.TimeoutError:
            # Handle timeout
            logger.error(f"Shutdown timeout exceeded: timeout_seconds={timeout}")
            
            self._progress.phase = ShutdownPhase.FORCED
            self._progress.completed_at = datetime.now()
            self._progress.errors.append(f"Shutdown timeout after {timeout}s")
            
            if self.config.force_after_timeout:
                await self._force_close_all()
            
            return ShutdownResult(
                status=ShutdownStatus.TIMEOUT,
                progress=self._progress,
                message=f"Shutdown timed out after {timeout}s"
            )
            
        except Exception as e:
            # Handle errors
            logger.error(f"Shutdown failed: error={str(e)}")
            
            self._progress.phase = ShutdownPhase.FORCED
            self._progress.completed_at = datetime.now()
            self._progress.errors.append(str(e))
            
            if self.config.raise_on_error:
                raise
            
            return ShutdownResult(
                status=ShutdownStatus.FAILED,
                progress=self._progress,
                message=f"Shutdown failed: {str(e)}"
            )
    
    async def _run_hooks(self, hooks: List[Callable], phase: str) -> None:
        """Run shutdown hooks"""
        for hook in hooks:
            try:
                result = hook()
                if asyncio.iscoroutine(result):
                    await asyncio.wait_for(
                        result,
                        timeout=self.config.resource_close_timeout
                    )
                logger.debug(f"{phase} hook completed: hook={str(hook)}")
            except Exception as e:
                logger.error(f"{phase} hook failed: hook={str(hook)}, error={str(e)}")
                self._progress.warnings.append(f"{phase} hook error: {str(e)}")
    
    async def _phase_stop_new_connections(self) -> None:
        """Phase 1: Stop accepting new connections"""
        self._progress.phase = ShutdownPhase.STOPPING_NEW_REQUESTS
        logger.info("Phase: Stopping new connections")
        
        self.connection_tracker.stop_accepting_new()
        self._progress.active_connections = await self.connection_tracker.get_active_connections_count()
    
    async def _phase_drain_connections(self) -> int:
        """Phase 2: Drain existing connections"""
        self._progress.phase = ShutdownPhase.DRAINING_CONNECTIONS
        logger.info("Phase: Draining connections")
        
        drain_result = await self.connection_tracker.drain_connections(
            timeout=self.config.drain_timeout,
            check_interval=self.config.drain_check_interval
        )
        
        self._progress.drained_connections = drain_result["drained_connections"]
        
        if drain_result["remaining_requests"] > 0:
            self._progress.warnings.append(
                f"{drain_result['remaining_requests']} requests still in flight after drain timeout"
            )
        
        return drain_result["drained_connections"]
    
    async def _phase_close_resources(self) -> int:
        """Phase 3: Close all resources"""
        self._progress.phase = ShutdownPhase.CLOSING_RESOURCES
        logger.info("Phase: Closing resources")
        
        self._progress.total_resources = len(self._resources)
        closed_count = 0
        
        for resource_name in self._resources_by_priority:
            resource_info = self._resources[resource_name]
            
            try:
                closed = await self._close_resource(resource_info)
                if closed:
                    closed_count += 1
                    self._progress.closed_resources = closed_count
                    logger.info(f"Resource closed: name={resource_name}, type={resource_info.resource_type.value}")
            except Exception as e:
                error_msg = f"Failed to close {resource_name}: {str(e)}"
                self._progress.errors.append(error_msg)
                logger.error(f"Failed to close resource: name={resource_name}, error={str(e)}")
        
        return closed_count
    
    async def _close_resource(self, resource_info: ResourceInfo) -> bool:
        """Close a single resource"""
        instance = resource_info.instance
        
        # Try to find close method
        close_method = None
        
        if resource_info.close_handler:
            # Use specified close handler
            close_method = getattr(instance, resource_info.close_handler, None)
        else:
            # Try common close method names
            for method_name in ['close', 'disconnect', 'shutdown', 'cleanup', 'dispose']:
                close_method = getattr(instance, method_name, None)
                if close_method:
                    break
        
        if not close_method:
            logger.warning(f"No close method found for resource: name={resource_info.name}")
            return False
        
        # Call close method with timeout
        try:
            result = close_method()
            if asyncio.iscoroutine(result):
                await asyncio.wait_for(
                    result,
                    timeout=self.config.resource_close_timeout
                )
            return True
        except asyncio.TimeoutError:
            logger.error(f"Resource close timeout: name={resource_info.name}, timeout={self.config.resource_close_timeout}")
            raise
        except Exception as e:
            logger.error(f"Error closing resource: name={resource_info.name}, error={str(e)}")
            raise
    
    async def flush_buffers(self) -> int:
        """
        Flush buffers/queues on registered resources exposing a flush() method.

        Iterates registered resources in priority order and invokes flush() when
        the resource exposes a callable flush method. Resources without flush()
        are skipped. Both sync and async flush() methods are supported.

        Errors during flush are caught, logged and recorded as warnings on the
        shutdown progress; they never stop the flush process or the shutdown.

        Returns:
            Number of resources whose flush() was invoked successfully.
        """
        flushed_count = 0

        for resource_name in self._resources_by_priority:
            resource_info = self._resources[resource_name]
            instance = resource_info.instance

            flush_method = getattr(instance, "flush", None)
            if not callable(flush_method):
                continue

            try:
                result = flush_method()
                if asyncio.iscoroutine(result):
                    await asyncio.wait_for(
                        result,
                        timeout=self.config.resource_close_timeout
                    )
                flushed_count += 1
                logger.info(
                    f"Buffer flushed: name={resource_name}, "
                    f"type={resource_info.resource_type.value}"
                )
            except asyncio.TimeoutError:
                error_msg = (
                    f"Buffer flush timeout: name={resource_name}, "
                    f"timeout={self.config.resource_close_timeout}"
                )
                self._progress.warnings.append(error_msg)
                logger.error(error_msg)
            except Exception as e:
                warning_msg = f"Failed to flush {resource_name}: {str(e)}"
                self._progress.warnings.append(warning_msg)
                logger.error(f"Error flushing buffer: name={resource_name}, error={str(e)}")

        return flushed_count

    async def _phase_flush_buffers(self) -> None:
        """Phase 4: Flush any pending buffers/queues"""
        self._progress.phase = ShutdownPhase.FLUSHING_BUFFERS
        logger.info("Phase: Flushing buffers")

        flushed = await self.flush_buffers()
        logger.info(f"Phase complete: Flushed buffers, count={flushed}")
    
    async def _force_close_all(self) -> None:
        """Force close all connections and resources"""
        logger.warning("Forcing shutdown")
        
        # Force close all tracked connections
        closed_conns = await self.connection_tracker.force_close_all()
        logger.info(f"Force closed connections: count={closed_conns}")
        
        # Force close resources
        for resource_name in self._resources_by_priority:
            resource_info = self._resources[resource_name]
            try:
                # Try quick close without timeout
                instance = resource_info.instance
                if hasattr(instance, 'close'):
                    instance.close()
            except Exception as e:
                logger.error(f"Error force closing resource: name={resource_name}, error={str(e)}")
    
    def get_progress(self) -> ShutdownProgress:
        """Get current shutdown progress"""
        return self._progress
    
    def is_shutting_down(self) -> bool:
        """Check if shutdown is in progress"""
        return self._is_shutting_down
    
    async def wait_for_shutdown(self, timeout: Optional[float] = None) -> bool:
        """
        Wait for shutdown to complete.
        
        Args:
            timeout: Maximum time to wait
            
        Returns:
            True if shutdown completed, False if timeout
        """
        try:
            await asyncio.wait_for(
                self._shutdown_complete.wait(),
                timeout=timeout
            )
            return True
        except asyncio.TimeoutError:
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get shutdown manager statistics"""
        return {
            "is_shutting_down": self._is_shutting_down,
            "phase": self._progress.phase.value,
            "resources_count": len(self._resources),
            "connection_stats": self.connection_tracker.get_stats(),
            "signal_handlers_installed": self._signal_handlers_installed
        }


# Global shutdown manager instance
shutdown_manager = ShutdownManager()
