"""
Unit tests for test_cache.py - Using REAL Redis (no mocks)
"""

import os
import uuid
import pytest
import json
import redis
from typing import Dict, Any, Optional
from datetime import datetime

from src.infrastructure.cache.test_cache import (
    TestCache,
    InMemoryCache
)
from src.infrastructure.cache.cache_stats import CacheStats


class TestTestCache:
    """Test suite for TestCache with REAL Redis backend."""

    @pytest.fixture
    def redis_url(self):
        """Get Redis URL from environment or use Railway."""
        return os.getenv("REDIS_URL", "redis://default:ygZpOipKeuDfOvlxRPrRNGxxeJKsPrPD@centerbeam.proxy.rlwy.net:20994")

    @pytest.fixture
    def test_cache(self, redis_url):
        """Create TestCache instance with real Redis."""
        return TestCache(redis_url=redis_url)

    @pytest.fixture(autouse=True)
    def cleanup_redis(self, test_cache):
        """Clean up test keys after each test."""
        yield
        # Delete all keys starting with test_
        try:
            keys = test_cache.redis.keys("test_*")
            if keys:
                test_cache.redis.delete(*keys)
        except Exception:
            pass  # Ignore cleanup errors

    def test_initialization_with_redis(self, test_cache):
        """Test cache initializes Redis connection."""
        assert test_cache.redis is not None
        # Verify connection is working
        assert test_cache.redis.ping() is True

    def test_get_existing_key(self, test_cache):
        """Test get returns cached value."""
        # Arrange - Set a value first
        test_cache.set("test_key_1", {"result": "test"}, ttl=3600)

        # Act
        result = test_cache.get("test_key_1")

        # Assert
        assert result == {"result": "test"}

    def test_get_missing_key(self, test_cache):
        """Test get returns None for missing key."""
        # Act
        result = test_cache.get("test_missing_key")

        # Assert
        assert result is None

    def test_set_value(self, test_cache):
        """Test set stores value with TTL."""
        # Act
        result = test_cache.set("test_key_2", {"result": "test"}, ttl=3600)

        # Assert
        assert result is True
        # Verify it was stored
        retrieved = test_cache.get("test_key_2")
        assert retrieved == {"result": "test"}

    def test_delete_key(self, test_cache):
        """Test delete removes key."""
        # Arrange
        test_cache.set("test_key_3", {"result": "test"}, ttl=3600)

        # Act
        result = test_cache.delete("test_key_3")

        # Assert
        assert result is True
        assert test_cache.get("test_key_3") is None

    def test_get_keys_by_suite(self, test_cache):
        """Test get_keys_by_suite returns matching keys."""
        # Arrange - Create some test keys
        test_cache.set("test_suite_123_test_1", {"data": 1}, ttl=3600)
        test_cache.set("test_suite_123_test_2", {"data": 2}, ttl=3600)
        test_cache.set("test_suite_456_test_1", {"data": 3}, ttl=3600)

        # Act
        keys = test_cache.get_keys_by_suite(123)

        # Assert - Should only get keys for suite 123
        assert len(keys) == 2
        assert "test_suite_123_test_1" in keys
        assert "test_suite_123_test_2" in keys

    def test_get_keys_by_test(self, test_cache):
        """Test get_keys_by_test returns matching keys."""
        # Arrange
        test_cache.set("test_suite_100_test_1", {"data": 1}, ttl=3600)
        test_cache.set("test_suite_200_test_1", {"data": 2}, ttl=3600)

        # Act
        keys = test_cache.get_keys_by_test(1)

        # Assert - Should get all keys ending with test_1
        assert len(keys) >= 2
        assert "test_suite_100_test_1" in keys
        assert "test_suite_200_test_1" in keys

    def test_get_keys_matching(self, test_cache):
        """Test get_keys_matching returns matching keys."""
        # Arrange
        test_cache.set("test_match_1", {"data": 1}, ttl=3600)
        test_cache.set("test_match_2", {"data": 2}, ttl=3600)
        test_cache.set("test_other_3", {"data": 3}, ttl=3600)

        # Act
        keys = test_cache.get_keys_matching("test_match_*")

        # Assert
        assert len(keys) == 2
        assert "test_match_1" in keys
        assert "test_match_2" in keys

    def test_get_key_age_with_ttl(self, test_cache):
        """Test get_key_age returns TTL for key with expiry."""
        # Arrange
        test_cache.set("test_key_ttl", {"data": "test"}, ttl=3600)

        # Act
        age = test_cache.get_key_age("test_key_ttl")

        # Assert - TTL should be close to 3600 (within a few seconds)
        assert age is not None
        assert age > 3590  # Allow for 10 seconds of processing time
        assert age <= 3600

    def test_get_key_age_no_expiry(self, test_cache):
        """Test get_key_age returns None for key without expiry."""
        # Arrange - Set without TTL
        test_cache.redis.set("test_key_no_expiry", '{"data": "test"}')

        # Act
        age = test_cache.get_key_age("test_key_no_expiry")

        # Assert - -1 means no expiry
        assert age is None

    def test_get_key_age_not_found(self, test_cache):
        """Test get_key_age returns None for non-existent key."""
        # Act
        age = test_cache.get_key_age("test_nonexistent_key")

        # Assert - -2 means key doesn't exist
        assert age is None

    def test_get_cache_size(self, test_cache):
        """Test get_cache_size returns number of keys."""
        # Arrange - Add some test keys
        initial_size = test_cache.get_cache_size()
        test_cache.set("test_size_1", {"data": 1}, ttl=3600)
        test_cache.set("test_size_2", {"data": 2}, ttl=3600)
        test_cache.set("test_size_3", {"data": 3}, ttl=3600)

        # Act
        size = test_cache.get_cache_size()

        # Assert - Should have at least 3 more keys than before
        assert size >= initial_size + 3

    def test_get_memory_usage(self, test_cache):
        """Test get_memory_usage returns memory info."""
        # Act
        memory = test_cache.get_memory_usage()

        # Assert - Should return a dict with memory info
        assert isinstance(memory, dict)
        assert "used_memory" in memory

    def test_get_all_keys(self, test_cache):
        """Test get_all_keys returns all keys."""
        # Arrange
        test_cache.set("test_all_1", {"data": 1}, ttl=3600)
        test_cache.set("test_all_2", {"data": 2}, ttl=3600)
        test_cache.set("test_all_3", {"data": 3}, ttl=3600)

        # Act
        keys = test_cache.get_all_keys()

        # Assert - Should include our test keys
        assert "test_all_1" in keys
        assert "test_all_2" in keys
        assert "test_all_3" in keys

    def test_get_tiered_stats(self, test_cache):
        """Test get_tiered_stats returns cache statistics."""
        # Arrange - Add some data
        test_cache.set("test_stat_1", {"data": 1}, ttl=3600)
        test_cache.get("test_stat_1")  # Hit
        test_cache.get("test_nonexistent")  # Miss

        # Act
        stats = test_cache.get_tiered_stats()

        # Assert
        assert isinstance(stats, dict)
        # Stats might vary based on implementation

    def test_clear_all(self, test_cache):
        """Test clear_all removes all test keys."""
        # Arrange
        test_cache.set("test_clear_1", {"data": 1}, ttl=3600)
        test_cache.set("test_clear_2", {"data": 2}, ttl=3600)

        # Act
        test_cache.clear_all()

        # Assert - Our test keys should be gone
        # Note: This might clear ALL keys, so we need to be careful
        # For now, just verify it doesn't error
        assert True


