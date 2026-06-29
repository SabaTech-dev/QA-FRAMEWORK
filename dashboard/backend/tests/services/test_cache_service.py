"""
Unit tests for cache_service.py
"""

import pytest
pytest.importorskip('redis')
pytest.importorskip('asyncpg')
import json
from typing import Dict, Any, Optional
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from services.cache_service import (
    CacheService,
    CacheKeyGenerator
)


class TestCacheService:
    """Test suite for CacheService."""

    @pytest.fixture
    def mock_test_cache(self):
        """Mock TestCache instance."""
        return Mock()

    @pytest.fixture
    def mock_stats(self):
        """Mock CacheStats instance."""
        return Mock()

    @pytest.fixture
    def cache_service(self, mock_test_cache, mock_stats):
        """Create CacheService instance."""
        return CacheService(
            test_cache=mock_test_cache,
            stats=mock_stats
        )

    def test_initialization(self, cache_service, mock_test_cache, mock_stats):
        """Test cache service initialization."""
        assert cache_service.test_cache == mock_test_cache
        assert cache_service.stats == mock_stats

    def test_get_or_execute_with_cache_hit(self, cache_service, mock_test_cache, mock_stats):
        """Test get_or_execute returns cached value."""
        # Arrange
        cached_value = {"result": "cached"}
        mock_test_cache.get.return_value = cached_value
        mock_stats.record_hit = Mock()

        # Act
        result = cache_service.get_or_execute(
            key="test_key",
            executor=lambda: {"result": "executed"},
            ttl=3600
        )

        # Assert
        assert result == cached_value
        mock_stats.record_hit.assert_called_once_with("test_key")

    def test_get_or_execute_with_cache_miss(self, cache_service, mock_test_cache, mock_stats):
        """Test get_or_execute executes when cache miss."""
        # Arrange
        mock_test_cache.get.return_value = None
        mock_stats.record_miss = Mock()

        # Act
        result = cache_service.get_or_execute(
            key="test_key",
            executor=lambda: {"result": "executed"},
            ttl=3600
        )

        # Assert
        assert result == {"result": "executed"}
        mock_test_cache.set.assert_called_once()
        mock_stats.record_miss.assert_called_once_with("test_key")

    def test_get_or_execute_with_exception(self, cache_service, mock_test_cache, mock_stats):
        """Test get_or_execute propagates exceptions."""
        # Arrange
        mock_test_cache.get.return_value = None

        # Act & Assert
        with pytest.raises(ValueError):
            cache_service.get_or_execute(
                key="test_key",
                executor=lambda: (_ for _ in ()).throw(ValueError("Test error")),
                ttl=3600
            )

    def test_invalidate_by_suite(self, cache_service, mock_test_cache):
        """Test invalidate by test suite ID."""
        # Arrange
        mock_test_cache.get_keys_by_suite.return_value = ["key1", "key2"]
        mock_test_cache.delete = Mock()

        # Act
        cache_service.invalidate(test_suite_id=123)

        # Assert
        mock_test_cache.get_keys_by_suite.assert_called_once_with(123)
        mock_test_cache.delete.assert_any_call("key1")
        mock_test_cache.delete.assert_any_call("key2")

    def test_invalidate_by_test(self, cache_service, mock_test_cache):
        """Test invalidate by test ID."""
        # Arrange
        mock_test_cache.get_keys_by_test.return_value = ["key1", "key2"]
        mock_test_cache.delete = Mock()

        # Act
        cache_service.invalidate(test_id=456)

        # Assert
        mock_test_cache.get_keys_by_test.assert_called_once_with(456)
        mock_test_cache.delete.assert_any_call("key1")
        mock_test_cache.delete.assert_any_call("key2")

    def test_invalidate_by_pattern(self, cache_service, mock_test_cache):
        """Test invalidate by pattern."""
        # Arrange
        mock_test_cache.get_keys_matching.return_value = ["key1", "key2", "key3"]
        mock_test_cache.delete = Mock()

        # Act
        cache_service.invalidate(pattern="test_*")

        # Assert
        mock_test_cache.get_keys_matching.assert_called_once_with("test_*")
        mock_test_cache.delete.assert_any_call("key1")
        mock_test_cache.delete.assert_any_call("key2")
        mock_test_cache.delete.assert_any_call("key3")

    def test_clear_all(self, cache_service, mock_test_cache):
        """Test clear_all."""
        # Act
        cache_service.clear_all()

        # Assert
        mock_test_cache.clear_all.assert_called_once()

    def test_get_stats(self, cache_service, mock_test_cache, mock_stats):
        """Test get_stats."""
        # Arrange
        mock_stats.get_stats.return_value = {"hits": 100, "misses": 10}

        # Act
        stats = cache_service.get_stats()

        # Assert
        assert stats == {"hits": 100, "misses": 10}
        mock_stats.get_stats.assert_called_once()

    def test_warm_cache(self, cache_service, mock_test_cache):
        """Test warm_cache pre-populates cache."""
        # Arrange
        mock_test_cache.get_keys_by_suite = Mock(return_value=[])
        mock_test_cache.set = Mock()

        def mock_executor(test_id):
            return {"test": test_id, "status": "passed"}

        # Act
        cache_service.warm_cache(
            test_suite_id=123,
            test_ids=[1, 2, 3, 4, 5],
            executor=mock_executor,
            batch_size=2
        )

        # Assert
        assert mock_test_cache.set.call_count == 5

    def test_cache_key_generator_suite_and_test(self):
        """Test CacheKeyGenerator from suite and test."""
        # Act
        key = CacheKeyGenerator.from_suite_and_test(123, 456)

        # Assert
        assert key == "test_suite_123_test_456"

    def test_cache_key_generator_execution(self):
        """Test CacheKeyGenerator from execution ID."""
        # Act
        key = CacheKeyGenerator.from_execution(789)

        # Assert
        assert key == "execution_789"

    def test_cache_key_generator_suite_result(self):
        """Test CacheKeyGenerator from suite result."""
        # Act
        key = CacheKeyGenerator.from_suite_result(123)

        # Assert
        assert key == "execution_result_suite_123"

    def test_cache_key_generator_test_result(self):
        """Test CacheKeyGenerator from test result."""
        # Act
        key = CacheKeyGenerator.from_test_result(456)

        # Assert
        assert key == "execution_result_test_456"

    def test_invalidate_with_multiple_params(self, cache_service, mock_test_cache):
        """Test invalidate with multiple parameters."""
        # Act & Assert
        with pytest.raises(ValueError):
            cache_service.invalidate(test_suite_id=123, test_id=456, pattern="test_*")


class TestCacheKeyGenerator:
    """Test suite for CacheKeyGenerator."""

    def test_all_methods_return_str(self):
        """Test all generator methods return strings."""
        assert isinstance(CacheKeyGenerator.from_suite_and_test(1, 2), str)
        assert isinstance(CacheKeyGenerator.from_execution(1), str)
        assert isinstance(CacheKeyGenerator.from_suite_result(1), str)
        assert isinstance(CacheKeyGenerator.from_test_result(1), str)
