"""
Rate Limiting Middleware

Implements granular rate limiting:
- Per-plan limits (Free: 100/hr, Pro: 1,000/hr, Enterprise: 10,000/hr)
- Per-endpoint limits (login: 20/min, executions: 60/min)
- Burst protection
- Redis-backed for distributed rate limiting

card e8a6b3a7:
- F-1: this middleware runs PRE-auth (Starlette order: the LAST
  add_middleware runs FIRST, so request.state.user never exists here).
  Identity/plan are extracted by decoding the JWT directly (light decode,
  no DB), falling back to ip:* for anonymous requests.
- F-3: all tier checks run in ONE atomic Lua script (previously up to ~12
  non-atomic Redis round-trips per request), and Redis failure fails
  CLOSED for anonymous requests (fail-open only for authenticated users).
"""

import time
from uuid import uuid4
from typing import Optional, Callable
from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from jose import jwt as jose_jwt
import structlog

from config import settings
from core.rate_limit_config import get_rate_limit, get_burst_limit, get_endpoint_limit
from services.auth_service import ACCESS_TOKEN_TYPES
from services.cache_service import get_redis_client

logger = structlog.get_logger()

# Atomic sliding-window check across all tiers in a single round-trip.
# ARGV layout: [limit_1, window_1, now, limit_2, window_2, now, ..., nonce]
# Returns: {denied_index (0=allowed), limit, remaining, reset} of the
# failing check, or of the last (hourly) check when allowed.
_SLIDING_WINDOW_LUA = """
local denied = 0
local counts = {}
for i = 1, #KEYS do
    local key = KEYS[i]
    local limit = tonumber(ARGV[i * 3 - 2])
    local window = tonumber(ARGV[i * 3 - 1])
    local now = tonumber(ARGV[i * 3])
    redis.call('ZREMRANGEBYSCORE', key, 0, now - window)
    local count = redis.call('ZCARD', key)
    counts[i] = count
    if count >= limit and denied == 0 then
        denied = i
    end
end
if denied == 0 then
    local nonce = ARGV[#KEYS * 3 + 1]
    for i = 1, #KEYS do
        local key = KEYS[i]
        local window = tonumber(ARGV[i * 3 - 1])
        local now = tonumber(ARGV[i * 3])
        redis.call('ZADD', key, now, nonce .. ':' .. i)
        redis.call('EXPIRE', key, window)
    end
end
local idx = denied
if idx == 0 then idx = #KEYS end
local limit = tonumber(ARGV[idx * 3 - 2])
local window = tonumber(ARGV[idx * 3 - 1])
local now = tonumber(ARGV[idx * 3])
local used = counts[idx]
if denied == 0 then used = used + 1 end
return {denied, limit, math.max(0, limit - used), math.floor(now + window)}
"""


