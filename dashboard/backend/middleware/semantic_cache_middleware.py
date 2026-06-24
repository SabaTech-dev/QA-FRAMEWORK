"""
Semantic Cache Middleware — FastAPI middleware for caching QA endpoint responses.

Caches GET responses for configured endpoints using semantic similarity.
Skips caching for non-GET requests and when Cache-Control: no-cache is set.

Usage in main.py:
    from middleware.semantic_cache_middleware import SemanticCacheMiddleware
    app.add_middleware(SemanticCacheMiddleware)

Configuration (env vars):
    SEMANTIC_CACHE_ENABLED   — "true"/"false" (default: true)
    SEMANTIC_CACHE_THRESHOLD — cosine similarity threshold (default: 0.92)
    SEMANTIC_CACHE_TTL       — default TTL in seconds (default: 300)
    SEMANTIC_CACHE_ENDPOINTS — comma-separated list of path prefixes to cache
                               (default: /api/v1/dashboard,/api/v1/suites,/api/v1/cases,/api/v1/executions)
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import List, Optional, Tuple

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)

# Default endpoints that benefit from semantic caching
_DEFAULT_CACHED_PREFIXES = [
    "/api/v1/dashboard",
    "/api/v1/suites",
    "/api/v1/cases",
    "/api/v1/executions",
    "/api/v1/scan",
]


def _get_cached_prefixes() -> List[str]:
    """Get list of path prefixes eligible for semantic caching."""
    raw = os.getenv(
        "SEMANTIC_CACHE_ENDPOINTS",
        ",".join(_DEFAULT_CACHED_PREFIXES),
    )
    return [p.strip() for p in raw.split(",") if p.strip()]


def _should_cache(method: str, path: str, status_code: int) -> bool:
    """Determine if a response should be cached."""
    if method != "GET":
        return False
    if status_code != 200:
        return False
    prefixes = _get_cached_prefixes()
    return any(path.startswith(p) for p in prefixes)


class SemanticCacheMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware that caches GET responses using semantic similarity.

    On cache hit, returns the cached JSON response directly (skipping endpoint logic).
    On cache miss, executes the endpoint and caches the response.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # Only cache GET requests
        if request.method != "GET":
            return await call_next(request)

        path = request.url.path
        if not _should_cache(request.method, path, 200):
            return await call_next(request)

        # Skip if client requests no-cache
        cache_control = request.headers.get("cache-control", "")
        if "no-cache" in cache_control.lower():
            return await call_next(request)

        # Build params dict from query string
        params = dict(request.query_params)

        # Try semantic cache
        try:
            from src.infrastructure.cache.semantic_cache import get_semantic_cache

            cache = get_semantic_cache()

            if cache.is_enabled:
                cached = cache.get(request.method, path, params)
                if cached is not None:
                    logger.debug("Semantic cache HIT: %s %s", request.method, path)
                    return Response(
                        content=json.dumps(cached, default=str),
                        media_type="application/json",
                        headers={"X-Cache": "HIT"},
                    )
        except Exception as exc:
            logger.warning("Semantic cache lookup failed: %s", exc)

        # Cache miss — execute endpoint
        response = await call_next(request)

        # Only touch the body for cacheable GET 200s; otherwise pass through
        # the original streaming response untouched (reading body_iterator
        # would consume it and break the response).
        if not _should_cache(request.method, path, response.status_code):
            return response

        # Consume the body once. body_iterator is exhausted after this, so we
        # MUST reconstruct a fresh Response regardless of caching outcome —
        # returning the original `response` here yields an empty body and a
        # "Response content shorter than Content-Length" RuntimeError.
        body = b""
        try:
            async for chunk in response.body_iterator:
                body += chunk
        except Exception as exc:
            logger.warning("Semantic cache body read failed: %s", exc)
            return response  # iterator not fully consumed; still safe to return

        # Best-effort cache store; never let it break the response.
        try:
            data = json.loads(body)
            from src.infrastructure.cache.semantic_cache import get_semantic_cache

            cache = get_semantic_cache()
            if cache.is_enabled:
                cache.set(request.method, path, params, data)
                logger.debug("Semantic cache SET: %s %s", request.method, path)
        except Exception as exc:
            logger.warning("Semantic cache store failed: %s", exc)

        # Reconstruct the response. Drop hop-by-hop / length headers so
        # Starlette recomputes Content-Length from `content` — reusing the
        # original content-length header causes truncated responses when the
        # body passes back through the BaseHTTPMiddleware chain.
        forwarded_headers = {
            k: v
            for k, v in response.headers.items()
            if k.lower() not in ("content-length", "transfer-encoding", "content-encoding")
        }
        return Response(
            content=body,
            status_code=response.status_code,
            media_type=response.media_type,
            headers=forwarded_headers,
        )
