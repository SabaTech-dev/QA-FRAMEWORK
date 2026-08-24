"""Aggregated health status endpoint for FastAPI integration"""

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse

from src.infrastructure.health.health_checker import HealthChecker, get_health_checker
from src.infrastructure.health.models import AggregatedHealthStatus, HealthCheckConfig, HealthStatus


def create_health_router(
    health_checker: HealthChecker | None = None,
    prefix: str = "/health",
    tags: list | None = None,
    include_liveness: bool = True,
    include_readiness: bool = True,
    include_startup: bool = True,
) -> APIRouter:
    """
    Create a FastAPI router with health check endpoints.

    This provides Kubernetes-compatible health probes and detailed status.

    Args:
        health_checker: HealthChecker instance (uses default if None)
        prefix: Router prefix (default: /health)
        tags: OpenAPI tags
        include_liveness: Include /live endpoint
        include_readiness: Include /ready endpoint
        include_startup: Include /startup endpoint

    Returns:
        FastAPI router with health endpoints

    Example:
        from fastapi import FastAPI
        from src.infrastructure.health.endpoint import create_health_router

        app = FastAPI()

        # Configure health checker
        checker = HealthChecker()
        checker.add_database_check("main_db", "postgresql://...", ServiceType.DATABASE_POSTGRESQL)
        checker.add_redis_check("cache", host="localhost")

        # Add health router
        app.include_router(create_health_router(checker))
    """
    router = APIRouter(prefix=prefix, tags=tags or ["health"])
    checker = health_checker or get_health_checker()

    # Application state
    startup_time: datetime | None = None

    def set_startup_complete():
        nonlocal startup_time
        startup_time = datetime.now(UTC)

    @router.get("/live", status_code=status.HTTP_200_OK)
    async def liveness_probe():
        """
        Kubernetes liveness probe.

        Returns 200 if the application is running.
        If this fails, Kubernetes will restart the pod.
        """
        now = datetime.now(UTC)
        uptime = (now - startup_time).total_seconds() if startup_time else 0

        return {
            "status": "alive",
            "timestamp": now.isoformat(),
            "uptime_seconds": uptime,
        }

    @router.get("/ready", status_code=status.HTTP_200_OK)
    async def readiness_probe():
        """
        Kubernetes readiness probe.

        Returns 200 if the application is ready to serve traffic.
        Checks all registered health services.
        If this fails, Kubernetes will remove the pod from the service.
        """
        health_status = await checker.run_health_checks()

        if health_status.overall_status == HealthStatus.UNHEALTHY:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=health_status.model_dump(mode="json"),
            )

        if health_status.overall_status == HealthStatus.DEGRADED:
            # Return 200 but indicate degraded state
            return JSONResponse(
                status_code=status.HTTP_200_OK, content=health_status.model_dump(mode="json")
            )

        return health_status.model_dump(mode="json")

    @router.get("/startup", status_code=status.HTTP_200_OK)
    async def startup_probe():
        """
        Kubernetes startup probe.

        Returns 200 when the application has finished starting up.
        Used to prevent premature liveness/readiness checks.
        """
        if startup_time is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "status": "starting",
                    "message": "Application is still initializing",
                },
            )

        now = datetime.now(UTC)
        return {
            "status": "started",
            "startup_time": startup_time.isoformat(),
            "startup_duration_seconds": (now - startup_time).total_seconds(),
        }

    @router.get("/status", status_code=status.HTTP_200_OK)
    async def detailed_health_status():
        """
        Detailed health status with all system information.

        Provides comprehensive health information about all components.
        """
        health_status = await checker.run_health_checks()

        # Add system information
        system_info = _get_system_info()

        response = health_status.model_dump(mode="json")
        response["system"] = system_info

        # Determine HTTP status based on health
        if health_status.overall_status == HealthStatus.UNHEALTHY:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=response)

        return response

    @router.get("/checks", status_code=status.HTTP_200_OK)
    async def list_registered_checks():
        """
        List all registered health checks.

        Returns information about what health checks are configured.
        """
        return {
            "registered_checks": checker.get_registered_checks(),
            "config": {
                "timeout_seconds": checker.config.timeout_seconds,
                "retry_count": checker.config.retry_count,
                "cache_results_seconds": checker.config.cache_results_seconds,
                "parallel_checks": checker.config.parallel_checks,
            },
        }

    @router.post("/invalidate-cache", status_code=status.HTTP_200_OK)
    async def invalidate_cache():
        """
        Invalidate health check cache.

        Forces the next health check to run all checks.
        """
        checker.invalidate_cache()
        return {"message": "Cache invalidated", "timestamp": datetime.now(UTC).isoformat()}

    # Store startup function reference
    router.set_startup_complete = set_startup_complete

    return router


