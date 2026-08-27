"""
Pytest configuration and fixtures

This file configures pytest to work with the backend module structure.
"""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from dotenv import load_dotenv

# Mock Redis to avoid connection errors during import
_mock_redis = MagicMock()
_mock_redis.Redis = MagicMock(return_value=MagicMock(ping=MagicMock(return_value=True)))
_mock_redis.from_url = MagicMock(return_value=MagicMock(ping=MagicMock(return_value=True)))
sys.modules.setdefault("redis", _mock_redis)
sys.modules.setdefault("redis.asyncio", MagicMock())
# Keep ``from redis.exceptions import RedisError`` importable under the
# mock (used by the refresh-token store); Exception keeps except-clauses
# functional. Suites that need the REAL client pop these entries first.
_mock_exceptions = MagicMock()
_mock_exceptions.RedisError = Exception
sys.modules.setdefault("redis.exceptions", _mock_exceptions)

# Add the backend directory to Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# Ensure the backend module can be imported
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# Load environment variables from .env files
env_file = backend_dir / ".env"
if env_file.exists():
    load_dotenv(env_file)
    print(f"Loaded environment from: {env_file}")
else:
    # Try project root .env
    project_root = backend_dir.parent.parent
    root_env = project_root / ".env"
    if root_env.exists():
        load_dotenv(root_env)
        print(f"Loaded environment from: {root_env}")

# Local Redis fallback for CI/testing (no credentials; redis is mocked in tests)
if not os.getenv("REDIS_URL"):
    os.environ["REDIS_URL"] = "redis://127.0.0.1:6379/0"

print(f"Backend directory: {backend_dir}")
print(f"Python path: {sys.path[:3]}")  # Show first 3 paths

# Configure logging before any tests run
from core.logging_config import configure_logging

configure_logging(log_level="WARNING", environment="test")


async def _purge_shared_rate_limit_keys() -> None:
    """Delete ``ratelimit:*`` keys left in the shared Redis by test traffic.

    Best-effort: a no-op when ``redis.asyncio`` is still the conftest
    MagicMock or when no local Redis is reachable.
    """
    try:
        import redis.asyncio as aioredis

        cleanup = aioredis.from_url(
            os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0"),
            decode_responses=True,
        )
        try:
            async for key in cleanup.scan_iter("ratelimit:*"):
                await cleanup.delete(key)
        finally:
            try:
                await cleanup.aclose()
            except AttributeError:  # older redis-py names it close()
                await cleanup.close()
    except Exception:
        pass


async def _aclose_client(client) -> None:
    """Close an async Redis client regardless of redis-py version."""
    close = getattr(client, "aclose", None) or getattr(client, "close", None)
    if close is not None:
        await close()


@pytest.fixture(autouse=True)
async def _isolated_rate_limit_redis():
    """Keep the shared async Redis client loop-local and stateless per test.

    ``services.cache_service.get_redis_client()`` caches an aioredis
    singleton bound to the event loop of the first test that used it.
    pytest-asyncio gives every test a fresh loop, so later tests reused
    a pool tied to a closed loop -> ``Event loop is closed`` error logs
    from RateLimitMiddleware, plus real-Redis ``ratelimit:*`` counters
    leaking across tests/runs (100-entry hourly cap -> flaky 429s).

    Purge shared counters before each test; after each test close the
    stale client and reset the singleton so the next test lazily builds
    a fresh, loop-local one. Both steps are best-effort (mocks and
    closed-loop pools must never fail a test here).
    """
    await _purge_shared_rate_limit_keys()
    yield
    import services.cache_service as cache_service

    client = cache_service._async_redis_client
    cache_service._async_redis_client = None
    if client is None:
        return
    try:
        await _aclose_client(client)
    except Exception:
        pass
