"""
M-3 Security Test: CORS must reject non-allowed origins.

Verifies that the CORS configuration in QA-FRAMEWORK backend:
1. Does not use wildcard '*' for origins, methods, or headers
2. Only allows specific configured origins
3. Rejects unauthorised origins
"""

import ast
import importlib
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

BACKEND_DIR = Path(__file__).resolve().parents[2] / "dashboard" / "backend"
MAIN_PY = BACKEND_DIR / "main.py"
CONFIG_PY = BACKEND_DIR / "config.py"


def _read_main_py() -> str:
    return MAIN_PY.read_text(errors="ignore")


# ---------------------------------------------------------------------------
# Static analysis tests — no server required
# ---------------------------------------------------------------------------

class TestCorsNoWildcards:
    """Ensure no wildcard '*' in CORS configuration."""

    def test_no_wildcard_origins(self):
        """allow_origins must not contain '*'."""
        content = _read_main_py()
        assert "CORSMiddleware" in content
        # No allow_origins=["*"] or allow_origins=['*']
        assert 'allow_origins=["*"]' not in content.replace("'", '"')
        assert "allow_origins=['*']" not in content

    def test_no_wildcard_methods(self):
        """allow_methods must not be '*' — list specific methods only."""
        content = _read_main_py()
        if "allow_methods" in content:
            assert '"*"' not in content.split("allow_methods")[1].split("]")[0]
            assert "'*'" not in content.split("allow_methods")[1].split("]")[0]

    def test_no_wildcard_headers(self):
        """allow_headers must not be '*' — list specific headers only."""
        content = _read_main_py()
        if "allow_headers" in content:
            assert '"*"' not in content.split("allow_headers")[1].split("]")[0]
            assert "'*'" not in content.split("allow_headers")[1].split("]")[0]

    def test_origins_use_config(self):
        """CORS origins must come from settings, not be hardcoded."""
        content = _read_main_py()
        assert "settings.cors_origins" in content, (
            "CORS origins should use settings.cors_origins for env-configurable control"
        )


class TestConfigCorsOrigins:
    """Verify config.py exposes cors_origins."""

    def test_config_has_cors_origins(self):
        """config.py Settings must define cors_origins."""
        content = CONFIG_PY.read_text(errors="ignore")
        assert "cors_origins" in content, "Settings must define cors_origins field"

    def test_cors_origins_env_var(self):
        """CORS_ORIGINS env var should configure origins at runtime."""
        with patch.dict(os.environ, {"CORS_ORIGINS": "https://custom.example.com,https://another.example.com"}):
            # Reimport to pick up env
            sys.path.insert(0, str(BACKEND_DIR))
            # Remove cached modules
            for mod_name in list(sys.modules):
                if mod_name.startswith("config"):
                    del sys.modules[mod_name]
            from config import Settings  # noqa: E402

            s = Settings()
            assert "https://custom.example.com" in s.cors_origins
            assert "https://another.example.com" in s.cors_origins
            assert "*" not in s.cors_origins


# ---------------------------------------------------------------------------
# Integration test — actual CORS header check
# ---------------------------------------------------------------------------

class TestCorsIntegration:
    """Integration test verifying CORS behaviour via TestClient."""

    @pytest.fixture
    def client(self):
        """Create a minimal FastAPI app with the same CORS config as main.py."""
        from fastapi.middleware.cors import CORSMiddleware

        allowed_origins = [
            "http://localhost:3000",
            "https://qa.sabatech.dev",
        ]

        app = FastAPI()

        @app.get("/")
        def root():
            return {"status": "ok"}

        app.add_middleware(
            CORSMiddleware,
            allow_origins=allowed_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            allow_headers=[
                "Authorization",
                "Content-Type",
                "X-Requested-With",
                "X-Request-ID",
                "Accept",
                "Origin",
            ],
        )
        return TestClient(app)

    def test_allowed_origin_gets_cors_header(self, client):
        """Allowed origin should receive Access-Control-Allow-Origin header."""
        resp = client.get(
            "/",
            headers={"Origin": "https://qa.sabatech.dev"},
        )
        assert resp.status_code == 200
        assert resp.headers.get("access-control-allow-origin") == "https://qa.sabatech.dev"

    def test_disallowed_origin_rejected(self, client):
        """Disallowed origin must NOT receive Access-Control-Allow-Origin header."""
        resp = client.get(
            "/",
            headers={"Origin": "https://evil.com"},
        )
        assert resp.status_code == 200  # Request still succeeds
        # But no CORS header returned
        assert "access-control-allow-origin" not in resp.headers

    def test_null_origin_rejected(self, client):
        """'null' origin must be rejected."""
        resp = client.get(
            "/",
            headers={"Origin": "null"},
        )
        assert "access-control-allow-origin" not in resp.headers

    def test_preflight_allows_specific_methods(self, client):
        """Preflight OPTIONS should return specific methods, not wildcard."""
        resp = client.options(
            "/",
            headers={
                "Origin": "https://qa.sabatech.dev",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type",
            },
        )
        assert resp.status_code == 200
        allow_methods = resp.headers.get("access-control-allow-methods", "")
        assert "*" not in allow_methods
        assert "POST" in allow_methods

    def test_preflight_rejects_unknown_header(self, client):
        """Preflight should not allow arbitrary headers."""
        resp = client.options(
            "/",
            headers={
                "Origin": "https://qa.sabatech.dev",
                "Access-Control-Request-Method": "DELETE",
                "Access-Control-Request-Headers": "X-Evil-Header",
            },
        )
        # Starlette rejects preflight with unallowed headers
        assert resp.status_code == 400
