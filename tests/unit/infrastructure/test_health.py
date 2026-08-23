"""Unit tests for health module"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.infrastructure.health import (
    AggregatedHealthStatus,
    DatabaseHealthCheckConfig,
    ExternalAPIHealthCheckConfig,
    HealthCheckConfig,
    HealthChecker,
    HealthCheckResult,
    HealthStatus,
    InternalServiceHealthCheckConfig,
    RedisHealthCheckConfig,
    ServiceType,
    check_database_health,
    check_external_api_health,
    check_internal_service_health,
    check_redis_health,
)


class TestHealthModels:
    """Tests for health check models."""

    def test_health_status_enum(self):
        """Test HealthStatus enum values."""
        assert HealthStatus.HEALTHY == "healthy"
        assert HealthStatus.UNHEALTHY == "unhealthy"
        assert HealthStatus.DEGRADED == "degraded"
        assert HealthStatus.UNKNOWN == "unknown"

    def test_service_type_enum(self):
        """Test ServiceType enum values."""
        assert ServiceType.DATABASE_POSTGRESQL == "postgresql"
        assert ServiceType.DATABASE_MYSQL == "mysql"
        assert ServiceType.REDIS == "redis"
        assert ServiceType.EXTERNAL_API == "external_api"
        assert ServiceType.INTERNAL_SERVICE == "internal_service"

    def test_health_check_result(self):
        """Test HealthCheckResult model."""
        result = HealthCheckResult(
            service_name="test_service",
            service_type=ServiceType.REDIS,
            status=HealthStatus.HEALTHY,
            response_time_ms=10.5,
            metadata={"version": "1.0"},
        )

        assert result.service_name == "test_service"
        assert result.status == HealthStatus.HEALTHY
        assert result.response_time_ms == 10.5
        assert result.error_details is None
        assert result.metadata["version"] == "1.0"
        assert isinstance(result.last_check_timestamp, datetime)

    def test_health_check_result_with_error(self):
        """Test HealthCheckResult with error details."""
        result = HealthCheckResult(
            service_name="failing_service",
            service_type=ServiceType.DATABASE_POSTGRESQL,
            status=HealthStatus.UNHEALTHY,
            response_time_ms=5000.0,
            error_details="Connection refused",
            error_type="connection_error",
        )

        assert result.status == HealthStatus.UNHEALTHY
        assert result.error_details == "Connection refused"
        assert result.error_type == "connection_error"

    def test_aggregated_health_status(self):
        """Test AggregatedHealthStatus model."""
        results = [
            HealthCheckResult(
                service_name="db",
                service_type=ServiceType.DATABASE_POSTGRESQL,
                status=HealthStatus.HEALTHY,
                response_time_ms=5.0,
            ),
            HealthCheckResult(
                service_name="redis",
                service_type=ServiceType.REDIS,
                status=HealthStatus.HEALTHY,
                response_time_ms=2.0,
            ),
        ]

        aggregated = AggregatedHealthStatus(
            overall_status=HealthStatus.HEALTHY,
            checks=results,
            summary={"healthy_count": 2, "total_checks": 2},
        )

        assert aggregated.overall_status == HealthStatus.HEALTHY
        assert len(aggregated.checks) == 2
        assert aggregated.summary["healthy_count"] == 2


class TestHealthChecker:
    """Tests for HealthChecker class."""

    @pytest.fixture
    def health_checker(self):
        """Create health checker instance."""
        return HealthChecker()

    def test_initialization(self, health_checker):
        """Test health checker initialization."""
        assert health_checker is not None
        assert health_checker.config is not None
        assert health_checker.config.timeout_seconds == 5.0

    def test_add_database_check(self, health_checker):
        """Test adding database health check."""
        result = health_checker.add_database_check(
            name="main_db",
            connection_string="postgresql://localhost/test",
            database_type=ServiceType.DATABASE_POSTGRESQL,
        )

        # Should return self for chaining
        assert result is health_checker

        # Check should be registered
        checks = health_checker.get_registered_checks()
        assert "main_db" in checks["database"]

    def test_add_redis_check(self, health_checker):
        """Test adding Redis health check."""
        health_checker.add_redis_check(name="cache", host="localhost", port=6379)

        checks = health_checker.get_registered_checks()
        assert "cache" in checks["redis"]

    def test_add_external_api_check(self, health_checker):
        """Test adding external API health check."""
        health_checker.add_external_api_check(
            name="payment_api", url="https://api.example.com/health", required=False
        )

        checks = health_checker.get_registered_checks()
        assert "payment_api" in checks["external_api"]

    def test_add_internal_service_check(self, health_checker):
        """Test adding internal service health check."""
        health_checker.add_internal_service_check(
            name="auth_service", health_endpoint="http://auth:8080/health"
        )

        checks = health_checker.get_registered_checks()
        assert "auth_service" in checks["internal_service"]

    def test_add_custom_check(self, health_checker):
        """Test adding custom health check."""

        async def custom_check():
            return HealthCheckResult(
                service_name="custom",
                service_type=ServiceType.INTERNAL_SERVICE,
                status=HealthStatus.HEALTHY,
                response_time_ms=1.0,
            )

        health_checker.add_custom_check("custom", custom_check)

        checks = health_checker.get_registered_checks()
        assert "custom" in checks["custom"]

    def test_remove_check(self, health_checker):
        """Test removing health check."""
        health_checker.add_redis_check("cache", "localhost", 6379)

        checks = health_checker.get_registered_checks()
        assert "cache" in checks["redis"]

        health_checker.remove_check("cache")

        checks = health_checker.get_registered_checks()
        assert "cache" not in checks["redis"]

    def test_clear_all_checks(self, health_checker):
        """Test clearing all health checks."""
        health_checker.add_redis_check("cache", "localhost", 6379)
        health_checker.add_database_check(
            "db", "postgresql://localhost/test", ServiceType.DATABASE_POSTGRESQL
        )

        health_checker.clear_all_checks()

        checks = health_checker.get_registered_checks()
        assert len(checks["redis"]) == 0
        assert len(checks["database"]) == 0

    def test_chaining(self, health_checker):
        """Test method chaining for configuration."""
        result = (
            health_checker.add_database_check(
                "db", "postgresql://localhost/test", ServiceType.DATABASE_POSTGRESQL
            )
            .add_redis_check("cache", "localhost", 6379)
            .add_external_api_check("api", "https://api.example.com/health")
        )

        assert result is health_checker

        checks = health_checker.get_registered_checks()
        assert len(checks["database"]) == 1
        assert len(checks["redis"]) == 1
        assert len(checks["external_api"]) == 1

    @pytest.mark.asyncio
    async def test_run_health_checks_empty(self, health_checker):
        """Test running health checks with no checks registered."""
        status = await health_checker.run_health_checks()

        assert status.overall_status == HealthStatus.UNKNOWN
        assert len(status.checks) == 0
        assert status.summary["total_checks"] == 0

    @pytest.mark.asyncio
    async def test_run_health_checks_with_custom(self, health_checker):
        """Test running health checks with custom check."""

        async def custom_check():
            return HealthCheckResult(
                service_name="custom",
                service_type=ServiceType.INTERNAL_SERVICE,
                status=HealthStatus.HEALTHY,
                response_time_ms=1.0,
            )

        health_checker.add_custom_check("custom", custom_check)

        status = await health_checker.run_health_checks()

        assert status.overall_status == HealthStatus.HEALTHY
        assert len(status.checks) == 1
        assert status.checks[0].status == HealthStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_cache_invalidation(self, health_checker):
        """Test health check result caching."""
        call_count = 0

        async def custom_check():
            nonlocal call_count
            call_count += 1
            return HealthCheckResult(
                service_name="custom",
                service_type=ServiceType.INTERNAL_SERVICE,
                status=HealthStatus.HEALTHY,
                response_time_ms=1.0,
            )

        health_checker.add_custom_check("custom", custom_check)
        health_checker.config.cache_results_seconds = 60

        # First call
        await health_checker.run_health_checks()
        assert call_count == 1

        # Second call should use cache
        await health_checker.run_health_checks(use_cache=True)
        assert call_count == 1

        # Third call without cache
        await health_checker.run_health_checks(use_cache=False)
        assert call_count == 2

        # Invalidate cache and run again
        health_checker.invalidate_cache()
        await health_checker.run_health_checks(use_cache=True)
        assert call_count == 3


class TestDatabaseHealthCheck:
    """Tests for database health check function."""

    @pytest.mark.asyncio
    async def test_check_database_health_missing_driver(self):
        """Test database health check when driver is missing."""
        config = DatabaseHealthCheckConfig(
            connection_string="postgresql://localhost/test",
            database_type=ServiceType.DATABASE_POSTGRESQL,
        )

        with patch.dict("sys.modules", {"asyncpg": None, "psycopg": None}):
            result = await check_database_health(config)

            assert result.status == HealthStatus.UNHEALTHY
            # Check for install instruction (case insensitive)
            assert "install" in result.error_details.lower()

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Requires asyncpg module to be installed for mocking")
    async def test_check_database_health_timeout(self):
        """Test database health check timeout."""
        config = DatabaseHealthCheckConfig(
            connection_string="postgresql://localhost/test",
            database_type=ServiceType.DATABASE_POSTGRESQL,
        )

        with patch("asyncpg.connect", new_callable=AsyncMock) as mock_connect:
            mock_connect.side_effect = TimeoutError()

            result = await check_database_health(config, timeout_seconds=1.0)

            assert result.status == HealthStatus.UNHEALTHY
            assert result.error_type == "timeout"


class TestRedisHealthCheck:
    """Tests for Redis health check function."""

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Requires redis module to be installed for mocking")
    async def test_check_redis_health_connection_refused(self):
        """Test Redis health check when connection refused."""
        config = RedisHealthCheckConfig(host="localhost", port=6379)

        with patch("redis.asyncio.Redis") as mock_redis:
            mock_client = MagicMock()
            mock_client.ping = AsyncMock(side_effect=ConnectionRefusedError())
            mock_client.close = AsyncMock()
            mock_redis.return_value = mock_client

            result = await check_redis_health(config)

            assert result.status == HealthStatus.UNHEALTHY
            assert result.error_type == "connection_refused"


class TestExternalAPIHealthCheck:
    """Tests for external API health check function."""

    @pytest.mark.asyncio
    async def test_check_external_api_healthy(self):
        """Test external API health check when healthy."""
        config = ExternalAPIHealthCheckConfig(
            name="test_api", url="https://api.example.com/health", expected_status_codes=[200]
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = MagicMock()
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_instance.request = AsyncMock(return_value=mock_response)
            mock_client.return_value = mock_instance

            result = await check_external_api_health(config)

            assert result.status == HealthStatus.HEALTHY
            assert result.metadata["status_code"] == 200

    @pytest.mark.asyncio
    async def test_check_external_api_unexpected_status(self):
        """Test external API health check with unexpected status."""
        config = ExternalAPIHealthCheckConfig(
            name="test_api",
            url="https://api.example.com/health",
            expected_status_codes=[200],
            required=True,
        )

        mock_response = MagicMock()
        mock_response.status_code = 503
        mock_response.headers = {}

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = MagicMock()
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_instance.request = AsyncMock(return_value=mock_response)
            mock_client.return_value = mock_instance

            result = await check_external_api_health(config)

            assert result.status == HealthStatus.UNHEALTHY
            assert "503" in result.error_details


class TestInternalServiceHealthCheck:
    """Tests for internal service health check function."""

    @pytest.mark.asyncio
    async def test_check_internal_service_healthy(self):
        """Test internal service health check when healthy."""
        config = InternalServiceHealthCheckConfig(
            name="auth_service", health_endpoint="http://auth:8080/health"
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(return_value={"status": "healthy"})

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = MagicMock()
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_instance.get = AsyncMock(return_value=mock_response)
            mock_client.return_value = mock_instance

            result = await check_internal_service_health(config)

            assert result.status == HealthStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_check_internal_service_degraded(self):
        """Test internal service health check when degraded."""
        config = InternalServiceHealthCheckConfig(
            name="auth_service", health_endpoint="http://auth:8080/health"
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(return_value={"status": "degraded"})

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = MagicMock()
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_instance.get = AsyncMock(return_value=mock_response)
            mock_client.return_value = mock_instance

            result = await check_internal_service_health(config)

            assert result.status == HealthStatus.DEGRADED


class TestHealthCheckConfig:
    """Tests for health check configuration."""

    def test_default_config(self):
        """Test default configuration values."""
        config = HealthCheckConfig()

        assert config.timeout_seconds == 5.0
        assert config.retry_count == 3
        assert config.retry_delay_seconds == 1.0
        assert config.cache_results_seconds == 30
        assert config.parallel_checks is True
        assert config.degraded_response_time_ms == 1000.0

    def test_custom_config(self):
        """Test custom configuration values."""
        config = HealthCheckConfig(timeout_seconds=10.0, retry_count=5, parallel_checks=False)

        assert config.timeout_seconds == 10.0
        assert config.retry_count == 5
        assert config.parallel_checks is False
