"""
Graceful Shutdown Module for QA-FRAMEWORK

This module provides comprehensive graceful shutdown functionality for
QA-FRAMEWORK services, including:
- Signal handling (SIGTERM, SIGINT)
- Connection tracking and draining
- Resource cleanup (Database, Redis, etc.)
- Configurable timeouts
- Both FastAPI and standalone usage

Quick Start - FastAPI:
    from fastapi import FastAPI
    from src.infrastructure.shutdown import setup_fastapi_shutdown, shutdown_manager, ResourceType

    app = FastAPI()

    # Setup graceful shutdown
    setup_fastapi_shutdown(app)

    # Register resources
    shutdown_manager.register_resource("db", ResourceType.DATABASE, db_engine)
    shutdown_manager.register_resource("redis", ResourceType.REDIS, redis_client)

Quick Start - Standalone:
    from src.infrastructure.shutdown import StandaloneShutdown, ResourceType

    shutdown = StandaloneShutdown()
    shutdown.setup()
    shutdown.register_database(db_engine)

    while not shutdown.is_shutting_down():
        # Do work
        pass

    await shutdown.wait_and_cleanup()

Components:
    - ShutdownManager: Main shutdown orchestrator
    - ConnectionTracker: Tracks active connections and requests
    - ShutdownMiddleware: FastAPI middleware for request tracking
    - StandaloneShutdown: Helper for non-FastAPI applications
    - BackgroundTaskManager: Manage background tasks with shutdown support
"""

from src.infrastructure.shutdown.connection_tracker import ConnectionTracker
from src.infrastructure.shutdown.fastapi_integration import (
    RequestTracker,
    ShutdownMiddleware,
    create_shutdown_lifespan,
    get_request_tracker,
    register_database_connection,
    register_redis_connection,
    setup_fastapi_shutdown,
)
from src.infrastructure.shutdown.models import (  # Enums; Data classes
    ConnectionInfo,
    ResourceInfo,
    ResourceType,
    ShutdownConfig,
    ShutdownPhase,
    ShutdownProgress,
    ShutdownResult,
    ShutdownStatus,
)
from src.infrastructure.shutdown.shutdown_manager import shutdown_manager  # Global instance
from src.infrastructure.shutdown.shutdown_manager import ShutdownManager
from src.infrastructure.shutdown.standalone import (
    BackgroundTaskManager,
    StandaloneShutdown,
    create_shutdown_decorator,
    install_signal_handler,
    run_with_shutdown,
    shutdown_context,
)

__all__ = [
    # Models
    "ShutdownPhase",
    "ShutdownStatus",
    "ResourceType",
    "ConnectionInfo",
    "ResourceInfo",
    "ShutdownProgress",
    "ShutdownConfig",
    "ShutdownResult",
    # Core components
    "ConnectionTracker",
    "ShutdownManager",
    "shutdown_manager",  # Global instance
    # FastAPI integration
    "ShutdownMiddleware",
    "setup_fastapi_shutdown",
    "create_shutdown_lifespan",
    "register_database_connection",
    "register_redis_connection",
    "RequestTracker",
    "get_request_tracker",
    # Standalone helpers
    "StandaloneShutdown",
    "shutdown_context",
    "BackgroundTaskManager",
    "create_shutdown_decorator",
    "run_with_shutdown",
    "install_signal_handler",
]


# Version info
__version__ = "1.0.0"
__author__ = "QA-FRAMEWORK Team"
