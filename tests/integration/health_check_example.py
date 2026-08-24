"""
Integration test example for health checks.

This demonstrates how to use the health check module in practice.
"""

import asyncio

from src.infrastructure.health import HealthChecker, HealthStatus, ServiceType, create_health_router


async def example_health_check():
    """Example of using health checks."""

    # Create health checker with custom configuration
    checker = HealthChecker()

    # Add database check (PostgreSQL)
    checker.add_database_check(
        name="main_database",
        connection_string="postgresql://qa_user:qa_password@localhost/qa_framework_db",
        database_type=ServiceType.DATABASE_POSTGRESQL,
        test_query="SELECT 1",
    )

    # Add Redis cache check
    checker.add_redis_check(name="session_cache", host="localhost", port=6379, password=None, db=0)

    # Add external API checks (non-critical)
    checker.add_external_api_check(
        name="github_api", url="https://api.github.com/health", required=False
    )

    # Add internal service checks
    checker.add_internal_service_check(
        name="dashboard_backend", health_endpoint="http://localhost:8000/health/live", required=True
    )

    # Run all health checks
    status = await checker.run_health_checks()

    # Print results
    print(f"\n{'='*60}")
    print("HEALTH CHECK RESULTS")
    print(f"{'='*60}")
    print(f"Overall Status: {status.overall_status.value.upper()}")
    print(f"Timestamp: {status.timestamp.isoformat()}")
    print("\nSummary:")
    print(f"  Total Checks: {status.summary['total_checks']}")
    print(f"  Healthy: {status.summary['healthy_count']}")
    print(f"  Unhealthy: {status.summary['unhealthy_count']}")
    print(f"  Degraded: {status.summary['degraded_count']}")
    print(f"  Health %: {status.summary['health_percentage']}%")
    print(f"  Total Time: {status.summary['total_time_ms']:.2f}ms")
    print("\nIndividual Checks:")

    for check in status.checks:
        icon = {
            HealthStatus.HEALTHY: "✅",
            HealthStatus.UNHEALTHY: "❌",
            HealthStatus.DEGRADED: "⚠️",
            HealthStatus.UNKNOWN: "❓",
        }.get(check.status, "❓")

        print(f"\n  {icon} {check.service_name}")
        print(f"     Type: {check.service_type}")
        print(f"     Status: {check.status}")
        print(f"     Response Time: {check.response_time_ms}ms")

        if check.error_details:
            print(f"     Error: {check.error_details}")

        if check.metadata:
            print(f"     Metadata: {check.metadata}")

    print(f"\n{'='*60}")

    return status


async def example_fastapi_integration():
    """Example of FastAPI integration."""
    from fastapi import FastAPI

    # Create FastAPI app
    app = FastAPI(title="QA-FRAMEWORK API")

    # Configure health checker
    checker = HealthChecker()
    checker.add_database_check(
        name="main_db",
        connection_string="postgresql://localhost/qa_framework",
        database_type=ServiceType.DATABASE_POSTGRESQL,
    )
    checker.add_redis_check("cache", "localhost", 6379)

    # Add health router
    health_router = create_health_router(checker)
    app.include_router(health_router)

    # Mark app as ready on startup
    @app.on_event("startup")
    async def startup():
        if hasattr(health_router, "set_startup_complete"):
            health_router.set_startup_complete()

    print("FastAPI app configured with health endpoints:")
    print("  GET /health/live     - Liveness probe")
    print("  GET /health/ready    - Readiness probe")
    print("  GET /health/startup  - Startup probe")
    print("  GET /health/status   - Detailed status")
    print("  GET /health/checks   - List registered checks")

    return app


if __name__ == "__main__":
    # Run example
    asyncio.run(example_health_check())
