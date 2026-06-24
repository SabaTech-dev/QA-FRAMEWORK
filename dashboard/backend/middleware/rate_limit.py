"""
Rate Limiting Middleware

Implements granular rate limiting:
- Per-plan limits (Free: 100/hr, Pro: 1,000/hr, Enterprise: 10,000/hr)
- Per-endpoint limits (login: 20/min, executions: 60/min)
- Burst protection
- Redis-backed for distributed rate limiting
"""

import time
from typing import Optional, Callable
from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import structlog

from core.rate_limit_config import get_rate_limit, get_burst_limit, get_endpoint_limit
from services.cache_service import get_redis_client

logger = structlog.get_logger()


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
            if not is_allowed:
                return False, info
        
        # Check burst limit
        burst_key = f"{self.prefix}burst:{identifier}"
        is_allowed, burst_info = await self._check_limit(
            burst_key,
            burst_limit,
            window=60  # 1 minute
        )
        if not is_allowed:
            return False, burst_info
        
        # Check hourly limit
        hourly_key = f"{self.prefix}hourly:{identifier}"
        is_allowed, hourly_info = await self._check_limit(
            hourly_key,
            hourly_limit,
            window=3600  # 1 hour
        )
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
            logger.error("Rate limit check failed", error=str(e), key=key)
            # Fail open - allow request if Redis fails
            return True, {"limit": limit, "remaining": limit, "error": str(e)}


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware for FastAPI
    
    Usage:
        app.add_middleware(RateLimitMiddleware)
    """
    
    def __init__(self, app, rate_limiter: Optional[RateLimiter] = None):
        super().__init__(app)
        self.rate_limiter = rate_limiter or RateLimiter()
        
        # Paths to skip rate limiting
        self.skip_paths = {
            "/metrics",
            "/health",
            "/api/v1/health",
            "/api/v1/health/live",
            "/api/v1/health/ready",
            "/docs",
            "/redoc",
            "/openapi.json"
        }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with rate limiting"""
        
        # Skip rate limiting for certain paths (exact match or health prefix)
        path = request.url.path
        if path in self.skip_paths or path.startswith("/api/v1/health"):
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
        
        # Add rate limit headers
        headers = {
            "X-RateLimit-Limit": str(rate_info.get("limit", 0)),
            "X-RateLimit-Remaining": str(rate_info.get("remaining", 0)),
            "X-RateLimit-Reset": str(rate_info.get("reset", 0))
        }
        
        if not is_allowed:
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
        raise HTTPException(
            status_code=429,
            detail={
                "message": "Rate limit exceeded",
                "limit": rate_info.get("limit"),
                "reset": rate_info.get("reset")
            }
        )
    
    return rate_info
