"""
Test Caching Service

Implementa un sistema de caching eficiente para resultados de tests,
reduciendo el tiempo de ejecución y eliminando redundancias.

Usage:
    from services.cache_service import CacheService

    cache = CacheService()

    # Cache un test result
    result = cache.get_or_execute(
        key="test_suite_123_test_456",
        executor=lambda: execute_test("test_456"),
        ttl=3600  # 1 hour
    )
"""

import json
import logging
import os
from typing import Any, Callable, Optional, Dict
from datetime import datetime, timedelta

from config import settings
from src.infrastructure.cache.test_cache import TestCache
from src.infrastructure.cache.cache_stats import CacheStats

logger = logging.getLogger(__name__)

# Singleton async Redis client for rate limiting and other async consumers
_async_redis_client = None


def get_redis_client():
    """
    Get or create a singleton async Redis client.
    Used by RateLimitMiddleware and other async components.
    """
    global _async_redis_client
    if _async_redis_client is None:
        import redis.asyncio as aioredis
        redis_url = os.getenv("REDIS_URL")
        if not redis_url:
            # Use centralized settings (config.py) instead of raw os.getenv so
            # the connection target is driven by the same Settings instance used
            # across the app. Fallback to localhost keeps local dev working when
            # the host is explicitly unset/empty.
            redis_host = settings.redis_host or "localhost"
            redis_port = settings.redis_port
            redis_password = os.getenv("REDIS_PASSWORD")
            if redis_password:
                redis_url = f"redis://:{redis_password}@{redis_host}:{redis_port}/0"
            else:
                redis_url = f"redis://{redis_host}:{redis_port}/0"
        _async_redis_client = aioredis.from_url(redis_url, decode_responses=True)
    return _async_redis_client


class CacheService:
    """
    Servicio centralizado para caching de tests.

    Maneja la lógica de negocio para caching, incluyendo:
    - Invalidation inteligente
    - Hit/miss tracking
    - Performance metrics
    - Cache warming
    """

    def __init__(
        self,
        test_cache: Optional[TestCache] = None,
        stats: Optional[CacheStats] = None
    ):
        """
        Initialize cache service.

        Args:
            test_cache: TestCache instance (defaults to Redis-backed)
            stats: CacheStats instance (defaults to in-memory)
        """
        self.test_cache = test_cache or TestCache()
        self.stats = stats or CacheStats()

    def get_or_execute(
        self,
        key: str,
        executor: Callable[[], Any],
        ttl: int = 3600,
        test_suite_id: Optional[int] = None,
        test_id: Optional[int] = None
    ) -> Any:
        """
        Get cached result or execute and cache result.

        Args:
            key: Unique cache key
            executor: Function to execute if cache miss
            ttl: Time to live in seconds (default: 1 hour)
            test_suite_id: Related test suite ID (for invalidation)
            test_id: Related test ID (for invalidation)

        Returns:
            Cached result or result from executor

        Raises:
            Exception: Propagated from executor
        """
        # Try to get from cache
        cached_result = self.test_cache.get(key)

        if cached_result is not None:
            self.stats.record_hit(key)
            logger.info(f"Cache hit for key: {key}")
            return cached_result

        # Cache miss, execute and cache
        self.stats.record_miss(key)

        logger.info(f"Cache miss for key: {key}, executing...")

        try:
            result = executor()

            # Store result in cache
            self.test_cache.set(
                key=key,
                value=result,
                ttl=ttl
            )

            # Log cache entry
            logger.info(f"Executed and cached: {key}, result type: {type(result).__name__}")

            return result

        except Exception as e:
            logger.error(f"Failed to execute: {key}, error: {e}")
            raise

    def invalidate(
        self,
        test_suite_id: Optional[int] = None,
        test_id: Optional[int] = None,
        pattern: Optional[str] = None
    ):
        """
        Invalidate cache entries.

        Args:
            test_suite_id: Invalidate all cache for this suite
            test_id: Invalidate cache for this specific test
            pattern: Invalidate all cache matching pattern (regex)
        """
        # Validate that only one invalidation strategy is used at a time
        provided = sum(1 for p in [test_suite_id, test_id, pattern] if p is not None)
        if provided > 1:
            raise ValueError(
                "Only one invalidation strategy can be used at a time. "
                "Provide exactly one of: test_suite_id, test_id, or pattern."
            )

        if test_suite_id:
            keys = self.test_cache.get_keys_by_suite(test_suite_id)
            for key in keys:
                self.test_cache.delete(key)
                logger.info(f"Invalidated cache for suite: {test_suite_id}, key: {key}")

        if test_id:
            keys = self.test_cache.get_keys_by_test(test_id)
            for key in keys:
                self.test_cache.delete(key)
                logger.info(f"Invalidated cache for test: {test_id}, key: {key}")

        if pattern:
            keys = self.test_cache.get_keys_matching(pattern)
            for key in keys:
                self.test_cache.delete(key)
                logger.info(f"Invalidated cache matching pattern: {pattern}, key: {key}")

    def clear_all(self):
        """Clear all cache entries."""
        self.test_cache.clear_all()
        logger.warning("All cache cleared")

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        return self.stats.get_stats()

    def warm_cache(
        self,
        test_suite_id: int,
        test_ids: list[int],
        executor: Callable[[int], Any],
        batch_size: int = 10
    ):
        """
        Pre-populate cache with test results (cache warming).

        Args:
            test_suite_id: Suite ID to warm
            test_ids: List of test IDs to warm
            executor: Function to execute tests
            batch_size: Batch size for execution
        """
        logger.info(f"Warming cache for suite: {test_suite_id}, tests: {len(test_ids)}")

        for i in range(0, len(test_ids), batch_size):
            batch = test_ids[i:i + batch_size]
            batch_keys = [f"test_suite_{test_suite_id}_test_{test_id}"
                         for test_id in batch]

            for key, test_id in zip(batch_keys, batch):
                try:
                    # Execute test
                    result = executor(test_id)

                    # Store in cache
                    self.test_cache.set(
                        key=key,
                        value=result,
                        ttl=86400  # 24 hours
                    )

                    logger.debug(f"Warmed cache: {key}")

                except Exception as e:
                    logger.error(f"Failed to warm cache for test {test_id}: {e}")

        logger.info(f"Cache warming complete: {len(test_ids)} tests")


class CacheKeyGenerator:
    """Helper class for generating cache keys."""

    @staticmethod
    def from_suite_and_test(test_suite_id: int, test_id: int) -> str:
        """Generate cache key from suite and test IDs."""
        return f"test_suite_{test_suite_id}_test_{test_id}"

    @staticmethod
    def from_execution(execution_id: int) -> str:
        """Generate cache key from execution ID."""
        return f"execution_{execution_id}"

    @staticmethod
    def from_suite_result(suite_id: int) -> str:
        """Generate cache key for suite execution result."""
        return f"execution_result_suite_{suite_id}"

    @staticmethod
    def from_test_result(test_id: int) -> str:
        """Generate cache key for test execution result."""
        return f"execution_result_test_{test_id}"
