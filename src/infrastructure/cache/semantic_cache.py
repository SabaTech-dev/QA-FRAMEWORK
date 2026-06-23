"""
SemanticCache — vector-similarity cache for QA endpoint responses.

Uses sentence-transformers (nomic-embed-text-v1.5) to embed query text,
stores embeddings in Redis with vector search (or in-memory fallback),
and returns cached responses when cosine similarity exceeds a threshold.

Usage:
    from src.infrastructure.cache import get_semantic_cache

    cache = get_semantic_cache()

    # Check cache
    cached = cache.get("GET /api/v1/dashboard/stats user:123")
    if cached is not None:
        return cached

    # Miss — compute and store
    result = compute_expensive_query()
    cache.set("GET /api/v1/dashboard/stats user:123", result, ttl=300)

Environment:
    SEMANTIC_CACHE_ENABLED     — "true" to enable (default: true)
    SEMANTIC_CACHE_THRESHOLD   — cosine similarity threshold (default: 0.92)
    SEMANTIC_CACHE_TTL         — default TTL in seconds (default: 300)
    SEMANTIC_CACHE_EMBED_MODEL — embedding model (default: nomic-ai/nomic-embed-text-v1.5)
    REDIS_URL / REDIS_HOST     — Redis connection
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from typing import Any, Dict, List, Optional, Tuple
from functools import lru_cache

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Embedding provider abstraction
# ---------------------------------------------------------------------------

class _EmbeddingProvider:
    """Base class for embedding providers."""

    def embed(self, text: str) -> List[float]:
        raise NotImplementedError

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        return [self.embed(t) for t in texts]


class _NomicEmbedProvider(_EmbeddingProvider):
    """nomic-embed-text-v1.5 via sentence-transformers."""

    def __init__(self, model_name: str = "nomic-ai/nomic-embed-text-v1.5") -> None:
        self._model_name = model_name
        self._model: Any = None

    def _load(self) -> None:
        if self._model is not None:
            return
        try:
            from sentence_transformers import SentenceTransformer
            logger.info("Loading embedding model: %s", self._model_name)
            self._model = SentenceTransformer(self._model_name)
            logger.info("Embedding model loaded successfully")
        except ImportError:
            raise ImportError(
                "sentence-transformers not installed. "
                "Add 'sentence-transformers>=3.0.0' to requirements.txt"
            )

    def embed(self, text: str) -> List[float]:
        self._load()
        vec = self._model.encode(text, normalize_embeddings=True)
        return vec.tolist()

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        self._load()
        vecs = self._model.encode(texts, normalize_embeddings=True)
        return [v.tolist() for v in vecs]


class _NullEmbedProvider(_EmbeddingProvider):
    """No-op provider when embeddings are unavailable."""

    def embed(self, text: str) -> List[float]:
        return []


# ---------------------------------------------------------------------------
# Vector store abstraction
# ---------------------------------------------------------------------------

class _VectorEntry:
    __slots__ = ("key", "embedding", "response", "created_at", "ttl")

    def __init__(self, key: str, embedding: List[float], response: Any, ttl: int) -> None:
        self.key = key
        self.embedding = embedding
        self.response = response
        self.created_at = time.time()
        self.ttl = ttl

    @property
    def is_expired(self) -> bool:
        return time.time() - self.created_at > self.ttl


class _InMemoryVectorStore:
    """Simple in-memory vector store with cosine similarity search."""

    def __init__(self) -> None:
        self._entries: Dict[str, _VectorEntry] = {}

    def upsert(self, entry: _VectorEntry) -> None:
        self._entries[entry.key] = entry

    def search(
        self, query_embedding: List[float], threshold: float, top_k: int = 1
    ) -> List[Tuple[str, float, Any]]:
        """Return (key, score, response) tuples above threshold, sorted desc."""
        import math

        results: List[Tuple[str, float, Any]] = []
        for key, entry in list(self._entries.items()):
            if entry.is_expired:
                del self._entries[key]
                continue
            if not entry.embedding:
                continue
            # Cosine similarity (vectors are already normalized)
            dot = sum(a * b for a, b in zip(query_embedding, entry.embedding))
            if dot >= threshold:
                results.append((key, dot, entry.response))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    def delete(self, key: str) -> None:
        self._entries.pop(key, None)

    def clear(self) -> None:
        self._entries.clear()

    @property
    def size(self) -> int:
        return len(self._entries)


class _RedisVectorStore:
    """Redis-backed vector store using RedisJSON + vector search (Redis 7.4+)."""

    def __init__(self, redis_client: Any, prefix: str = "qa:semantic:") -> None:
        self._redis = redis_client
        self._prefix = prefix

    def _key(self, key: str) -> str:
        return f"{self._prefix}{key}"

    def upsert(self, entry: _VectorEntry) -> None:
        try:
            data = json.dumps({
                "embedding": entry.embedding,
                "response": entry.response,
                "created_at": entry.created_at,
                "ttl": entry.ttl,
            })
            self._redis.setex(self._key(entry.key), entry.ttl, data)
        except Exception as exc:
            logger.warning("Redis vector upsert failed: %s", exc)

    def search(
        self, query_embedding: List[float], threshold: float, top_k: int = 1
    ) -> List[Tuple[str, float, Any]]:
        """Fallback: scan all entries and compute cosine similarity in Python."""
        import math

        results: List[Tuple[str, float, Any]] = []
        try:
            cursor = 0
            while True:
                cursor, keys = self._redis.scan(cursor, match=f"{self._prefix}*", count=100)
                for raw_key in keys:
                    try:
                        data = self._redis.get(raw_key)
                        if data is None:
                            continue
                        obj = json.loads(data)
                        if time.time() - obj["created_at"] > obj["ttl"]:
                            self._redis.delete(raw_key)
                            continue
                        emb = obj["embedding"]
                        if not emb:
                            continue
                        dot = sum(a * b for a, b in zip(query_embedding, emb))
                        if dot >= threshold:
                            short_key = raw_key.replace(self._prefix, "", 1)
                            results.append((short_key, dot, obj["response"]))
                    except Exception:
                        continue
                if cursor == 0:
                    break
        except Exception as exc:
            logger.warning("Redis vector search failed: %s", exc)

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    def delete(self, key: str) -> None:
        try:
            self._redis.delete(self._key(key))
        except Exception:
            pass

    def clear(self) -> None:
        try:
            cursor = 0
            while True:
                cursor, keys = self._redis.scan(cursor, match=f"{self._prefix}*", count=100)
                if keys:
                    self._redis.delete(*keys)
                if cursor == 0:
                    break
        except Exception:
            pass

    @property
    def size(self) -> int:
        try:
            count = 0
            cursor = 0
            while True:
                cursor, keys = self._redis.scan(cursor, match=f"{self._prefix}*", count=100)
                count += len(keys)
                if cursor == 0:
                    break
            return count
        except Exception:
            return 0


# ---------------------------------------------------------------------------
# SemanticCache — main class
# ---------------------------------------------------------------------------

class SemanticCache:
    """
    Semantic cache using vector similarity for QA endpoint responses.

    Caches responses keyed by a semantic fingerprint (method + path + params).
    On lookup, embeds the query and searches for similar cached queries above
    a cosine similarity threshold. Returns the cached response on hit.

    Falls back to in-memory store when Redis is unavailable.
    Falls back to no-op when embedding model is unavailable.
    """

    def __init__(
        self,
        *,
        embed_provider: Optional[_EmbeddingProvider] = None,
        vector_store: Optional[Any] = None,
        threshold: float = 0.92,
        default_ttl: int = 300,
        prefix: str = "qa:semantic:",
    ) -> None:
        self._threshold = threshold
        self._default_ttl = default_ttl
        self._prefix = prefix
        self._embedder = embed_provider or self._default_embedder()
        self._store = vector_store or _InMemoryVectorStore()
        self._enabled = os.getenv("SEMANTIC_CACHE_ENABLED", "true").lower() == "true"
        self._stats = {"hits": 0, "misses": 0}

    @staticmethod
    def _default_embedder() -> _EmbeddingProvider:
        model = os.getenv(
            "SEMANTIC_CACHE_EMBED_MODEL", "nomic-ai/nomic-embed-text-v1.5"
        )
        try:
            return _NomicEmbedProvider(model_name=model)
        except Exception as exc:
            logger.warning("Embedding provider unavailable: %s — semantic cache disabled", exc)
            return _NullEmbedProvider()

    @property
    def is_enabled(self) -> bool:
        return self._enabled and not isinstance(self._embedder, _NullEmbedProvider)

    # -- key helpers ---------------------------------------------------------

    @staticmethod
    def make_key(method: str, path: str, params: Optional[Dict] = None) -> str:
        """Build a deterministic cache key from request attributes."""
        parts = [method.upper(), path]
        if params:
            # Sort for determinism
            for k in sorted(params.keys()):
                parts.append(f"{k}={params[k]}")
        raw = "|".join(parts)
        return hashlib.sha256(raw.encode()).hexdigest()[:24]

    @staticmethod
    def make_query_text(method: str, path: str, params: Optional[Dict] = None) -> str:
        """Build human-readable query text for embedding."""
        text = f"{method.upper()} {path}"
        if params:
            text += " " + " ".join(f"{k}={v}" for k, v in sorted(params.items()))
        return text

    # -- core API ------------------------------------------------------------

    def get(
        self,
        method: str,
        path: str,
        params: Optional[Dict] = None,
    ) -> Optional[Any]:
        """
        Look up a cached response by semantic similarity.

        Returns the cached response if a similar query is found above
        the similarity threshold, or None on miss.
        """
        if not self.is_enabled:
            return None

        query_text = self.make_query_text(method, path, params)
        try:
            query_embedding = self._embedder.embed(query_text)
        except Exception as exc:
            logger.warning("Embedding failed: %s", exc)
            return None

        if not query_embedding:
            return None

        results = self._store.search(query_embedding, self._threshold, top_k=1)
        if results:
            key, score, response = results[0]
            self._stats["hits"] += 1
            logger.debug("Semantic cache hit: %s (score=%.4f)", key, score)
            return response

        self._stats["misses"] += 1
        return None

    def set(
        self,
        method: str,
        path: str,
        params: Optional[Dict],
        response: Any,
        ttl: Optional[int] = None,
    ) -> bool:
        """Cache a response for the given query."""
        if not self.is_enabled:
            return False

        key = self.make_key(method, path, params)
        query_text = self.make_query_text(method, path, params)
        try:
            embedding = self._embedder.embed(query_text)
        except Exception as exc:
            logger.warning("Embedding failed on set: %s", exc)
            return False

        if not embedding:
            return False

        entry = _VectorEntry(
            key=key,
            embedding=embedding,
            response=response,
            ttl=ttl or self._default_ttl,
        )
        try:
            self._store.upsert(entry)
            return True
        except Exception as exc:
            logger.warning("Cache set failed: %s", exc)
            return False

    def invalidate(self, method: str, path: str, params: Optional[Dict] = None) -> None:
        """Invalidate a specific cache entry (exact key match)."""
        key = self.make_key(method, path, params)
        self._store.delete(key)

    def clear(self) -> None:
        """Clear all semantic cache entries."""
        self._store.clear()
        self._stats = {"hits": 0, "misses": 0}

    def get_stats(self) -> Dict[str, Any]:
        total = self._stats["hits"] + self._stats["misses"]
        return {
            "enabled": self.is_enabled,
            "threshold": self._threshold,
            "default_ttl": self._default_ttl,
            "hits": self._stats["hits"],
            "misses": self._stats["misses"],
            "hit_rate": round(
                (self._stats["hits"] / total * 100.0) if total > 0 else 0.0, 2
            ),
            "store_size": getattr(self._store, "size", -1),
        }


@lru_cache(maxsize=1)
def get_semantic_cache() -> SemanticCache:
    """Get the SemanticCache singleton."""
    threshold = float(os.getenv("SEMANTIC_CACHE_THRESHOLD", "0.92"))
    ttl = int(os.getenv("SEMANTIC_CACHE_TTL", "300"))

    # Try Redis first
    store: Any = _InMemoryVectorStore()
    try:
        from services.cache_service import get_redis_client
        redis = get_redis_client()
        store = _RedisVectorStore(redis)
        logger.info("SemanticCache using Redis vector store")
    except Exception as exc:
        logger.info("SemanticCache using in-memory vector store: %s", exc)

    return SemanticCache(
        vector_store=store,
        threshold=threshold,
        default_ttl=ttl,
    )
