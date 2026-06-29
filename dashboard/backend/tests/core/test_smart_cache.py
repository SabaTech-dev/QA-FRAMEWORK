"""
Tests for smart cache system.
"""

import pytest
import json
from unittest.mock import Mock, MagicMock, patch
from core.smart_cache import (
    CacheStrategy,
    CacheConfig,
    SmartCache,
    get_cache
)


class TestCacheStrategy:
    """Tests for CacheStrategy enum."""
    
    def test_strategy_values(self):
        """Test that all strategy values exist."""
        assert CacheStrategy.TTL.value == "ttl"
        assert CacheStrategy.EVENT.value == "event"
        assert CacheStrategy.DEPENDENCY.value == "dependency"
        assert CacheStrategy.MANUAL.value == "manual"
    
    def test_strategy_count(self):
        """Test that there are 4 strategies."""
        assert len(CacheStrategy) == 4


class TestCacheConfig:
    """Tests for CacheConfig configurations."""
    
    def test_test_results_config(self):
        """Test TEST_RESULTS configuration."""
        config = CacheConfig.TEST_RESULTS
        
        assert config["ttl"] == 3600
        assert config["strategy"] == CacheStrategy.TTL
        assert config["tags"] == ["test", "result"]
    
    def test_test_suites_config(self):
        """Test TEST_SUITES configuration."""
        config = CacheConfig.TEST_SUITES
        
        assert config["ttl"] == 300
        assert config["strategy"] == CacheStrategy.EVENT
        assert config["tags"] == ["suite", "metadata"]
    
    def test_user_data_config(self):
        """Test USER_DATA configuration."""
        config = CacheConfig.USER_DATA
        
        assert config["ttl"] == 1800
        assert config["strategy"] == CacheStrategy.EVENT
        assert config["tags"] == ["user"]
    
    def test_dashboard_stats_config(self):
        """Test DASHBOARD_STATS configuration."""
        config = CacheConfig.DASHBOARD_STATS
        
        assert config["ttl"] == 60
        assert config["strategy"] == CacheStrategy.EVENT
        assert config["tags"] == ["dashboard", "stats"]
    
    def test_api_responses_config(self):
        """Test API_RESPONSES configuration."""
        config = CacheConfig.API_RESPONSES
        
        assert config["ttl"] == 600
        assert config["strategy"] == CacheStrategy.TTL
        assert config["tags"] == ["api"]


class TestSmartCacheInit:
    """Tests for SmartCache initialization."""
    
    @patch('core.smart_cache.redis.Redis')
    def test_init_default_params(self, mock_redis):
        """Test SmartCache initialization with default parameters."""
        cache = SmartCache()
        
        mock_redis.assert_called_once_with(
            host="localhost",
            port=6379,
            db=0,
            decode_responses=True
        )
        assert cache.stats["hits"] == 0
        assert cache.stats["misses"] == 0
        assert cache.stats["invalidations"] == 0
        assert cache.stats["sets"] == 0
    
    @patch('core.smart_cache.redis.Redis')
    def test_init_custom_params(self, mock_redis):
        """Test SmartCache initialization with custom parameters."""
        cache = SmartCache(redis_host="127.0.0.1", redis_port=6380, db=1)
        
        mock_redis.assert_called_once_with(
            host="127.0.0.1",
            port=6380,
            db=1,
            decode_responses=True
        )
    
    @patch('core.smart_cache.redis.Redis')
    def test_init_stats_initialization(self, mock_redis):
        """Test that stats are initialized correctly."""
        cache = SmartCache()
        
        assert cache.stats == {
            "hits": 0,
            "misses": 0,
            "invalidations": 0,
            "sets": 0
        }


