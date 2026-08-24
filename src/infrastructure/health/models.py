"""Health check data models"""

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class HealthStatus(str, Enum):
    """Health status enumeration"""

    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


class ServiceType(str, Enum):
    """Types of services that can be health checked"""

    DATABASE_POSTGRESQL = "postgresql"
    DATABASE_MYSQL = "mysql"
    DATABASE_SQLITE = "sqlite"
    REDIS = "redis"
    EXTERNAL_API = "external_api"
    INTERNAL_SERVICE = "internal_service"
    CACHE = "cache"
    QUEUE = "queue"


def _utc_now() -> datetime:
    """Get current UTC time in a timezone-aware manner."""
    return datetime.now(UTC)


class HealthCheckResult(BaseModel):
    """Individual health check result"""

    service_name: str = Field(..., description="Name of the service being checked")
    service_type: ServiceType = Field(..., description="Type of service")
    status: HealthStatus = Field(..., description="Health status")
    response_time_ms: float = Field(..., description="Response time in milliseconds")
    last_check_timestamp: datetime = Field(
        default_factory=_utc_now, description="Timestamp of last check"
    )
    error_details: str | None = Field(None, description="Error message if unhealthy")
    error_type: str | None = Field(None, description="Type of error (timeout, connection, etc.)")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata about the service"
    )

    model_config = ConfigDict(
        use_enum_values=True,
        extra="allow",  # Allow extra fields for flexibility
    )


class AggregatedHealthStatus(BaseModel):
    """Aggregated health status for all services"""

    overall_status: HealthStatus = Field(..., description="Overall system health")
    timestamp: datetime = Field(default_factory=_utc_now, description="Timestamp of health check")
    checks: list[HealthCheckResult] = Field(
        default_factory=list, description="Individual health check results"
    )
    summary: dict[str, Any] = Field(default_factory=dict, description="Summary statistics")

    model_config = ConfigDict(
        use_enum_values=True,
        extra="allow",  # Allow extra fields for flexibility
    )


class HealthCheckConfig(BaseModel):
    """Configuration for health checks"""

    timeout_seconds: float = Field(5.0, description="Timeout for each health check")
    retry_count: int = Field(3, description="Number of retries on failure")
    retry_delay_seconds: float = Field(1.0, description="Delay between retries")
    cache_results_seconds: int = Field(30, description="Cache health results for this many seconds")
    parallel_checks: bool = Field(True, description="Run health checks in parallel")

    # Thresholds for degraded status
    degraded_response_time_ms: float = Field(
        1000.0, description="Response time threshold for degraded status"
    )
    critical_response_time_ms: float = Field(
        5000.0, description="Response time threshold for critical degradation"
    )


class DatabaseHealthCheckConfig(BaseModel):
    """Configuration for database health checks"""

    connection_string: str = Field(..., description="Database connection string")
    database_type: ServiceType = Field(..., description="Type of database")
    test_query: str = Field("SELECT 1", description="Query to test database connectivity")
    pool_size: int | None = Field(None, description="Connection pool size")


class RedisHealthCheckConfig(BaseModel):
    """Configuration for Redis health checks"""

    host: str = Field("localhost", description="Redis host")
    port: int = Field(6379, description="Redis port")
    password: str | None = Field(None, description="Redis password")
    db: int = Field(0, description="Redis database number")
    socket_timeout: float = Field(5.0, description="Socket timeout in seconds")
    socket_connect_timeout: float = Field(5.0, description="Connection timeout in seconds")


class ExternalAPIHealthCheckConfig(BaseModel):
    """Configuration for external API health checks"""

    name: str = Field(..., description="Name of the external API")
    url: str = Field(..., description="URL to check")
    method: str = Field("GET", description="HTTP method")
    expected_status_codes: list[int] = Field(
        default_factory=lambda: [200], description="Expected status codes"
    )
    headers: dict[str, str] = Field(
        default_factory=dict, description="Headers to send with request"
    )
    timeout_seconds: float = Field(10.0, description="Request timeout")
    required: bool = Field(True, description="Whether this API is required for healthy status")


class InternalServiceHealthCheckConfig(BaseModel):
    """Configuration for internal service health checks"""

    name: str = Field(..., description="Name of the internal service")
    health_endpoint: str = Field(..., description="Health check endpoint URL")
    timeout_seconds: float = Field(5.0, description="Request timeout")
    required: bool = Field(True, description="Whether this service is required for healthy status")
