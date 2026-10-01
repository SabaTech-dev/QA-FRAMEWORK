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
from types import SimpleNamespace
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
import time

from middleware.rate_limit import RateLimiter, RateLimitMiddleware
from middleware import rate_limit as rate_limit_mod
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
        """Should allow request if Redis fails (default open), flagged degraded"""
        mock_redis.zcard = AsyncMock(side_effect=Exception("Redis error"))

        is_allowed, info = await rate_limiter.is_allowed(
            identifier="user:123",
            plan="free",
            endpoint="/api/v1/test"
        )

        assert is_allowed is True
        assert info.get("degraded") is True
        # S-3 (PR #106 port): error details stay server-side, not in info


def _make_failing_redis():
    """Redis mock where the first sliding-window op blows up (Redis down)"""
    redis = AsyncMock()
    redis.zremrangebyscore = AsyncMock(side_effect=Exception("Redis down"))
    redis.zcard = AsyncMock(side_effect=Exception("Redis down"))
    return redis


class TestFailModeF1:
    """card 39ea6180 (F-1, OWASP API4:2023): RATE_LIMIT_FAIL_MODE=open|closed.

    Env is read at CALL time (pattern F-2), never frozen at import.
    Default open keeps staging compat; closed denies (429) when Redis is down.
    """

    @pytest.fixture(autouse=True)
    def _clean_env_and_alert_state(self, monkeypatch):
        monkeypatch.delenv("RATE_LIMIT_FAIL_MODE", raising=False)
        rate_limit_mod._redis_down["last_alert"] = 0.0
        yield
        rate_limit_mod._redis_down["last_alert"] = 0.0

    @pytest.mark.asyncio
    async def test_open_mode_allows_and_alerts_once(self, monkeypatch):
        """mode=open: requests pass + critical alert logged ONCE (dedup window)"""
        monkeypatch.setenv("RATE_LIMIT_FAIL_MODE", "open")
        limiter = RateLimiter(redis_client=_make_failing_redis())

        with patch("middleware.rate_limit.logger") as mock_logger:
            for _ in range(2):  # 2 requests → 1 redis failure each (short-circuit, port PR #106)
                is_allowed, info = await limiter.is_allowed(
                    identifier="user:123", plan="free", endpoint="/api/v1/test"
                )
                assert is_allowed is True
                assert info.get("degraded") is True
            assert mock_logger.critical.call_count == 1

    @pytest.mark.asyncio
    async def test_closed_mode_denies(self, monkeypatch):
        """mode=closed: Redis down -> denied with remaining=0"""
        monkeypatch.setenv("RATE_LIMIT_FAIL_MODE", "closed")
        limiter = RateLimiter(redis_client=_make_failing_redis())

        is_allowed, info = await limiter.is_allowed(
            identifier="user:123", plan="free", endpoint="/api/v1/test"
        )

        assert is_allowed is False
        assert info["remaining"] == 0
        assert info.get("degraded") is True

    @pytest.mark.asyncio
    async def test_closed_mode_middleware_returns_429(self, monkeypatch):
        """mode=closed: middleware dispatch returns a 429 response"""
        monkeypatch.setenv("RATE_LIMIT_FAIL_MODE", "closed")
        mw = RateLimitMiddleware(
            app=Mock(),
            rate_limiter=RateLimiter(redis_client=_make_failing_redis()),
        )
        request = MagicMock()
        request.url.path = "/api/v1/test"
        request.headers.get.return_value = None
        request.client.host = "127.0.0.1"
        call_next = AsyncMock(return_value=MagicMock())

        response = await mw.dispatch(request, call_next)

        assert response.status_code == 429
        call_next.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_env_read_at_call_time(self, monkeypatch):
        """Same limiter instance: flipping env flips behavior (pattern F-2)"""
        limiter = RateLimiter(redis_client=_make_failing_redis())

        monkeypatch.setenv("RATE_LIMIT_FAIL_MODE", "open")
        is_allowed, _ = await limiter.is_allowed(
            identifier="user:123", plan="free", endpoint="/api/v1/test"
        )
        assert is_allowed is True

        monkeypatch.setenv("RATE_LIMIT_FAIL_MODE", "closed")
        is_allowed, _ = await limiter.is_allowed(
            identifier="user:123", plan="free", endpoint="/api/v1/test"
        )
        assert is_allowed is False

    @pytest.mark.asyncio
    async def test_invalid_mode_falls_back_to_open(self, monkeypatch):
        """Garbage value -> treated as open (staging-safe default)"""
        monkeypatch.setenv("RATE_LIMIT_FAIL_MODE", "garbage")
        limiter = RateLimiter(redis_client=_make_failing_redis())

        is_allowed, info = await limiter.is_allowed(
            identifier="user:123", plan="free", endpoint="/api/v1/test"
        )

        assert is_allowed is True
        assert info.get("degraded") is True


