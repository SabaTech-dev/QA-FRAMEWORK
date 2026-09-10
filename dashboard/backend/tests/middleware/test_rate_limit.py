"""
Tests for Rate Limiting

Covers:
- Per-plan rate limiting
- Endpoint-specific limits (incl. prefix match)
- Burst protection
- Atomic Lua sliding window (single Redis round-trip)
- Fail-closed for anonymous requests when Redis is down (card e8a6b3a7 F-3)
- Per-user/plan identity from JWT inside the middleware (card e8a6b3a7 F-1)
"""

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("redis")
pytest.importorskip("asyncpg")
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient

from middleware.rate_limit import RateLimiter, RateLimitMiddleware
from core.rate_limit_config import (
    get_rate_limit,
    get_burst_limit,
    get_endpoint_limit,
    PlanType,
    RATE_LIMITS,
    BURST_LIMITS,
)
from services.auth_service import create_access_token


def _eval_result(denied=0, limit=100, remaining=99, reset=9999999):
    """Simulated Lua script reply: [denied_index, limit, remaining, reset]"""
    return [denied, limit, remaining, reset]


@pytest.fixture
def mock_redis():
    """Mock Redis client whose eval() always allows"""
    redis = AsyncMock()
    redis.eval = AsyncMock(return_value=_eval_result())
    return redis


@pytest.fixture
def rate_limiter(mock_redis):
    return RateLimiter(redis_client=mock_redis)


@pytest.fixture
def app(mock_redis):
    """Test FastAPI app with rate limiting (limiter injected, no real Redis)"""
    app = FastAPI()
    limiter = RateLimiter(redis_client=mock_redis)
    app.add_middleware(RateLimitMiddleware, rate_limiter=limiter)

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
    return TestClient(app)


class TestRateLimitConfig:
    def test_get_rate_limit_free(self):
        assert get_rate_limit("free") == RATE_LIMITS[PlanType.FREE]

    def test_get_rate_limit_pro(self):
        assert get_rate_limit("pro") == RATE_LIMITS[PlanType.PRO]

    def test_get_rate_limit_invalid(self):
        assert get_rate_limit("invalid") == RATE_LIMITS[PlanType.FREE]

    def test_get_burst_limit(self):
        assert get_burst_limit("pro") == BURST_LIMITS[PlanType.PRO]

    def test_get_endpoint_limit_exact(self):
        assert get_endpoint_limit("/api/v1/auth/login") == 20

    def test_get_endpoint_limit_prefix_match(self):
        """Subpaths of a limited endpoint inherit its limit (prefix match)"""
        assert get_endpoint_limit("/api/v1/executions/123") == 60
        assert get_endpoint_limit("/api/v1/auth/login") == 20

    def test_get_endpoint_limit_unmatched(self):
        assert get_endpoint_limit("/api/v1/suites") is None
        assert get_endpoint_limit("/api/v1/auth/logout") is None


