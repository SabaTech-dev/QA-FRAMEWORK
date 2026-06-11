import asyncio
"""
Redis Cache Module

Provides distributed caching functionality with Redis.
Supports both synchronous and asynchronous operations,
TTL-based expiration, and cache invalidation strategies.
"""

import json
import pickle
from typing import Optional, Any, Union, List
from datetime import timedelta
import redis.asyncio as aioredis
import redis
from functools import wraps
import hashlib

from config import settings
from core.logging_config import get_logger

logger = get_logger(__name__)


class CacheManager:
    """
    Redis Cache Manager

    Manages Redis connections and provides caching operations
    with support for both sync and async operations.
    """

    # Default TTL values (in seconds)
    DEFAULT_TTL = 300  # 5 minutes
    SHORT_TTL = 60  # 1 minute
    MEDIUM_TTL = 600  # 10 minutes
    LONG_TTL = 3600  # 1 hour
    EXTENDED_TTL = 86400  # 24 hours

    # Cache key prefixes for different entities
    KEY_PREFIXES = {
        "suite": "suite",
        "suite_list": "suites:list",
        "case": "case",
        "case_list": "cases:list",
        "execution": "execution",
        "execution_list": "executions:list",
        "dashboard_stats": "dashboard:stats",
        "dashboard_trends": "dashboard:trends",
        "dashboard_recent": "dashboard:recent",
    }

    _instance = None
    _async_client: Optional[aioredis.Redis] = None
    _sync_client: Optional[redis.Redis] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CacheManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, "initialized"):
            self.initialized = True
            self._host = settings.redis_host
            self._port = settings.redis_port
            self._password = settings.redis_password

    async def get_async_client(self) -> aioredis.Redis:
        """Get or create async Redis client"""
        if self._async_client is None:
            try:
                self._async_client = aioredis.Redis(
                    host=self._host,
                    port=self._port,
                    password=self._password,
                    decode_responses=False,  # We'll handle encoding manually
                    socket_connect_timeout=5,
                    socket_keepalive=True,
                    health_check_interval=30,
                )
                await self._async_client.ping()
                logger.info("Async Redis client connected successfully")
            except Exception as e:
                logger.error("Failed to connect to Redis (async)", error=str(e))
                raise
        return self._async_client

    def get_sync_client(self) -> redis.Redis:
        """Get or create sync Redis client"""
        if self._sync_client is None:
            try:
                self._sync_client = redis.Redis(
                    host=self._host,
                    port=self._port,
                    password=self._password,
                    decode_responses=False,
                    socket_connect_timeout=5,
                    socket_keepalive=True,
                    health_check_interval=30,
                )
                self._sync_client.ping()
                logger.info("Sync Redis client connected successfully")
            except Exception as e:
                logger.error("Failed to connect to Redis (sync)", error=str(e))
                raise
        return self._sync_client

    def _serialize(self, value: Any) -> bytes:
        """Serialize value to bytes"""
        return pickle.dumps(value)

    def _deserialize(self, value: bytes) -> Any:
        """Deserialize bytes to value"""
        return pickle.loads(value)

    def _build_key(self, prefix: str, identifier: Union[str, int]) -> str:
        """Build cache key with prefix"""
        return f"{prefix}:{identifier}"

    # Async Operations

    async def async_get(self, key: str) -> Optional[Any]:
        """Get value from cache (async)"""
        try:
            client = await self.get_async_client()
            value = await client.get(key)
            if value is not None:
                logger.debug("Cache hit", key=key)
                return self._deserialize(value)
            logger.debug("Cache miss", key=key)
            return None
        except Exception as e:
            logger.error("Cache get error", key=key, error=str(e))
            return None

    async def async_set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache (async)"""
        try:
            client = await self.get_async_client()
            serialized = self._serialize(value)
            ttl = ttl or self.DEFAULT_TTL
            await client.setex(key, ttl, serialized)
            logger.debug("Cache set", key=key, ttl=ttl)
            return True
        except Exception as e:
            logger.error("Cache set error", key=key, error=str(e))
            return False

    async def async_delete(self, key: str) -> bool:
        """Delete value from cache (async)"""
        try:
            client = await self.get_async_client()
            result = await client.delete(key)
            logger.debug("Cache delete", key=key, deleted=result > 0)
            return result > 0
        except Exception as e:
            logger.error("Cache delete error", key=key, error=str(e))
            return False

    async def async_delete_pattern(self, pattern: str) -> int:
        """Delete values matching pattern (async)"""
        try:
            client = await self.get_async_client()
            keys = []
            async for key in client.scan_iter(match=pattern):
                keys.append(key)
            if keys:
                await client.delete(*keys)
                logger.debug("Cache delete pattern", pattern=pattern, count=len(keys))
                return len(keys)
            return 0
        except Exception as e:
            logger.error("Cache delete pattern error", pattern=pattern, error=str(e))
            return 0

    async def async_exists(self, key: str) -> bool:
        """Check if key exists in cache (async)"""
        try:
            client = await self.get_async_client()
            return await client.exists(key) > 0
        except Exception as e:
            logger.error("Cache exists error", key=key, error=str(e))
            return False

    async def async_ttl(self, key: str) -> int:
        """Get TTL of key in cache (async)"""
        try:
            client = await self.get_async_client()
            return await client.ttl(key)
        except Exception as e:
            logger.error("Cache TTL error", key=key, error=str(e))
            return -2

    async def async_clear(self) -> bool:
        """Clear all cache (async) - Use with caution!"""
        try:
            client = await self.get_async_client()
            await client.flushdb()
            logger.warning("Cache cleared (async)")
            return True
        except Exception as e:
            logger.error("Cache clear error", error=str(e))
            return False

    # Sync Operations

    def sync_get(self, key: str) -> Optional[Any]:
        """Get value from cache (sync)"""
        try:
            client = self.get_sync_client()
            value = client.get(key)
            if value is not None:
                logger.debug("Cache hit (sync)", key=key)
                return self._deserialize(value)
            logger.debug("Cache miss (sync)", key=key)
            return None
        except Exception as e:
            logger.error("Cache get error (sync)", key=key, error=str(e))
            return None

    def sync_set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache (sync)"""
        try:
            client = self.get_sync_client()
            serialized = self._serialize(value)
            ttl = ttl or self.DEFAULT_TTL
            client.setex(key, ttl, serialized)
            logger.debug("Cache set (sync)", key=key, ttl=ttl)
            return True
        except Exception as e:
            logger.error("Cache set error (sync)", key=key, error=str(e))
            return False

    def sync_delete(self, key: str) -> bool:
        """Delete value from cache (sync)"""
        try:
            client = self.get_sync_client()
            result = client.delete(key)
            logger.debug("Cache delete (sync)", key=key, deleted=result > 0)
            return result > 0
        except Exception as e:
            logger.error("Cache delete error (sync)", key=key, error=str(e))
            return False

    def sync_delete_pattern(self, pattern: str) -> int:
        """Delete values matching pattern (sync)"""
        try:
            client = self.get_sync_client()
            keys = list(client.scan_iter(match=pattern))
            if keys:
                client.delete(*keys)
                logger.debug(
                    "Cache delete pattern (sync)", pattern=pattern, count=len(keys)
                )
                return len(keys)
            return 0
        except Exception as e:
            logger.error(
                "Cache delete pattern error (sync)", pattern=pattern, error=str(e)
            )
            return 0

    def sync_exists(self, key: str) -> bool:
        """Check if key exists in cache (sync)"""
        try:
            client = self.get_sync_client()
            return client.exists(key) > 0
        except Exception as e:
            logger.error("Cache exists error (sync)", key=key, error=str(e))
            return False

    def sync_clear(self) -> bool:
        """Clear all cache (sync) - Use with caution!"""
        try:
            client = self.get_sync_client()
            client.flushdb()
            logger.warning("Cache cleared (sync)")
            return True
        except Exception as e:
            logger.error("Cache clear error (sync)", error=str(e))
            return False

    # Cache Invalidation Helpers

    async def invalidate_suite_cache(self, suite_id: Optional[int] = None):
        """Invalidate suite-related cache"""
        if suite_id:
            await self.async_delete(
                self._build_key(self.KEY_PREFIXES["suite"], suite_id)
            )
        await self.async_delete_pattern(f"{self.KEY_PREFIXES['suite_list']}:*")
        logger.info("Suite cache invalidated", suite_id=suite_id)

    async def invalidate_case_cache(
        self, case_id: Optional[int] = None, suite_id: Optional[int] = None
    ):
        """Invalidate case-related cache"""
        if case_id:
            await self.async_delete(self._build_key(self.KEY_PREFIXES["case"], case_id))
        if suite_id:
            await self.async_delete_pattern(
                f"{self.KEY_PREFIXES['case_list']}:suite:{suite_id}:*"
            )
        await self.async_delete_pattern(f"{self.KEY_PREFIXES['case_list']}:*")
        logger.info("Case cache invalidated", case_id=case_id, suite_id=suite_id)

    async def invalidate_execution_cache(self, execution_id: Optional[int] = None):
        """Invalidate execution-related cache"""
        if execution_id:
            await self.async_delete(
                self._build_key(self.KEY_PREFIXES["execution"], execution_id)
            )
        await self.async_delete_pattern(f"{self.KEY_PREFIXES['execution_list']}:*")
        logger.info("Execution cache invalidated", execution_id=execution_id)

    async def invalidate_dashboard_cache(self):
        """Invalidate dashboard-related cache"""
        await self.async_delete(self.KEY_PREFIXES["dashboard_stats"])
        await self.async_delete_pattern(f"{self.KEY_PREFIXES['dashboard_trends']}:*")
        await self.async_delete_pattern(f"{self.KEY_PREFIXES['dashboard_recent']}:*")
        logger.info("Dashboard cache invalidated")

    async def invalidate_all_cache(self):
        """Invalidate all cache - Use with caution!"""
        await self.async_clear()
        logger.warning("All cache invalidated")

    # Key Generation Helpers

    def get_suite_key(self, suite_id: int) -> str:
        """Generate cache key for a suite"""
        return self._build_key(self.KEY_PREFIXES["suite"], suite_id)

    def get_suite_list_key(self, skip: int = 0, limit: int = 100) -> str:
        """Generate cache key for suite list"""
        return f"{self.KEY_PREFIXES['suite_list']}:skip:{skip}:limit:{limit}"

    def get_case_key(self, case_id: int) -> str:
        """Generate cache key for a case"""
        return self._build_key(self.KEY_PREFIXES["case"], case_id)

    def get_case_list_key(
        self, suite_id: Optional[int] = None, skip: int = 0, limit: int = 100
    ) -> str:
        """Generate cache key for case list"""
        if suite_id:
            return f"{self.KEY_PREFIXES['case_list']}:suite:{suite_id}:skip:{skip}:limit:{limit}"
        return f"{self.KEY_PREFIXES['case_list']}:skip:{skip}:limit:{limit}"

    def get_execution_key(self, execution_id: int) -> str:
        """Generate cache key for an execution"""
        return self._build_key(self.KEY_PREFIXES["execution"], execution_id)

    def get_execution_list_key(
        self,
        suite_id: Optional[int] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> str:
        """Generate cache key for execution list"""
        key = f"{self.KEY_PREFIXES['execution_list']}"
        if suite_id:
            key += f":suite:{suite_id}"
        if status:
            key += f":status:{status}"
        key += f":skip:{skip}:limit:{limit}"
        return key

    def get_dashboard_stats_key(self) -> str:
        """Generate cache key for dashboard stats"""
        return self.KEY_PREFIXES["dashboard_stats"]

    def get_dashboard_trends_key(self, days: int = 30) -> str:
        """Generate cache key for dashboard trends"""
        return f"{self.KEY_PREFIXES['dashboard_trends']}:days:{days}"

    def get_dashboard_recent_key(self, limit: int = 10) -> str:
        """Generate cache key for dashboard recent executions"""
        return f"{self.KEY_PREFIXES['dashboard_recent']}:limit:{limit}"


# Global cache manager instance
cache_manager = CacheManager()


# Decorator for caching function results
def cached(
    ttl: Optional[int] = None,
    key_prefix: Optional[str] = None,
    key_builder: Optional[callable] = None,
):
    """
    Decorator to cache function results

    Args:
        ttl: Time to live in seconds
        key_prefix: Prefix for cache key
        key_builder: Custom function to build cache key from function arguments
    """

    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Build cache key
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                prefix = key_prefix or func.__name__
                # Create hash from args and kwargs
                key_data = f"{args}:{kwargs}"
                key_hash = hashlib.sha256(key_data.encode()).hexdigest()[:32]
                cache_key = f"{prefix}:{key_hash}"

            # Try to get from cache
            cached_value = await cache_manager.async_get(cache_key)
            if cached_value is not None:
                return cached_value

            # Execute function and cache result
            result = await func(*args, **kwargs)
            await cache_manager.async_set(cache_key, result, ttl)
            return result

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Build cache key
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                prefix = key_prefix or func.__name__
                key_data = f"{args}:{kwargs}"
                key_hash = hashlib.sha256(key_data.encode()).hexdigest()[:32]
                cache_key = f"{prefix}:{key_hash}"

            # Try to get from cache
            cached_value = cache_manager.sync_get(cache_key)
            if cached_value is not None:
                return cached_value

            # Execute function and cache result
            result = func(*args, **kwargs)
            cache_manager.sync_set(cache_key, result, ttl)
            return result

        # Return appropriate wrapper based on whether func is async
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


# Convenience functions for direct cache access
async def cache_get(key: str) -> Optional[Any]:
    """Get value from cache (async)"""
    return await cache_manager.async_get(key)


async def cache_set(key: str, value: Any, ttl: Optional[int] = None) -> bool:
    """Set value in cache (async)"""
    return await cache_manager.async_set(key, value, ttl)


async def cache_delete(key: str) -> bool:
    """Delete value from cache (async)"""
    return await cache_manager.async_delete(key)


async def cache_delete_pattern(pattern: str) -> int:
    """Delete values matching pattern (async)"""
    return await cache_manager.async_delete_pattern(pattern)
