"""Main Health Checker class for QA-FRAMEWORK services"""

import asyncio
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional

from src.infrastructure.health.checks import (
    check_database_health,
    check_external_api_health,
    check_internal_service_health,
    check_redis_health,
)
from src.infrastructure.health.models import (
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
from src.infrastructure.logger.logger import QALogger


class HealthChecker:
    """
    Main health checker class for QA-FRAMEWORK.

    Provides centralized health checking for all services including:
    - Database connectivity (PostgreSQL, MySQL, SQLite)
    - Redis cache connectivity
    - External API availability
    - Internal service status

    Features:
    - Configurable timeouts and retries
    - Parallel or sequential health checks
    - Result caching
    - Detailed error reporting

    Example:
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

        # Run all checks
        status = await checker.run_health_checks()
        print(f"Overall status: {status.overall_status}")
    """

    def __init__(self, config: Optional[HealthCheckConfig] = None):
        """
        Initialize health checker.

        Args:
            config: Health check configuration (optional)
        """
        self.config = config or HealthCheckConfig()
        self.logger = QALogger.get_logger("health-checker")

        # Registered health checks
        self._database_checks: Dict[str, DatabaseHealthCheckConfig] = {}
        self._redis_checks: Dict[str, RedisHealthCheckConfig] = {}
        self._external_api_checks: Dict[str, ExternalAPIHealthCheckConfig] = {}
        self._internal_service_checks: Dict[str, InternalServiceHealthCheckConfig] = {}
        self._custom_checks: Dict[str, Callable[[], HealthCheckResult]] = {}

        # Cached results
        self._cached_results: Optional[AggregatedHealthStatus] = None
        self._cache_timestamp: Optional[datetime] = None

    def add_database_check(
        self,
        name: str,
        connection_string: str,
        database_type: ServiceType,
        test_query: str = "SELECT 1",
    ) -> "HealthChecker":
        """
        Add a database health check.

        Args:
            name: Unique name for this check
            connection_string: Database connection string
            database_type: Type of database (postgresql, mysql, sqlite)
            test_query: Query to test connectivity

        Returns:
            Self for chaining
        """
        self._database_checks[name] = DatabaseHealthCheckConfig(
            connection_string=connection_string,
            database_type=database_type,
            test_query=test_query,
        )
        self.logger.info(f"Added database health check: {name}")
        return self

    def add_redis_check(
        self,
        name: str,
        host: str = "localhost",
        port: int = 6379,
        password: Optional[str] = None,
        db: int = 0,
    ) -> "HealthChecker":
        """
        Add a Redis health check.

        Args:
            name: Unique name for this check
            host: Redis host
            port: Redis port
            password: Redis password
            db: Redis database number

        Returns:
            Self for chaining
        """
        self._redis_checks[name] = RedisHealthCheckConfig(
            host=host,
            port=port,
            password=password,
            db=db,
        )
        self.logger.info(f"Added Redis health check: {name}")
        return self

    def add_external_api_check(
        self,
        name: str,
        url: str,
        method: str = "GET",
        expected_status_codes: Optional[List[int]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout_seconds: float = 10.0,
        required: bool = True,
    ) -> "HealthChecker":
        """
        Add an external API health check.

        Args:
            name: Unique name for this check
            url: API URL to check
            method: HTTP method
            expected_status_codes: Expected status codes
            headers: Request headers
            timeout_seconds: Request timeout
            required: Whether this API is required for healthy status

        Returns:
            Self for chaining
        """
        self._external_api_checks[name] = ExternalAPIHealthCheckConfig(
            name=name,
            url=url,
            method=method,
            expected_status_codes=expected_status_codes or [200],
            headers=headers or {},
            timeout_seconds=timeout_seconds,
            required=required,
        )
        self.logger.info(f"Added external API health check: {name}")
        return self

    def add_internal_service_check(
        self,
        name: str,
        health_endpoint: str,
        timeout_seconds: float = 5.0,
        required: bool = True,
    ) -> "HealthChecker":
        """
        Add an internal service health check.

        Args:
            name: Unique name for this check
            health_endpoint: Health endpoint URL
            timeout_seconds: Request timeout
            required: Whether this service is required for healthy status

        Returns:
            Self for chaining
        """
        self._internal_service_checks[name] = InternalServiceHealthCheckConfig(
            name=name,
            health_endpoint=health_endpoint,
            timeout_seconds=timeout_seconds,
            required=required,
        )
        self.logger.info(f"Added internal service health check: {name}")
        return self

    def add_custom_check(
        self,
        name: str,
        check_func: Callable[[], HealthCheckResult],
    ) -> "HealthChecker":
        """
        Add a custom health check function.

        Args:
            name: Unique name for this check
            check_func: Async function that returns HealthCheckResult

        Returns:
            Self for chaining
        """
        self._custom_checks[name] = check_func
        self.logger.info(f"Added custom health check: {name}")
        return self

    def remove_check(self, name: str) -> "HealthChecker":
        """
        Remove a health check by name.

        Args:
            name: Name of the check to remove

        Returns:
            Self for chaining
        """
        removed = False
        for check_dict in [
            self._database_checks,
            self._redis_checks,
            self._external_api_checks,
            self._internal_service_checks,
            self._custom_checks,
        ]:
            if name in check_dict:
                del check_dict[name]
                removed = True
                break

        if removed:
            self.logger.info(f"Removed health check: {name}")
        else:
            self.logger.warning(f"Health check not found: {name}")

        return self

    def clear_all_checks(self) -> "HealthChecker":
        """
        Remove all registered health checks.

        Returns:
            Self for chaining
        """
        self._database_checks.clear()
        self._redis_checks.clear()
        self._external_api_checks.clear()
        self._internal_service_checks.clear()
        self._custom_checks.clear()
        self._cached_results = None
        self._cache_timestamp = None
        self.logger.info("Cleared all health checks")
        return self

    async def run_health_checks(
        self,
        use_cache: bool = True,
    ) -> AggregatedHealthStatus:
        """
        Run all registered health checks.

        Args:
            use_cache: Whether to use cached results if available

        Returns:
            AggregatedHealthStatus with all results
        """
        # Check cache
        if use_cache and self._is_cache_valid():
            self.logger.debug("Returning cached health check results")
            return self._cached_results

        start_time = time.time()
        self.logger.info("Starting health checks...")

        # Prepare all check coroutines
        check_tasks = []
        check_names = []

        # Database checks
        for name, config in self._database_checks.items():
            check_tasks.append(
                self._run_with_retry(check_database_health, config, self.config.timeout_seconds)
            )
            check_names.append(f"db:{name}")

        # Redis checks
        for name, config in self._redis_checks.items():
            check_tasks.append(
                self._run_with_retry(check_redis_health, config, self.config.timeout_seconds)
            )
            check_names.append(f"redis:{name}")

        # External API checks
        for name, config in self._external_api_checks.items():
            check_tasks.append(self._run_with_retry(check_external_api_health, config))
            check_names.append(f"api:{name}")

        # Internal service checks
        for name, config in self._internal_service_checks.items():
            check_tasks.append(self._run_with_retry(check_internal_service_health, config))
            check_names.append(f"service:{name}")

        # Custom checks
        for name, check_func in self._custom_checks.items():
            check_tasks.append(self._run_custom_check(check_func))
            check_names.append(f"custom:{name}")

        # Run checks
        if self.config.parallel_checks and check_tasks:
            results = await asyncio.gather(*check_tasks, return_exceptions=True)
        else:
            results = []
            for task in check_tasks:
                try:
                    result = await task
                    results.append(result)
                except Exception as e:
                    results.append(e)

        # Process results
        health_results: List[HealthCheckResult] = []
        for name, result in zip(check_names, results):
            if isinstance(result, Exception):
                health_results.append(
                    HealthCheckResult(
                        service_name=name,
                        service_type=ServiceType.INTERNAL_SERVICE,
                        status=HealthStatus.UNHEALTHY,
                        response_time_ms=0,
                        error_details=str(result),
                        error_type=type(result).__name__.lower(),
                    )
                )
            else:
                health_results.append(result)

        # Calculate overall status
        overall_status = self._calculate_overall_status(health_results)

        # Build summary
        summary = self._build_summary(health_results, time.time() - start_time)

        # Create aggregated status
        aggregated = AggregatedHealthStatus(
            overall_status=overall_status,
            timestamp=datetime.now(timezone.utc),
            checks=health_results,
            summary=summary,
        )

        # Cache results
        self._cached_results = aggregated
        self._cache_timestamp = datetime.now(timezone.utc)

        self.logger.info(
            f"Health checks completed: {overall_status} "
            f"({len(health_results)} checks, {summary['total_time_ms']:.2f}ms)"
        )

        return aggregated

    async def _run_with_retry(self, check_func: Callable, *args, **kwargs) -> HealthCheckResult:
        """Run a health check with retry logic."""
        last_error: Optional[Exception] = None

        for attempt in range(self.config.retry_count):
            try:
                return await check_func(*args, **kwargs)
            except Exception as e:
                last_error = e
                if attempt < self.config.retry_count - 1:
                    await asyncio.sleep(self.config.retry_delay_seconds)

        # All retries failed
        return HealthCheckResult(
            service_name="retry_failed",
            service_type=ServiceType.INTERNAL_SERVICE,
            status=HealthStatus.UNHEALTHY,
            response_time_ms=0,
            error_details=str(last_error),
            error_type=type(last_error).__name__.lower() if last_error else "unknown",
        )

    async def _run_custom_check(
        self,
        check_func: Callable[[], HealthCheckResult],
    ) -> HealthCheckResult:
        """Run a custom health check function."""
        try:
            result = check_func()
            if asyncio.iscoroutine(result):
                result = await result
            return result
        except Exception as e:
            return HealthCheckResult(
                service_name="custom_check",
                service_type=ServiceType.INTERNAL_SERVICE,
                status=HealthStatus.UNHEALTHY,
                response_time_ms=0,
                error_details=str(e),
                error_type=type(e).__name__.lower(),
            )

    def _is_cache_valid(self) -> bool:
        """Check if cached results are still valid."""
        if self._cached_results is None or self._cache_timestamp is None:
            return False

        cache_age = datetime.now(timezone.utc) - self._cache_timestamp
        return cache_age < timedelta(seconds=self.config.cache_results_seconds)

    def _calculate_overall_status(
        self,
        results: List[HealthCheckResult],
    ) -> HealthStatus:
        """Calculate overall health status from individual results."""
        if not results:
            return HealthStatus.UNKNOWN

        statuses = [r.status for r in results]

        # If any required service is unhealthy, overall is unhealthy
        if HealthStatus.UNHEALTHY in statuses:
            # Check if it's a required service
            for result in results:
                if result.status == HealthStatus.UNHEALTHY:
                    # For now, treat all as required unless configured otherwise
                    return HealthStatus.UNHEALTHY

        # If any service is degraded, overall is degraded
        if HealthStatus.DEGRADED in statuses:
            return HealthStatus.DEGRADED

        # All healthy
        if all(s == HealthStatus.HEALTHY for s in statuses):
            return HealthStatus.HEALTHY

        return HealthStatus.UNKNOWN

    def _build_summary(
        self,
        results: List[HealthCheckResult],
        total_time: float,
    ) -> Dict[str, Any]:
        """Build summary statistics from results."""
        status_counts = {
            HealthStatus.HEALTHY: 0,
            HealthStatus.UNHEALTHY: 0,
            HealthStatus.DEGRADED: 0,
            HealthStatus.UNKNOWN: 0,
        }

        total_response_time = 0.0
        services_by_type: Dict[str, List[str]] = {}

        for result in results:
            status_counts[result.status] += 1
            total_response_time += result.response_time_ms

            service_type = result.service_type
            if service_type not in services_by_type:
                services_by_type[service_type] = []
            services_by_type[service_type].append(result.service_name)

        healthy_count = status_counts[HealthStatus.HEALTHY]
        total_count = len(results)

        return {
            "total_checks": total_count,
            "healthy_count": healthy_count,
            "unhealthy_count": status_counts[HealthStatus.UNHEALTHY],
            "degraded_count": status_counts[HealthStatus.DEGRADED],
            "unknown_count": status_counts[HealthStatus.UNKNOWN],
            "health_percentage": (
                round((healthy_count / total_count * 100), 2) if total_count > 0 else 0
            ),
            "total_time_ms": round(total_time * 1000, 2),
            "average_response_time_ms": (
                round(total_response_time / total_count, 2) if total_count > 0 else 0
            ),
            "services_by_type": services_by_type,
        }

    def get_registered_checks(self) -> Dict[str, List[str]]:
        """Get list of all registered health checks."""
        return {
            "database": list(self._database_checks.keys()),
            "redis": list(self._redis_checks.keys()),
            "external_api": list(self._external_api_checks.keys()),
            "internal_service": list(self._internal_service_checks.keys()),
            "custom": list(self._custom_checks.keys()),
        }

    def invalidate_cache(self) -> None:
        """Invalidate cached health check results."""
        self._cached_results = None
        self._cache_timestamp = None
        self.logger.debug("Health check cache invalidated")


# Singleton instance for convenience
_default_health_checker: Optional[HealthChecker] = None


def get_health_checker() -> HealthChecker:
    """Get the default health checker instance."""
    global _default_health_checker
    if _default_health_checker is None:
        _default_health_checker = HealthChecker()
    return _default_health_checker


def set_health_checker(checker: HealthChecker) -> None:
    """Set the default health checker instance."""
    global _default_health_checker
    _default_health_checker = checker
