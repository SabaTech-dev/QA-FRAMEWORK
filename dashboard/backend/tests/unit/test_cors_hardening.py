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


@pytest.fixture()
def dev_client_no_origins(monkeypatch):
    """App booted outside production with no CORS_ORIGINS (dev defaults)."""
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
    monkeypatch.setenv("ENVIRONMENT", "development")
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


def _boot_app(monkeypatch, **env):
    """Reload config+main with the given env overrides; return TestClient."""
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
    monkeypatch.setenv("SECRET_KEY", "cors-test-signing-key-0123456789abcdef")
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@h:5432/d")
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    import config as dashboard_config
    import main as dashboard_main

    importlib.reload(dashboard_config)
    app = importlib.reload(dashboard_main).app
    return TestClient(app)


class TestDevDefaults:
    def test_dev_without_cors_origins_allows_localhost(self, dev_client_no_origins):
        resp = _preflight(dev_client_no_origins, "http://localhost:3000")
        assert resp.status_code == 200
        assert resp.headers.get("access-control-allow-origin") == "http://localhost:3000"

    def test_dev_with_cors_origins_set_uses_it_exclusively(self, monkeypatch):
        client = _boot_app(
            monkeypatch,
            ENVIRONMENT="development",
            CORS_ORIGINS="https://staging.example.com",
        )
        allowed = _preflight(client, "https://staging.example.com")
        assert allowed.status_code == 200
        localhost = _preflight(client, "http://localhost:3000")
        assert "access-control-allow-origin" not in localhost.headers


class TestNegativeScenarios:
    def test_disallowed_method_preflight_rejected(self, cors_client):
        resp = cors_client.options(
            "/api/v1/health",
            headers={
                "Origin": ALLOWED,
                "Access-Control-Request-Method": "TRACE",
            },
        )
        assert resp.status_code == 400

    def test_disallowed_method_actual_request_no_allow_origin(self, cors_client):
        resp = cors_client.request("TRACE", "/api/v1/health", headers={"Origin": ALLOWED})
        assert "access-control-allow-origin" not in resp.headers

    def test_unlisted_origin_actual_request_no_allow_origin(self, cors_client):
        resp = cors_client.get("/api/v1/health", headers={"Origin": DISALLOWED})
        assert "access-control-allow-origin" not in resp.headers


class TestOriginNormalization:
    def test_trailing_slash_is_stripped(self, monkeypatch):
        client = _boot_app(
            monkeypatch,
            ENVIRONMENT="production",
            CORS_ORIGINS="https://a.example.com/, https://b.example.com/",
        )
        resp = _preflight(client, "https://a.example.com")
        assert resp.status_code == 200
        assert resp.headers.get("access-control-allow-origin") == "https://a.example.com"

    def test_trailing_slash_with_slash_is_still_rejected(self, monkeypatch):
        # The raw (malformed) origin must NOT be allowed — normalization
        # fixes the entry, it does not widen the allowlist.
        client = _boot_app(
            monkeypatch,
            ENVIRONMENT="production",
            CORS_ORIGINS="https://a.example.com/",
        )
        resp = _preflight(client, "https://a.example.com/")
        assert "access-control-allow-origin" not in resp.headers

    def test_normalization_is_idempotent(self, monkeypatch):
        client_a = _boot_app(
            monkeypatch,
            ENVIRONMENT="production",
            CORS_ORIGINS="https://a.example.com/",
        )
        resp_a = _preflight(client_a, "https://a.example.com")
        client_b = _boot_app(
            monkeypatch,
            ENVIRONMENT="production",
            CORS_ORIGINS="https://a.example.com",
        )
        resp_b = _preflight(client_b, "https://a.example.com")
        assert resp_a.status_code == resp_b.status_code == 200
        assert resp_a.headers.get("access-control-allow-origin") == resp_b.headers.get(
            "access-control-allow-origin"
        )

    def test_warn_logged_for_normalized_entries(self, monkeypatch, capsys):
        # structlog writes JSON to stdout; caplog does not reliably capture
        # the module-level boot warning, so assert on the boot output.
        _boot_app(
            monkeypatch,
            ENVIRONMENT="production",
            CORS_ORIGINS="https://a.example.com/,  , https://b.example.com",
        )
        out = capsys.readouterr().out
        warn_lines = [
            line
            for line in out.splitlines()
            if "cors_origins_normalized" in line or "CORS_ORIGINS" in line
        ]
        assert warn_lines, "expected a WARN about malformed CORS_ORIGINS entries"
        assert "https://a.example.com" in warn_lines[-1]


class TestNoHardcodedOrigins:
    def test_vercel_origin_not_allowed(self, cors_client):
        resp = _preflight(cors_client, "https://frontend-phi-three-52.vercel.app")
        assert resp.status_code == 400
        assert "access-control-allow-origin" not in resp.headers

    def test_prod_without_cors_origins_fails_closed(self, prod_client_no_origins):
        resp = _preflight(prod_client_no_origins, ALLOWED)
        assert "access-control-allow-origin" not in resp.headers
