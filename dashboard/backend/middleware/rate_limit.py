"""
Rate Limiting Middleware

Implements granular rate limiting:
- Per-plan limits (Free: 100/hr, Pro: 1,000/hr, Enterprise: 10,000/hr)
- Per-endpoint limits (see core.rate_limit_config.ENDPOINT_LIMITS)
- Burst protection
- Redis-backed for distributed rate limiting
"""

import os
import time
from typing import Optional, Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from prometheus_client import Counter
import structlog

from core.rate_limit_config import get_rate_limit, get_burst_limit, get_endpoint_limit
from services.cache_service import get_redis_client

logger = structlog.get_logger()

# F-1 (card 39ea6180): Redis-down alert dedup - log critical once per window,
# not on every request (post-mortem Read the Docs DDoS scenario).
_REDIS_ALERT_WINDOW_SECONDS = 60.0
_redis_down = {"last_alert": 0.0}

# PR #106 port (card 77079bca, audit OBS-1): backing-store failures are never
# silent — Prometheus counter per fail_mode, exposed via the existing /metrics
# mount and alertable.
RATE_LIMIT_BACKEND_FAILURES = Counter(
    "rate_limit_backend_failures",
    "Rate limit checks that failed on the backing store (e.g. redis errors)",
    ["fail_mode"],
)


def _get_fail_mode() -> str:
    """F-1: RATE_LIMIT_FAIL_MODE=open|closed, read at call time (pattern F-2).

    open (default, staging compat): allow requests when Redis fails.
    closed (recommended prod): deny (429) when Redis fails.
    """
    mode = os.getenv("RATE_LIMIT_FAIL_MODE", "open").strip().lower()
    return "closed" if mode == "closed" else "open"


def _alert_redis_down(key: str, error: Exception) -> None:
    """Critical structured alert, deduped once per alert window (F-1)."""
    now = time.monotonic()
    if now - _redis_down["last_alert"] < _REDIS_ALERT_WINDOW_SECONDS:
        return
    _redis_down["last_alert"] = now
    logger.critical(
        "Redis unavailable - rate limiting degraded",
        fail_mode=_get_fail_mode(),
        key=key,
        error=str(error),
        alert_window_seconds=_REDIS_ALERT_WINDOW_SECONDS,
    )


def _resolve_client_ip(request: Request) -> str:
    """Resolve the client IP for rate limiting (card d9056216, F-2; fix
    off-by-one card 77079bca, review Alfred).

    With TRUSTED_PROXY_DEPTH=N, the rightmost N XFF entries were put there by
    our own proxies, so the client IP is the N-th entry from the right
    (invariant under attacker prepends). Covers both real proxy semantics:
    - SET (nginx vhost qa.sabatech.dev: `proxy_set_header X-Forwarded-For
      $remote_addr`): XFF carries EXACTLY the real client IP (client-sent
      history is destroyed by the proxy) -> depth=1 picks it.
    - APPEND (`$proxy_add_x_forwarded_for` chains): the appended peers form
      the trusted suffix; prepended attacker entries fall outside it.

    depth=0 (default, staging): XFF is fully client-controlled and is
    ignored; the socket peer address (request.client.host) is used instead.
    Read at call time, not import time, so config is never frozen.
    """
    try:
        depth = int(os.getenv("TRUSTED_PROXY_DEPTH", "0"))
    except ValueError:
        depth = 0

    if depth <= 0:
        return request.client.host if request.client else "unknown"

    forwarded = request.headers.get("X-Forwarded-For", "")
    hops = [hop.strip() for hop in forwarded.split(",") if hop.strip()]
    if len(hops) < depth:
        # Fewer hops than the configured proxy depth: the XFF chain does not
        # prove the trusted proxies touched it -> fall back to peer IP.
        return request.client.host if request.client else "unknown"

    # Fix off-by-one (card 77079bca, review Alfred): the client IP is the N-th
    # entry from the right, not the (N+1)-th. Covers SET semantics (nginx
    # XFF=$remote_addr: single entry = real client) and APPEND chains (the
    # trusted suffix is ours; prepended attacker entries fall outside it).
    return hops[-depth]


