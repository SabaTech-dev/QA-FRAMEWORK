"""Refresh token rotation, reuse detection and revocation (card 3ae2e5c1, F-2).

OWASP API2 hardening for the dashboard auth service:

- ROTATION: every successful refresh mints a NEW access + refresh token
  pair and invalidates the consumed refresh token (jti denylist in Redis,
  TTL = remaining token lifetime).
- REUSE DETECTION: replaying a consumed refresh token answers 401,
  revokes the whole token family (so rotated descendants die too) and
  raises a security alarm log.
- REVOKE: POST /auth/revoke implements RFC 7009-style explicit logout.

These tests run against a REAL local Redis (127.0.0.1:6379, no
credentials) on a dedicated database with a test-only key prefix. The
dashboard conftest replaces ``redis`` with a MagicMock before any
import; we drop that mock here because the real client behaviour is
exactly what these tests must exercise.
"""

import logging
import sys
from datetime import timedelta
from unittest.mock import AsyncMock, Mock

import pytest

# Drop conftest's global redis mock and bind the real client BEFORE the
# auth service / store get imported by anything below.
for _mod in ("redis", "redis.asyncio", "redis.exceptions"):
    sys.modules.pop(_mod, None)

import redis.asyncio as aioredis

pytest.importorskip("jose")

from fastapi import HTTPException
from jose import jwt
from models import User
from schemas import LoginRequest
from services.auth_service import (
    create_refresh_token,
    login_for_access_token,
    refresh_access_token,
    revoke_refresh_token,
)

from config import settings
from src.infrastructure.refresh_tokens.store import (
    RefreshTokenStore,
    TokenStoreUnavailableError,
)

TEST_REDIS_URL = "redis://127.0.0.1:6379/15"
TEST_PREFIX = "qa:test:auth"


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


@pytest.fixture
async def store():
    client = aioredis.from_url(TEST_REDIS_URL)
    s = RefreshTokenStore(client=client, prefix=TEST_PREFIX)
    await _purge_test_keys(s)
    yield s
    await _purge_test_keys(s)
    await s.aclose()


def make_user(**overrides) -> User:
    fields = dict(
        id=1,
        username="testuser",
        email="test@example.com",
        hashed_password="x",
        is_active=True,
        is_superuser=False,
    )
    fields.update(overrides)
    return User(**fields)


def make_db(user: User | None) -> AsyncMock:
    mock_db = AsyncMock()
    mock_result = AsyncMock()
    mock_result.scalar_one_or_none = Mock(return_value=user)
    mock_db.execute = AsyncMock(return_value=mock_result)
    return mock_db


def decode(token: str) -> dict:
    return jwt.decode(token, settings.secret_key.get_secret_value(), algorithms=[settings.algorithm])


def make_broken_store() -> RefreshTokenStore:
    broken = Mock()
    broken.is_denied = AsyncMock(side_effect=TokenStoreUnavailableError("down"))
    broken.is_family_revoked = AsyncMock(side_effect=TokenStoreUnavailableError("down"))
    broken.deny_jti = AsyncMock(side_effect=TokenStoreUnavailableError("down"))
    broken.revoke_family = AsyncMock(side_effect=TokenStoreUnavailableError("down"))
    broken.try_consume_jti = AsyncMock(side_effect=TokenStoreUnavailableError("down"))
    return broken


class TestJtiClaims:
    """Requirement 1: refresh tokens carry a unique jti per emission."""

    async def test_refresh_token_has_jti_and_family(self):
        payload = decode(create_refresh_token({"sub": "testuser"}))
        assert payload["type"] == "refresh"
        assert payload["jti"]
        assert payload["fam"]

    async def test_jti_unique_per_emission(self):
        first = decode(create_refresh_token({"sub": "testuser"}))
        second = decode(create_refresh_token({"sub": "testuser"}))
        assert first["jti"] != second["jti"]
        assert first["fam"] != second["fam"]

    async def test_login_mints_jti_refresh_token(self, monkeypatch):
        # Password verification is passlib/bcrypt territory and unrelated
        # to what this suite asserts (token claims), so stub the lookup.
        from services import auth_service

        user = make_user()
        monkeypatch.setattr(auth_service, "authenticate_user", AsyncMock(return_value=user))
        request = LoginRequest(username="testuser", password="pw")
        response = await login_for_access_token(request, make_db(user))
        payload = decode(response.refresh_token)
        assert payload["jti"]
        assert payload["fam"]


class TestRotation:
    """Requirement 2: use refresh -> new access+refresh, old one invalidated."""

    async def test_rotation_returns_new_token_pair(self, store):
        old_refresh = create_refresh_token({"sub": "testuser"})
        response = await refresh_access_token(old_refresh, make_db(make_user()), store=store)
        assert response.access_token
        assert response.refresh_token
        assert response.refresh_token != old_refresh
        # the new access token is a valid access token
        assert decode(response.access_token)["type"] == "access"
        # the new refresh token carries fresh jti but SAME family
        old_payload, new_payload = decode(old_refresh), decode(response.refresh_token)
        assert new_payload["jti"] != old_payload["jti"]
        assert new_payload["fam"] == old_payload["fam"]

    async def test_used_jti_denied_after_rotation(self, store):
        old_refresh = create_refresh_token({"sub": "testuser"})
        old_jti = decode(old_refresh)["jti"]
        await refresh_access_token(old_refresh, make_db(make_user()), store=store)
        assert await store.is_denied(old_jti) is True

    async def test_rotated_token_is_usable(self, store):
        """The fresh refresh token must work for the next cycle."""
        first = create_refresh_token({"sub": "testuser"})
        response = await refresh_access_token(first, make_db(make_user()), store=store)
        second = await refresh_access_token(
            response.refresh_token, make_db(make_user()), store=store
        )
        assert second.refresh_token

    async def test_denylist_ttl_matches_remaining_lifetime(self, store):
        old_refresh = create_refresh_token({"sub": "testuser"}, expires_delta=timedelta(seconds=90))
        jti = decode(old_refresh)["jti"]
        await refresh_access_token(old_refresh, make_db(make_user()), store=store)
        pttl = await store.client.pttl(f"{TEST_PREFIX}:jti:{jti}")
        assert 0 < pttl <= 90 * 1000


