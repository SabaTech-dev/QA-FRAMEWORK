"""
Unit tests for test_cache.py
"""

import os
import pytest
import json
import redis
from typing import Dict, Any, Optional
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime

from src.infrastructure.cache.test_cache import (
    TestCache,
    InMemoryCache
)
from src.infrastructure.cache.cache_stats import CacheStats


class TestTestCache:
    """Test suite for TestCache with Redis backend."""

    @pytest.fixture
    def redis_url(self):
        """Get Redis URL from environment or use Railway."""
        return os.getenv("REDIS_URL", "redis://default:ygZpOipKeuDfOvlxRPrRNGxxeJKsPrPD@centerbeam.proxy.rlwy.net:20994")

    @pytest.fixture
    def mock_redis(self):
        """Mock Redis client."""
        return Mock(spec=redis.Redis)

    @pytest.fixture
    def test_cache(self, mock_redis, redis_url):
        """Create TestCache instance with mocked Redis."""
        mock_redis.ping.return_value = True
        mock_redis.get.return_value = None
        mock_redis.set.return_value = True
        mock_redis.setex.return_value = True
        mock_redis.delete.return_value = True
        with patch('redis.from_url', return_value=mock_redis):
            cache = TestCache(redis_url=redis_url)
            yield cache

    def test_initialization_with_redis(self, mock_redis, redis_url):
        """Test cache initializes Redis connection."""
        with patch('redis.from_url', return_value=mock_redis):
            cache = TestCache(redis_url=redis_url)

        assert cache.redis is not None

    def test_get_existing_key(self, test_cache, mock_redis):
        """Test get returns cached value."""
        # Arrange
        mock_redis.get.return_value = '{"result": "test"}'

        # Act
        result = test_cache.get("test_key")

        # Assert
        assert result == {"result": "test"}
        mock_redis.get.assert_called_once_with("test_key")

    def test_get_missing_key(self, test_cache, mock_redis):
        """Test get returns None for missing key."""
        # Arrange
        mock_redis.get.return_value = None

        # Act
        result = test_cache.get("missing_key")

        # Assert
        assert result is None
        mock_redis.get.assert_called_once_with("missing_key")

    def test_set_value(self, test_cache, mock_redis):
        """Test set stores value with TTL."""
        # Act
        result = test_cache.set("test_key", {"result": "test"}, ttl=3600)

        # Assert
        assert result is True
        mock_redis.setex.assert_called_once_with("test_key", 3600, '{"result": "test"}')

    def test_delete_key(self, test_cache, mock_redis):
        """Test delete removes key."""
        # Act
        result = test_cache.delete("test_key")

        # Assert
        assert result is True
        mock_redis.delete.assert_called_once_with("test_key")

    def test_get_keys_by_suite(self, test_cache, mock_redis):
        """Test get_keys_by_suite returns matching keys."""
        # Arrange
        mock_redis.keys.return_value = [b"test_suite_123_test_1", b"test_suite_123_test_2"]

        # Act
        keys = test_cache.get_keys_by_suite(123)

        # Assert
        assert keys == ["test_suite_123_test_1", "test_suite_123_test_2"]
        mock_redis.keys.assert_called_once_with("test_suite_123_*")

    def test_get_keys_by_test(self, test_cache, mock_redis):
        """Test get_keys_by_test returns matching keys."""
        # Arrange
        mock_redis.keys.return_value = [b"test_suite_123_test_1", b"other_test_1"]

        # Act
        keys = test_cache.get_keys_by_test(1)

        # Assert
        assert keys == ["test_suite_123_test_1", "other_test_1"]
        mock_redis.keys.assert_called_once_with("*test_1")

    def test_get_keys_matching(self, test_cache, mock_redis):
        """Test get_keys_matching returns matching keys."""
        # Arrange
        mock_redis.keys.return_value = [b"test_1", b"test_2", b"other_3"]

        # Act
        keys = test_cache.get_keys_matching("test_*")

        # Assert
        assert keys == ["test_1", "test_2", "other_3"]
        mock_redis.keys.assert_called_once_with("test_*")

    def test_get_key_age_with_ttl(self, test_cache, mock_redis):
        """Test get_key_age returns TTL for key with expiry."""
        # Arrange
        mock_redis.ttl.return_value = 1800  # 30 minutes

        # Act
        age = test_cache.get_key_age("test_key")

        # Assert
        assert age == 1800
        mock_redis.ttl.assert_called_once_with("test_key")

    def test_get_key_age_no_expiry(self, test_cache, mock_redis):
        """Test get_key_age returns None for key without expiry."""
        # Arrange
        mock_redis.ttl.return_value = -1

        # Act
        age = test_cache.get_key_age("test_key")

        # Assert
        assert age is None
        mock_redis.ttl.assert_called_once_with("test_key")

    def test_get_key_age_not_found(self, test_cache, mock_redis):
        """Test get_key_age returns None for non-existent key."""
        # Arrange
        mock_redis.ttl.return_value = -2

        # Act
        age = test_cache.get_key_age("test_key")

        # Assert
        assert age is None
        mock_redis.ttl.assert_called_once_with("test_key")

    def test_get_cache_size(self, test_cache, mock_redis):
        """Test get_cache_size returns number of entries."""
        # Arrange
        mock_redis.dbsize.return_value = 100

        # Act
        size = test_cache.get_cache_size()

        # Assert
        assert size == 100
        mock_redis.dbsize.assert_called_once()

    def test_get_memory_usage(self, test_cache, mock_redis):
        """Test get_memory_usage returns memory in bytes."""
        # Arrange
        mock_redis.info.return_value = {"used_memory": 10485760}  # 10 MB

        # Act
        memory = test_cache.get_memory_usage()

        # Assert
        assert memory == 10485760
        mock_redis.info.assert_called_once_with("memory")

    def test_get_all_keys(self, test_cache, mock_redis):
        """Test get_all_keys returns all keys."""
        # Arrange
        mock_redis.keys.return_value = [b"key1", b"key2", b"key3"]

        # Act
        keys = test_cache.get_all_keys()

        # Assert
        assert keys == ["key1", "key2", "key3"]
        mock_redis.keys.assert_called_once_with("*")

    def test_get_tiered_stats(self, test_cache, mock_redis):
        """Test get_tiered_stats returns stats by prefix."""
        # Arrange
        mock_redis.keys.side_effect = [
            [b"test_suite_1_test_1", b"test_suite_1_test_2"],
            [b"execution_1", b"execution_2"],
            [b"execution_result_suite_1", b"execution_result_test_1"]
        ]

        # Act
        stats = test_cache.get_tiered_stats()

        # Assert
        assert "test_suite_" in stats
        assert "execution_" in stats
        assert "execution_result_" in stats
        assert stats["test_suite_"]["count"] == 2
        assert stats["execution_"]["count"] == 2
        assert stats["execution_result_"]["count"] == 2

    def test_clear_all(self, test_cache, mock_redis):
        """Test clear_all flushes database."""
        # Act
        test_cache.clear_all()

        # Assert
        mock_redis.flushdb.assert_called_once()


