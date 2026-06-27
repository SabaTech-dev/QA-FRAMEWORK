"""
Integration tests for healing_routes.py (self-healing API).

Covers the CRUD endpoints, the heal action and the JWT auth gate (401).
Uses FastAPI TestClient with dependency overrides so the HTTP layer is
exercised without a real database or a real JWT.
"""

import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from api.v1 import healing_routes
from database import get_db_session as get_db
from services.auth_service import get_current_user


def _selector_dict(i=1):
    """A complete selector payload matching HealingSelectorResponse."""
    return {
        "id": i,
        "value": "#submit-button",
        "selector_type": "id",
        "description": None,
        "confidence_score": 0.95,
        "confidence_level": "high",
        "is_active": True,
        "usage_count": 10,
        "success_rate": 0.9,
        "created_at": datetime(2026, 1, 1).isoformat(),
        "updated_at": datetime(2026, 1, 1).isoformat(),
    }


def _result_dict(i=1):
    return {
        "id": i,
        "session_id": 1,
        "selector_id": 1,
        "original_selector_value": ".flaky",
        "healed_selector_value": "[data-testid='healed']",
        "status": "success",
        "confidence_score": 0.8,
        "confidence_level": "high",
        "healing_time_ms": 120,
        "attempts": 3,
        "created_at": datetime(2026, 1, 1).isoformat(),
    }


def _session_dict(i=1):
    return {
        "id": i,
        "status": "success",
        "total_selectors": 1,
        "successful_heals": 1,
        "failed_heals": 0,
        "success_rate": 1.0,
        "average_confidence": 0.8,
        "started_at": datetime(2026, 1, 1).isoformat(),
        "completed_at": datetime(2026, 1, 1).isoformat(),
    }


