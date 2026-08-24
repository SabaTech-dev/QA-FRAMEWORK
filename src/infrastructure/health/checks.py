"""Individual health check functions for various services"""

import asyncio
import time
from typing import Any

from src.infrastructure.health.models import (
    DatabaseHealthCheckConfig,
    ExternalAPIHealthCheckConfig,
    HealthCheckResult,
    HealthStatus,
    InternalServiceHealthCheckConfig,
    RedisHealthCheckConfig,
    ServiceType,
)


async def check_database_health(
    config: DatabaseHealthCheckConfig,
    timeout_seconds: float = 5.0,
) -> HealthCheckResult:
    """
    Check database connectivity (PostgreSQL/MySQL).

    Args:
        config: Database health check configuration
        timeout_seconds: Timeout for the health check

    Returns:
        HealthCheckResult with database status
    """
    start_time = time.time()
    error_details: str | None = None
    error_type: str | None = None
    metadata: dict[str, Any] = {}

    try:
        if config.database_type == ServiceType.DATABASE_POSTGRESQL:
            result = await _check_postgresql_health(config, timeout_seconds)
        elif config.database_type == ServiceType.DATABASE_MYSQL:
            result = await _check_mysql_health(config, timeout_seconds)
        elif config.database_type == ServiceType.DATABASE_SQLITE:
            result = await _check_sqlite_health(config, timeout_seconds)
        else:
            raise ValueError(f"Unsupported database type: {config.database_type}")

        return result

    except TimeoutError:
        error_details = f"Database health check timed out after {timeout_seconds}s"
        error_type = "timeout"
        status = HealthStatus.UNHEALTHY
    except ConnectionRefusedError as e:
        error_details = f"Connection refused: {e!s}"
        error_type = "connection_refused"
        status = HealthStatus.UNHEALTHY
    except Exception as e:
        error_details = str(e)
        error_type = type(e).__name__.lower()
        status = HealthStatus.UNHEALTHY

    response_time_ms = round((time.time() - start_time) * 1000, 2)

    return HealthCheckResult(
        service_name=f"{config.database_type.value}_database",
        service_type=config.database_type,
        status=status,
        response_time_ms=response_time_ms,
        error_details=error_details,
        error_type=error_type,
        metadata=metadata,
    )


async def _check_postgresql_health(
    config: DatabaseHealthCheckConfig,
    timeout_seconds: float,
) -> HealthCheckResult:
    """Check PostgreSQL database health."""
    start_time = time.time()
    metadata: dict[str, Any] = {}

    try:
        # Try to import asyncpg
        import asyncpg

        # Parse connection string or use direct connection
        conn = await asyncio.wait_for(
            asyncpg.connect(config.connection_string), timeout=timeout_seconds
        )

        try:
            # Execute test query
            _result = await conn.fetchval(config.test_query)

            # Get server version
            version = await conn.fetchval("SHOW server_version")
            metadata["server_version"] = version

            # Get connection info
            metadata["database"] = conn.db
            metadata["user"] = conn.user
            metadata["host"] = conn.addr

            response_time_ms = round((time.time() - start_time) * 1000, 2)

            return HealthCheckResult(
                service_name="postgresql_database",
                service_type=ServiceType.DATABASE_POSTGRESQL,
                status=HealthStatus.HEALTHY,
                response_time_ms=response_time_ms,
                metadata=metadata,
            )
        finally:
            await conn.close()

    except ImportError:
        # Fall back to psycopg if asyncpg not available
        return await _check_postgresql_psycopg(config, timeout_seconds)