def _get_system_info() -> dict[str, Any]:
    """Get system information for health status."""
    import os
    import platform

    info = {
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "hostname": platform.node(),
    }

    # Try to get resource usage
    try:
        import psutil

        info.update(
            {
                "cpu_percent": psutil.cpu_percent(interval=0.1),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_usage_percent": psutil.disk_usage("/").percent,
                "process_count": len(psutil.pids()),
            }
        )
    except ImportError:
        info["psutil"] = "not installed"

    # Environment info
    info["environment"] = os.getenv("ENVIRONMENT", "unknown")

    return info


class HealthEndpointManager:
    """
    Manager for health endpoints with lifecycle management.

    Example:
        from fastapi import FastAPI
        from src.infrastructure.health.endpoint import HealthEndpointManager

        app = FastAPI()

        health_manager = HealthEndpointManager()
        health_manager.configure_database("postgresql://...")
        health_manager.configure_redis("localhost", 6379)

        app.include_router(health_manager.get_router())

        @app.on_event("startup")
        async def startup():
            health_manager.mark_ready()
    """

    def __init__(self, config: HealthCheckConfig | None = None):
        """Initialize health endpoint manager."""
        self.checker = HealthChecker(config)
        self._router: APIRouter | None = None
        self._ready = False

    def configure_database(
        self,
        name: str,
        connection_string: str,
        database_type: str = "postgresql",
        test_query: str = "SELECT 1",
    ) -> "HealthEndpointManager":
        """Configure database health check."""
        from src.infrastructure.health.models import ServiceType

        db_type = ServiceType(database_type)
        self.checker.add_database_check(name, connection_string, db_type, test_query)
        return self

    def configure_redis(
        self,
        name: str,
        host: str = "localhost",
        port: int = 6379,
        password: str | None = None,
        db: int = 0,
    ) -> "HealthEndpointManager":
        """Configure Redis health check."""
        self.checker.add_redis_check(name, host, port, password, db)
        return self

    def configure_external_api(
        self,
        name: str,
        url: str,
        method: str = "GET",
        required: bool = True,
    ) -> "HealthEndpointManager":
        """Configure external API health check."""
        self.checker.add_external_api_check(name, url, method, required=required)
        return self

    def configure_internal_service(
        self,
        name: str,
        health_endpoint: str,
        required: bool = True,
    ) -> "HealthEndpointManager":
        """Configure internal service health check."""
        self.checker.add_internal_service_check(name, health_endpoint, required=required)
        return self

    def get_router(self, prefix: str = "/health") -> APIRouter:
        """Get the health check router."""
        if self._router is None:
            self._router = create_health_router(self.checker, prefix)
        return self._router

    def mark_ready(self) -> None:
        """Mark the application as ready."""
        self._ready = True
        if self._router and hasattr(self._router, "set_startup_complete"):
            self._router.set_startup_complete()

    async def check_health(self) -> AggregatedHealthStatus:
        """Run health checks manually."""
        return await self.checker.run_health_checks()
