"""
Tests for Waitlist API endpoints.

Covers:
- Public join endpoint (create, duplicate rejection)
- Public check endpoint (status lookup)
- Admin list, get, update, delete endpoints
- Stats endpoint
- Authorization enforcement (non-admin blocked)
"""

import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, MagicMock

from dashboard.backend.main import app
from dashboard.backend.models import WaitlistEntry


@pytest.fixture
def mock_waitlist_entry():
    """Factory for waitlist entry mocks."""
    def _make(
        id=1,
        email="user@example.com",
        name="Test User",
        status="pending",
        source=None,
        notes=None,
    ):
        entry = MagicMock()
        entry.id = id
        entry.email = email
        entry.name = name
        entry.status = status
        entry.source = source
        entry.notes = notes
        entry.created_at = "2026-06-23T06:00:00"
        entry.updated_at = "2026-06-23T06:00:00"
        return entry
    return _make


@pytest.fixture
def mock_admin_user():
    """Admin user mock."""
    user = MagicMock()
    user.id = 1
    user.is_superuser = True
    user.username = "admin"
    return user


@pytest.fixture
def mock_regular_user():
    """Regular non-admin user mock."""
    user = MagicMock()
    user.id = 2
    user.is_superuser = False
    user.username = "regular"
    return user


class TestWaitlistJoin:
    """Tests for POST /api/v1/waitlist/join (public)."""

    @pytest.mark.asyncio
    async def test_join_success(self, monkeypatch, mock_waitlist_entry):
        """Successfully join waitlist with valid email."""
        new_entry = mock_waitlist_entry()

        monkeypatch.setattr(
            "api.v1.waitlist_routes.get_waitlist_entry_by_email",
            AsyncMock(return_value=None),
        )
        monkeypatch.setattr(
            "api.v1.waitlist_routes.create_waitlist_entry",
            AsyncMock(return_value=new_entry),
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/api/v1/waitlist/join", json={
                "email": "newuser@example.com",
                "name": "New User",
            })

        assert resp.status_code == 201
        data = resp.json()
        assert data["email"] == "newuser@example.com"
        assert data["name"] == "New User"

    @pytest.mark.asyncio
    async def test_join_duplicate_email(self, monkeypatch, mock_waitlist_entry):
        """Duplicate email returns 409."""
        existing = mock_waitlist_entry(email="dup@example.com")

        monkeypatch.setattr(
            "api.v1.waitlist_routes.get_waitlist_entry_by_email",
            AsyncMock(return_value=existing),
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/api/v1/waitlist/join", json={
                "email": "dup@example.com",
            })

        assert resp.status_code == 409
        assert "already" in resp.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_join_invalid_email(self, monkeypatch):
        """Invalid email format returns 422."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/api/v1/waitlist/join", json={
                "email": "not-an-email",
            })

        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_join_no_name(self, monkeypatch, mock_waitlist_entry):
        """Join with email only (name optional)."""
        new_entry = mock_waitlist_entry(name=None)

        monkeypatch.setattr(
            "api.v1.waitlist_routes.get_waitlist_entry_by_email",
            AsyncMock(return_value=None),
        )
        monkeypatch.setattr(
            "api.v1.waitlist_routes.create_waitlist_entry",
            AsyncMock(return_value=new_entry),
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/api/v1/waitlist/join", json={
                "email": "noname@example.com",
            })

        assert resp.status_code == 201


class TestWaitlistCheck:
    """Tests for GET /api/v1/waitlist/check (public)."""

    @pytest.mark.asyncio
    async def test_check_registered(self, monkeypatch, mock_waitlist_entry):
        """Check returns registered=True for existing email."""
        entry = mock_waitlist_entry(status="contacted")

        monkeypatch.setattr(
            "api.v1.waitlist_routes.get_waitlist_entry_by_email",
            AsyncMock(return_value=entry),
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/waitlist/check", params={"email": "user@example.com"})

        assert resp.status_code == 200
        data = resp.json()
        assert data["registered"] is True
        assert data["status"] == "contacted"

    @pytest.mark.asyncio
    async def test_check_not_registered(self, monkeypatch):
        """Check returns registered=False for unknown email."""
        monkeypatch.setattr(
            "api.v1.waitlist_routes.get_waitlist_entry_by_email",
            AsyncMock(return_value=None),
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/waitlist/check", params={"email": "unknown@example.com"})

        assert resp.status_code == 200
        data = resp.json()
        assert data["registered"] is False
        assert data["status"] is None


class TestWaitlistAdmin:
    """Tests for admin-only waitlist endpoints."""

    @pytest.mark.asyncio
    async def test_list_requires_admin(self, monkeypatch, mock_regular_user):
        """Non-admin cannot list waitlist."""
        monkeypatch.setattr(
            "api.v1.waitlist_routes.get_current_user",
            AsyncMock(return_value=mock_regular_user),
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/waitlist")

        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_list_success(self, monkeypatch, mock_admin_user, mock_waitlist_entry):
        """Admin can list waitlist entries."""
        entries = [mock_waitlist_entry(id=1), mock_waitlist_entry(id=2, email="second@example.com")]

        monkeypatch.setattr(
            "api.v1.waitlist_routes.get_current_user",
            AsyncMock(return_value=mock_admin_user),
        )
        monkeypatch.setattr(
            "api.v1.waitlist_routes.list_waitlist_entries",
            AsyncMock(return_value=(entries, 2)),
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/waitlist")

        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2

    @pytest.mark.asyncio
    async def test_stats_requires_admin(self, monkeypatch, mock_regular_user):
        """Non-admin cannot view stats."""
        monkeypatch.setattr(
            "api.v1.waitlist_routes.get_current_user",
            AsyncMock(return_value=mock_regular_user),
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/waitlist/stats")

        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_stats_success(self, monkeypatch, mock_admin_user):
        """Admin gets waitlist stats."""
        stats = {
            "total": 42,
            "by_status": {"pending": 30, "contacted": 10, "converted": 2},
            "pending": 30,
            "contacted": 10,
            "converted": 2,
        }

        monkeypatch.setattr(
            "api.v1.waitlist_routes.get_current_user",
            AsyncMock(return_value=mock_admin_user),
        )
        monkeypatch.setattr(
            "api.v1.waitlist_routes.get_waitlist_stats",
            AsyncMock(return_value=stats),
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/waitlist/stats")

        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 42

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, monkeypatch, mock_admin_user):
        """Get non-existent entry returns 404."""
        monkeypatch.setattr(
            "api.v1.waitlist_routes.get_current_user",
            AsyncMock(return_value=mock_admin_user),
        )
        monkeypatch.setattr(
            "api.v1.waitlist_routes.get_waitlist_entry_by_id",
            AsyncMock(return_value=None),
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/waitlist/999")

        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_update_entry(self, monkeypatch, mock_admin_user, mock_waitlist_entry):
        """Admin updates entry status."""
        updated = mock_waitlist_entry(status="contacted")

        monkeypatch.setattr(
            "api.v1.waitlist_routes.get_current_user",
            AsyncMock(return_value=mock_admin_user),
        )
        monkeypatch.setattr(
            "api.v1.waitlist_routes.update_waitlist_entry",
            AsyncMock(return_value=updated),
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.patch("/api/v1/waitlist/1", json={"status": "contacted"})

        assert resp.status_code == 200
        assert resp.json()["status"] == "contacted"

    @pytest.mark.asyncio
    async def test_delete_entry(self, monkeypatch, mock_admin_user):
        """Admin deletes entry."""
        monkeypatch.setattr(
            "api.v1.waitlist_routes.get_current_user",
            AsyncMock(return_value=mock_admin_user),
        )
        monkeypatch.setattr(
            "api.v1.waitlist_routes.delete_waitlist_entry",
            AsyncMock(return_value=True),
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.delete("/api/v1/waitlist/1")

        assert resp.status_code == 200
        assert resp.json()["success"] is True

    @pytest.mark.asyncio
    async def test_delete_not_found(self, monkeypatch, mock_admin_user):
        """Delete non-existent entry returns 404."""
        monkeypatch.setattr(
            "api.v1.waitlist_routes.get_current_user",
            AsyncMock(return_value=mock_admin_user),
        )
        monkeypatch.setattr(
            "api.v1.waitlist_routes.delete_waitlist_entry",
            AsyncMock(return_value=False),
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.delete("/api/v1/waitlist/999")

        assert resp.status_code == 404