async def _check_postgresql_psycopg(
    config: DatabaseHealthCheckConfig,
    timeout_seconds: float,
) -> HealthCheckResult:
    """Check PostgreSQL using psycopg (fallback)."""
    start_time = time.time()

    try:
        import psycopg

        async with await asyncio.wait_for(
            psycopg.AsyncConnection.connect(config.connection_string), timeout=timeout_seconds
        ) as conn:
            async with conn.cursor() as cur:
                await cur.execute(config.test_query)
                _result = await cur.fetchone()

            # Get server version
            async with conn.cursor() as cur:
                await cur.execute("SHOW server_version")
                version = (await cur.fetchone())[0]

            metadata = {"server_version": version}
            response_time_ms = round((time.time() - start_time) * 1000, 2)

            return HealthCheckResult(
                service_name="postgresql_database",
                service_type=ServiceType.DATABASE_POSTGRESQL,
                status=HealthStatus.HEALTHY,
                response_time_ms=response_time_ms,
                metadata=metadata,
            )
    except ImportError:
        raise ImportError(
            "Neither asyncpg nor psycopg is installed. "
            "Install with: pip install asyncpg or pip install psycopg[binary]"
        )


async def _check_mysql_health(
    config: DatabaseHealthCheckConfig,
    timeout_seconds: float,
) -> HealthCheckResult:
    """Check MySQL database health."""
    start_time = time.time()
    metadata: dict[str, Any] = {}

    try:
        import aiomysql

        # Parse connection string
        conn_params = _parse_mysql_connection_string(config.connection_string)

        conn = await asyncio.wait_for(aiomysql.connect(**conn_params), timeout=timeout_seconds)

        try:
            async with conn.cursor() as cur:
                await cur.execute(config.test_query)
                _result = await cur.fetchone()

            # Get server version
            async with conn.cursor() as cur:
                await cur.execute("SELECT VERSION()")
                version = (await cur.fetchone())[0]

            metadata["server_version"] = version

            response_time_ms = round((time.time() - start_time) * 1000, 2)

            return HealthCheckResult(
                service_name="mysql_database",
                service_type=ServiceType.DATABASE_MYSQL,
                status=HealthStatus.HEALTHY,
                response_time_ms=response_time_ms,
                metadata=metadata,
            )
        finally:
            conn.close()

    except ImportError:
        raise ImportError("aiomysql is not installed. Install with: pip install aiomysql")


async def _check_sqlite_health(
    config: DatabaseHealthCheckConfig,
    timeout_seconds: float,
) -> HealthCheckResult:
    """Check SQLite database health."""
    start_time = time.time()
    metadata: dict[str, Any] = {}

    try:
        import aiosqlite

        db_path = config.connection_string.replace("sqlite:///", "").replace("sqlite://", "")

        async with asyncio.wait_for(aiosqlite.connect(db_path), timeout=timeout_seconds) as conn:
            async with conn.execute(config.test_query) as cur:
                _result = await cur.fetchone()

            # Get SQLite version
            async with conn.execute("SELECT sqlite_version()") as cur:
                version = (await cur.fetchone())[0]

            metadata["server_version"] = version
            metadata["database_path"] = db_path

            response_time_ms = round((time.time() - start_time) * 1000, 2)

            return HealthCheckResult(
                service_name="sqlite_database",
                service_type=ServiceType.DATABASE_SQLITE,
                status=HealthStatus.HEALTHY,
                response_time_ms=response_time_ms,
                metadata=metadata,
            )

    except ImportError:
        raise ImportError("aiosqlite is not installed. Install with: pip install aiosqlite")


def _parse_mysql_connection_string(conn_str: str) -> dict[str, Any]:
    """Parse MySQL connection string into connection parameters."""
    from urllib.parse import urlparse

    parsed = urlparse(conn_str)

    params = {
        "host": parsed.hostname or "localhost",
        "port": parsed.port or 3306,
        "user": parsed.username,
        "password": parsed.password,
        "db": parsed.path.lstrip("/") if parsed.path else None,
    }

    return {k: v for k, v in params.items() if v is not None}


