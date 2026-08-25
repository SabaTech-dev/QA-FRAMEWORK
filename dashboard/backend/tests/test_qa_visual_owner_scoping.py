"""S-1R owner-scoping authorization tests on the REAL dashboard app (card 9b67f430).

The feature-flag tests documented why the qa-visual router stayed
unmounted: the store was global and any authenticated user could read
other users' reports (cross-tenant BOLA, CVSS 5.4). This file proves
the fix end to end against the app mounted by ``main`` with
``QA_VISUAL_ENABLED=1``:

- real JWTs minted with the app's own secret
- real ``get_current_user`` (JWT decode + user lookup against SQLite)
- two regular users (alice, bob) and one admin (root, is_superuser)

Matrix:
- alice reads her own report      -> 200 (owner)
- bob reads alice's report        -> 403 (authenticated NON-owner)
- admin reads alice's report      -> 200 (role bypass)
- listing / trends / baselines scoped the same way

The gateway is never called: reports are pre-seeded on disk and only
GET endpoints are exercised (analyze ownership is covered at module
level in tests/unit/infrastructure/test_qa_visual_owner_scoping.py).
"""

import importlib
from datetime import datetime, timedelta, timezone

import pytest
from database import get_db_session
from fastapi.testclient import TestClient
from models import User
from services.auth_service import create_access_token, create_refresh_token
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from src.infrastructure.qa_visual.models import AnalyzeResponse, QAAnalysis
from src.infrastructure.qa_visual.storage import QAVisualReportStore

ALICE_REPORTS = [
    dict(
        report_id="rep-alice-1",
        target="amc",
        score=95,
        timestamp=datetime(2026, 8, 20, 12, 0, 0, tzinfo=timezone.utc),
    ),
    dict(
        report_id="rep-alice-2",
        target="amc",
        score=90,
        timestamp=datetime(2026, 8, 24, 12, 0, 0, tzinfo=timezone.utc),
    ),
]
BOB_REPORTS = [
    dict(
        report_id="rep-bob-1",
        target="landing",
        score=88,
        timestamp=datetime(2026, 8, 23, 9, 0, 0, tzinfo=timezone.utc),
    ),
]


def _response(owner: str, **fields) -> AnalyzeResponse:
    return AnalyzeResponse(
        analysis=QAAnalysis(overall_score=fields["score"], summary="seeded"),
        passed=fields["score"] >= 80,
        threshold=80,
        cost_usd=0.0004,
        latency_s=4.0,
        model="deepseek-v4-flash-vision-exp",
        owner=owner,
        **fields,
    )


@pytest.fixture(scope="module")
def qa_app(tmp_path_factory):
    """The real dashboard app with the qa-visual router mounted.

    QA_VISUAL_REPORTS_DIR points at a temp dir seeded with alice's and
    bob's reports, so no real runtime artifacts are touched.
    """
    reports_dir = tmp_path_factory.mktemp("qa-visual-reports")
    store = QAVisualReportStore(reports_dir=str(reports_dir))
    for fields in ALICE_REPORTS:
        store.save(_response("alice", **fields))
    for fields in BOB_REPORTS:
        store.save(_response("bob", **fields))

    mp = pytest.MonkeyPatch()
    mp.setenv("QA_VISUAL_ENABLED", "1")
    mp.setenv("QA_VISUAL_REPORTS_DIR", str(reports_dir))
    import main as dashboard_main

    app = importlib.reload(dashboard_main).app
    yield app
    mp.undo()


@pytest.fixture()
async def auth_headers(qa_app):
    """Real users in SQLite + real JWTs; get_db_session is overridden."""
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(User.__table__.create)

    async with AsyncSession(engine) as session:
        session.add_all(
            [
                User(
                    username="alice",
                    email="alice@example.com",
                    hashed_password="x",
                    is_active=True,
                    is_superuser=False,
                ),
                User(
                    username="bob",
                    email="bob@example.com",
                    hashed_password="x",
                    is_active=True,
                    is_superuser=False,
                ),
                User(
                    username="root",
                    email="root@example.com",
                    hashed_password="x",
                    is_active=True,
                    is_superuser=True,
                ),
                User(
                    username="dormant",
                    email="dormant@example.com",
                    hashed_password="x",
                    is_active=False,
                    is_superuser=False,
                ),
            ]
        )
        await session.commit()

    async def override_session():
        async with AsyncSession(engine) as session:
            yield session

    qa_app.dependency_overrides[get_db_session] = override_session
    try:
        yield {
            "alice": {"Authorization": f"Bearer {create_access_token({'sub': 'alice'})}"},
            "bob": {"Authorization": f"Bearer {create_access_token({'sub': 'bob'})}"},
            "admin": {"Authorization": f"Bearer {create_access_token({'sub': 'root'})}"},
            # L-2: valid credentials for a deactivated account.
            "dormant": {"Authorization": f"Bearer {create_access_token({'sub': 'dormant'})}"},
            # L-1: valid refresh token minted for alice.
            "alice_refresh": {"Authorization": f"Bearer {create_refresh_token({'sub': 'alice'})}"},
            # JWT edge (a): well-formed but expired access token.
            "expired": {
                "Authorization": (
                    f"Bearer {create_access_token({'sub': 'alice'}, expires_delta=timedelta(minutes=-5))}"
                )
            },
        }
    finally:
        qa_app.dependency_overrides.pop(get_db_session, None)
        await engine.dispose()


@pytest.fixture()
def client(qa_app):
    return TestClient(qa_app)


