"""TestCache — Redis-backed key-value cache for test results.

Stores serialized test results in Redis with TTL support.
Used by CacheService for exact-match caching.
"""

import json
import logging
from typing import Any, Optional, List

logger = logging.getLogger(__name__)


class TestCache:
    """Redis-backed cache for test execution results."""

    def __init__(self, redis_client: Any = None, prefix: str = "qa:cache:") -> None:
        """
        Initialize TestCache.

        Args:
            redis_client: Redis client (sync). If None, uses in-memory fallback.
            prefix: Key prefix for Redis entries.
        """
        self._prefix = prefix
        self._redis = redis_client
        self._memory: dict = {}  # Fallback when Redis is unavailable

    def _key(self, key: str) -> str:
        return f"{self._prefix}{key}"

    def get(self, key: str) -> Optional[Any]:
        """Get cached value by key. Returns None on miss."""
        full_key = self._key(key)
        try:
            if self._redis is not None:
                raw = self._redis.get(full_key)
                if raw is not None:
                    return json.loads(raw)
                return None
            # In-memory fallback
            entry = self._memory.get(full_key)
            if entry is not None:
                return entry.get("value")
            return None
        except Exception as exc:
            logger.warning("Cache get failed for %s: %s", key, exc)
            return None

    def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """Set cached value with TTL in seconds."""
        full_key = self._key(key)
        try:
            serialized = json.dumps(value, default=str)
            if self._redis is not None:
                self._redis.setex(full_key, ttl, serialized)
            else:
                import time
                self._memory[full_key] = {
                    "value": value,
                    "expires": time.time() + ttl,
                }
            return True
        except Exception as exc:
            logger.warning("Cache set failed for %s: %s", key, exc)
            return False

    def delete(self, key: str) -> bool:
        """Delete cached entry."""
        full_key = self._key(key)
        try:
            if self._redis is not None:
                self._redis.delete(full_key)
            else:
                self._memory.pop(full_key, None)
            return True
        except Exception as exc:
            logger.warning("Cache delete failed for %s: %s", key, exc)
            return False

    def clear_all(self) -> bool:
        """Clear all cached entries matching the prefix."""
        try:
            if self._redis is not None:
                cursor = 0
                while True:
                    cursor, keys = self._redis.scan(cursor, match=f"{self._prefix}*", count=100)
                    if keys:
                        self._redis.delete(*keys)
                    if cursor == 0:
                        break
            else:
                self._memory.clear()
            return True
        except Exception as exc:
            logger.warning("Cache clear_all failed: %s", exc)
            return False

    def get_keys_by_suite(self, test_suite_id: int) -> List[str]:
        """Get all cache keys for a test suite."""
        pattern = f"{self._prefix}test_suite_{test_suite_id}_*"
        try:
            if self._redis is not None:
                keys = []
                cursor = 0
                while True:
                    cursor, batch = self._redis.scan(cursor, match=pattern, count=100)
                    keys.extend(batch)
                    if cursor == 0:
                        break
                return [k.replace(self._prefix, "", 1) for k in keys]
            return [k.replace(self._prefix, "", 1)
                    for k in self._memory if k.startswith(f"{self._prefix}test_suite_{test_suite_id}_")]
        except Exception as exc:
            logger.warning("get_keys_by_suite failed: %s", exc)
            return []

    def get_keys_by_test(self, test_id: int) -> List[str]:
        """Get all cache keys for a specific test."""
        pattern = f"{self._prefix}*_test_{test_id}_*"
        try:
            if self._redis is not None:
                keys = []
                cursor = 0
                while True:
                    cursor, batch = self._redis.scan(cursor, match=pattern, count=100)
                    keys.extend(batch)
                    if cursor == 0:
                        break
                return [k.replace(self._prefix, "", 1) for k in keys]
            return [k.replace(self._prefix, "", 1)
                    for k in self._memory if f"_test_{test_id}_" in k]
        except Exception as exc:
            logger.warning("get_keys_by_test failed: %s", exc)
            return []

    def get_keys_matching(self, pattern: str) -> List[str]:
        """Get all cache keys matching a glob pattern."""
        full_pattern = f"{self._prefix}{pattern}"
        try:
            if self._redis is not None:
                keys = []
                cursor = 0
                while True:
                    cursor, batch = self._redis.scan(cursor, match=full_pattern, count=100)
                    keys.extend(batch)
                    if cursor == 0:
                        break
                return [k.replace(self._prefix, "", 1) for k in keys]
            import fnmatch
            return [k.replace(self._prefix, "", 1)
                    for k in self._memory if fnmatch.fnmatch(k, full_pattern)]
        except Exception as exc:
            logger.warning("get_keys_matching failed: %s", exc)
            return []