class TestReuseDetection:
    """Requirement 3: replaying a consumed token -> 401 + family revoked + alarm."""

    async def test_reuse_answered_401(self, store):
        old_refresh = create_refresh_token({"sub": "testuser"})
        await refresh_access_token(old_refresh, make_db(make_user()), store=store)
        with pytest.raises(HTTPException) as exc_info:
            await refresh_access_token(old_refresh, make_db(make_user()), store=store)
        assert exc_info.value.status_code == 401

    async def test_reuse_revokes_whole_family(self, store):
        """The legitimately-rotated descendant must die with the reused token."""
        first = create_refresh_token({"sub": "testuser"})
        response = await refresh_access_token(first, make_db(make_user()), store=store)
        fam = decode(first)["fam"]
        # replay the consumed token
        with pytest.raises(HTTPException):
            await refresh_access_token(first, make_db(make_user()), store=store)
        assert await store.is_family_revoked(fam) is True
        # the still-fresh rotated token is now dead too
        with pytest.raises(HTTPException) as exc_info:
            await refresh_access_token(response.refresh_token, make_db(make_user()), store=store)
        assert exc_info.value.status_code == 401

    async def test_reuse_raises_security_alarm(self, store, caplog):
        first = create_refresh_token({"sub": "testuser"})
        await refresh_access_token(first, make_db(make_user()), store=store)
        with caplog.at_level(logging.ERROR, logger="services.auth_service"):
            with pytest.raises(HTTPException):
                await refresh_access_token(first, make_db(make_user()), store=store)
        assert any(
            "reuse" in record.message.lower() and "refresh" in record.message.lower()
            for record in caplog.records
        ), f"expected reuse alarm log, got: {[r.message for r in caplog.records]}"


class TestRevoke:
    """Requirement 4: explicit logout revokes the presented refresh token."""

    async def test_revoke_denies_token(self, store):
        token = create_refresh_token({"sub": "testuser"})
        revoked = await revoke_refresh_token(token, store=store)
        assert revoked is True
        with pytest.raises(HTTPException) as exc_info:
            await refresh_access_token(token, make_db(make_user()), store=store)
        assert exc_info.value.status_code == 401

    async def test_revoke_kills_family_descendants(self, store):
        parent = create_refresh_token({"sub": "testuser"})
        response = await refresh_access_token(parent, make_db(make_user()), store=store)
        await revoke_refresh_token(parent, store=store)
        with pytest.raises(HTTPException):
            await refresh_access_token(response.refresh_token, make_db(make_user()), store=store)

    async def test_revoke_invalid_token_is_not_an_error(self, store):
        """RFC 7009: revoking an unknown/invalid token still succeeds."""
        assert await revoke_refresh_token("not-a-jwt", store=store) is False
        expired = create_refresh_token({"sub": "testuser"}, expires_delta=timedelta(minutes=-5))
        assert await revoke_refresh_token(expired, store=store) is False


class TestLegacyMigration:
    """Tokens minted before this change (no jti) refresh once and upgrade."""

    async def test_legacy_token_upgrades_to_jti_token(self, store):
        legacy = jwt.encode(
            {
                "sub": "testuser",
                "type": "refresh",
                "exp": decode(create_refresh_token({"sub": "x"}))["exp"],
            },
            settings.secret_key.get_secret_value(),
            algorithm=settings.algorithm,
        )
        response = await refresh_access_token(legacy, make_db(make_user()), store=store)
        payload = decode(response.refresh_token)
        assert payload["jti"]
        assert payload["fam"]


class TestStoreFailure:
    """Fail-closed: refresh is refused (503) when the denylist is unreachable."""

    async def test_refresh_fails_closed_without_store(self):
        token = create_refresh_token({"sub": "testuser"})
        with pytest.raises(HTTPException) as exc_info:
            await refresh_access_token(token, make_db(make_user()), store=make_broken_store())
        assert exc_info.value.status_code == 503

    async def test_reuse_detection_cannot_be_bypassed_by_store_outage(self):
        """A revoked family must not refresh just because Redis went down."""
        token = create_refresh_token({"sub": "testuser"})
        broken = make_broken_store()
        broken.is_family_revoked = AsyncMock(return_value=True)
        with pytest.raises(HTTPException) as exc_info:
            await refresh_access_token(token, make_db(make_user()), store=broken)
        assert exc_info.value.status_code == 401


class TestRoute:
    """POST /auth/revoke endpoint wiring."""

    async def test_revoke_endpoint_registered(self):
        from api.v1.auth_routes import router

        paths = {route.path for route in router.routes}
        assert "/auth/revoke" in paths

    async def test_revoke_endpoint_calls_service(self, store, monkeypatch):
        from api.v1 import auth_routes

        called = {}

        async def fake_revoke(token: str, store=None):
            called["token"] = token
            return True

        monkeypatch.setattr(auth_routes, "revoke_refresh_token", fake_revoke)
        response = await auth_routes.revoke_token(refresh_request=Mock(refresh_token="abc"))
        assert called["token"] == "abc"
        assert response["revoked"] is True