class TestRateLimiter:
    @pytest.mark.asyncio
    async def test_is_allowed_under_limit(self, rate_limiter, mock_redis):
        mock_redis.eval = AsyncMock(return_value=_eval_result(0, 1000, 995))

        is_allowed, info = await rate_limiter.is_allowed(
            identifier="user:123", plan="pro", endpoint="/api/v1/test"
        )

        assert is_allowed is True
        assert info["remaining"] == 995

    @pytest.mark.asyncio
    async def test_is_allowed_at_limit(self, rate_limiter, mock_redis):
        # denied at hourly check (index 2: burst=1, hourly=2)
        mock_redis.eval = AsyncMock(return_value=_eval_result(2, 1000, 0))

        is_allowed, info = await rate_limiter.is_allowed(
            identifier="user:123", plan="pro", endpoint="/api/v1/test"
        )

        assert is_allowed is False
        assert info["remaining"] == 0

    @pytest.mark.asyncio
    async def test_is_allowed_endpoint_limit_denied(self, rate_limiter, mock_redis):
        # denied at endpoint check (index 1)
        mock_redis.eval = AsyncMock(return_value=_eval_result(1, 20, 0))

        is_allowed, info = await rate_limiter.is_allowed(
            identifier="user:123", plan="pro", endpoint="/api/v1/auth/login"
        )

        assert is_allowed is False
        assert info["limit"] == 20

    @pytest.mark.asyncio
    async def test_single_atomic_redis_call(self, rate_limiter, mock_redis):
        """F-3: all tier checks run in ONE atomic Lua eval, not N round-trips"""
        await rate_limiter.is_allowed(
            identifier="user:123", plan="pro", endpoint="/api/v1/auth/login"
        )

        mock_redis.eval.assert_awaited_once()
        args = mock_redis.eval.await_args.args
        numkeys = args[1]
        keys = args[2 : 2 + numkeys]
        # endpoint + burst + hourly = 3 keys in one script invocation
        assert numkeys == 3
        assert any("endpoint:" in k for k in keys)
        assert any("burst:" in k for k in keys)
        assert any("hourly:" in k for k in keys)

    @pytest.mark.asyncio
    async def test_redis_failure_fails_open_for_authenticated(self, rate_limiter, mock_redis):
        """F-3: authenticated users degrade to fail-open when Redis dies"""
        mock_redis.eval = AsyncMock(side_effect=Exception("Redis error"))

        is_allowed, info = await rate_limiter.is_allowed(
            identifier="user:123",
            plan="pro",
            endpoint="/api/v1/test",
            authenticated=True,
        )

        assert is_allowed is True
        assert "error" in info

    @pytest.mark.asyncio
    async def test_redis_failure_fails_closed_for_anonymous(self, rate_limiter, mock_redis):
        """F-3: anonymous requests fail CLOSED when Redis dies (DDoS protection)"""
        mock_redis.eval = AsyncMock(side_effect=Exception("Redis error"))

        is_allowed, info = await rate_limiter.is_allowed(
            identifier="ip:1.2.3.4",
            plan="free",
            endpoint="/api/v1/test",
            authenticated=False,
        )

        assert is_allowed is False


class TestRateLimitMiddlewareIdentity:
    """F-1: middleware runs PRE-auth, so it must decode the JWT itself"""

    def _capturing_limiter(self):
        limiter = Mock()
        limiter.is_allowed = AsyncMock(
            return_value=(True, {"limit": 100, "remaining": 99, "reset": 0})
        )
        return limiter

    def test_valid_jwt_uses_user_identity_and_plan(self, app):
        limiter = self._capturing_limiter()
        app.add_middleware(RateLimitMiddleware, rate_limiter=limiter)
        token = create_access_token({"sub": "alice", "plan": "pro"})
        client = TestClient(app)

        client.get("/test", headers={"Authorization": f"Bearer {token}"})

        limiter.is_allowed.assert_awaited_once()
        kwargs = limiter.is_allowed.await_args.kwargs
        assert kwargs["identifier"] == "user:alice"
        assert kwargs["plan"] == "pro"
        assert kwargs["authenticated"] is True

    def test_jwt_without_plan_defaults_to_free(self, app):
        limiter = self._capturing_limiter()
        app.add_middleware(RateLimitMiddleware, rate_limiter=limiter)
        token = create_access_token({"sub": "bob"})
        client = TestClient(app)

        client.get("/test", headers={"Authorization": f"Bearer {token}"})

        kwargs = limiter.is_allowed.await_args.kwargs
        assert kwargs["identifier"] == "user:bob"
        assert kwargs["plan"] == "free"

    def test_invalid_jwt_falls_back_to_ip(self, app):
        limiter = self._capturing_limiter()
        app.add_middleware(RateLimitMiddleware, rate_limiter=limiter)
        client = TestClient(app)

        client.get("/test", headers={"Authorization": "Bearer not-a-jwt"})

        kwargs = limiter.is_allowed.await_args.kwargs
        assert kwargs["identifier"].startswith("ip:")
        assert kwargs["plan"] == "free"
        assert kwargs["authenticated"] is False

    def test_no_jwt_uses_ip(self, app):
        limiter = self._capturing_limiter()
        app.add_middleware(RateLimitMiddleware, rate_limiter=limiter)
        client = TestClient(app)

        client.get("/test")

        kwargs = limiter.is_allowed.await_args.kwargs
        assert kwargs["identifier"].startswith("ip:")
        assert kwargs["authenticated"] is False

    def test_refresh_token_not_treated_as_authenticated(self, app):
        """A refresh token must not unlock authenticated rate-limit identity"""
        from services.auth_service import create_refresh_token

        limiter = self._capturing_limiter()
        app.add_middleware(RateLimitMiddleware, rate_limiter=limiter)
        token = create_refresh_token({"sub": "alice"})
        client = TestClient(app)

        client.get("/test", headers={"Authorization": f"Bearer {token}"})

        kwargs = limiter.is_allowed.await_args.kwargs
        assert kwargs["identifier"].startswith("ip:")
        assert kwargs["authenticated"] is False


