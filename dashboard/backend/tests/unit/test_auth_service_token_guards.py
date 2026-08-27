"""Token-type and account-status guards for the auth service (cards L-1, L-2, JWT edges).

Security findings hardened here:

- L-1: ``get_current_user`` / ``get_qa_visual_principal`` accepted refresh
  tokens (7-day expiry) as access tokens because the ``type`` claim was
  never checked. A leaked refresh token must not grant API access.
- L-2: ``get_current_user`` did not check ``is_active`` while the refresh
  and optional paths did — a deactivated user kept full API access until
  token expiry.
- JWT edge (a): an expired token must answer 401, never 500.
- JWT edge (b): a principal with an empty owner must be rejected with a
  4xx instead of silently scoping reports to an empty owner.

All tests run against the real token minting helpers and a mocked DB
session (same pattern as tests/unit/test_auth_service.py).
"""

from datetime import timedelta
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import HTTPException
from jose import jwt

pytest.importorskip("jose")

from models import User
from services.auth_service import (
    create_access_token,
    create_refresh_token,
    get_current_user,
    get_current_user_optional,
    get_qa_visual_principal,
)

from config import settings


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


def make_credentials(token: str) -> Mock:
    mock_credentials = Mock()
    mock_credentials.credentials = token
    return mock_credentials


def decode(token: str) -> dict:
    return jwt.decode(token, settings.secret_key.get_secret_value(), algorithms=[settings.algorithm])


class TestTokenTypeGuard:
    """L-1: refresh tokens must never authenticate access-token endpoints."""

    async def test_refresh_token_rejected_as_access(self):
        token = create_refresh_token({"sub": "testuser"})
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(make_credentials(token), make_db(make_user()))
        assert exc_info.value.status_code == 401

    async def test_access_token_carries_type_claim(self):
        token = create_access_token({"sub": "testuser"})
        assert decode(token).get("type") == "access"

    async def test_typed_access_token_accepted(self):
        token = create_access_token({"sub": "testuser"})
        user = await get_current_user(make_credentials(token), make_db(make_user()))
        assert user.username == "testuser"

    async def test_legacy_typeless_access_token_accepted(self):
        """Tokens minted before the type tag stay valid until they expire."""
        legacy = jwt.encode(
            {"sub": "testuser", "exp": decode(create_access_token({"sub": "x"}))["exp"]},
            settings.secret_key.get_secret_value(),
            algorithm=settings.algorithm,
        )
        user = await get_current_user(make_credentials(legacy), make_db(make_user()))
        assert user.username == "testuser"

    async def test_unknown_token_type_rejected(self):
        token = create_access_token({"sub": "testuser"})
        payload = decode(token)
        payload["type"] = "password-reset"
        forged = jwt.encode(payload, settings.secret_key.get_secret_value(), algorithm=settings.algorithm)
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(make_credentials(forged), make_db(make_user()))
        assert exc_info.value.status_code == 401

    async def test_optional_auth_treats_refresh_token_as_anonymous(self):
        token = create_refresh_token({"sub": "testuser"})
        user = await get_current_user_optional(make_credentials(token), make_db(make_user()))
        assert user is None

    async def test_optional_auth_accepts_typed_access_token(self):
        token = create_access_token({"sub": "testuser"})
        user = await get_current_user_optional(make_credentials(token), make_db(make_user()))
        assert user is not None
        assert user.username == "testuser"


class TestActiveUserGuard:
    """L-2: deactivated users must lose API access immediately."""

    async def test_inactive_user_rejected(self):
        token = create_access_token({"sub": "testuser"})
        inactive = make_user(is_active=False)
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(make_credentials(token), make_db(inactive))
        assert exc_info.value.status_code in (401, 403)

    async def test_active_user_still_accepted(self):
        token = create_access_token({"sub": "testuser"})
        user = await get_current_user(make_credentials(token), make_db(make_user()))
        assert user.is_active is True


class TestExpiredTokenEdge:
    """JWT edge (a): expired tokens answer 401, never 500."""

    async def test_expired_token_rejected_401(self):
        token = create_access_token({"sub": "testuser"}, expires_delta=timedelta(minutes=-5))
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(make_credentials(token), make_db(make_user()))
        assert exc_info.value.status_code == 401

    async def test_expired_refresh_token_rejected_401(self):
        token = create_refresh_token({"sub": "testuser"}, expires_delta=timedelta(minutes=-5))
        from services.auth_service import refresh_access_token

        with pytest.raises(HTTPException) as exc_info:
            await refresh_access_token(token, make_db(make_user()))
        assert exc_info.value.status_code == 401


class TestPrincipalOwnerEdge:
    """JWT edge (b): an empty owner identity is rejected with 4xx, not scoped."""

    async def test_empty_username_principal_rejected_4xx(self):
        with pytest.raises(HTTPException) as exc_info:
            await get_qa_visual_principal(current_user=make_user(username=""))
        assert 400 <= exc_info.value.status_code < 500

    async def test_regular_username_principal_still_maps(self):
        principal = await get_qa_visual_principal(current_user=make_user())
        assert principal.owner == "testuser"
        assert principal.is_admin is False
