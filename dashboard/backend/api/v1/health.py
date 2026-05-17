"""
Health Check Endpoints for QA-FRAMEWORK Dashboard

Provides Kubernetes-compatible health probes and Prometheus metrics.
"""

import time
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional

from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import redis.asyncio as redis
from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    generate_latest,
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
)

from database import get_db_session as get_db, engine, AsyncSessionFactory
from core.logging_config import get_logger
from config import settings

logger = get_logger(__name__)
router = APIRouter(prefix="/health", tags=["health"])

# Prometheus Metrics Registry
registry = CollectorRegistry()

# Custom Metrics
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
    registry=registry,
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    registry=registry,
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

db_connections_active = Gauge(
    "db_connections_active", "Number of active database connections", registry=registry
)

db_connection_errors_total = Counter(
    "db_connection_errors_total", "Total database connection errors", registry=registry
)

cache_hits_total = Counter("cache_hits_total", "Total cache hits", registry=registry)

cache_misses_total = Counter(
    "cache_misses_total", "Total cache misses", registry=registry
)

active_executions = Gauge(
    "active_test_executions", "Number of active test executions", registry=registry
)

test_executions_total = Counter(
    "test_executions_total",
    "Total test executions by status",
    ["status"],
    registry=registry,
)

app_start_time = Gauge(
    "app_start_timestamp",
    "Unix timestamp when the application started",
    registry=registry,
)

# Set start time
app_start_time.set_to_current_time()

# Application state
startup_time: Optional[datetime] = None
health_checks: Dict[str, Any] = {}


async def check_database_health() -> Dict[str, Any]:
    """Check database connectivity and performance."""
    start_time = time.time()
    try:
        async with AsyncSessionFactory() as session:
            result = await session.execute(text("SELECT 1"))
            await result.scalar()

            # Get connection pool stats if available
            pool = session.bind.pool
            size = pool.size() if hasattr(pool, "size") else 0
            checked_in = pool.checkedin() if hasattr(pool, "checkedin") else 0
            checked_out = pool.checkedout() if hasattr(pool, "checkedout") else 0

            db_connections_active.set(checked_out)

            return {
                "status": "healthy",
                "response_time_ms": round((time.time() - start_time) * 1000, 2),
                "connections": {
                    "total": size,
                    "active": checked_out,
                    "idle": checked_in,
                },
            }
    except Exception as e:
        db_connection_errors_total.inc()
        logger.error("Database health check failed", error=str(e))
        return {
            "status": "unhealthy",
            "error": str(e),
            "response_time_ms": round((time.time() - start_time) * 1000, 2),
        }


async def check_redis_health() -> Dict[str, Any]:
    """Check Redis connectivity and performance."""
    start_time = time.time()
    try:
        r = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            password=settings.redis_password,
            socket_connect_timeout=5,
            socket_timeout=5,
            decode_responses=True,
        )

        # Test connection
        await r.ping()

        # Get Redis info
        info = await r.info()

        # Test write/read
        test_key = f"health_check:{int(time.time())}"
        await r.setex(test_key, 10, "ok")
        value = await r.get(test_key)
        await r.delete(test_key)

        if value == "ok":
            cache_hits_total.inc()
        else:
            cache_misses_total.inc()

        await r.close()

        return {
            "status": "healthy",
            "response_time_ms": round((time.time() - start_time) * 1000, 2),
            "version": info.get("redis_version", "unknown"),
            "connected_clients": info.get("connected_clients", 0),
            "used_memory_human": info.get("used_memory_human", "unknown"),
            "hit_rate": info.get("keyspace_hits", 0)
            / (info.get("keyspace_hits", 0) + info.get("keyspace_misses", 1))
            * 100,
        }
    except Exception as e:
        logger.error("Redis health check failed", error=str(e))
        return {
            "status": "unhealthy",
            "error": str(e),
            "response_time_ms": round((time.time() - start_time) * 1000, 2),
        }