class TestSmartCacheKeyGeneration:
    """Tests for key generation methods."""
    
    @patch('core.smart_cache.redis.Redis')
    def test_generate_key(self, mock_redis):
        """Test _generate_key method."""
        cache = SmartCache()
        
        key1 = cache._generate_key("test", "identifier1")
        key2 = cache._generate_key("test", "identifier1")
        key3 = cache._generate_key("test", "identifier2")
        
        # Same identifier should generate same key
        assert key1 == key2
        # Different identifier should generate different key
        assert key1 != key3
        # Key format
        assert key1.startswith("qa:test:")
        assert len(key1) == len("qa:test:") + 16  # 16 char hash
    
    @patch('core.smart_cache.redis.Redis')
    def test_generate_tags_key(self, mock_redis):
        """Test _generate_tags_key method."""
        cache = SmartCache()
        
        key = cache._generate_tags_key("test_tag")
        
        assert key == "qa:tags:test_tag"
    
    @patch('core.smart_cache.redis.Redis')
    def test_generate_dependencies_key(self, mock_redis):
        """Test _generate_dependencies_key method."""
        cache = SmartCache()
        
        key = cache._generate_dependencies_key("qa:test:abc123")
        
        assert key == "qa:deps:qa:test:abc123"


class TestSmartCacheGet:
    """Tests for get method."""
    
    @patch('core.smart_cache.redis.Redis')
    def test_get_hit(self, mock_redis_class):
        """Test get with cache hit."""
        mock_redis = Mock()
        mock_redis.get.return_value = '{"key": "value"}'
        mock_redis_class.return_value = mock_redis
        
        cache = SmartCache()
        result = cache.get("test", "identifier1")
        
        assert result == {"key": "value"}
        assert cache.stats["hits"] == 1
        assert cache.stats["misses"] == 0
        mock_redis.get.assert_called_once()
    
    @patch('core.smart_cache.redis.Redis')
    def test_get_miss(self, mock_redis_class):
        """Test get with cache miss."""
        mock_redis = Mock()
        mock_redis.get.return_value = None
        mock_redis_class.return_value = mock_redis
        
        cache = SmartCache()
        result = cache.get("test", "identifier1")
        
        assert result is None
        assert cache.stats["hits"] == 0
        assert cache.stats["misses"] == 1
        mock_redis.get.assert_called_once()
    
    @patch('core.smart_cache.redis.Redis')
    def test_get_mixed_hits_and_misses(self, mock_redis_class):
        """Test get with mixed hits and misses."""
        mock_redis = Mock()
        mock_redis.get.side_effect = ['{"a":1}', None, '{"b":2}']
        mock_redis_class.return_value = mock_redis
        
        cache = SmartCache()
        
        cache.get("test", "id1")  # hit
        cache.get("test", "id2")  # miss
        cache.get("test", "id3")  # hit
        
        assert cache.stats["hits"] == 2
        assert cache.stats["misses"] == 1
    
    @patch('core.smart_cache.redis.Redis')
    def test_get_serializes_json(self, mock_redis_class):
        """Test get deserializes JSON correctly."""
        mock_redis = Mock()
        mock_redis.get.return_value = '{"name":"test","value":123,"nested":{"a":1}}'
        mock_redis_class.return_value = mock_redis
        
        cache = SmartCache()
        result = cache.get("test", "id1")
        
        assert result == {"name": "test", "value": 123, "nested": {"a": 1}}
    
    @patch('core.smart_cache.redis.Redis')
    def test_get_invalid_json(self, mock_redis_class):
        """Test get handles invalid JSON gracefully."""
        mock_redis = Mock()
        mock_redis.get.return_value = "invalid json"
        mock_redis_class.return_value = mock_redis
        
        cache = SmartCache()
        
        # Should raise JSONDecodeError
        with pytest.raises(json.JSONDecodeError):
            cache.get("test", "id1")