class RateLimiter:
    """
    Redis-backed rate limiter with sliding window algorithm

    Features:
    - Per-plan rate limiting
    - Endpoint-specific limits
    - Burst protection
    - Sliding window for accurate rate limiting
    """

    def __init__(self, redis_client=None):
        """
        Initialize rate limiter

        Args:
            redis_client: Redis client (optional, will use default if not provided)
        """
        self.redis = redis_client or get_redis_client()
        self.prefix = "ratelimit:"

    async def is_allowed(self, identifier: str, plan: str, endpoint: str) -> tuple[bool, dict]:
        """
        Check if request is allowed

        Args:
            identifier: Unique identifier (user_id or IP)
            plan: User's subscription plan
            endpoint: API endpoint path

        Returns:
            Tuple of (is_allowed, rate_limit_info)
        """
        current_time = time.time()

        # Get limits
        hourly_limit = get_rate_limit(plan)
        burst_limit = get_burst_limit(plan)
        endpoint_limit = get_endpoint_limit(endpoint)

        # Check endpoint-specific limit first
        if endpoint_limit:
            endpoint_key = f"{self.prefix}endpoint:{identifier}:{endpoint}"
            is_allowed, info = await self._check_limit(
                endpoint_key,
                endpoint_limit,
                window=60,  # 1 minute
            )
            if not is_allowed:
                return False, info
            if info.get("degraded"):
                # PR #106 port: single backing-store failure per request —
                # remaining buckets skipped (counter stays 1:1, no 3x inflation).
                return is_allowed, info

        # Check burst limit
        burst_key = f"{self.prefix}burst:{identifier}"
        is_allowed, burst_info = await self._check_limit(
            burst_key,
            burst_limit,
            window=60,  # 1 minute
        )
        if not is_allowed:
            return False, burst_info
        if burst_info.get("degraded"):
            return is_allowed, burst_info

        # Check hourly limit
        hourly_key = f"{self.prefix}hourly:{identifier}"
        is_allowed, hourly_info = await self._check_limit(
            hourly_key,
            hourly_limit,
            window=3600,  # 1 hour
        )
        if not is_allowed:
            return False, hourly_info

        # All checks passed
        return True, hourly_info

    async def _check_limit(self, key: str, limit: int, window: int) -> tuple[bool, dict]:
        """
        Check rate limit using sliding window

        Args:
            key: Redis key
            limit: Maximum requests allowed
            window: Time window in seconds

        Returns:
            Tuple of (is_allowed, rate_limit_info)
        """
        current_time = time.time()
        window_start = current_time - window

        try:
            # Remove old entries
            await self.redis.zremrangebyscore(key, 0, window_start)

            # Count current entries
            current_count = await self.redis.zcard(key)

            # Calculate remaining
            remaining = max(0, limit - current_count)

            # Check if allowed
            is_allowed = current_count < limit

            if is_allowed:
                # Add current request
                await self.redis.zadd(key, {str(current_time): current_time})
                # Set expiry
                await self.redis.expire(key, window)

            # Prepare info
            info = {
                "limit": limit,
                "remaining": remaining,
                "reset": int(current_time + window),
                "window": window,
            }

            return is_allowed, info

        except Exception as e:
            _alert_redis_down(key, e)
            try:
                RATE_LIMIT_BACKEND_FAILURES.labels(fail_mode=_get_fail_mode()).inc()
            except Exception:
                pass
            if _get_fail_mode() == "closed":
                # F-1 (card 39ea6180): fail closed - deny when Redis is down
                return False, {"limit": limit, "remaining": 0, "degraded": True}
            # Fail open (default, staging compat) - allow request if Redis fails.
            # PR #106 port: degraded flag + S-3 (no backend error strings in info;
            # details stay server-side in the alert log).
            return True, {"limit": limit, "remaining": limit, "degraded": True}


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware for FastAPI

    Usage:
        app.add_middleware(RateLimitMiddleware)
    """

    def __init__(self, app, rate_limiter: Optional[RateLimiter] = None):
        super().__init__(app)
        self.rate_limiter = rate_limiter or RateLimiter()

        # Paths to skip rate limiting.
        # NOTE (card f90a8079): FastAPI redirect_slashes 307-redirects /metrics to
        # /metrics/, so this middleware sees the TRAILING-SLASH variant. Compare
        # with trailing slashes stripped on BOTH sides; the request path itself
        # is never mutated.
        self.skip_paths = {
            "/metrics",
            "/health",
            "/api/v1/health",
            "/docs",
            "/redoc",
            "/openapi.json",
        }
        self._skip_paths_norm = {p.rstrip("/") for p in self.skip_paths}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with rate limiting"""

        # Skip rate limiting for certain paths (trailing-slash tolerant)
        if request.url.path.rstrip("/") in self._skip_paths_norm:
            return await call_next(request)

        # Get identifier (user_id or IP)
        identifier = self._get_identifier(request)

        # Get plan (from user or default to free)
        plan = self._get_plan(request)

        # Check rate limit
        is_allowed, rate_info = await self.rate_limiter.is_allowed(
            identifier=identifier, plan=plan, endpoint=request.url.path
        )

        # Add rate limit headers
        headers = {
            "X-RateLimit-Limit": str(rate_info.get("limit", 0)),
            "X-RateLimit-Remaining": str(rate_info.get("remaining", 0)),
            "X-RateLimit-Reset": str(rate_info.get("reset", 0)),
        }
        if rate_info.get("degraded"):
            # PR #106 port: open mode keeps serving but signals degradation.
            headers["X-RateLimit-Mode"] = "degraded"

        if not is_allowed:
            # Rate limit exceeded
            logger.warning(
                "Rate limit exceeded",
                identifier=identifier,
                endpoint=request.url.path,
                limit=rate_info.get("limit"),
            )

            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded",
                    "limit": rate_info.get("limit"),
                    "reset": rate_info.get("reset"),
                },
                headers=headers,
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers to response
        for key, value in headers.items():
            response.headers[key] = value

        return response

    def _get_identifier(self, request: Request) -> str:
        """Get unique identifier for rate limiting"""
        # Try to get user_id from state
        if hasattr(request.state, "user") and request.state.user:
            return f"user:{request.state.user.id}"

        # Fall back to client IP (validated against TRUSTED_PROXY_DEPTH,
        # never the raw client-controlled X-Forwarded-For leftmost value)
        return f"ip:{_resolve_client_ip(request)}"

    def _get_plan(self, request: Request) -> str:
        """Get user's plan for rate limiting"""
        # Try to get plan from user
        if hasattr(request.state, "user") and request.state.user:
            return getattr(request.state.user, "subscription_plan", "free")

        # Default to free plan
        return "free"
