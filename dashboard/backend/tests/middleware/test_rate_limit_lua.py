"""
Runtime coverage for the atomic Lua sliding-window script (card e8a6b3a7,
review blocker 1).

The unit suite mocks redis.eval; these tests execute the REAL
_SLIDING_WINDOW_LUA through fakeredis's embedded Lua interpreter (lupa,
dev dependency), so script syntax and semantics are actually exercised.
"""

import sys

# Drop conftest's global redis MagicMock: fakeredis needs the REAL redis
# package to build its Lua-capable client (same pattern as
# tests/unit/test_refresh_rotation.py).
for _mod in ("redis", "redis.asyncio", "redis.exceptions"):
    sys.modules.pop(_mod, None)

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("fakeredis")
pytest.importorskip("lupa")

import fakeredis

from middleware.rate_limit import RateLimiter, _SLIDING_WINDOW_LUA


@pytest.fixture
async def fake_redis():
    client = fakeredis.FakeAsyncRedis()
    yield client
    await client.aclose()


@pytest.fixture
def limiter(fake_redis):
    return RateLimiter(redis_client=fake_redis)


class TestLuaScriptRuntime:
    async def test_script_is_executed_for_real(self, fake_redis):
        """The Lua script itself runs inside fakeredis's interpreter"""
        await fake_redis.eval(_SLIDING_WINDOW_LUA, 1, "k", 5, 60, 1000.0, "n1")
        assert await fake_redis.zcard("k") == 1

    async def test_burst_limit_enforced(self, limiter):
        """Free plan burst (20/min): request 21 is denied at the burst tier"""
        results = [
            await limiter.is_allowed(identifier="ip:1.2.3.4", plan="free", endpoint="/api/v1/other")
            for _ in range(21)
        ]
        assert sum(1 for ok, _ in results if ok) == 20
        ok, info = results[-1]
        assert ok is False
        assert info["limit"] == 20
        assert info["remaining"] == 0

    async def test_members_unique_within_same_timestamp(self, limiter, fake_redis, monkeypatch):
        """Same-second requests must be distinct ZADD members (no undercount).

        time.time() is pinned so every request gets the IDENTICAL timestamp:
        only a unique per-request nonce keeps the sorted-set count correct.
        """
        import middleware.rate_limit as rl

        monkeypatch.setattr(rl.time, "time", lambda: 1_000_000.0)
        for _ in range(5):
            await limiter.is_allowed(identifier="ip:5.6.7.8", plan="free", endpoint="/api/v1/other")
        # 5 rapid requests -> 5 distinct members in the burst sorted set
        assert await fake_redis.zcard("ratelimit:burst:ip:5.6.7.8") == 5

    async def test_endpoint_tier_enforced(self, limiter):
        """Login endpoint limit (20/min) applies to authenticated pro users
        regardless of their higher plan limits"""
        results = [
            await limiter.is_allowed(
                identifier="user:alice",
                plan="pro",
                endpoint="/api/v1/auth/login",
                authenticated=True,
            )
            for _ in range(21)
        ]
        assert sum(1 for ok, _ in results if ok) == 20
        assert results[-1][1]["limit"] == 20

    async def test_denied_request_not_counted(self, limiter, fake_redis):
        """A denied request adds no member to any tier key"""
        for _ in range(21):
            await limiter.is_allowed(identifier="ip:9.9.9.9", plan="free", endpoint="/api/v1/other")
        assert await fake_redis.zcard("ratelimit:burst:ip:9.9.9.9") == 20