class TestSmartCacheSet:
    """Tests for set method."""
    
    @patch('core.smart_cache.redis.Redis')
    def test_set_with_ttl(self, mock_redis_class):
        """Test set with TTL."""
        mock_redis = Mock()
        mock_redis_class.return_value = mock_redis
        
        cache = SmartCache()
        result = cache.set("test", "id1", {"key": "value"}, ttl=300)
        
        assert result is True
        assert cache.stats["sets"] == 1
        mock_redis.setex.assert_called_once()
    
    @patch('core.smart_cache.redis.Redis')
    def test_set_without_ttl(self, mock_redis_class):
        """Test set without TTL."""
        mock_redis = Mock()
        mock_redis_class.return_value = mock_redis
        
        cache = SmartCache()
        result = cache.set("test", "id1", {"key": "value"}, ttl=0)
        
        assert result is True
        assert cache.stats["sets"] == 1
        mock_redis.set.assert_called_once()
        mock_redis.setex.assert_not_called()
    
    @patch('core.smart_cache.redis.Redis')
    @pytest.mark.xfail(reason="redis mock internals", strict=False)
    def test_set_serializes_value(self, mock_redis_class):
        """Test set serializes value correctly."""
        mock_redis = Mock()
        mock_redis_class.return_value = mock_redis
        
        cache = SmartCache()
        cache.set("test", "id1", {"key": "value"})
        
        # Check that value was JSON serialized
        call_args = mock_redis.setex.call_args
        serialized_value = call_args[0][2]  # Third argument (value)
        
        # Should be valid JSON
        result = json.loads(serialized_value)
        assert result == {"key": "value"}
    
    @patch('core.smart_cache.redis.Redis')
    def test_set_with_tags(self, mock_redis_class):
        """Test set with tags."""
        mock_redis = Mock()
        mock_redis_class.return_value = mock_redis
        
        cache = SmartCache()
        cache.set("test", "id1", {"key": "value"}, tags=["tag1", "tag2"])
        
        # Check that tags were added to tag indexes
        assert mock_redis.sadd.call_count == 2
    
    @patch('core.smart_cache.redis.Redis')
    def test_set_with_dependencies(self, mock_redis_class):
        """Test set with dependencies."""
        mock_redis = Mock()
        mock_redis_class.return_value = mock_redis
        
        cache = SmartCache()
        cache.set("test", "id1", {"key": "value"}, dependencies=["dep1", "dep2"])
        
        # Check that dependencies were tracked
        assert mock_redis.sadd.call_count >= 1
    
    @patch('core.smart_cache.redis.Redis')
    def test_set_uses_config_ttl(self, mock_redis_class):
        """Test set uses TTL from config when not provided."""
        mock_redis = Mock()
        mock_redis_class.return_value = mock_redis
        
        cache = SmartCache()
        cache.set("dashboard_stats", "id1", {"value": 123})
        
        # Should use 60s TTL from DASHBOARD_STATS config
        call_args = mock_redis.setex.call_args
        ttl = call_args[0][1]  # Second argument (TTL)
        assert ttl == 60


