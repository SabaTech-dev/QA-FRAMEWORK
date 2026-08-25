"""Unit tests for the Redis-backed refresh token store (card 3ae2e5c1, F-2).

The store implements the server-side state needed for refresh token
rotation and reuse detection (OWASP API2):

- ``deny_jti`` / ``is_denied``: denylist of consumed refresh tokens,
  keyed by the token's unique ``jti``. Entries carry a TTL equal to the
  token's remaining lifetime so the denylist self-cleans.
- ``revoke_family`` / ``is_family_revoked``: family tombstones used to
  kill every descendant of a token family after reuse detection fires.

Tests run against a REAL local Redis (127.0.0.1:6379, no credentials)
and are skipped when it is unreachable. A dedicated test database and
key prefix keep them isolated from any other data.
"""

from uuid import uuid4

import pytest
import pytest_asyncio

from src.infrastructure.refresh_tokens.store import RefreshTokenStore, TokenStoreUnavailableError

TEST_REDIS_URL = "redis://127.0.0.1:6379/15"
TEST_PREFIX = "qa:test:rt:store"


def _redis_available() -> bool:
    import redis

    try:
        client = redis.from_url(TEST_REDIS_URL, socket_connect_timeout=1)
        client.ping()
        client.close()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _redis_available(), reason="local Redis not available")


async def _purge_test_keys(store: RefreshTokenStore) -> None:
    async for key in store.client.scan_iter(f"{TEST_PREFIX}:*"):
        await store.client.delete(key)


@pytest_asyncio.fixture
async def store():
    import redis.asyncio as aioredis

    client = aioredis.from_url(TEST_REDIS_URL)
    s = RefreshTokenStore(client=client, prefix=TEST_PREFIX)
    await _purge_test_keys(s)
    yield s
    await _purge_test_keys(s)
    await s.aclose()


class TestJtiDenylist:
    @pytest.mark.asyncio
    async def test_denied_jti_is_reported(self, store):
        jti = str(uuid4())
        assert await store.is_denied(jti) is False
        await store.deny_jti(jti, ttl_seconds=60)
        assert await store.is_denied(jti) is True

    @pytest.mark.asyncio
    async def test_unknown_jti_not_denied(self, store):
        assert await store.is_denied(str(uuid4())) is False

    @pytest.mark.asyncio
    async def test_deny_is_idempotent(self, store):
        jti = str(uuid4())
        await store.deny_jti(jti, ttl_seconds=60)
        await store.deny_jti(jti, ttl_seconds=60)
        assert await store.is_denied(jti) is True

    @pytest.mark.asyncio
    async def test_deny_sets_ttl(self, store):
        """The denylist entry must expire with the token, not linger forever."""
        jti = str(uuid4())
        await store.deny_jti(jti, ttl_seconds=90)
        pttl = await store.client.pttl(f"{TEST_PREFIX}:jti:{jti}")
        assert 0 < pttl <= 90 * 1000

    @pytest.mark.asyncio
    async def test_denied_jti_expires_after_ttl(self, store):
        jti = str(uuid4())
        await store.deny_jti(jti, ttl_seconds=1)
        await _sleep(1.3)
        assert await store.is_denied(jti) is False


class TestFamilyRevocation:
    @pytest.mark.asyncio
    async def test_revoked_family_is_reported(self, store):
        fam = str(uuid4())
        assert await store.is_family_revoked(fam) is False
        await store.revoke_family(fam, ttl_seconds=60)
        assert await store.is_family_revoked(fam) is True

    @pytest.mark.asyncio
    async def test_unknown_family_not_revoked(self, store):
        assert await store.is_family_revoked(str(uuid4())) is False

    @pytest.mark.asyncio
    async def test_revocation_sets_ttl(self, store):
        fam = str(uuid4())
        await store.revoke_family(fam, ttl_seconds=120)
        pttl = await store.client.pttl(f"{TEST_PREFIX}:fam:{fam}")
        assert 0 < pttl <= 120 * 1000


class TestIsolation:
    @pytest.mark.asyncio
    async def test_prefix_isolation(self, store):
        """Two stores with different prefixes never see each other's keys."""
        jti = str(uuid4())
        await store.deny_jti(jti, ttl_seconds=60)
        other = RefreshTokenStore(client=store.client, prefix=f"{TEST_PREFIX}:other")
        assert await other.is_denied(jti) is False


class TestAtomicConsume:
    """try_consume_jti closes the concurrent-refresh race via SET NX EX."""

    @pytest.mark.asyncio
    async def test_first_consume_wins(self, store):
        jti = str(uuid4())
        assert await store.try_consume_jti(jti, ttl_seconds=60) is True

    @pytest.mark.asyncio
    async def test_second_consume_signals_replay(self, store):
        jti = str(uuid4())
        await store.try_consume_jti(jti, ttl_seconds=60)
        assert await store.try_consume_jti(jti, ttl_seconds=60) is False

    @pytest.mark.asyncio
    async def test_consumed_jti_is_denied(self, store):
        jti = str(uuid4())
        await store.try_consume_jti(jti, ttl_seconds=60)
        assert await store.is_denied(jti) is True

    @pytest.mark.asyncio
    async def test_consume_sets_ttl(self, store):
        jti = str(uuid4())
        await store.try_consume_jti(jti, ttl_seconds=45)
        pttl = await store.client.pttl(f"{TEST_PREFIX}:jti:{jti}")
        assert 0 < pttl <= 45 * 1000


class TestUnavailableStore:
    @pytest.mark.asyncio
    async def test_broken_client_raises_unavailable(self):
        """Redis errors surface as TokenStoreUnavailableError, never as 500s."""
        from unittest.mock import AsyncMock, Mock

        from redis.exceptions import ConnectionError as RedisConnectionError

        broken = Mock()
        side_effect = RedisConnectionError("connection lost")
        broken.setex = AsyncMock(side_effect=side_effect)
        broken.exists = AsyncMock(side_effect=side_effect)
        broken.ping = AsyncMock(side_effect=side_effect)
        s = RefreshTokenStore(client=broken)
        with pytest.raises(TokenStoreUnavailableError):
            await s.deny_jti("jti", ttl_seconds=60)
        with pytest.raises(TokenStoreUnavailableError):
            await s.is_denied("jti")
        with pytest.raises(TokenStoreUnavailableError):
            await s.ping()

    @pytest.mark.asyncio
    async def test_url_client_ping(self, store):
        assert await store.ping() is True


async def _sleep(seconds: float) -> None:
    import asyncio

    await asyncio.sleep(seconds)
