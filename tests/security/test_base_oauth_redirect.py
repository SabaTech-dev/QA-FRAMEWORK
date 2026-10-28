"""OAuth redirect_uri localhost carve-out tests (card e34711f3, finding M2).

M2: the carve-out was a string PREFIX (``uri.startswith("http://localhost")``),
so ``http://localhost.evil.com/callback`` (and ``http://localhostfoo/...``)
skipped allowlist validation entirely. The carve-out must be by exact
normalized hostname (``localhost``) or loopback IP literal — nothing else.
"""

import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
# base_oauth imports ``domain.auth...`` (src/ layout aliasing): make src/
# importable the same way the application runtime does.
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from src.core.security.url_validator import URLValidationError
from src.infrastructure.oauth import base_oauth


class TestLocalRedirectUriCarveout:
    """Exact-hostname carve-out semantics for local development URIs."""

    def test_exact_localhost_true(self):
        assert base_oauth._is_local_redirect_uri("http://localhost:3000/auth/x/callback") is True

    def test_mixed_case_hostname_true(self):
        assert base_oauth._is_local_redirect_uri("http://LocalHost:3000/callback") is True

    def test_loopback_ipv4_literal_true(self):
        assert base_oauth._is_local_redirect_uri("http://127.0.0.1:3000/callback") is True

    def test_loopback_ipv6_literal_true(self):
        assert base_oauth._is_local_redirect_uri("http://[::1]:3000/callback") is True

    def test_localhost_evil_com_false(self):
        assert base_oauth._is_local_redirect_uri("http://localhost.evil.com/callback") is False

    def test_localhost_prefixed_suffix_false(self):
        assert base_oauth._is_local_redirect_uri("http://localhostcms/callback") is False

    def test_public_host_false(self):
        assert base_oauth._is_local_redirect_uri("https://github.com/callback") is False


class _StubProvider(base_oauth.BaseOAuthProvider):
    """Minimal concrete provider to drive BaseOAuthProvider.get_authorization_url."""

    @property
    def name(self) -> str:
        return "stub"

    @property
    def display_name(self) -> str:
        return "Stub"

    @property
    def _authorization_url(self) -> str:
        return "https://github.com/login/oauth/authorize"

    @property
    def _token_url(self) -> str:
        return "https://github.com/login/oauth/access_token"

    def _get_authorization_params(self, state: str, redirect_uri: str) -> dict[str, str]:
        return {"client_id": "cid", "redirect_uri": redirect_uri, "state": state}

    async def _exchange_code_impl(self, code: str, redirect_uri: str):
        raise NotImplementedError

    async def _refresh_token_impl(self, refresh_token: str):
        raise NotImplementedError

    async def get_user_info(self, token):
        raise NotImplementedError


class TestGetAuthorizationUrlValidation:
    def _provider(self, redirect_uri: str) -> _StubProvider:
        return _StubProvider(client_id="cid", client_secret="sec", redirect_uri=redirect_uri)

    def test_exact_localhost_redirect_uri_still_allowed(self):
        url = asyncio.run(
            self._provider("http://localhost:3000/auth/stub/callback").get_authorization_url("s")
        )
        assert url.startswith("https://github.com/login/oauth/authorize")

    def test_localhost_evil_redirect_uri_rejected(self):
        with pytest.raises(URLValidationError):
            asyncio.run(
                self._provider("http://localhost.evil.com/callback").get_authorization_url("s")
            )

    def test_loopback_literal_redirect_uri_allowed(self):
        url = asyncio.run(
            self._provider("http://127.0.0.1:3000/callback").get_authorization_url("s")
        )
        assert url.startswith("https://github.com/login/oauth/authorize")