class TestRateLimitMiddleware:
    def test_skip_paths(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert "X-RateLimit-Limit" not in response.headers

    def test_rate_limit_headers_added(self, client):
        response = client.get("/test")
        assert response.status_code == 200
        assert "X-RateLimit-Limit" in response.headers

    def test_rate_limit_exceeded_returns_429(self, app, mock_redis):
        mock_redis.eval = AsyncMock(return_value=_eval_result(2, 100, 0))
        client = TestClient(app)

        response = client.get("/test")

        assert response.status_code == 429
        assert response.headers["X-RateLimit-Remaining"] == "0"

    def test_429_includes_retry_after(self, app, mock_redis):
        """A real limit hit must tell the client when to retry (>= 1s)"""
        reset = int(__import__("time").time()) + 120
        mock_redis.eval = AsyncMock(return_value=_eval_result(2, 100, 0, reset))
        client = TestClient(app)

        response = client.get("/test")

        assert response.status_code == 429
        retry_after = int(response.headers["Retry-After"])
        assert 1 <= retry_after <= 120

    def test_redis_outage_anonymous_returns_503_not_429(self, app, mock_redis):
        """Redis down + anonymous: honest 503 with generic body, no
        'rate limit exceeded' lie and no limit=0 leak"""
        mock_redis.eval = AsyncMock(side_effect=Exception("Redis error"))
        client = TestClient(app)

        response = client.get("/test")

        assert response.status_code == 503
        assert response.headers["Retry-After"] == "30"
        assert "unavailable" in response.json()["detail"].lower()
        assert "Redis error" not in response.text
        assert "X-RateLimit-Limit" not in response.headers

    def test_redis_outage_authenticated_still_allowed(self, app, mock_redis):
        mock_redis.eval = AsyncMock(side_effect=Exception("Redis error"))
        token = create_access_token({"sub": "alice", "plan": "pro"})
        client = TestClient(app)

        response = client.get("/test", headers={"Authorization": f"Bearer {token}"})

        assert response.status_code == 200

    def test_options_preflight_skips_limiter(self, app):
        """CORS preflight must not consume rate-limit budget"""
        limiter = Mock()
        limiter.is_allowed = AsyncMock(
            return_value=(True, {"limit": 100, "remaining": 99, "reset": 0})
        )
        app.add_middleware(RateLimitMiddleware, rate_limiter=limiter)
        client = TestClient(app)

        response = client.options("/test")

        assert response.status_code in (200, 405)  # routed by CORS/app, not 429
        limiter.is_allowed.assert_not_called()


class TestSkipPathTrailingSlash:
    """card f90a8079: trailing-slash tolerant skip paths"""

    @staticmethod
    def _make_middleware(rate_limiter=None):
        return RateLimitMiddleware(app=Mock(), rate_limiter=rate_limiter or Mock())

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "path",
        [
            "/metrics",
            "/metrics/",
            "/health",
            "/health/",
            "/docs",
            "/docs/",
            "/openapi.json",
            "/openapi.json/",
        ],
    )
    async def test_dispatch_skips_without_ratelimit_call(self, path):
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
        limiter = Mock()
        limiter.is_allowed = AsyncMock(
            return_value=(True, {"limit": 100, "remaining": 99, "reset": 0})
        )
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
        limiter = Mock()
        limiter.is_allowed = AsyncMock(
            return_value=(True, {"limit": 100, "remaining": 99, "reset": 0})
        )
        mw = self._make_middleware(rate_limiter=limiter)
        for path in ("/api/v1/metrics", "/metricsx", "/v1/health"):
            request = MagicMock()
            request.url.path = path
            request.headers.get.return_value = None
            request.client.host = "127.0.0.1"
            await mw.dispatch(request, AsyncMock(return_value=MagicMock()))
        assert limiter.is_allowed.await_count == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