def _build_app(auth_user=None, auth_raise=False, mock_db=None):
    """Mount the healing router with overridden DB + auth dependencies.

    The router declares its own ``prefix="/healing"``.
    """
    app = FastAPI()
    app.include_router(healing_routes.router)

    async def _override_db():
        yield mock_db

    if auth_raise:

        async def _raise_unauthorized():
            raise HTTPException(
                status_code=401,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        app.dependency_overrides[get_current_user] = _raise_unauthorized
    elif auth_user is not None:

        async def _fake_user():
            return auth_user

        app.dependency_overrides[get_current_user] = _fake_user

    app.dependency_overrides[get_db] = _override_db
    return app


class _FakeUser:
    def __init__(self, user_id=1):
        self.id = user_id
        self.is_superuser = False
        self.username = "tester"


# ─── Auth gate (401) ──────────────────────────────────────────────
class TestHealingAuthGate:
    @pytest.fixture
    def unauth_client(self):
        app = _build_app(auth_raise=True, mock_db=AsyncMock())
        return TestClient(app)

    def test_list_selectors_requires_auth(self, unauth_client):
        assert unauth_client.get("/healing/selectors").status_code == 401

    def test_create_selector_requires_auth(self, unauth_client):
        resp = unauth_client.post("/healing/selectors", json={"value": "#x", "selector_type": "id"})
        assert resp.status_code == 401

    def test_get_selector_requires_auth(self, unauth_client):
        assert unauth_client.get("/healing/selectors/1").status_code == 401

    def test_update_selector_requires_auth(self, unauth_client):
        resp = unauth_client.put("/healing/selectors/1", json={"value": "#y"})
        assert resp.status_code == 401

    def test_delete_selector_requires_auth(self, unauth_client):
        assert unauth_client.delete("/healing/selectors/1").status_code == 401

    def test_heal_selector_requires_auth(self, unauth_client):
        assert unauth_client.post("/healing/selectors/1/heal").status_code == 401

    def test_list_sessions_requires_auth(self, unauth_client):
        assert unauth_client.get("/healing/sessions").status_code == 401

    def test_list_results_requires_auth(self, unauth_client):
        assert unauth_client.get("/healing/results").status_code == 401


# ─── Selectors CRUD ───────────────────────────────────────────────
class TestSelectorRoutes:
    def test_create_selector_201(self):
        mock_db = AsyncMock()

        async def _refresh(obj):
            obj.id = 1

        mock_db.refresh = AsyncMock(side_effect=_refresh)
        client = TestClient(_build_app(auth_user=_FakeUser(), mock_db=mock_db))

        resp = client.post(
            "/healing/selectors",
            json={"value": "#submit", "selector_type": "id", "confidence_score": 0.9},
        )
        assert resp.status_code == 201
        assert resp.json()["value"] == "#submit"
        assert resp.json()["confidence_level"] == "high"

    def test_create_selector_invalid_payload_422(self):
        client = TestClient(_build_app(auth_user=_FakeUser(), mock_db=AsyncMock()))
        resp = client.post("/healing/selectors", json={"selector_type": "css"})
        assert resp.status_code == 422

    def test_list_selectors_200(self):
        client = TestClient(_build_app(auth_user=_FakeUser(), mock_db=AsyncMock()))
        with patch(
            "api.v1.healing_routes.list_selectors_service",
            new_callable=AsyncMock,
            return_value=[_selector_dict()],
        ):
            resp = client.get("/healing/selectors", params={"skip": 0, "limit": 10})
        assert resp.status_code == 200
        assert resp.json()[0]["value"] == "#submit-button"

    def test_get_selector_200(self):
        client = TestClient(_build_app(auth_user=_FakeUser(), mock_db=AsyncMock()))
        with patch(
            "api.v1.healing_routes.get_selector_by_id",
            new_callable=AsyncMock,
            return_value=_selector_dict(7),
        ):
            resp = client.get("/healing/selectors/7")
        assert resp.status_code == 200
        assert resp.json()["id"] == 7

    def test_get_selector_not_found_404(self):
        client = TestClient(_build_app(auth_user=_FakeUser(), mock_db=AsyncMock()))
        with patch(
            "api.v1.healing_routes.get_selector_by_id",
            new_callable=AsyncMock,
            side_effect=HTTPException(status_code=404, detail="not found"),
        ):
            resp = client.get("/healing/selectors/999")
        assert resp.status_code == 404

    def test_update_selector_200(self):
        client = TestClient(_build_app(auth_user=_FakeUser(), mock_db=AsyncMock()))
        updated = _selector_dict()
        updated["value"] = "[data-testid='y']"
        with patch(
            "api.v1.healing_routes.update_selector_service",
            new_callable=AsyncMock,
            return_value=updated,
        ):
            resp = client.put(
                "/healing/selectors/1",
                json={"value": "[data-testid='y']", "selector_type": "data_attribute"},
            )
        assert resp.status_code == 200
        assert resp.json()["value"] == "[data-testid='y']"

    def test_delete_selector_204(self):
        client = TestClient(_build_app(auth_user=_FakeUser(), mock_db=AsyncMock()))
        with patch(
            "api.v1.healing_routes.delete_selector_service",
            new_callable=AsyncMock,
            return_value=None,
        ):
            resp = client.delete("/healing/selectors/1")
        assert resp.status_code == 204


# ─── Heal action ──────────────────────────────────────────────────
class TestHealRoute:
    def test_heal_selector_200(self):
        client = TestClient(_build_app(auth_user=_FakeUser(), mock_db=AsyncMock()))
        with patch(
            "api.v1.healing_routes.heal_selector_service",
            new_callable=AsyncMock,
            return_value=_result_dict(),
        ):
            resp = client.post("/healing/selectors/5/heal")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "success"
        assert body["healed_selector_value"] == "[data-testid='healed']"

    def test_heal_selector_not_found_404(self):
        client = TestClient(_build_app(auth_user=_FakeUser(), mock_db=AsyncMock()))
        with patch(
            "api.v1.healing_routes.heal_selector_service",
            new_callable=AsyncMock,
            side_effect=HTTPException(status_code=404, detail="not found"),
        ):
            resp = client.post("/healing/selectors/404/heal")
        assert resp.status_code == 404


# ─── Sessions & results ───────────────────────────────────────────
class TestSessionResultRoutes:
    def test_list_sessions_200(self):
        client = TestClient(_build_app(auth_user=_FakeUser(), mock_db=AsyncMock()))
        with patch(
            "api.v1.healing_routes.list_sessions_service",
            new_callable=AsyncMock,
            return_value=[_session_dict()],
        ):
            resp = client.get("/healing/sessions")
        assert resp.status_code == 200
        assert resp.json()[0]["status"] == "success"

    def test_get_session_200(self):
        client = TestClient(_build_app(auth_user=_FakeUser(), mock_db=AsyncMock()))
        with patch(
            "api.v1.healing_routes.get_session_by_id",
            new_callable=AsyncMock,
            return_value=_session_dict(3),
        ):
            resp = client.get("/healing/sessions/3")
        assert resp.status_code == 200
        assert resp.json()["id"] == 3

    def test_list_results_with_selector_filter(self):
        client = TestClient(_build_app(auth_user=_FakeUser(), mock_db=AsyncMock()))
        with patch(
            "api.v1.healing_routes.list_results_service",
            new_callable=AsyncMock,
            return_value=[_result_dict()],
        ) as mocked:
            resp = client.get("/healing/results", params={"selector_id": 7})
        assert resp.status_code == 200
        mocked.assert_called_once()
        assert mocked.call_args.kwargs["selector_id"] == 7
