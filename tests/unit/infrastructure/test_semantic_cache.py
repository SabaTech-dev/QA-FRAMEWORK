"""Tests for semantic cache module."""

import pytest
from unittest.mock import MagicMock, patch
from typing import Any, Dict, List, Optional

from src.infrastructure.cache.semantic_cache import (
    SemanticCache,
    _EmbeddingProvider,
    _NullEmbedProvider,
    _InMemoryVectorStore,
    _VectorEntry,
)
from src.infrastructure.cache.cache_stats import CacheStats
from src.infrastructure.cache.test_cache import TestCache


# ---------------------------------------------------------------------------
# _NullEmbedProvider
# ---------------------------------------------------------------------------

class TestNullEmbedProvider:
    def test_embed_returns_empty(self):
        provider = _NullEmbedProvider()
        assert provider.embed("hello") == []

    def test_embed_batch_returns_empty_list(self):
        provider = _NullEmbedProvider()
        assert provider.embed_batch(["hello", "world"]) == []


# ---------------------------------------------------------------------------
# _VectorEntry
# ---------------------------------------------------------------------------

class TestVectorEntry:
    def test_not_expired_fresh(self):
        entry = _VectorEntry("k", [1.0], "val", ttl=300)
        assert not entry.is_expired

    def test_expired(self):
        entry = _VectorEntry("k", [1.0], "val", ttl=0)
        import time
        time.sleep(0.01)
        assert entry.is_expired


# ---------------------------------------------------------------------------
# _InMemoryVectorStore
# ---------------------------------------------------------------------------

class TestInMemoryVectorStore:
    def _make_store(self):
        return _InMemoryVectorStore()

    def test_upsert_and_search_exact_match(self):
        store = self._make_store()
        entry = _VectorEntry("k1", [1.0, 0.0, 0.0], {"data": "a"}, ttl=300)
        store.upsert(entry)
        results = store.search([1.0, 0.0, 0.0], threshold=0.9)
        assert len(results) == 1
        assert results[0][0] == "k1"
        assert results[0][2] == {"data": "a"}

    def test_search_below_threshold(self):
        store = self._make_store()
        entry = _VectorEntry("k1", [1.0, 0.0, 0.0], "val", ttl=300)
        store.upsert(entry)
        results = store.search([0.0, 1.0, 0.0], threshold=0.9)
        assert len(results) == 0

    def test_search_returns_top_k(self):
        store = self._make_store()
        store.upsert(_VectorEntry("k1", [1.0, 0.0], "a", ttl=300))
        store.upsert(_VectorEntry("k2", [0.9, 0.1], "b", ttl=300))
        store.upsert(_VectorEntry("k3", [0.8, 0.2], "c", ttl=300))
        results = store.search([1.0, 0.0], threshold=0.5, top_k=2)
        assert len(results) == 2
        # k1 should be first (highest similarity)
        assert results[0][0] == "k1"

    def test_expired_entries_removed_on_search(self):
        store = self._make_store()
        store.upsert(_VectorEntry("k1", [1.0], "val", ttl=0))
        import time
        time.sleep(0.01)
        results = store.search([1.0], threshold=0.9)
        assert len(results) == 0
        assert store.size == 0

    def test_delete(self):
        store = self._make_store()
        store.upsert(_VectorEntry("k1", [1.0], "val", ttl=300))
        store.delete("k1")
        assert store.size == 0

    def test_clear(self):
        store = self._make_store()
        store.upsert(_VectorEntry("k1", [1.0], "a", ttl=300))
        store.upsert(_VectorEntry("k2", [0.0], "b", ttl=300))
        store.clear()
        assert store.size == 0


# ---------------------------------------------------------------------------
# CacheStats
# ---------------------------------------------------------------------------

class TestCacheStats:
    def test_initial_state(self):
        stats = CacheStats()
        assert stats.total_hits == 0
        assert stats.total_misses == 0
        assert stats.hit_rate == 0.0

    def test_record_hit(self):
        stats = CacheStats()
        stats.record_hit("key1")
        stats.record_hit("key1")
        assert stats.total_hits == 2
        assert stats.total_misses == 0

    def test_record_miss(self):
        stats = CacheStats()
        stats.record_miss("key1")
        assert stats.total_misses == 1

    def test_hit_rate(self):
        stats = CacheStats()
        stats.record_hit("k1")
        stats.record_hit("k2")
        stats.record_miss("k3")
        assert stats.hit_rate == pytest.approx(66.67, abs=0.1)

    def test_get_stats(self):
        stats = CacheStats()
        stats.record_hit("k1")
        stats.record_miss("k2")
        result = stats.get_stats()
        assert result["total_hits"] == 1
        assert result["total_misses"] == 1
        assert result["total_requests"] == 2
        assert result["unique_keys"] == 2

    def test_reset(self):
        stats = CacheStats()
        stats.record_hit("k1")
        stats.reset()
        assert stats.total_hits == 0
        assert stats.total_misses == 0


# ---------------------------------------------------------------------------
# TestCache
# ---------------------------------------------------------------------------