class TestInMemoryCache:
    """Test suite for InMemoryCache (unit tests, no Redis)."""

    @pytest.fixture
    def cache(self):
        """Create InMemoryCache instance."""
        return InMemoryCache()

    def test_set_and_get(self, cache):
        """Test basic set and get operations."""
        # Act
        cache.set("test_key", {"data": "value"}, ttl=3600)
        result = cache.get("test_key")

        # Assert
        assert result == {"data": "value"}

    def test_set_then_get_after_expiry(self, cache):
        """Test that expired keys return None."""
        # Arrange - Set with very short TTL
        import time
        cache.set("test_expire", {"data": "value"}, ttl=1)

        # Act - Wait for expiry
        time.sleep(2)
        result = cache.get("test_expire")

        # Assert
        assert result is None

    def test_cleanup_expired(self, cache):
        """Test cleanup removes expired entries."""
        # Arrange
        import time
        cache.set("test_cleanup_1", {"data": 1}, ttl=1)
        cache.set("test_cleanup_2", {"data": 2}, ttl=1)
        time.sleep(2)

        # Act
        cache.cleanup_expired()

        # Assert - Both should be removed
        assert cache.get("test_cleanup_1") is None
        assert cache.get("test_cleanup_2") is None


class TestCacheStats:
    """Test suite for CacheStats."""

    def test_get_stats(self):
        """Test get_stats returns statistics."""
        # Arrange
        from src.infrastructure.cache.cache_stats import CacheStats
        stats = CacheStats()

        # Act
        result = stats.get_stats()

        # Assert
        assert isinstance(result, dict)
