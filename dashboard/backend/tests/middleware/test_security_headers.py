"""
Tests for Security Headers Middleware — Cache-Control policy (F-5).

Covers (card d81bbdd7, OWASP API8:2023 / ASVS V14.4):
- Authenticated endpoints must respond with Cache-Control: no-store
- Public cacheable endpoints (/api/v1/billing/plans) get an explicit
  max-age policy instead of an implicit CDN default
- Existing security headers (HSTS, CSP, XFO, nosniff) stay intact
- Handler-set Cache-Control values are respected, not overwritten
"""

import pytest

pytest.importorskip("fastapi")
from fastapi import Depends, FastAPI, Response
from fastapi.testclient import TestClient

from middleware.security_headers import SecurityHeadersMiddleware


class FakeUser:
    """Minimal stand-in for models.User — the middleware is path-based,
    the dependency only proves the endpoint is authenticated."""

    id = 1
    email = "user@example.com"
    username = "user"


def _authenticated_user():
    return FakeUser()


@pytest.fixture
def app():
    """Mini-app mirroring main.py wiring: SecurityHeadersMiddleware plus
    one authenticated endpoint (/api/v1/me) and one public cacheable
    endpoint (/api/v1/billing/plans)."""
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)

    @app.get("/api/v1/me")
    async def me(current_user=Depends(_authenticated_user)):
        return {"email": current_user.email}

    @app.get("/api/v1/billing/plans")
    async def plans():
        return {"plans": []}

    @app.get("/api/v1/explicit-cache")
    async def explicit_cache(response: Response):
        response.headers["Cache-Control"] = "private, max-age=0"
        return {"ok": True}

    return app


@pytest.fixture
def client(app):
    return TestClient(app)


class TestCacheControlPolicy:
    def test_authenticated_endpoint_no_store(self, client):
        """F-5: authenticated responses (PII) must never be cacheable."""
        response = client.get("/api/v1/me")
        assert response.status_code == 200
        assert response.headers["Cache-Control"] == "no-store"

    def test_public_plans_explicit_max_age(self, client):
        """F-5: public cacheable endpoint gets an explicit short max-age."""
        response = client.get("/api/v1/billing/plans")
        assert response.status_code == 200
        cache_control = response.headers["Cache-Control"]
        assert "max-age" in cache_control
        assert cache_control == "public, max-age=300"

    def test_handler_cache_control_not_overwritten(self, client):
        """Handlers may set their own policy; middleware must respect it."""
        response = client.get("/api/v1/explicit-cache")
        assert response.status_code == 200
        assert response.headers["Cache-Control"] == "private, max-age=0"


class TestExistingHeadersRegression:
    """F-5 fix must not alter the pre-existing security headers."""

    def test_security_headers_intact_on_authenticated(self, client):
        response = client.get("/api/v1/me")
        headers = response.headers
        assert headers["X-Frame-Options"] == "DENY"
        assert headers["X-Content-Type-Options"] == "nosniff"
        assert "max-age=31536000" in headers["Strict-Transport-Security"]
        assert "default-src 'self'" in headers["Content-Security-Policy"]

    def test_security_headers_intact_on_public(self, client):
        response = client.get("/api/v1/billing/plans")
        headers = response.headers
        assert headers["X-Frame-Options"] == "DENY"
        assert headers["X-Content-Type-Options"] == "nosniff"
        assert "max-age=31536000" in headers["Strict-Transport-Security"]
        assert "default-src 'self'" in headers["Content-Security-Policy"]


class TestPublicMaxAgeConfig:
    def test_public_max_age_env_driven(self, monkeypatch):
        """CACHE_CONTROL_PUBLIC_MAX_AGE overrides the default (pattern F-1/F-2)."""
        from middleware.security_headers import cache_policy_for

        monkeypatch.setenv("CACHE_CONTROL_PUBLIC_MAX_AGE", "60")
        assert cache_policy_for("/api/v1/billing/plans") == "public, max-age=60"

    def test_default_is_no_store_for_unknown_paths(self):
        from middleware.security_headers import cache_policy_for

        assert cache_policy_for("/api/v1/executions") == "no-store"
        assert cache_policy_for("/api/v1/health") == "no-store"
        assert cache_policy_for("/") == "no-store"
