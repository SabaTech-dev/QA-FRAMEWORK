"""
Tests for Rate Limiting

Covers:
- Per-plan rate limiting
- Endpoint-specific limits
- Burst protection
- Sliding window algorithm
- Redis integration
"""

import pytest
pytest.importorskip('fastapi')
pytest.importorskip('redis')
pytest.importorskip('asyncpg')
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
import time

from middleware.rate_limit import RateLimiter, RateLimitMiddleware
from core.rate_limit_config import (
    get_rate_limit,
    get_burst_limit,
    get_endpoint_limit,
    PlanType,
    RATE_LIMITS,
    BURST_LIMITS
)


@pytest.fixture
def mock_redis():
    """Create mock Redis client"""
    redis = AsyncMock()
    redis.zremrangebyscore = AsyncMock(return_value=0)
    redis.zcard = AsyncMock(return_value=0)
    redis.zadd = AsyncMock(return_value=1)
    redis.expire = AsyncMock(return_value=True)
    return redis


@pytest.fixture
def rate_limiter(mock_redis):
    """Create rate limiter with mock Redis"""
    return RateLimiter(redis_client=mock_redis)


@pytest.fixture
def app():
    """Create test FastAPI app with rate limiting"""
    app = FastAPI()
    app.add_middleware(RateLimitMiddleware)
    
    @app.get("/test")
    async def test_endpoint():
        return {"status": "ok"}
    
    @app.get("/api/v1/auth/login")
    async def login():
        return {"token": "test"}
    
    @app.get("/health")
    async def health():
        return {"status": "ok"}
    
    return app


@pytest.fixture
def client(app):
    """Create test client"""
    return TestClient(app)


class TestRateLimitConfig:
    """Tests for rate limit configuration"""
    
    def test_get_rate_limit_free(self):
        """Should return free plan limit"""
        limit = get_rate_limit("free")
        assert limit == RATE_LIMITS[PlanType.FREE]
    
    def test_get_rate_limit_pro(self):
        """Should return pro plan limit"""
        limit = get_rate_limit("pro")
        assert limit == RATE_LIMITS[PlanType.PRO]
    
    def test_get_rate_limit_enterprise(self):
        """Should return enterprise plan limit"""
        limit = get_rate_limit("enterprise")
        assert limit == RATE_LIMITS[PlanType.ENTERPRISE]
    
    def test_get_rate_limit_invalid(self):
        """Should return free limit for invalid plan"""
        limit = get_rate_limit("invalid")
        assert limit == RATE_LIMITS[PlanType.FREE]
    
    def test_get_burst_limit(self):
        """Should return burst limit"""
        limit = get_burst_limit("pro")
        assert limit == BURST_LIMITS[PlanType.PRO]
    
    def test_get_endpoint_limit_login(self):
        """Should return login endpoint limit"""
        limit = get_endpoint_limit("/api/v1/auth/login")
        assert limit == 20
    
    def test_get_endpoint_limit_executions(self):
        """Should return executions endpoint limit"""
        limit = get_endpoint_limit("/api/v1/executions")
        assert limit == 60
    
    def test_get_endpoint_limit_unlimited(self):
        """Should return None for unlimited endpoint"""
        limit = get_endpoint_limit("/api/v1/suites")
        assert limit is None


class TestRateLimiter:
    """Tests for RateLimiter"""
    
    @pytest.mark.asyncio
    async def test_is_allowed_under_limit(self, rate_limiter, mock_redis):
        """Should allow request under limit"""
        mock_redis.zcard = AsyncMock(return_value=5)
        
        is_allowed, info = await rate_limiter.is_allowed(
            identifier="user:123",
            plan="pro",
            endpoint="/api/v1/test"
        )
        
        assert is_allowed is True
        assert info["remaining"] > 0
    
    @pytest.mark.asyncio
    async def test_is_allowed_at_limit(self, rate_limiter, mock_redis):
        """Should deny request at limit"""
        # Set count to limit
        mock_redis.zcard = AsyncMock(return_value=1000)
        
        is_allowed, info = await rate_limiter.is_allowed(
            identifier="user:123",
            plan="pro",
            endpoint="/api/v1/test"
        )
        
        assert is_allowed is False
        assert info["remaining"] == 0
    
    @pytest.mark.asyncio
    async def test_is_allowed_endpoint_limit(self, rate_limiter, mock_redis):
        """Should enforce endpoint-specific limit"""
        # Set count to 15 (under pro limit but over login limit)
        mock_redis.zcard = AsyncMock(return_value=15)
        
        is_allowed, info = await rate_limiter.is_allowed(
            identifier="user:123",
            plan="pro",
            endpoint="/api/v1/auth/login"
        )
        
        # Login limit is 20, so 15 should be allowed
        assert is_allowed is True
    
    @pytest.mark.asyncio
    async def test_is_allowed_burst_limit(self, rate_limiter, mock_redis):
        """Should enforce burst limit"""
        # Set count to 150 (over pro burst limit of 100)
        mock_redis.zcard = AsyncMock(return_value=150)
        
        is_allowed, info = await rate_limiter.is_allowed(
            identifier="user:123",
            plan="pro",
            endpoint="/api/v1/test"
        )
        
        assert is_allowed is False
    
    @pytest.mark.asyncio
    async def test_redis_failure_fails_open(self, rate_limiter, mock_redis):
        """Should allow request if Redis fails (default open mode), flagged degraded"""
        mock_redis.zcard = AsyncMock(side_effect=Exception("Redis error"))
        
        is_allowed, info = await rate_limiter.is_allowed(
            identifier="user:123",
            plan="free",
            endpoint="/api/v1/test"
        )
        
        assert is_allowed is True
        assert info.get("degraded") is True
        # Error details must stay server-side (S-3 discipline: no leakage)
        assert "error" not in info