class TestRealAppOwnerScoping:
    """Card AC: 200 for owner, 403 for non-owner, 200 for admin."""

    def test_owner_reads_own_report_200(self, client, auth_headers):
        response = client.get(
            "/api/v1/qa-visual/reports/rep-alice-1", headers=auth_headers["alice"]
        )
        assert response.status_code == 200
        assert response.json()["report_id"] == "rep-alice-1"

    def test_non_owner_gets_403(self, client, auth_headers):
        response = client.get("/api/v1/qa-visual/reports/rep-alice-1", headers=auth_headers["bob"])
        assert response.status_code == 403

    def test_admin_reads_others_report_200(self, client, auth_headers):
        response = client.get(
            "/api/v1/qa-visual/reports/rep-alice-1", headers=auth_headers["admin"]
        )
        assert response.status_code == 200

    def test_owner_reads_second_own_report_200(self, client, auth_headers):
        response = client.get(
            "/api/v1/qa-visual/reports/rep-alice-2", headers=auth_headers["alice"]
        )
        assert response.status_code == 200

    def test_non_owner_still_reads_own_report_200(self, client, auth_headers):
        response = client.get("/api/v1/qa-visual/reports/rep-bob-1", headers=auth_headers["bob"])
        assert response.status_code == 200

    def test_unknown_report_404_for_owner(self, client, auth_headers):
        response = client.get("/api/v1/qa-visual/reports/missing", headers=auth_headers["alice"])
        assert response.status_code == 404

    def test_unknown_report_404_for_non_owner(self, client, auth_headers):
        """PR #134 advisory item 4: nonexistent id → 404 for an authenticated
        non-owner (valid tenant), never 403 — 403 only means "exists but
        forbidden", so a missing report must never answer 403."""
        response = client.get("/api/v1/qa-visual/reports/missing", headers=auth_headers["bob"])
        assert response.status_code == 404

    def test_reports_listing_scoped_to_owner(self, client, auth_headers):
        body = client.get("/api/v1/qa-visual/reports", headers=auth_headers["alice"]).json()
        assert sorted(r["report_id"] for r in body) == ["rep-alice-1", "rep-alice-2"]

    def test_reports_listing_non_owner_excludes_others(self, client, auth_headers):
        body = client.get("/api/v1/qa-visual/reports", headers=auth_headers["bob"]).json()
        assert [r["report_id"] for r in body] == ["rep-bob-1"]

    def test_reports_listing_admin_sees_all(self, client, auth_headers):
        body = client.get("/api/v1/qa-visual/reports", headers=auth_headers["admin"]).json()
        assert len(body) == 3

    def test_trends_scoped_to_owner(self, client, auth_headers):
        body = client.get("/api/v1/qa-visual/trends", headers=auth_headers["bob"]).json()
        targets = {p["target"] for p in body["points"]}
        assert targets == {"landing"}

    def test_baseline_404_for_non_owner(self, client, auth_headers):
        response = client.get("/api/v1/qa-visual/baselines/amc", headers=auth_headers["bob"])
        assert response.status_code == 404

    def test_baseline_200_for_owner(self, client, auth_headers):
        response = client.get("/api/v1/qa-visual/baselines/amc", headers=auth_headers["alice"])
        assert response.status_code == 200
        assert response.json()["target"] == "amc"


class TestPrincipalAdapter:
    """get_qa_visual_principal maps the dashboard User to the module contract."""

    async def test_regular_user_maps_to_owner_without_admin(self):
        from services.auth_service import get_qa_visual_principal

        user = User(
            username="alice",
            email="alice@example.com",
            hashed_password="x",
            is_superuser=False,
        )
        principal = await get_qa_visual_principal(current_user=user)
        assert principal.owner == "alice"
        assert principal.is_admin is False

    async def test_superuser_maps_to_admin(self):
        from services.auth_service import get_qa_visual_principal

        user = User(
            username="root",
            email="root@example.com",
            hashed_password="x",
            is_superuser=True,
        )
        principal = await get_qa_visual_principal(current_user=user)
        assert principal.owner == "root"
        assert principal.is_admin is True


class TestAuthHardeningMatrix:
    """Auth regression matrix (cards L-1, L-2, JWT edges) on the real app.

    Rows: valid access / refresh-as-access / expired / inactive / admin.
    """

    def test_valid_access_token_still_authenticates(self, client, auth_headers):
        response = client.get("/api/v1/qa-visual/reports", headers=auth_headers["alice"])
        assert response.status_code == 200

    def test_refresh_token_as_access_rejected_401(self, client, auth_headers):
        response = client.get("/api/v1/qa-visual/reports", headers=auth_headers["alice_refresh"])
        assert response.status_code == 401

    def test_refresh_token_on_single_report_rejected_401(self, client, auth_headers):
        response = client.get(
            "/api/v1/qa-visual/reports/rep-alice-1", headers=auth_headers["alice_refresh"]
        )
        assert response.status_code == 401

    def test_expired_token_rejected_401_not_500(self, client, auth_headers):
        response = client.get("/api/v1/qa-visual/reports", headers=auth_headers["expired"])
        assert response.status_code == 401

    def test_inactive_user_rejected_403(self, client, auth_headers):
        response = client.get("/api/v1/qa-visual/reports", headers=auth_headers["dormant"])
        assert response.status_code in (401, 403)

    def test_admin_access_token_still_sees_all(self, client, auth_headers):
        body = client.get("/api/v1/qa-visual/reports", headers=auth_headers["admin"]).json()
        assert len(body) == 3

    def test_refresh_token_on_optional_endpoint_is_anonymous(self, client, auth_headers):
        """L-1 on get_current_user_optional: a refresh token on the
        anonymous-friendly feedback endpoint must not authenticate."""
        response = client.post(
            "/api/v1/feedback",
            json={"type": "bug", "title": "x", "description": "y"},
            headers=auth_headers["alice_refresh"],
        )
        assert response.status_code != 500
        if response.status_code == 201:
            assert response.json().get("user_id") is None