class TestFailModePortPR106:
    """Port PR #106 (card 77079bca): metric, degraded header, short-circuit.
    Adaptado a semántica F-1: fail mode leído at call time (env), closed→429.
    """

    @pytest.mark.asyncio
    async def test_backend_failure_short_circuits_single_event(self, monkeypatch):
        """One backing-store failure per request: first redis error short-circuits"""
        monkeypatch.setenv("RATE_LIMIT_FAIL_MODE", "open")
        redis = _make_failing_redis()
        limiter = RateLimiter(redis_client=redis)
        await limiter.is_allowed("user:1", "pro", "/api/v1/auth/login")
        # Primer bucket en fallar hace short-circuit → exactamente 1 redis op, no 3
        assert redis.zremrangebyscore.await_count == 1

    @pytest.mark.asyncio
    async def test_failure_metric_incremented(self, monkeypatch):
        """Every backing-store failure increments the Prometheus counter"""
        from prometheus_client import REGISTRY

        def sample(mode):
            return REGISTRY.get_sample_value(
                "rate_limit_backend_failures_total", {"fail_mode": mode}
            ) or 0

        before_open = sample("open")
        before_closed = sample("closed")

        monkeypatch.setenv("RATE_LIMIT_FAIL_MODE", "open")
        await RateLimiter(redis_client=_make_failing_redis()).is_allowed(
            "user:1", "free", "/api/v1/test")
        monkeypatch.setenv("RATE_LIMIT_FAIL_MODE", "closed")
        await RateLimiter(redis_client=_make_failing_redis()).is_allowed(
            "user:1", "free", "/api/v1/test")

        assert sample("open") == before_open + 1
        assert sample("closed") == before_closed + 1

    def test_middleware_open_mode_200_with_degraded_header(self, monkeypatch):
        """Middleware: open mode keeps serving but exposes X-RateLimit-Mode: degraded"""
        monkeypatch.setenv("RATE_LIMIT_FAIL_MODE", "open")
        app = FastAPI()
        app.add_middleware(
            RateLimitMiddleware,
            rate_limiter=RateLimiter(redis_client=_make_failing_redis()),
        )

        @app.get("/test")
        async def test_endpoint():
            return {"status": "ok"}

        response = TestClient(app).get("/test")
        assert response.status_code == 200
        assert response.headers.get("X-RateLimit-Mode") == "degraded"


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