class TestInMemoryCache:
    """Test suite for InMemoryCache fallback."""

    @pytest.fixture
    def in_memory_cache(self):
        """Create InMemoryCache instance."""
        return InMemoryCache()

    def test_get_nonexistent_key(self, in_memory_cache):
        """Test get returns None for non-existent key."""
        assert in_memory_cache.get("nonexistent") is None

    def test_set_and_get(self, in_memory_cache):
        """Test set and get works."""
        in_memory_cache.set("key", "value", ttl=3600)
        assert in_memory_cache.get("key") == "value"

    def test_set_then_get_after_expiry(self, in_memory_cache):
        """Test get returns None after TTL expiry."""
        in_memory_cache.set("key", "value", ttl=1)
        assert in_memory_cache.get("key") == "value"

        # Wait for expiry
        import time
        time.sleep(1.1)

        assert in_memory_cache.get("key") is None

    def test_delete_key(self, in_memory_cache):
        """Test delete removes key."""
        in_memory_cache.set("key", "value")
        in_memory_cache.delete("key")
        assert in_memory_cache.get("key") is None

    def test_clear_all(self, in_memory_cache):
        """Test clear_all removes all entries."""
        in_memory_cache.set("key1", "value1")
        in_memory_cache.set("key2", "value2")
        in_memory_cache.clear_all()

        assert in_memory_cache.get("key1") is None
        assert in_memory_cache.get("key2") is None

    def test_get_keys_by_suite(self, in_memory_cache):
        """Test get_keys_by_suite returns matching keys."""
        in_memory_cache.set("test_suite_1_test_1", "value1")
        in_memory_cache.set("test_suite_1_test_2", "value2")
        in_memory_cache.set("test_suite_2_test_1", "value3")

        keys = in_memory_cache.get_keys_by_suite(1)

        assert keys == ["test_suite_1_test_1", "test_suite_1_test_2"]

    def test_get_keys_by_test(self, in_memory_cache):
        """Test get_keys_by_test returns matching keys."""
        in_memory_cache.set("test_suite_1_test_1", "value1")
        in_memory_cache.set("other_test_1", "value2")

        keys = in_memory_cache.get_keys_by_test(1)

        assert keys == ["test_suite_1_test_1", "other_test_1"]

    def test_get_cache_size(self, in_memory_cache):
        """Test get_cache_size returns number of entries."""
        in_memory_cache.set("key1", "value1")
        in_memory_cache.set("key2", "value2")

        assert in_memory_cache.get_cache_size() == 2

    def test_get_memory_usage(self, in_memory_cache):
        """Test get_memory_usage returns total bytes."""
        in_memory_cache.set("key1", "value1")
        in_memory_cache.set("key2", "value2")

        memory = in_memory_cache.get_memory_usage()
        assert memory > 0

    def test_cleanup_expired(self, in_memory_cache):
        """Test cleanup_expired removes expired entries."""
        in_memory_cache.set("key1", "value1", ttl=1)
        in_memory_cache.set("key2", "value2", ttl=3600)

        import time
        time.sleep(1.1)

        removed = in_memory_cache.cleanup_expired()

        assert removed == 1
        assert in_memory_cache.get("key1") is None
        assert in_memory_cache.get("key2") is not None