class TestTestCache:
    def _make_store(self):
        return TestCache(redis_client=None)

    def test_set_and_get(self):
        cache = self._make_store()
        cache.set("key1", {"result": "ok"}, ttl=60)
        assert cache.get("key1") == {"result": "ok"}

    def test_get_miss(self):
        cache = self._make_store()
        assert cache.get("nonexistent") is None

    def test_delete(self):
        cache = self._make_store()
        cache.set("key1", "val", ttl=60)
        cache.delete("key1")
        assert cache.get("key1") is None

    def test_clear_all(self):
        cache = self._make_store()
        cache.set("k1", "a", ttl=60)
        cache.set("k2", "b", ttl=60)
        cache.clear_all()
        assert cache.get("k1") is None
        assert cache.get("k2") is None

    def test_get_keys_by_suite(self):
        cache = self._make_store()
        cache.set("test_suite_123_test_456", "a", ttl=60)
        cache.set("test_suite_123_test_789", "b", ttl=60)
        cache.set("test_suite_999_test_111", "c", ttl=60)
        keys = cache.get_keys_by_suite(123)
        assert len(keys) == 2

    def test_get_keys_by_test(self):
        cache = self._make_store()
        cache.set("test_suite_100_test_456", "a", ttl=60)
        cache.set("test_suite_200_test_456", "b", ttl=60)
        keys = cache.get_keys_by_test(456)
        assert len(keys) == 2

    def test_get_keys_matching(self):
        cache = self._make_store()
        cache.set("test_suite_123_test_456", "a", ttl=60)
        cache.set("other_key", "b", ttl=60)
        keys = cache.get_keys_matching("test_suite_123_*")
        assert len(keys) == 1


# ---------------------------------------------------------------------------
# SemanticCache — unit tests with mock embedder
# ---------------------------------------------------------------------------


class _MockEmbedProvider(_EmbeddingProvider):
    """Deterministic mock embedder for testing."""

    def __init__(self, vectors: Optional[Dict[str, List[float]]] = None) -> None:
        self._vectors = vectors or {}
        self._default = [1.0, 0.0, 0.0]
        self.call_count = 0

    def embed(self, text: str) -> List[float]:
        self.call_count += 1
        if text in self._vectors:
            return self._vectors[text]
        # Return a deterministic vector based on text hash
        h = hash(text) % 1000
        return [float(h) / 1000.0, 1.0 - float(h) / 1000.0, 0.0]


class TestSemanticCache:
    def _make_cache(self, **kwargs: Any) -> SemanticCache:
        store = _InMemoryVectorStore()
        embedder = _MockEmbedProvider()
        return SemanticCache(
            embed_provider=embedder,
            vector_store=store,
            threshold=0.9,
            default_ttl=300,
            **kwargs,
        )

    def test_make_key_deterministic(self):
        k1 = SemanticCache.make_key("GET", "/api/v1/stats", {"user": "1"})
        k2 = SemanticCache.make_key("GET", "/api/v1/stats", {"user": "1"})
        assert k1 == k2

    def test_make_key_different_for_different_params(self):
        k1 = SemanticCache.make_key("GET", "/api/v1/stats", {"user": "1"})
        k2 = SemanticCache.make_key("GET", "/api/v1/stats", {"user": "2"})
        assert k1 != k2

    def test_make_key_order_independent(self):
        k1 = SemanticCache.make_key("GET", "/api/v1/stats", {"a": "1", "b": "2"})
        k2 = SemanticCache.make_key("GET", "/api/v1/stats", {"b": "2", "a": "1"})
        assert k1 == k2

    def test_make_query_text(self):
        text = SemanticCache.make_query_text("GET", "/api/v1/stats", {"user": "1"})
        assert "GET" in text
        assert "/api/v1/stats" in text
        assert "user=1" in text

    def test_get_returns_none_when_disabled(self):
        cache = self._make_cache()
        cache._enabled = False
        result = cache.get("GET", "/api/v1/stats")
        assert result is None

    def test_set_and_get_roundtrip(self):
        cache = self._make_cache()
        # Use same mock vector for both texts so they match
        embedder = cache._embedder
        assert isinstance(embedder, _MockEmbedProvider)
        embedder._vectors["GET /api/v1/stats"] = [1.0, 0.0, 0.0]
        embedder._vectors["GET /api/v1/stats"] = [1.0, 0.0, 0.0]

        cache.set("GET", "/api/v1/stats", None, {"result": "ok"})
        result = cache.get("GET", "/api/v1/stats", None)
        assert result == {"result": "ok"}

    def test_get_miss_returns_none(self):
        cache = self._make_cache()
        result = cache.get("GET", "/api/v1/nonexistent")
        assert result is None

    def test_stats_tracking(self):
        cache = self._make_cache()
        embedder = cache._embedder
        assert isinstance(embedder, _MockEmbedProvider)
        embedder._vectors["GET /api/v1/stats"] = [1.0, 0.0, 0.0]

        cache.set("GET", "/api/v1/stats", None, "data")
        cache.get("GET", "/api/v1/stats", None)  # hit
        cache.get("GET", "/api/v1/other", None)  # miss

        stats = cache.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_rate"] == 50.0

    def test_invalidate(self):
        cache = self._make_cache()
        embedder = cache._embedder
        assert isinstance(embedder, _MockEmbedProvider)
        embedder._vectors["GET /api/v1/stats"] = [1.0, 0.0, 0.0]

        cache.set("GET", "/api/v1/stats", None, "data")
        cache.invalidate("GET", "/api/v1/stats", None)
        result = cache.get("GET", "/api/v1/stats", None)
        assert result is None

    def test_clear(self):
        cache = self._make_cache()
        embedder = cache._embedder
        assert isinstance(embedder, _MockEmbedProvider)
        embedder._vectors["GET /api/v1/stats"] = [1.0, 0.0, 0.0]

        cache.set("GET", "/api/v1/stats", None, "data")
        cache.clear()
        assert cache.get_stats()["store_size"] == 0

    def test_null_embedder_disables_cache(self):
        cache = SemanticCache(embed_provider=_NullEmbedProvider())
        assert not cache.is_enabled
        assert cache.get("GET", "/api/v1/stats") is None
        assert not cache.set("GET", "/api/v1/stats", None, "data")