class TestClientIPTrustedProxyDepth:
    """card d9056216 (F-2) + fix off-by-one (card 77079bca, review Alfred).

    The rate-limit key must never derive from a client-controlled XFF entry.
    Real proxy semantics covered (the old tests modeled an append form that
    exists neither on this host nor in standard semantics):

    - SET (nginx vhost qa.sabatech.dev: `proxy_set_header X-Forwarded-For
      $remote_addr`): XFF carries EXACTLY the real client IP (1 entry);
      the client's own XFF history is destroyed by the proxy.
    - APPEND ($proxy_add_x_forwarded_for chains): trusted proxies append
      their peer; the client IP is the N-th entry from the right (depth=N)
      and attacker prepends fall outside the trusted suffix.

    depth=0 / invalid / unset -> XFF ignored, socket peer used.
    Insufficient hops (len(hops) < depth) -> peer (chain not proven).
    """

    @staticmethod
    def _make_middleware():
        # rate_limiter injection avoids any Redis dependency
        return RateLimitMiddleware(app=Mock(), rate_limiter=Mock())

    @staticmethod
    def _make_request(xff=None, client_ip="203.0.113.7"):
        headers = {}
        if xff is not None:
            headers["X-Forwarded-For"] = xff
        request = Mock()
        request.headers = headers  # real dict -> .get() behaves like Headers
        request.client = Mock(host=client_ip)
        request.state = SimpleNamespace(user=None)
        return request

    def test_depth1_set_semantics_uses_the_single_entry(self, monkeypatch):
        """nginx SET (prod vhost): XFF = real client IP only -> depth=1 picks it.
        Old code (len<=depth fallback) returned the peer for EVERYONE:
        global bucket collapse (Probe A, review Alfred)."""
        monkeypatch.setenv("TRUSTED_PROXY_DEPTH", "1")
        mw = self._make_middleware()
        request = self._make_request(xff="1.2.3.4", client_ip="10.0.0.9")
        assert mw._get_identifier(request) == "ip:1.2.3.4"

    def test_depth1_append_semantics_uses_rightmost(self, monkeypatch):
        """APPEND with one trusted proxy: the client real IP is the appended
        peer (rightmost entry); the client-controlled leftmost is ignored."""
        monkeypatch.setenv("TRUSTED_PROXY_DEPTH", "1")
        mw = self._make_middleware()
        request = self._make_request(xff="9.9.9.9, 1.2.3.4", client_ip="10.0.0.9")
        assert mw._get_identifier(request) == "ip:1.2.3.4"

    def test_depth1_prepends_do_not_change_key(self, monkeypatch):
        """Attack: prepending XFF hops must NOT yield a fresh bucket — the
        trusted suffix (rightmost depth entries) is anchored."""
        monkeypatch.setenv("TRUSTED_PROXY_DEPTH", "1")
        mw = self._make_middleware()
        key_before = mw._get_identifier(
            self._make_request(xff="9.9.9.9, 1.2.3.4", client_ip="10.0.0.9")
        )
        for rotated in (
            "8.8.8.8, 9.9.9.9, 1.2.3.4",
            "7.7.7.7, 8.8.8.8, 9.9.9.9, 1.2.3.4",
        ):
            key_after = mw._get_identifier(self._make_request(xff=rotated, client_ip="10.0.0.9"))
            assert key_after == key_before == "ip:1.2.3.4"

    def test_depth2_append_uses_second_from_right(self, monkeypatch):
        """APPEND with two trusted proxies: client is the 2nd entry from the
        right (the rightmost is the closest trusted proxy's peer)."""
        monkeypatch.setenv("TRUSTED_PROXY_DEPTH", "2")
        mw = self._make_middleware()
        request = self._make_request(xff="evil, 1.2.3.4, 10.0.0.8", client_ip="10.0.0.9")
        assert mw._get_identifier(request) == "ip:1.2.3.4"

    def test_depth2_insufficient_hops_falls_back_to_peer(self, monkeypatch):
        """depth=2 but only 1 entry: the chain does not prove the trusted
        proxies touched it -> fall back to the socket peer."""
        monkeypatch.setenv("TRUSTED_PROXY_DEPTH", "2")
        mw = self._make_middleware()
        request = self._make_request(xff="1.2.3.4", client_ip="203.0.113.7")
        assert mw._get_identifier(request) == "ip:203.0.113.7"

    def test_depth0_ignores_xff_uses_client_host(self, monkeypatch):
        """depth=0 (staging, no proxy): XFF must be ignored entirely"""
        monkeypatch.setenv("TRUSTED_PROXY_DEPTH", "0")
        mw = self._make_middleware()
        request = self._make_request(xff="1.2.3.4", client_ip="203.0.113.7")
        assert mw._get_identifier(request) == "ip:203.0.113.7"

    def test_default_without_env_ignores_xff(self, monkeypatch):
        """Default (env unset) must be the safe path: XFF ignored"""
        monkeypatch.delenv("TRUSTED_PROXY_DEPTH", raising=False)
        mw = self._make_middleware()
        request = self._make_request(xff="1.2.3.4", client_ip="203.0.113.7")
        assert mw._get_identifier(request) == "ip:203.0.113.7"

    def test_invalid_depth_value_falls_back_to_client_host(self, monkeypatch):
        """Garbage in TRUSTED_PROXY_DEPTH must fail safe (peer address), not crash"""
        monkeypatch.setenv("TRUSTED_PROXY_DEPTH", "not-a-number")
        mw = self._make_middleware()
        request = self._make_request(xff="1.2.3.4, 10.0.0.9", client_ip="203.0.113.7")
        assert mw._get_identifier(request) == "ip:203.0.113.7"


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