class TestCacheStats:
    """Test suite for CacheStats."""

    @pytest.fixture
    def cache_stats(self):
        """Create CacheStats instance."""
        return CacheStats()

    def test_initialization(self, cache_stats):
        """Test cache stats initializes with zero values."""
        assert cache_stats.hits == 0
        assert cache_stats.misses == 0
        assert cache_stats.errors == 0

    def test_record_hit(self, cache_stats):
        """Test record_hit increments hits."""
        cache_stats.record_hit("test_key", duration_ms=5.0)

        assert cache_stats.hits == 1
        assert len(cache_stats.hit_times) == 1
        assert cache_stats.hit_times[0] == 5.0

    def test_record_miss(self, cache_stats):
        """Test record_miss increments misses."""
        cache_stats.record_miss("test_key", duration_ms=10.0)

        assert cache_stats.misses == 1
        assert len(cache_stats.miss_times) == 1
        assert cache_stats.miss_times[0] == 10.0

    def test_record_error(self, cache_stats):
        """Test record_error increments errors."""
        cache_stats.record_error()

        assert cache_stats.errors == 1

    def test_get_hit_rate_all_misses(self, cache_stats):
        """Test get_hit_rate is 0 when all misses."""
        cache_stats.record_miss("test_key")
        cache_stats.record_miss("test_key2")

        hit_rate = cache_stats.get_hit_rate()

        assert hit_rate == 0.0

    def test_get_hit_rate_all_hits(self, cache_stats):
        """Test get_hit_rate is 100 when all hits."""
        cache_stats.record_hit("test_key")
        cache_stats.record_hit("test_key2")

        hit_rate = cache_stats.get_hit_rate()

        assert hit_rate == 100.0

    def test_get_hit_rate_mixed(self, cache_stats):
        """Test get_hit_rate calculates correctly with mixed."""
        cache_stats.record_hit("test_key")
        cache_stats.record_miss("test_key2")

        hit_rate = cache_stats.get_hit_rate()

        assert hit_rate == 50.0

    def test_get_average_hit_time(self, cache_stats):
        """Test get_average_hit_time calculates correctly."""
        cache_stats.record_hit("test_key", duration_ms=5.0)
        cache_stats.record_hit("test_key2", duration_ms=10.0)

        avg = cache_stats.get_average_hit_time()

        assert avg == 7.5

    def test_get_average_hit_time_zero(self, cache_stats):
        """Test get_average_hit_time returns 0 when no hits."""
        avg = cache_stats.get_average_hit_time()

        assert avg == 0.0

    def test_format_bytes(self, cache_stats):
        """Test format_bytes formats correctly."""
        assert cache_stats.format_bytes(0) == "0 Bytes"
        assert cache_stats.format_bytes(1024) == "1.00 KB"
        assert cache_stats.format_bytes(1024 * 1024) == "1.00 MB"

    def test_get_stats(self, cache_stats):
        """Test get_stats returns comprehensive stats."""
        cache_stats.record_hit("test_key", duration_ms=5.0)
        cache_stats.record_miss("test_key2", duration_ms=10.0)

        stats = cache_stats.get_stats()

        assert "hits" in stats
        assert "misses" in stats
        assert "errors" in stats
        assert "hit_rate_percent" in stats
        assert "average_hit_time_ms" in stats
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_rate_percent"] == 50.0
        assert stats["average_hit_time_ms"] == 5.0

    def test_reset(self, cache_stats):
        """Test reset clears all statistics."""
        cache_stats.record_hit("test_key")
        cache_stats.record_miss("test_key2")
        cache_stats.record_error()
        cache_stats.reset()

        assert cache_stats.hits == 0
        assert cache_stats.misses == 0
        assert cache_stats.errors == 0
        assert len(cache_stats.hit_times) == 0
        assert len(cache_stats.miss_times) == 0
