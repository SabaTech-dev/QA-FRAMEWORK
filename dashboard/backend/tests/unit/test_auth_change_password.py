"""Card 4920f947 — /auth/change-password and /auth/register must be real.

Rejects the "success sin efecto" stub pattern: every success response is
proven against a persisted row (in-memory sqlite via aiosqlite), so a stub
that returns 200 without touching the database fails these tests.

Findings that shaped this suite (2026-09-28):
- POST /auth/register is already real (auth_routes -> create_user_service);
  these tests pin that behavior so it cannot regress to a stub.
- POST /auth/change-password did not exist at all (404); admin rotation had
  to be done via direct psql (context of card 4920f947).
- api/v1/auth/email.py was an unmounted all-stub router (fake uuid4()
  responses, no DB): it is deleted and must stay deleted.

Frontend contract (frontend/src/api/client.ts): the UI sends
{"oldPassword": ..., "newPassword": ...} — camelCase — so the endpoint
accepts those names (plus snake_case aliases).
"""

import bcrypt
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from api.v1 import auth_routes
from database import get_db_session
from models import Base, User
from services.auth_service import get_current_user, hash_password

OLD_PW = "OldPass123!"
NEW_PW = "NewPass456!"


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


@pytest.fixture
async def seeded_user(db_factory):
    """A user row whose password is OLD_PW."""
    async with db_factory() as session:
        user = User(
            username="alice",
            email="alice@test.local",
            hashed_password=hash_password(OLD_PW),
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        yield user


def build_app(db_factory, authenticated: bool = True):
    """Mini app mounting only the real auth router, wired to the test DB.

    authenticated=False keeps the real JWT dependency, so requests without
    a token must be rejected.
    """
    from fastapi import Depends, FastAPI

    app = FastAPI()
    app.include_router(auth_routes.router)

    async def override_db():
        async with db_factory() as session:
            yield session

    async def override_current_user(
        session=Depends(get_db_session),
    ):
        # Depends(get_db_session) resolves to override_db and FastAPI's
        # per-request cache hands us the SAME session the endpoint uses —
        # mirroring production, where get_current_user and the endpoint
        # share one session and the returned user stays attached.
        result = await session.execute(select(User).where(User.username == "alice"))
        user = result.scalar_one_or_none()
        assert user is not None, "seeded user missing"
        return user

    app.dependency_overrides[get_db_session] = override_db
    if authenticated:
        app.dependency_overrides[get_current_user] = override_current_user
    return app


def client(app):
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


# ---------------------------------------------------------------- register


async def test_register_persists_user_and_hashes_password(db_factory):
    """/auth/register success MUST have a DB effect: row inserted, bcrypt
    cost-12 hash stored, plaintext never stored."""
    async with client(build_app(db_factory)) as c:
        resp = await c.post(
            "/auth/register",
            json={
                "username": "bob",
                "email": "bob@test.local",
                "password": "Sup3rSecret!",
            },
        )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["email"] == "bob@test.local"

    async with db_factory() as session:
        user = (
            await session.execute(select(User).where(User.email == "bob@test.local"))
        ).scalar_one()
        assert user.username == "bob"
        assert user.hashed_password.startswith("$2b$12$"), "bcrypt cost must be 12"
        assert user.hashed_password != "Sup3rSecret!"
        assert bcrypt.checkpw(b"Sup3rSecret!", user.hashed_password.encode())


async def test_register_duplicate_email_rejected_without_side_effect(db_factory):
    async with client(build_app(db_factory)) as c:
        payload = {
            "username": "bob",
            "email": "bob@test.local",
            "password": "Sup3rSecret!",
        }
        first = await c.post("/auth/register", json=payload)
        dup = await c.post("/auth/register", json=payload)

    assert first.status_code == 200
    assert dup.status_code == 400

    async with db_factory() as session:
        users = (
            (await session.execute(select(User).where(User.email == "bob@test.local")))
            .scalars()
            .all()
        )
        assert len(users) == 1, "duplicate register must not insert"


# ---------------------------------------------------------- change-password


async def test_change_password_updates_hash_in_db(db_factory, seeded_user):
    """Happy path: success MUST equal a persisted re-hash. A stub returning
    200 without updating the row fails here (the 'success sin efecto'
    rejection test)."""
    original_hash = seeded_user.hashed_password

    async with client(build_app(db_factory)) as c:
        resp = await c.post(
            "/auth/change-password",
            json={"oldPassword": OLD_PW, "newPassword": NEW_PW},
        )

    assert resp.status_code == 200, resp.text

    async with db_factory() as session:
        user = (await session.execute(select(User).where(User.username == "alice"))).scalar_one()
        assert user.hashed_password != original_hash, "hash must change in DB"
        assert user.hashed_password.startswith("$2b$12$"), "re-hash must be bcrypt cost 12"
        assert bcrypt.checkpw(NEW_PW.encode(), user.hashed_password.encode())
        assert not bcrypt.checkpw(OLD_PW.encode(), user.hashed_password.encode())


async def test_change_password_accepts_snake_case_aliases(db_factory, seeded_user):
    """snake_case clients (API consumers, curl) get the same behavior."""
    async with client(build_app(db_factory)) as c:
        resp = await c.post(
            "/auth/change-password",
            json={"old_password": OLD_PW, "new_password": NEW_PW},
        )

    assert resp.status_code == 200, resp.text
    async with db_factory() as session:
        user = (await session.execute(select(User).where(User.username == "alice"))).scalar_one()
        assert bcrypt.checkpw(NEW_PW.encode(), user.hashed_password.encode())


async def test_change_password_wrong_current_password_rejected(db_factory, seeded_user):
    """Wrong current password: 401 and NO DB change (no silent success)."""
    original_hash = seeded_user.hashed_password

    async with client(build_app(db_factory)) as c:
        resp = await c.post(
            "/auth/change-password",
            json={"oldPassword": "WrongPass9!", "newPassword": NEW_PW},
        )

    assert resp.status_code == 401, resp.text
    async with db_factory() as session:
        user = (await session.execute(select(User).where(User.username == "alice"))).scalar_one()
        assert user.hashed_password == original_hash, "rejected change must not touch DB"


async def test_change_password_requires_authentication(db_factory, seeded_user):
    """Without a valid JWT the endpoint must refuse (401/403), never act."""
    async with client(build_app(db_factory, authenticated=False)) as c:
        resp = await c.post(
            "/auth/change-password",
            json={"oldPassword": OLD_PW, "newPassword": NEW_PW},
        )

    assert resp.status_code in (401, 403), resp.text


async def test_change_password_weak_new_password_rejected(db_factory, seeded_user):
    """New password under 8 chars: 422, no DB change."""
    original_hash = seeded_user.hashed_password

    async with client(build_app(db_factory)) as c:
        resp = await c.post(
            "/auth/change-password",
            json={"oldPassword": OLD_PW, "newPassword": "short"},
        )

    assert resp.status_code == 422, resp.text
    async with db_factory() as session:
        user = (await session.execute(select(User).where(User.username == "alice"))).scalar_one()
        assert user.hashed_password == original_hash


# ------------------------------------------------------- stub-router guard


def test_stub_email_module_stays_deleted():
    """api/v1/auth/email.py was an unmounted all-stub auth router (fake
    register/login/change-password responses, no DB). It must not come
    back: a mounted-looking stub is worse than no route."""
    import importlib

    with pytest.raises(ImportError):
        importlib.import_module("api.v1.auth.email")