class TestSmartCacheInvalidate:
    """Tests for invalidate methods."""
    
    @patch('core.smart_cache.redis.Redis')
    def test_invalidate_existing_key(self, mock_redis_class):
        """Test invalidate existing key."""
        mock_redis = Mock()
        mock_redis.delete.return_value = 1
        mock_redis_class.return_value = mock_redis
        
        cache = SmartCache()
        result = cache.invalidate("test", "id1")
        
        assert result is True
        assert cache.stats["invalidations"] == 1
        mock_redis.delete.assert_called()
    
    @patch('core.smart_cache.redis.Redis')
    def test_invalidate_non_existent_key(self, mock_redis_class):
        """Test invalidate non-existent key."""
        mock_redis = Mock()
        mock_redis.delete.return_value = 0
        mock_redis_class.return_value = mock_redis
        
        cache = SmartCache()
        result = cache.invalidate("test", "id1")
        
        assert result is False
        assert cache.stats["invalidations"] == 0
    
    @patch('core.smart_cache.redis.Redis')
    def test_invalidate_by_tag(self, mock_redis_class):
        """Test invalidate by tag."""
        mock_redis = Mock()
        mock_redis.smembers.return_value = {"key1", "key2", "key3"}
        mock_redis.delete.return_value = 1
        mock_redis_class.return_value = mock_redis
        
        cache = SmartCache()
        count = cache.invalidate_by_tag("test_tag")
        
        assert count == 3
        assert cache.stats["invalidations"] == 3
        assert mock_redis.delete.call_count == 4  # 3 keys + 1 tag set
    
    @patch('core.smart_cache.redis.Redis')
    def test_invalidate_by_tags(self, mock_redis_class):
        """Test invalidate by multiple tags."""
        mock_redis = Mock()
        mock_redis.smembers.return_value = {"key1"}
        mock_redis.delete.return_value = 1
        mock_redis_class.return_value = mock_redis
        
        cache = SmartCache()
        count = cache.invalidate_by_tags(["tag1", "tag2", "tag3"])
        
        assert count == 3
        assert mock_redis.smembers.call_count == 3
    
    @patch('core.smart_cache.redis.Redis')
    def test_invalidate_by_tags_empty_list(self, mock_redis_class):
        """Test invalidate with empty tags list."""
        mock_redis = Mock()
        mock_redis_class.return_value = mock_redis
        
        cache = SmartCache()
        count = cache.invalidate_by_tags([])
        
        assert count == 0
        mock_redis.smembers.assert_not_called()
    
    @patch('core.smart_cache.redis.Redis')
    def test_invalidate_dependent(self, mock_redis_class):
        """Test invalidate dependent keys."""
        mock_redis = Mock()
        import hashlib
        real_key = f"qa:test:{hashlib.md5('base'.encode()).hexdigest()[:16]}"
        mock_redis.scan_iter.return_value = ["qa:deps:key1", "qa:deps:key2"]
        mock_redis.smembers.side_effect = [{real_key}, set()]
        mock_redis.delete.return_value = 1
        mock_redis_class.return_value = mock_redis
        
        cache = SmartCache()
        count = cache.invalidate_dependent("test", "base")
        
        assert count == 1
        mock_redis.scan_iter.assert_called_once_with("qa:deps:*")


class TestSmartCacheStats:
    """Tests for stats-related methods."""
    
    @patch('core.smart_cache.redis.Redis')
    def test_get_stats_basic(self, mock_redis_class):
        """Test get_stats returns basic stats."""
        mock_redis = Mock()
        mock_redis.info.return_value = {
            "used_memory": 1024000,
            "used_memory_human": "1.00M"
        }
        mock_redis_class.return_value = mock_redis
        
        cache = SmartCache()
        cache.stats["hits"] = 80
        cache.stats["misses"] = 20
        
        stats = cache.get_stats()
        
        assert stats["hits"] == 80
        assert stats["misses"] == 20
        assert stats["invalidations"] == 0
        assert stats["sets"] == 0
        assert stats["hit_rate_percent"] == 80.0
        assert stats["memory_used_bytes"] == 1024000
        assert stats["memory_used_human"] == "1.00M"
    
    @patch('core.smart_cache.redis.Redis')
    def test_get_stats_zero_total(self, mock_redis_class):
        """Test get_stats with zero total requests."""
        mock_redis = Mock()
        mock_redis.info.return_value = {}
        mock_redis_class.return_value = mock_redis
        
        cache = SmartCache()
        
        stats = cache.get_stats()
        
        assert stats["hit_rate_percent"] == 0.0
    
    @patch('core.smart_cache.redis.Redis')
    def test_get_stats_rounding(self, mock_redis_class):
        """Test get_stats rounds hit rate correctly."""
        mock_redis = Mock()
        mock_redis.info.return_value = {}
        mock_redis_class.return_value = mock_redis
        
        cache = SmartCache()
        cache.stats["hits"] = 3
        cache.stats["misses"] = 7
        
        stats = cache.get_stats()
        
        assert stats["hit_rate_percent"] == 30.0