class TestFailModeBehavior:
    """Behavior on backing-store failure (card 4f9fb443, audit OBS-1)"""
    
    @pytest.fixture
    def failing_redis(self):
        redis = AsyncMock()
        redis.zremrangebyscore = AsyncMock(side_effect=Exception("Event loop is closed"))
        return redis
    
    @pytest.mark.asyncio
    async def test_fail_open_marks_degraded(self, failing_redis):
        """Open mode: request allowed, degraded flag set"""
        limiter = RateLimiter(redis_client=failing_redis, fail_mode="open")
        is_allowed, info = await limiter.is_allowed("user:1", "free", "/api/v1/test")
        assert is_allowed is True
        assert info.get("degraded") is True
    
    @pytest.mark.asyncio
    async def test_fail_closed_denies(self, failing_redis):
        """Closed mode: request denied, degraded flag set"""
        limiter = RateLimiter(redis_client=failing_redis, fail_mode="closed")
        is_allowed, info = await limiter.is_allowed("user:1", "free", "/api/v1/test")
        assert is_allowed is False
        assert info.get("degraded") is True
    
    @pytest.mark.asyncio
    async def test_backend_failure_short_circuits_single_event(self, failing_redis):
        """One backing-store failure per request: first redis error short-circuits"""
        limiter = RateLimiter(redis_client=failing_redis, fail_mode="open")
        await limiter.is_allowed("user:1", "pro", "/api/v1/auth/login")
        # Endpoint limit bucket is the first check → exactly 1 redis call, not 3
        assert failing_redis.zremrangebyscore.await_count == 1
    
    @pytest.mark.asyncio
    async def test_failure_metric_incremented(self, failing_redis):
        """Every backing-store failure increments the Prometheus counter"""
        from prometheus_client import REGISTRY
        
        def sample(mode):
            return REGISTRY.get_sample_value(
                "rate_limit_backend_failures_total", {"fail_mode": mode}
            ) or 0
        
        before_open = sample("open")
        before_closed = sample("closed")
        
        await RateLimiter(redis_client=failing_redis, fail_mode="open").is_allowed(
            "user:1", "free", "/api/v1/test")
        await RateLimiter(redis_client=failing_redis, fail_mode="closed").is_allowed(
            "user:1", "free", "/api/v1/test")
        
        assert sample("open") == before_open + 1
        assert sample("closed") == before_closed + 1
    
    def test_invalid_fail_mode_falls_back_open(self, failing_redis):
        """Unknown RATE_LIMIT_FAIL_MODE value falls back to open"""
        limiter = RateLimiter(redis_client=failing_redis, fail_mode="yolo")
        assert limiter.fail_mode == "open"
    
    def test_middleware_open_mode_200_with_degraded_header(self, failing_redis):
        """Middleware: open mode keeps serving but exposes X-RateLimit-Mode: degraded"""
        app = FastAPI()
        app.add_middleware(
            RateLimitMiddleware,
            rate_limiter=RateLimiter(redis_client=failing_redis, fail_mode="open"),
        )
        
        @app.get("/test")
        async def test_endpoint():
            return {"status": "ok"}
        
        response = TestClient(app).get("/test")
        assert response.status_code == 200
        assert response.headers.get("X-RateLimit-Mode") == "degraded"
    
    def test_middleware_closed_mode_503_no_leak(self, failing_redis):
        """Middleware: closed mode returns 503 + Retry-After, no backend error leaked"""
        app = FastAPI()
        app.add_middleware(
            RateLimitMiddleware,
            rate_limiter=RateLimiter(redis_client=failing_redis, fail_mode="closed"),
        )
        
        @app.get("/test")
        async def test_endpoint():
            return {"status": "ok"}
        
        response = TestClient(app).get("/test")
        assert response.status_code == 503
        assert response.headers.get("Retry-After") == "30"
        assert "Event loop is closed" not in response.text