async def check_redis_health(
    config: RedisHealthCheckConfig,
    timeout_seconds: float = 5.0,
) -> HealthCheckResult:
    """
    Check Redis cache connectivity.

    Args:
        config: Redis health check configuration
        timeout_seconds: Timeout for the health check

    Returns:
        HealthCheckResult with Redis status
    """
    start_time = time.time()
    error_details: str | None = None
    error_type: str | None = None
    metadata: dict[str, Any] = {}

    try:
        import redis.asyncio as redis

        client = redis.Redis(
            host=config.host,
            port=config.port,
            password=config.password,
            db=config.db,
            socket_timeout=config.socket_timeout,
            socket_connect_timeout=config.socket_connect_timeout,
            decode_responses=True,
        )

        try:
            # Test connection with ping
            await asyncio.wait_for(client.ping(), timeout=timeout_seconds)

            # Get Redis info
            info = await client.info()

            # Test write/read
            test_key = f"health_check:{int(time.time())}"
            test_value = "health_test"
            await client.setex(test_key, 10, test_value)
            value = await client.get(test_key)
            await client.delete(test_key)

            if value != test_value:
                raise ValueError("Redis read/write test failed")

            # Collect metadata
            metadata["version"] = info.get("redis_version", "unknown")
            metadata["connected_clients"] = info.get("connected_clients", 0)
            metadata["used_memory"] = info.get("used_memory_human", "unknown")
            metadata["uptime_seconds"] = info.get("uptime_in_seconds", 0)

            # Calculate hit rate
            hits = info.get("keyspace_hits", 0)
            misses = info.get("keyspace_misses", 0)
            if hits + misses > 0:
                metadata["hit_rate_percent"] = round((hits / (hits + misses)) * 100, 2)

            response_time_ms = round((time.time() - start_time) * 1000, 2)

            # Determine if degraded (slow response)
            status = HealthStatus.HEALTHY
            if response_time_ms > 1000:
                status = HealthStatus.DEGRADED
                metadata["degraded_reason"] = "Slow response time"

            return HealthCheckResult(
                service_name="redis_cache",
                service_type=ServiceType.REDIS,
                status=status,
                response_time_ms=response_time_ms,
                metadata=metadata,
            )

        finally:
            await client.close()

    except TimeoutError:
        error_details = f"Redis health check timed out after {timeout_seconds}s"
        error_type = "timeout"
        status = HealthStatus.UNHEALTHY
    except ConnectionRefusedError:
        error_details = f"Connection refused to Redis at {config.host}:{config.port}"
        error_type = "connection_refused"
        status = HealthStatus.UNHEALTHY
    except ImportError:
        error_details = "redis package not installed. Install with: pip install redis"
        error_type = "dependency_missing"
        status = HealthStatus.UNHEALTHY
    except Exception as e:
        error_details = str(e)
        error_type = type(e).__name__.lower()
        status = HealthStatus.UNHEALTHY

    response_time_ms = round((time.time() - start_time) * 1000, 2)

    return HealthCheckResult(
        service_name="redis_cache",
        service_type=ServiceType.REDIS,
        status=status,
        response_time_ms=response_time_ms,
        error_details=error_details,
        error_type=error_type,
        metadata=metadata,
    )


async def check_external_api_health(
    config: ExternalAPIHealthCheckConfig,
) -> HealthCheckResult:
    """
    Check external API availability.

    Args:
        config: External API health check configuration

    Returns:
        HealthCheckResult with API status
    """
    start_time = time.time()
    error_details: str | None = None
    error_type: str | None = None
    metadata: dict[str, Any] = {}

    try:
        import httpx

        async with httpx.AsyncClient(timeout=config.timeout_seconds) as client:
            response = await client.request(
                method=config.method,
                url=config.url,
                headers=config.headers,
            )

            response_time_ms = round((time.time() - start_time) * 1000, 2)

            metadata["status_code"] = response.status_code
            metadata["content_type"] = response.headers.get("content-type", "unknown")

            if response.status_code in config.expected_status_codes:
                status = HealthStatus.HEALTHY

                # Check if degraded due to slow response
                if response_time_ms > config.timeout_seconds * 500:
                    status = HealthStatus.DEGRADED
                    metadata["degraded_reason"] = "Slow response time"

                return HealthCheckResult(
                    service_name=config.name,
                    service_type=ServiceType.EXTERNAL_API,
                    status=status,
                    response_time_ms=response_time_ms,
                    metadata=metadata,
                )
            else:
                error_details = f"Unexpected status code: {response.status_code}"
                error_type = "unexpected_status"
                status = HealthStatus.UNHEALTHY if config.required else HealthStatus.DEGRADED

    except httpx.TimeoutException:
        error_details = f"Request timed out after {config.timeout_seconds}s"
        error_type = "timeout"
        status = HealthStatus.UNHEALTHY if config.required else HealthStatus.DEGRADED
    except httpx.ConnectError as e:
        error_details = f"Connection failed: {e!s}"
        error_type = "connection_error"
        status = HealthStatus.UNHEALTHY if config.required else HealthStatus.DEGRADED
    except ImportError:
        error_details = "httpx package not installed. Install with: pip install httpx"
        error_type = "dependency_missing"
        status = HealthStatus.UNHEALTHY
    except Exception as e:
        error_details = str(e)
        error_type = type(e).__name__.lower()
        status = HealthStatus.UNHEALTHY if config.required else HealthStatus.DEGRADED

    response_time_ms = round((time.time() - start_time) * 1000, 2)

    return HealthCheckResult(
        service_name=config.name,
        service_type=ServiceType.EXTERNAL_API,
        status=status,
        response_time_ms=response_time_ms,
        error_details=error_details,
        error_type=error_type,
        metadata=metadata,
    )


