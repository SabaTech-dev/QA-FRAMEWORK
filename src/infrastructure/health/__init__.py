"""
Health Check Module for QA-FRAMEWORK

This module provides comprehensive health checking capabilities for:
- Database connectivity (PostgreSQL, MySQL, SQLite)
- Redis cache connectivity
- External API availability
- Internal service status

Features:
- Configurable timeouts and retries
- Parallel or sequential health checks
- Result caching
- Detailed error reporting
- Kubernetes-compatible health probes
- FastAPI integration

Example usage:

    from src.infrastructure.health import HealthChecker, ServiceType

    # Create health checker
    checker = HealthChecker()

    # Add database check
    checker.add_database_check(
        name="main_db",
        connection_string="postgresql://user:pass@localhost/db",
        database_type=ServiceType.DATABASE_POSTGRESQL
    )

    # Add Redis check
    checker.add_redis_check(
        name="cache",
        host="localhost",
        port=6379
    )

    # Add external API check
    checker.add_external_api_check(
        name="payment_api",
        url="https://api.example.com/health",
        required=False
    )

    # Run all health checks
    status = await checker.run_health_checks()
    print(f"Overall status: {status.overall_status}")
    print(f"Healthy: {status.summary['healthy_count']}/{status.summary['total_checks']}")

FastAPI integration:

    from fastapi import FastAPI
    from src.infrastructure.health import create_health_router, HealthChecker

    app = FastAPI()

    checker = HealthChecker()
    checker.add_database_check("db", "postgresql://...")

    app.include_router(create_health_router(checker))

    # Endpoints available:
    # GET /health/live     - Liveness probe
    # GET /health/ready    - Readiness probe
    # GET /health/startup  - Startup probe
    # GET /health/status   - Detailed status
    # GET /health/checks   - List registered checks
"""

from src.infrastructure.health.checks import (  # Individual check functions
    check_database_health,
    check_external_api_health,
    check_internal_service_health,
    check_redis_health,
)
from src.infrastructure.health.endpoint import (  # FastAPI integration
    HealthEndpointManager,
    create_health_router,
)
from src.infrastructure.health.health_checker import (  # Main checker class; Convenience functions
    HealthChecker,
    get_health_checker,
    set_health_checker,
)
from src.infrastructure.health.models import (  # Enums; Models
    AggregatedHealthStatus,
    DatabaseHealthCheckConfig,
    ExternalAPIHealthCheckConfig,
    HealthCheckConfig,
    HealthCheckResult,
    HealthStatus,
    InternalServiceHealthCheckConfig,
    RedisHealthCheckConfig,
    ServiceType,
)

__all__ = [
    # Enums
    "HealthStatus",
    "ServiceType",
    # Models
    "HealthCheckResult",
    "AggregatedHealthStatus",
    "HealthCheckConfig",
    "DatabaseHealthCheckConfig",
    "RedisHealthCheckConfig",
    "ExternalAPIHealthCheckConfig",
    "InternalServiceHealthCheckConfig",
    # Check functions
    "check_database_health",
    "check_redis_health",
    "check_external_api_health",
    "check_internal_service_health",
    # Health checker
    "HealthChecker",
    "get_health_checker",
    "set_health_checker",
    # FastAPI integration
    "create_health_router",
    "HealthEndpointManager",
]

__version__ = "1.0.0"