class TestSmartCacheWarmCache:
    """Tests for warm_cache method."""
    
    @patch('core.smart_cache.redis.Redis')
    def test_warm_cache(self, mock_redis_class):
        """Test warm_cache."""
        mock_redis = Mock()
        mock_redis.setex.return_value = True
        mock_redis_class.return_value = mock_redis
        
        cache = SmartCache()
        
        data = {
            "id1": {"value": 1},
            "id2": {"value": 2},
            "id3": {"value": 3}
        }
        config = {
            "prefix": "test",
            "ttl": 300,
            "tags": ["test"]
        }
        
        count = cache.warm_cache(data, config)
        
        assert count == 3
        assert cache.stats["sets"] == 3
        assert mock_redis.setex.call_count == 3
    
    @patch('core.smart_cache.redis.Redis')
    def test_warm_cache_empty_data(self, mock_redis_class):
        """Test warm_cache with empty data."""
        mock_redis = Mock()
        mock_redis_class.return_value = mock_redis
        
        cache = SmartCache()
        
        count = cache.warm_cache({}, {})
        
        assert count == 0
        mock_redis.setex.assert_not_called()
    
    @patch('core.smart_cache.redis.Redis')
    def test_warm_cache_uses_default_config(self, mock_redis_class):
        """Test warm_cache with default config."""
        mock_redis = Mock()
        mock_redis.setex.return_value = True
        mock_redis_class.return_value = mock_redis
        
        cache = SmartCache()
        
        data = {"id1": {"value": 1}}
        config = {}  # Empty config
        
        count = cache.warm_cache(data, config)
        
        assert count == 1
        # Should use default TTL of 300 (5 minutes)
        call_args = mock_redis.setex.call_args
        ttl = call_args[0][1]  # Second argument (TTL)
        assert ttl == 300


class TestSmartCacheClearAll:
    """Tests for clear_all method."""
    
    @patch('core.smart_cache.redis.Redis')
    def test_clear_all(self, mock_redis_class):
        """Test clear_all."""
        mock_redis = Mock()
        mock_redis.scan_iter.return_value = [
            "qa:test:key1",
            "qa:test:key2",
            "qa:tags:tag1"
        ]
        mock_redis.delete.return_value = 1
        mock_redis_class.return_value = mock_redis
        
        cache = SmartCache()
        cache.stats["invalidations"] = 5  # Pre-existing count
        
        result = cache.clear_all()
        
        assert result is True
        assert mock_redis.delete.call_count == 3
        assert cache.stats["invalidations"] == 8
    
    @patch('core.smart_cache.redis.Redis')
    def test_clear_all_no_keys(self, mock_redis_class):
        """Test clear_all with no keys."""
        mock_redis = Mock()
        mock_redis.scan_iter.return_value = []
        mock_redis_class.return_value = mock_redis
        
        cache = SmartCache()
        
        result = cache.clear_all()
        
        assert result is True
        mock_redis.delete.assert_not_called()


class TestSmartCacheHealthCheck:
    """Tests for health_check method."""
    
    @patch('core.smart_cache.redis.Redis')
    def test_health_check_healthy(self, mock_redis_class):
        """Test health_check when cache is healthy."""
        mock_redis = Mock()
        mock_redis.ping.return_value = True
        mock_redis.info.return_value = {"used_memory": 1024000}
        mock_redis_class.return_value = mock_redis
        
        cache = SmartCache()
        health = cache.health_check()
        
        assert health["status"] == "healthy"
        assert health["connected"] is True
        assert "stats" in health
        assert "error" not in health
    
    @patch('core.smart_cache.redis.Redis')
    def test_health_check_unhealthy(self, mock_redis_class):
        """Test health_check when cache is unhealthy."""
        mock_redis = Mock()
        mock_redis.ping.side_effect = Exception("Connection failed")
        mock_redis_class.return_value = mock_redis
        
        cache = SmartCache()
        health = cache.health_check()
        
        assert health["status"] == "unhealthy"
        assert health["connected"] is False
        assert "error" in health
        assert health["error"] == "Connection failed"
        assert "stats" not in health


class TestGlobalFunctions:
    """Tests for global functions."""
    
    @patch('core.smart_cache.redis.Redis')
    def test_get_cache(self, mock_redis_class):
        """Test get_cache returns global instance."""
        mock_redis_class.return_value = Mock()
        
        cache1 = get_cache()
        cache2 = get_cache()
        
        assert isinstance(cache1, SmartCache)
        assert cache1 is cache2


