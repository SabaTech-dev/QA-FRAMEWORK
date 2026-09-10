"""
Token issuance contract: access tokens must carry the user's plan claim
(card e8a6b3a7, F-1). RateLimitMiddleware decodes the JWT pre-auth and
relies on this claim, so login and refresh issuance are contract-tested:
plan=pro for a pro user, fallback 'free' when the column is NULL.
"""

import pytest

pytest.importorskip("jose")
from unittest.mock import AsyncMock, Mock

from jose import jwt

from config import settings
from models import User
from schemas import LoginRequest
from services.auth_service import (
    create_refresh_token,
    login_for_access_token,
    refresh_access_token,
)
from src.infrastructure.refresh_tokens.store import RefreshTokenStore


def decode(token: str) -> dict:
    return jwt.decode(
        token,
        settings.secret_key.get_secret_value(),
        algorithms=[settings.algorithm],
    )


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


def make_db(user: User) -> AsyncMock:
    db = AsyncMock()
    result = AsyncMock()
    result.scalar_one_or_none = Mock(return_value=user)
    db.execute = AsyncMock(return_value=result)
    return db


def make_store() -> RefreshTokenStore:
    store = Mock()
    store.is_denied = AsyncMock(return_value=False)
    store.is_family_revoked = AsyncMock(return_value=False)
    store.try_consume_jti = AsyncMock(return_value=True)
    store.revoke_family = AsyncMock()
    store.deny_jti = AsyncMock()
    return store


@pytest.mark.asyncio
async def test_login_mints_token_with_real_plan(monkeypatch):
    """auth_service login: plan claim reflects subscription_plan (pro)"""
    import services.auth_service as svc

    user = make_user(subscription_plan="pro")
    monkeypatch.setattr(svc, "authenticate_user", AsyncMock(return_value=user))

    response = await login_for_access_token(
        LoginRequest(username="testuser", password="pw"), db=AsyncMock()
    )

    payload = decode(response.access_token)
    assert payload["sub"] == "testuser"
    assert payload["plan"] == "pro"


@pytest.mark.asyncio
async def test_refresh_mints_token_with_plan_fallback_free(monkeypatch):
    """auth_service refresh: NULL subscription_plan falls back to 'free'"""
    user = make_user(subscription_plan=None)
    refresh_token = create_refresh_token({"sub": "testuser"})

    response = await refresh_access_token(refresh_token, db=make_db(user), store=make_store())

    payload = decode(response.access_token)
    assert payload["sub"] == "testuser"
    assert payload["plan"] == "free"