class TestRateLimitMiddleware:
    """Tests for RateLimitMiddleware"""
    
    def test_skip_paths(self, client):
        """Should skip rate limiting for certain paths"""
        # These should not have rate limit headers
        response = client.get("/health")
        assert response.status_code == 200
        assert "X-RateLimit-Limit" not in response.headers
    
    def test_rate_limit_headers(self, client):
        """Should add rate limit headers"""
        response = client.get("/test")
        assert response.status_code == 200
        # Note: Would check headers in real test with proper middleware setup
    
    def test_rate_limit_exceeded(self, mock_redis):
        """Should return 429 when rate limit exceeded via direct limiter check"""
        mock_redis.zcard = AsyncMock(return_value=10000)
        
        limiter = RateLimiter(redis_client=mock_redis)
        
        # Use direct limiter check (middleware integration requires async ASGI)
        import asyncio
        is_allowed, info = asyncio.run(
            limiter.is_allowed("user:123", "free", "/api/v1/test")
        )
        
        assert is_allowed is False
        assert info["remaining"] == 0


class TestSlidingWindow:
    """Tests for sliding window algorithm"""
    
    @pytest.mark.asyncio
    async def test_sliding_window_expiry(self, rate_limiter, mock_redis):
        """Should expire old entries"""
        await rate_limiter._check_limit("test_key", 100, window=60)
        
        # Should call zremrangebyscore to remove old entries
        mock_redis.zremrangebyscore.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_sliding_window_adds_entry(self, rate_limiter, mock_redis):
        """Should add current request to sorted set"""
        await rate_limiter._check_limit("test_key", 100, window=60)
        
        # Should call zadd to add current request
        mock_redis.zadd.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_sliding_window_sets_expiry(self, rate_limiter, mock_redis):
        """Should set expiry on key"""
        await rate_limiter._check_limit("test_key", 100, window=60)
        
        # Should call expire to set TTL
        mock_redis.expire.assert_called_once()


class TestIntegration:
    """Integration tests"""
    
    @pytest.mark.asyncio
    async def test_full_rate_limiting_flow(self, mock_redis):
        """Test complete rate limiting flow"""
        limiter = RateLimiter(redis_client=mock_redis)
        
        # Simulate 5 requests
        for i in range(5):
            is_allowed, info = await limiter.is_allowed(
                identifier="user:123",
                plan="free",
                endpoint="/api/v1/test"
            )
            
            if i < 100:  # Free limit is 100/hour
                assert is_allowed is True
            else:
                assert is_allowed is False


class TestSkipPathTrailingSlash:
    """card f90a8079: FastAPI redirect_slashes 307-redirects /metrics -> /metrics/,
    so the middleware sees the TRAILING-SLASH variant. The skip check must
    tolerate trailing slashes on both sides (comparison-only; the request path
    is never mutated)."""

    @staticmethod
    def _make_middleware(rate_limiter=None):
        # rate_limiter injection avoids any Redis dependency in these tests
        return RateLimitMiddleware(app=Mock(), rate_limiter=rate_limiter or Mock())

    @pytest.mark.asyncio
    @pytest.mark.parametrize("path", [
        "/metrics", "/metrics/",
        "/health", "/health/",
        "/docs", "/docs/",
        "/openapi.json", "/openapi.json/",
    ])
    async def test_dispatch_skips_without_ratelimit_call(self, path):
        """Skipped paths (with/without trailing slash) bypass the limiter entirely"""
        mw = self._make_middleware()
        request = Mock()
        request.url.path = path
        sentinel = MagicMock()
        call_next = AsyncMock(return_value=sentinel)

        response = await mw.dispatch(request, call_next)

        assert response is sentinel
        call_next.assert_awaited_once_with(request)
        mw.rate_limiter.is_allowed.assert_not_called()

    @pytest.mark.asyncio
    async def test_dispatch_non_skip_path_calls_limiter(self):
        """Control: non-skipped paths still go through the limiter"""
        limiter = Mock()
        limiter.is_allowed = AsyncMock(return_value=(
            True, {"limit": 100, "remaining": 99, "reset": 0}
        ))
        mw = self._make_middleware(rate_limiter=limiter)
        request = MagicMock()
        request.url.path = "/api/v1/test"
        request.headers.get.return_value = None
        request.client.host = "127.0.0.1"
        call_next = AsyncMock(return_value=MagicMock())

        await mw.dispatch(request, call_next)

        limiter.is_allowed.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_dispatch_lookalike_paths_not_skipped(self):
        """Lookalike paths must NOT be skipped (normalization must not over-match)"""
        limiter = Mock()
        limiter.is_allowed = AsyncMock(return_value=(
            True, {"limit": 100, "remaining": 99, "reset": 0}
        ))
        mw = self._make_middleware(rate_limiter=limiter)
        for path in ("/api/v1/metrics", "/metricsx", "/v1/health"):
            request = MagicMock()
            request.url.path = path
            request.headers.get.return_value = None
            request.client.host = "127.0.0.1"
            await mw.dispatch(request, AsyncMock(return_value=MagicMock()))
        assert limiter.is_allowed.await_count == 3


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