async def check_qa_framework_integration() -> Dict[str, Any]:
    """Check QA-FRAMEWORK integration connectivity."""
    start_time = time.time()
    try:
        from integration.qa_framework_client import get_qa_test_suites

        # Attempt to fetch test suites (lightweight check)
        suites = await get_qa_test_suites()

        return {
            "status": "healthy",
            "response_time_ms": round((time.time() - start_time) * 1000, 2),
            "suites_available": len(suites) if suites else 0,
        }
    except Exception as e:
        logger.error("QA-FRAMEWORK integration health check failed", error=str(e))
        return {
            "status": "unhealthy",
            "error": str(e),
            "response_time_ms": round((time.time() - start_time) * 1000, 2),
        }


@router.get("/live", status_code=status.HTTP_200_OK)
async def liveness_probe():
    """
    Kubernetes liveness probe.

    Returns 200 if the application is running.
    If this fails, Kubernetes will restart the pod.
    """
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat(),
        "uptime_seconds": (datetime.utcnow() - startup_time).total_seconds()
        if startup_time
        else 0,
    }


@router.get("/ready", status_code=status.HTTP_200_OK)
async def readiness_probe():
    """
    Kubernetes readiness probe.

    Returns 200 if the application is ready to serve traffic.
    Checks database and Redis connectivity.
    If this fails, Kubernetes will remove the pod from the service.
    """
    checks = await asyncio.gather(
        check_database_health(),
        check_redis_health(),
        check_qa_framework_integration(),
        return_exceptions=True,
    )

    db_status = (
        checks[0]
        if not isinstance(checks[0], Exception)
        else {"status": "error", "error": str(checks[0])}
    )
    redis_status = (
        checks[1]
        if not isinstance(checks[1], Exception)
        else {"status": "error", "error": str(checks[1])}
    )
    qa_status = (
        checks[2]
        if not isinstance(checks[2], Exception)
        else {"status": "error", "error": str(checks[2])}
    )

    all_healthy = all(
        check.get("status") == "healthy"
        for check in [db_status, redis_status, qa_status]
    )

    response = {
        "status": "ready" if all_healthy else "not_ready",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {
            "database": db_status,
            "redis": redis_status,
            "qa_framework": qa_status,
        },
    }

    if not all_healthy:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=response
        )

    return response


@router.get("/metrics", response_class=PlainTextResponse)
async def metrics():
    """
    Prometheus metrics endpoint.

    Returns all registered metrics in Prometheus exposition format.
    """
    return PlainTextResponse(
        content=generate_latest(registry), media_type=CONTENT_TYPE_LATEST
    )


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

    return {
        "status": "started",
        "startup_time": startup_time.isoformat(),
        "startup_duration_seconds": (datetime.utcnow() - startup_time).total_seconds(),
    }


@router.get("/status", status_code=status.HTTP_200_OK)
async def detailed_health_status(db: AsyncSession = Depends(get_db)):
    """
    Detailed health status with all system information.

    Provides comprehensive health information about all components.
    """
    import psutil
    import platform

    # System metrics
    system_info = {
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "cpu_percent": psutil.cpu_percent(interval=1),
        "memory_percent": psutil.virtual_memory().percent,
        "disk_usage_percent": psutil.disk_usage("/").percent,
    }

    # Run all health checks
    db_health = await check_database_health()
    redis_health = await check_redis_health()
    qa_health = await check_qa_framework_integration()

    # Get application metrics
    app_metrics = {
        "uptime_seconds": (datetime.utcnow() - startup_time).total_seconds()
        if startup_time
        else 0,
        "start_time": startup_time.isoformat() if startup_time else None,
    }

    all_healthy = all(
        check.get("status") == "healthy"
        for check in [db_health, redis_health, qa_health]
    )

    return {
        "status": "healthy" if all_healthy else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "system": system_info,
        "application": app_metrics,
        "services": {
            "database": db_health,
            "redis": redis_health,
            "qa_framework": qa_health,
        },
    }


def set_startup_complete():
    """Mark the application startup as complete."""
    global startup_time
    startup_time = datetime.utcnow()
    logger.info("Application startup complete", startup_time=startup_time.isoformat())
