"""CORS hardening F-8 (card 2834cce9, audit d4ff9268).

main.py mounted CORSMiddleware with allow_credentials=True,
allow_methods=["*"], allow_headers=["*"] and a hardcoded vercel origin.
Auth is Bearer-based (no cookies), so credentials are unnecessary and a
wildcard-tolerant policy only invites regressions. Contract:

- allow_credentials=False: no Access-Control-Allow-Credentials header,
  neither on preflight responses nor on actual responses;
- explicit methods/headers (Authorization, Content-Type);
- origins come from CORS_ORIGINS (comma-separated env var); the dev
  localhost defaults only apply when ENVIRONMENT != production;
- no hardcoded vercel origin: a production boot without CORS_ORIGINS
  gets an empty allowlist (fail closed), not a stale frontend.
"""

import importlib

import pytest
from fastapi.testclient import TestClient

ALLOWED = "https://qa.example.com"
DISALLOWED = "https://evil.example.com"


@pytest.fixture()
def cors_client(monkeypatch):
    """App booted in production with CORS_ORIGINS=ALLOWED (hermetic)."""
    for var in (
        "REDIS_PASSWORD",
        "STRIPE_API_KEY",
        "STRIPE_WEBHOOK_SECRET",
        "GROQ_API_KEY",
        "ENABLE_BILLING",
    ):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("SECRET_KEY", "cors-test-signing-key-0123456789abcdef")
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@h:5432/d")
    monkeypatch.setenv("CORS_ORIGINS", ALLOWED)
    import config as dashboard_config
    import main as dashboard_main

    importlib.reload(dashboard_config)
    app = importlib.reload(dashboard_main).app
    yield TestClient(app)
    monkeypatch.undo()
    importlib.reload(dashboard_config)
    importlib.reload(dashboard_main)


@pytest.fixture()
def prod_client_no_origins(monkeypatch):
    """App booted in production with no CORS_ORIGINS (fail closed)."""
    for var in (
        "REDIS_PASSWORD",
        "STRIPE_API_KEY",
        "STRIPE_WEBHOOK_SECRET",
        "GROQ_API_KEY",
        "ENABLE_BILLING",
        "CORS_ORIGINS",
        "FRONTEND_URL",
    ):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("SECRET_KEY", "cors-test-signing-key-0123456789abcdef")
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@h:5432/d")
    import config as dashboard_config
    import main as dashboard_main

    importlib.reload(dashboard_config)
    app = importlib.reload(dashboard_main).app
    yield TestClient(app)
    monkeypatch.undo()
    importlib.reload(dashboard_config)
    importlib.reload(dashboard_main)


def _preflight(client, origin):
    return client.options(
        "/api/v1/health",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization, content-type",
        },
    )


class TestPreflightAllowedOrigin:
    def test_preflight_200(self, cors_client):
        assert _preflight(cors_client, ALLOWED).status_code == 200

    def test_no_credentials_header_on_preflight(self, cors_client):
        resp = _preflight(cors_client, ALLOWED)
        assert "access-control-allow-credentials" not in resp.headers

    def test_explicit_allow_headers(self, cors_client):
        resp = _preflight(cors_client, ALLOWED)
        allowed = resp.headers.get("access-control-allow-headers", "")
        assert "authorization" in allowed.lower()
        assert "content-type" in allowed.lower()

    def test_explicit_allow_methods(self, cors_client):
        resp = _preflight(cors_client, ALLOWED)
        assert "*" not in resp.headers.get("access-control-allow-methods", "")


class TestDisallowedOrigin:
    def test_preflight_denied(self, cors_client):
        resp = _preflight(cors_client, DISALLOWED)
        assert resp.status_code == 400
        assert "access-control-allow-origin" not in resp.headers

    def test_actual_request_no_allow_origin(self, cors_client):
        resp = cors_client.get("/health", headers={"Origin": DISALLOWED})
        assert "access-control-allow-origin" not in resp.headers


class TestNoCredentialsAnywhere:
    def test_actual_request_no_credentials_header(self, cors_client):
        resp = cors_client.get("/health", headers={"Origin": ALLOWED})
        assert "access-control-allow-credentials" not in resp.headers


class TestNoHardcodedOrigins:
    def test_vercel_origin_not_allowed(self, cors_client):
        resp = _preflight(cors_client, "https://frontend-phi-three-52.vercel.app")
        assert resp.status_code == 400
        assert "access-control-allow-origin" not in resp.headers

    def test_prod_without_cors_origins_fails_closed(self, prod_client_no_origins):
        resp = _preflight(prod_client_no_origins, ALLOWED)
        assert "access-control-allow-origin" not in resp.headers
