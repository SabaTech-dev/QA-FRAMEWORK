"""Card 3fb18833 (F-4) — POST /users must not create accounts.

Account creation lives ONLY at POST /auth/register (hardened in card
4920f947: explicit bcrypt cost, 72-byte password bound). The legacy
POST /users endpoint in api/v1/routes.py had no auth dependency and no
entry in ENDPOINT_LIMITS — an unauthenticated account-minting path
outside the hardened register flow (OWASP API1/API6:2023, CVSS 5.3).

Why 405 and not just 404: GET /users (auth-protected) keeps the /users
path alive, so Starlette answers POST /users with 405 Method Not
Allowed. The security property under test is stronger than the status
code: no row may be persisted, authenticated or not.
"""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from api.v1 import auth_routes
from database import get_db_session
from models import Base, User

VALID_REGISTER = {
    "username": "eve",
    "email": "eve@test.local",
    "password": "Sup3rSecret!",
}


@pytest.fixture
async def db_factory():
    """One real (in-memory) database per test: successes must have effects."""
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


def _override_db(db_factory):
    async def override_db():
        async with db_factory() as session:
            yield session

    return override_db


def build_v1_app(db_factory):
    """Full v1 router mounted exactly like main.py (prefix /api/v1).

    Mounting the real router (not a re-declaration) proves the route is
    gone from production wiring, not just from a test copy.
    """
    from fastapi import FastAPI

    from api.v1 import routes as v1_routes

    app = FastAPI()
    app.include_router(v1_routes.router, prefix="/api/v1")
    app.dependency_overrides[get_db_session] = _override_db(db_factory)
    return app


def build_auth_app(db_factory):
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(auth_routes.router)
    app.dependency_overrides[get_db_session] = _override_db(db_factory)
    return app


async def test_post_users_does_not_create_accounts(db_factory):
    """POST /api/v1/users must not exist and must have zero DB effect."""
    app = build_v1_app(db_factory)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.post("/api/v1/users", json=VALID_REGISTER)

    assert resp.status_code in (404, 405), (
        "POST /users must not exist: account creation is /auth/register only "
        f"(got {resp.status_code}: {resp.text})"
    )

    async with db_factory() as session:
        rows = (await session.execute(select(User))).scalars().all()
    assert rows == [], "POST /users must have zero DB effect"


async def test_post_users_with_token_also_rejected(db_factory):
    """Even a (forged/valid) Authorization header must not revive the route."""
    app = build_v1_app(db_factory)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.post(
            "/api/v1/users",
            json=VALID_REGISTER,
            headers={"Authorization": "Bearer whatever"},
        )

    assert resp.status_code in (404, 405)
    async with db_factory() as session:
        rows = (await session.execute(select(User))).scalars().all()
    assert rows == []


async def test_auth_register_still_creates_accounts(db_factory):
    """Regression pin: the hardened register flow keeps working unchanged."""
    app = build_auth_app(db_factory)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.post("/auth/register", json=VALID_REGISTER)

    assert resp.status_code == 200, resp.text
    assert resp.json()["email"] == "eve@test.local"

    async with db_factory() as session:
        user = (
            await session.execute(select(User).where(User.email == "eve@test.local"))
        ).scalar_one_or_none()
    assert user is not None, "register must persist the user"
    assert user.username == "eve"