async def check_internal_service_health(
    config: InternalServiceHealthCheckConfig,
) -> HealthCheckResult:
    """
    Check internal service status.

    Args:
        config: Internal service health check configuration

    Returns:
        HealthCheckResult with service status
    """
    start_time = time.time()
    error_details: str | None = None
    error_type: str | None = None
    metadata: dict[str, Any] = {}

    try:
        import httpx

        async with httpx.AsyncClient(timeout=config.timeout_seconds) as client:
            response = await client.get(config.health_endpoint)

            response_time_ms = round((time.time() - start_time) * 1000, 2)
            metadata["status_code"] = response.status_code

            if response.status_code == 200:
                # Try to parse response body for additional info
                try:
                    body = response.json()
                    metadata["response_body"] = body

                    # Check for health status in response
                    if "status" in body:
                        service_status = body["status"]
                        if service_status in ("healthy", "ok", "up"):
                            status = HealthStatus.HEALTHY
                        elif service_status in ("degraded", "warning"):
                            status = HealthStatus.DEGRADED
                        else:
                            status = HealthStatus.UNHEALTHY
                    else:
                        status = HealthStatus.HEALTHY

                except Exception:
                    status = HealthStatus.HEALTHY

                # Check for degraded due to slow response
                if status == HealthStatus.HEALTHY and response_time_ms > 1000:
                    status = HealthStatus.DEGRADED
                    metadata["degraded_reason"] = "Slow response time"

                return HealthCheckResult(
                    service_name=config.name,
                    service_type=ServiceType.INTERNAL_SERVICE,
                    status=status,
                    response_time_ms=response_time_ms,
                    metadata=metadata,
                )
            else:
                error_details = f"Health endpoint returned status {response.status_code}"
                error_type = "health_check_failed"
                status = HealthStatus.UNHEALTHY if config.required else HealthStatus.DEGRADED

    except httpx.TimeoutException:
        error_details = f"Request timed out after {config.timeout_seconds}s"
        error_type = "timeout"
        status = HealthStatus.UNHEALTHY if config.required else HealthStatus.DEGRADED
    except httpx.ConnectError as e:
        error_details = f"Connection failed: {e!s}"
        error_type = "connection_error"
        status = HealthStatus.UNHEALTHY if config.required else HealthStatus.DEGRADED
    except ImportError:
        error_details = "httpx package not installed. Install with: pip install httpx"
        error_type = "dependency_missing"
        status = HealthStatus.UNHEALTHY
    except Exception as e:
        error_details = str(e)
        error_type = type(e).__name__.lower()
        status = HealthStatus.UNHEALTHY if config.required else HealthStatus.DEGRADED

    response_time_ms = round((time.time() - start_time) * 1000, 2)

    return HealthCheckResult(
        service_name=config.name,
        service_type=ServiceType.INTERNAL_SERVICE,
        status=status,
        response_time_ms=response_time_ms,
        error_details=error_details,
        error_type=error_type,
        metadata=metadata,
    )
