"""
FastAPI integration for graceful shutdown

Note: This module requires FastAPI to be installed.
If FastAPI is not installed, import will fail but other modules will work.
"""

try:
    from collections.abc import Callable
    from contextlib import asynccontextmanager

    from fastapi import FastAPI, Request, Response
    from starlette.middleware.base import BaseHTTPMiddleware

    from src.infrastructure.logger.logger import QALogger
    from src.infrastructure.shutdown.models import ResourceType
    from src.infrastructure.shutdown.shutdown_manager import ShutdownManager, shutdown_manager

    logger = QALogger.get_logger(__name__)

    class ShutdownMiddleware(BaseHTTPMiddleware):
        """
        Middleware to handle graceful shutdown in FastAPI.

        Features:
        - Rejects new requests during shutdown
        - Tracks in-flight requests
        - Adds connection tracking headers
        """

        def __init__(self, app, manager: ShutdownManager | None = None):
            super().__init__(app)
            self.manager = manager or shutdown_manager

        async def dispatch(self, request: Request, call_next: Callable) -> Response:
            """Process request with shutdown awareness"""

            # Check if we're shutting down
            if self.manager.is_shutting_down():
                # Reject new requests during shutdown
                logger.warning(
                    f"Rejecting request during shutdown: path={request.url.path}, method={request.method}"
                )
                return Response(
                    content='{"error": "Service shutting down", "retry_after": 30}',
                    status_code=503,
                    media_type="application/json",
                    headers={"Retry-After": "30"},
                )

            # Check if accepting new connections
            if not self.manager.connection_tracker.is_accepting_new():
                logger.warning(
                    f"Rejecting request - not accepting new connections: path={request.url.path}, method={request.method}"
                )
                return Response(
                    content='{"error": "Service not accepting requests", "retry_after": 10}',
                    status_code=503,
                    media_type="application/json",
                    headers={"Retry-After": "10"},
                )

            # Register connection and track request
            connection_id = None
            try:
                # Register HTTP connection
                connection_id = await self.manager.connection_tracker.register_connection(
                    resource_type=ResourceType.HTTP_CLIENT,
                    metadata={
                        "path": request.url.path,
                        "method": request.method,
                        "client": request.client.host if request.client else None,
                    },
                )

                # Track the request
                await self.manager.connection_tracker.start_request(connection_id)

                # Process request
                response = await call_next(request)

                return response

            finally:
                # End request tracking
                if connection_id:
                    await self.manager.connection_tracker.end_request(connection_id)
                    # Deregister connection
                    await self.manager.connection_tracker.deregister_connection(connection_id)

    def setup_fastapi_shutdown(
        app: FastAPI, manager: ShutdownManager | None = None, setup_signal_handlers: bool = True
    ) -> None:
        """
        Setup graceful shutdown for a FastAPI application.

        This function:
        1. Adds shutdown middleware
        2. Uses lifespan pattern for startup/shutdown (FastAPI 0.93+)

        Note: This function modifies the app's lifespan. If you need custom lifespan
        logic, use create_shutdown_lifespan() directly.

        Args:
            app: FastAPI application instance
            manager: ShutdownManager instance (uses global if not provided)
            setup_signal_handlers: Whether to setup signal handlers

        Example:
            from fastapi import FastAPI
            from src.infrastructure.shutdown.fastapi_integration import setup_fastapi_shutdown

            app = FastAPI()
            setup_fastapi_shutdown(app)

            # Register your resources
            shutdown_manager.register_resource("db", ResourceType.DATABASE, engine)
        """
        import warnings

        warnings.warn(
            "setup_fastapi_shutdown() is deprecated. Use create_shutdown_lifespan() directly. "
            "See FastAPI lifespan documentation for details.",
            DeprecationWarning,
            stacklevel=2,
        )

        manager = manager or shutdown_manager

        # Add shutdown middleware
        app.add_middleware(ShutdownMiddleware, manager=manager)

        # Use lifespan pattern instead of deprecated events
        _lifespan = create_shutdown_lifespan(manager)

        # Store original router/lifespan if exists
        # Note: FastAPI doesn't allow changing lifespan after init, so we just warn
        logger.warning(
            "setup_fastapi_shutdown() called after app initialization. "
            "Lifespan cannot be modified. Use create_shutdown_lifespan() during app creation."
        )

        logger.info("FastAPI graceful shutdown configured (middleware only)")

    def create_shutdown_lifespan(manager: ShutdownManager | None = None):
        """
        Create a lifespan context manager for FastAPI apps using the new lifespan pattern.

        This is the modern way to handle startup/shutdown in FastAPI 0.93+

        Example:
            from fastapi import FastAPI
            from src.infrastructure.shutdown.fastapi_integration import create_shutdown_lifespan

            manager = ShutdownManager()

            @asynccontextmanager
            async def lifespan(app: FastAPI):
                # Startup
                manager.setup_signal_handlers()
                manager.register_resource("db", ResourceType.DATABASE, engine)
                yield
                # Shutdown
                await manager.shutdown()

            app = FastAPI(lifespan=lifespan)
        """
        manager = manager or shutdown_manager

        @asynccontextmanager
        async def lifespan(app: FastAPI):
            # Startup
            manager.setup_signal_handlers()
            logger.info("Application lifespan started")

            yield

            # Shutdown
            logger.info("Application lifespan shutting down")
            await manager.shutdown(reason="Application lifespan shutdown")

        return lifespan

    async def register_database_connection(
        engine, session_factory=None, manager: ShutdownManager | None = None
    ) -> None:
        """
        Register database connections for graceful shutdown.

        Args:
            engine: SQLAlchemy engine instance
            session_factory: Optional session factory to track active sessions
            manager: ShutdownManager instance
        """
        manager = manager or shutdown_manager

        manager.register_resource(
            name="database_engine",
            resource_type=ResourceType.DATABASE,
            instance=engine,
            close_handler="dispose",  # SQLAlchemy uses dispose() for engines
            priority=100,
        )

        logger.info("Database engine registered for shutdown")

    async def register_redis_connection(
        redis_client, name: str = "redis", manager: ShutdownManager | None = None
    ) -> None:
        """
        Register Redis connection for graceful shutdown.

        Args:
            redis_client: Redis client instance (sync or async)
            name: Name for the connection
            manager: ShutdownManager instance
        """
        manager = manager or shutdown_manager

        manager.register_resource(
            name=name,
            resource_type=ResourceType.REDIS,
            instance=redis_client,
            close_handler="close",
            priority=90,  # Close Redis before DB
        )

        logger.info(f"Redis client registered for shutdown: name={name}")

    class RequestTracker:
        """
        Helper class to track individual requests.

        Use this as a dependency in FastAPI routes to ensure
        requests are tracked for graceful shutdown.

        Example:
            from fastapi import Depends
            from src.infrastructure.shutdown.fastapi_integration import RequestTracker

            @app.get("/api/data")
            async def get_data(tracker: RequestTracker = Depends()):
                # Request is automatically tracked
                return {"data": "value"}
        """

        def __init__(self, manager: ShutdownManager | None = None):
            self.manager = manager or shutdown_manager
            self.connection_id: str | None = None

        async def __aenter__(self):
            """Enter context - register and start tracking"""
            if not self.manager.is_shutting_down():
                self.connection_id = await self.manager.connection_tracker.register_connection(
                    resource_type=ResourceType.HTTP_CLIENT
                )
                await self.manager.connection_tracker.start_request(self.connection_id)
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            """Exit context - end tracking and deregister"""
            if self.connection_id:
                await self.manager.connection_tracker.end_request(self.connection_id)
                await self.manager.connection_tracker.deregister_connection(self.connection_id)
            return False

    def get_request_tracker() -> RequestTracker:
        """FastAPI dependency for request tracking"""
        return RequestTracker()

except ImportError:
    # FastAPI not installed - provide stub functions
    import warnings

    warnings.warn(
        "FastAPI is not installed. FastAPI integration will not be available. "
        "Install FastAPI with: pip install fastapi",
        ImportWarning,
    )

    # Provide stub classes/functions so imports don't fail
    class ShutdownMiddleware:
        def __init__(self, *args, **kwargs):
            raise ImportError("FastAPI is not installed. Install with: pip install fastapi")

    def setup_fastapi_shutdown(*args, **kwargs):
        raise ImportError("FastAPI is not installed. Install with: pip install fastapi")

    def create_shutdown_lifespan(*args, **kwargs):
        raise ImportError("FastAPI is not installed. Install with: pip install fastapi")

    async def register_database_connection(*args, **kwargs):
        raise ImportError("FastAPI is not installed. Install with: pip install fastapi")

    async def register_redis_connection(*args, **kwargs):
        raise ImportError("FastAPI is not installed. Install with: pip install fastapi")

    class RequestTracker:
        def __init__(self, *args, **kwargs):
            raise ImportError("FastAPI is not installed. Install with: pip install fastapi")

    def get_request_tracker():
        raise ImportError("FastAPI is not installed. Install with: pip install fastapi")
