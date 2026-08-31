"""
Rate Limiting Middleware

Implements granular rate limiting:
- Per-plan limits (Free: 100/hr, Pro: 1,000/hr, Enterprise: 10,000/hr)
- Per-endpoint limits (login: 20/min, executions: 60/min)
- Burst protection
- Redis-backed for distributed rate limiting
"""

import os
import time
from typing import Optional, Callable
from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import structlog
from prometheus_client import Counter

from core.rate_limit_config import get_rate_limit, get_burst_limit, get_endpoint_limit
from services.cache_service import get_redis_client

logger = structlog.get_logger()

# Backing-store (redis) failures inside the rate limiter are never silent:
# every failure increments this counter (exposed via /metrics, alertable).
RATE_LIMIT_BACKEND_FAILURES = Counter(
    "rate_limit_backend_failures",
    "Rate limit checks that failed on the backing store (e.g. redis errors)",
    ["fail_mode"],
)


class RateLimiter:
    """
    Redis-backed rate limiter with sliding window algorithm
    
    Features:
    - Per-plan rate limiting
    - Endpoint-specific limits
    - Burst protection
    - Sliding window for accurate rate limiting
    """
    
    def __init__(self, redis_client=None, fail_mode: Optional[str] = None):
        """
        Initialize rate limiter
        
        Args:
            redis_client: Redis client (optional, will use default if not provided)
            fail_mode: Behavior on backing-store failure ("open"|"closed").
                Defaults to env RATE_LIMIT_FAIL_MODE, else "open".
        Valid fail modes (env RATE_LIMIT_FAIL_MODE):
        - "open" (default): allow requests if the backing store fails, but
          mark the response as degraded (header + metric + log event).
        - "closed": deny requests with 503 while the backing store is down.
        """
        self.redis = redis_client or get_redis_client()
        self.prefix = "ratelimit:"
        self.fail_mode = (fail_mode or os.getenv("RATE_LIMIT_FAIL_MODE", "open")).strip().lower()
        if self.fail_mode not in ("open", "closed"):
            logger.warning("Invalid RATE_LIMIT_FAIL_MODE, falling back to open", value=self.fail_mode)
            self.fail_mode = "open"
    
    async def is_allowed(
        self,
        identifier: str,
        plan: str,
        endpoint: str
    ) -> tuple[bool, dict]:
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
                window=60  # 1 minute
            )
            if info.get("degraded"):
                # Backing store down: short-circuit so each request produces
                # exactly one failure event, not one per limit bucket.
                return is_allowed, info
            if not is_allowed:
                return False, info
        
        # Check burst limit
        burst_key = f"{self.prefix}burst:{identifier}"
        is_allowed, burst_info = await self._check_limit(
            burst_key,
            burst_limit,
            window=60  # 1 minute
        )
        if burst_info.get("degraded"):
            return is_allowed, burst_info
        if not is_allowed:
            return False, burst_info
        
        # Check hourly limit
        hourly_key = f"{self.prefix}hourly:{identifier}"
        is_allowed, hourly_info = await self._check_limit(
            hourly_key,
            hourly_limit,
            window=3600  # 1 hour
        )
        if hourly_info.get("degraded"):
            return is_allowed, hourly_info
        if not is_allowed:
            return False, hourly_info
        
        # All checks passed
        return True, hourly_info
    
    async def _check_limit(
        self,
        key: str,
        limit: int,
        window: int
    ) -> tuple[bool, dict]:
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
                "window": window
            }
            
            return is_allowed, info
            
        except Exception as e:
            # Backing-store failure — never silent: distinct log event + metric.
            # Details stay server-side (no error strings in responses).
            try:
                RATE_LIMIT_BACKEND_FAILURES.labels(fail_mode=self.fail_mode).inc()
            except Exception:
                pass
            logger.error(
                "rate_limit_backend_failure",
                fail_mode=self.fail_mode,
                error_type=type(e).__name__,
                error=str(e),
                key=key,
            )
            info = {
                "limit": limit,
                "remaining": limit,
                "reset": int(current_time + window),
                "window": window,
                "degraded": True,
            }
            if self.fail_mode == "closed":
                return False, info
            # Fail open (default): allow request but flag degradation
            return True, info


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
            "/openapi.json"
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
            identifier=identifier,
            plan=plan,
            endpoint=request.url.path
        )
        
        degraded = bool(rate_info.get("degraded"))
        
        # Add rate limit headers
        headers = {
            "X-RateLimit-Limit": str(rate_info.get("limit", 0)),
            "X-RateLimit-Remaining": str(rate_info.get("remaining", 0)),
            "X-RateLimit-Reset": str(rate_info.get("reset", 0))
        }
        if degraded:
            # Externally visible signal that rate limiting is currently
            # unavailable (backing store failure).
            headers["X-RateLimit-Mode"] = "degraded"
        
        if not is_allowed:
            if degraded:
                # RATE_LIMIT_FAIL_MODE=closed: backing store down. This is a
                # service degradation, NOT a client abuse signal — 503, not 429.
                return JSONResponse(
                    status_code=503,
                    content={"detail": "Service temporarily degraded, please retry later"},
                    headers={**headers, "Retry-After": "30"}
                )
            # Rate limit exceeded
            logger.warning(
                "Rate limit exceeded",
                identifier=identifier,
                endpoint=request.url.path,
                limit=rate_info.get("limit")
            )
            
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded",
                    "limit": rate_info.get("limit"),
                    "reset": rate_info.get("reset")
                },
                headers=headers
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
        
        # Fall back to IP address
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return f"ip:{forwarded.split(',')[0].strip()}"
        
        client_ip = request.client.host if request.client else "unknown"
        return f"ip:{client_ip}"
    
    def _get_plan(self, request: Request) -> str:
        """Get user's plan for rate limiting"""
        # Try to get plan from user
        if hasattr(request.state, "user") and request.state.user:
            return getattr(request.state.user, "subscription_plan", "free")
        
        # Default to free plan
        return "free"


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
    identifier = f"user:{request.state.user.id}" if hasattr(request.state, "user") else f"ip:{request.client.host}"
    
    is_allowed, rate_info = await limiter.is_allowed(
        identifier=identifier,
        plan=plan,
        endpoint=request.url.path
    )
    
    if not is_allowed:
        if rate_info.get("degraded"):
            raise HTTPException(
                status_code=503,
                detail="Service temporarily degraded, please retry later"
            )
        raise HTTPException(
            status_code=429,
            detail={
                "message": "Rate limit exceeded",
                "limit": rate_info.get("limit"),
                "reset": rate_info.get("reset")
            }
        )
    
    return rate_info