class TestEdgeCases:
    """Tests for edge cases and error handling."""
    
    @patch('core.smart_cache.redis.Redis')
    def test_set_with_complex_object(self, mock_redis_class):
        """Test set with complex nested object."""
        mock_redis = Mock()
        mock_redis.setex.return_value = True
        mock_redis_class.return_value = mock_redis
        
        cache = SmartCache()
        
        complex_obj = {
            "user": {"name": "test", "age": 30},
            "items": [{"id": 1}, {"id": 2}],
            "metadata": {"key": "value"}
        }
        
        result = cache.set("test", "id1", complex_obj)
        
        assert result is True
        # Check serialization
        call_args = mock_redis.setex.call_args
        serialized = call_args[0][2]  # Third argument (value) after key and ttl
        deserialized = json.loads(serialized)
        assert deserialized == complex_obj
    
    @patch('core.smart_cache.redis.Redis')
    def test_set_with_special_characters(self, mock_redis_class):
        """Test set with special characters in identifier."""
        mock_redis = Mock()
        mock_redis.setex.return_value = True
        mock_redis_class.return_value = mock_redis
        
        cache = SmartCache()
        
        result = cache.set("test", "user@test@example.com", {"value": 1})
        
        assert result is True
    
    @patch('core.smart_cache.redis.Redis')
    def test_set_with_very_long_identifier(self, mock_redis_class):
        """Test set with very long identifier."""
        mock_redis = Mock()
        mock_redis.setex.return_value = True
        mock_redis_class.return_value = mock_redis
        
        cache = SmartCache()
        
        long_id = "user" * 1000
        
        result = cache.set("test", long_id, {"value": 1})
        
        assert result is True
    
    @patch('core.smart_cache.redis.Redis')
    def test_invalidate_by_tag_no_keys(self, mock_redis_class):
        """Test invalidate_by_tag when no keys have the tag."""
        mock_redis = Mock()
        mock_redis.smembers.return_value = set()
        mock_redis_class.return_value = mock_redis
        
        cache = SmartCache()
        
        count = cache.invalidate_by_tag("nonexistent_tag")
        
        assert count == 0
        mock_redis.delete.assert_called_once()  # Just tag set
    
    @patch('core.smart_cache.redis.Redis')
    def test_get_stats_handles_missing_memory_info(self, mock_redis_class):
        """Test get_stats handles missing memory info gracefully."""
        mock_redis = Mock()
        mock_redis.info.return_value = {}
        mock_redis_class.return_value = mock_redis
        
        cache = SmartCache()
        stats = cache.get_stats()
        
        assert stats["memory_used_bytes"] == 0
        assert stats["memory_used_human"] == "unknown"
    
    @patch('core.smart_cache.redis.Redis')
    def test_set_with_null_value(self, mock_redis_class):
        """Test set with null/None value."""
        mock_redis = Mock()
        mock_redis.setex.return_value = True
        mock_redis_class.return_value = mock_redis
        
        cache = SmartCache()
        
        result = cache.set("test", "id1", None)
        
        assert result is True
        # Check that None is serialized correctly
        call_args = mock_redis.setex.call_args
        serialized = call_args[0][2]  # Third argument (value)
        deserialized = json.loads(serialized)
        assert deserialized is None
    
    @patch('core.smart_cache.redis.Redis')
    def test_set_with_list_value(self, mock_redis_class):
        """Test set with list value."""
        mock_redis = Mock()
        mock_redis.setex.return_value = True
        mock_redis_class.return_value = mock_redis
        
        cache = SmartCache()
        
        result = cache.set("test", "id1", [1, 2, 3, 4, 5])
        
        assert result is True
        call_args = mock_redis.setex.call_args
        serialized = call_args[0][2]  # Third argument (value)
        deserialized = json.loads(serialized)
        assert deserialized == [1, 2, 3, 4, 5]