class RateLimiter:
    """
    Redis-backed rate limiter with sliding window algorithm

    All tiers (endpoint / burst / hourly) are checked and incremented
    atomically by a single Lua script per request.
    """

    def __init__(self, redis_client=None):
        self.redis = redis_client or get_redis_client()
        self.prefix = "ratelimit:"

    async def is_allowed(
        self,
        identifier: str,
        plan: str,
        endpoint: str,
        authenticated: bool = False,
    ) -> tuple[bool, dict]:
        """
        Check if request is allowed

        Args:
            identifier: Unique identifier (user:{sub} or ip:{addr})
            plan: User's subscription plan
            endpoint: API endpoint path
            authenticated: whether the request carries a valid access JWT.
                On Redis failure, authenticated requests degrade to
                fail-open; anonymous ones fail CLOSED (F-3).
        """
        checks = []  # (key, limit, window_seconds)
        endpoint_limit = get_endpoint_limit(endpoint)
        if endpoint_limit:
            checks.append(
                (
                    f"{self.prefix}endpoint:{identifier}:{endpoint}",
                    endpoint_limit,
                    60,
                )
            )
        checks.append(
            (
                f"{self.prefix}burst:{identifier}",
                get_burst_limit(plan),
                60,
            )
        )
        checks.append(
            (
                f"{self.prefix}hourly:{identifier}",
                get_rate_limit(plan),
                3600,
            )
        )

        now = time.time()
        keys = [c[0] for c in checks]
        args: list = []
        for _, limit, window in checks:
            args.extend([limit, window, now])
        args.append(uuid4().hex)  # unique member nonce: same-timestamp requests must not collide

        try:
            res = await self.redis.eval(_SLIDING_WINDOW_LUA, len(keys), *(keys + args))
        except Exception as e:
            logger.error("Rate limit check failed", error=str(e), identifier=identifier)
            if authenticated:
                # Degraded mode: never lock out authenticated users
                return True, {"limit": 0, "remaining": 0, "reset": 0, "error": str(e)}
            # F-3: fail CLOSED for anonymous traffic when Redis is down
            return False, {"limit": 0, "remaining": 0, "reset": 0, "error": str(e)}

        denied, limit, remaining, reset = (int(res[0]), int(res[1]), int(res[2]), int(res[3]))
        return denied == 0, {
            "limit": limit,
            "remaining": remaining,
            "reset": reset,
        }


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

        identifier, plan, authenticated = self._get_identity(request)

        is_allowed, rate_info = await self.rate_limiter.is_allowed(
            identifier=identifier,
            plan=plan,
            endpoint=request.url.path,
            authenticated=authenticated,
        )

        # Add rate limit headers
        headers = {
            "X-RateLimit-Limit": str(rate_info.get("limit", 0)),
            "X-RateLimit-Remaining": str(rate_info.get("remaining", 0)),
            "X-RateLimit-Reset": str(rate_info.get("reset", 0)),
        }

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

    def _get_identity(self, request: Request) -> tuple[str, str, bool]:
        """
        F-1: this middleware runs PRE-auth, so request.state.user is never
        set here. Decode the access JWT lightly (no DB): valid token ->
        (user:{sub}, token plan claim, True); otherwise -> (ip:{addr},
        free, False).
        """
        auth = request.headers.get("Authorization") or ""
        if auth.startswith("Bearer "):
            try:
                payload = jose_jwt.decode(
                    auth[len("Bearer ") :],
                    settings.secret_key.get_secret_value(),
                    algorithms=[settings.algorithm],
                )
                sub = payload.get("sub")
                if sub and payload.get("type") in ACCESS_TOKEN_TYPES:
                    plan = payload.get("plan") or "free"
                    return f"user:{sub}", plan, True
            except Exception:
                pass  # invalid/expired token -> treat as anonymous
        return self._ip_identity(request), "free", False

    def _ip_identity(self, request: Request) -> str:
        forwarded = request.headers.get("X-Forwarded-For") or ""
        if forwarded:
            return f"ip:{forwarded.split(',')[0].strip()}"
        client_ip = request.client.host if request.client else "unknown"
        return f"ip:{client_ip}"


# Dependency for manual rate limiting
async def check_rate_limit(request: Request, plan: str = "free"):
    """
    Dependency to check rate limit manually

    Usage:
        @router.get("/endpoint")
        async def endpoint(request: Request, _: None = Depends(check_rate_limit)):
            ...
    """
    limiter = RateLimiter()
    identifier = (
        f"user:{request.state.user.id}"
        if hasattr(request.state, "user")
        else f"ip:{request.client.host}"
    )

    is_allowed, rate_info = await limiter.is_allowed(
        identifier=identifier, plan=plan, endpoint=request.url.path
    )

    if not is_allowed:
        raise HTTPException(
            status_code=429,
            detail={
                "message": "Rate limit exceeded",
                "limit": rate_info.get("limit"),
                "reset": rate_info.get("reset"),
            },
        )

    return rate_info
