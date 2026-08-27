"""
Unit tests for the SSRF URL allowlist validator (card 47b8ef45).

Fail-closed policy: without explicit configuration (SSRF_ALLOWED_DOMAINS env
var or an explicit ``allowed_domains`` set), loopback/local hosts must NOT be
allowed: localhost, 127.0.0.1, 0.0.0.0, [::1], ``*.localhost`` and ``.local``
mDNS-style hosts are rejected by default. Only the public domains already
listed in DEFAULT_ALLOWED_DOMAINS remain allowed, and the explicit override
mechanism keeps working for local development.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.security.url_validator import (
    DEFAULT_ALLOWED_DOMAINS,
    URLValidationError,
    is_allowed_url,
    validate_url,
)


class TestDefaultAllowlistIsFailClosed:
    """The built-in default allowlist must not contain local/loopback hosts."""

    @pytest.mark.parametrize(
        "host",
        ["localhost", "127.0.0.1", "0.0.0.0", "::1"],
    )
    def test_default_allowlist_excludes_loopback_hosts(self, host: str):
        assert host not in DEFAULT_ALLOWED_DOMAINS

    @pytest.mark.parametrize(
        "domain",
        ["github.com", "api.github.com", "accounts.google.com", "api.stripe.com"],
    )
    def test_default_allowlist_keeps_public_domains(self, domain: str):
        assert domain in DEFAULT_ALLOWED_DOMAINS


class TestLoopbackRejectedByDefault:
    """Without explicit configuration, local targets are blocked (SSRF)."""

    @pytest.mark.parametrize(
        "url",
        [
            "http://localhost:8000/callback",
            "https://localhost/admin",
            "http://127.0.0.1:9000/api",
            "http://0.0.0.0:8080/",
            "http://127.0.0.2:9000/api",  # neighbour loopback address
            "http://[::1]:9000/api",  # IPv6 loopback
            "https://[::1]/metadata",
            "http://api.localhost/v1",  # subdomain of localhost
            "http://device.local/info",  # mDNS-style .local host
            "http://service.internal:8080",  # internal-style hostname
        ],
    )
    def test_is_allowed_url_rejects_local_targets(self, url: str):
        assert is_allowed_url(url) is False

    def test_validate_url_raises_on_localhost_by_default(self):
        with pytest.raises(URLValidationError):
            validate_url("http://localhost:8000/callback")

    def test_validate_url_returns_false_on_127_0_0_1_by_default(self):
        assert validate_url("http://127.0.0.1:9000/api", raise_on_error=False) is False


class TestPublicDomainsStillAllowed:
    """The public domains kept in the default allowlist keep working."""

    @pytest.mark.parametrize(
        "url",
        [
            "https://github.com/login/oauth/authorize",
            "https://api.github.com/user",
            "https://accounts.google.com/o/oauth2/v2/auth",
            "https://api.stripe.com/v1/charges",
            "https://api.openai.com/v1/models",
        ],
    )
    def test_public_urls_allowed_by_default(self, url: str):
        assert is_allowed_url(url) is True


class TestExplicitOverrideMechanism:
    """Local development remains possible via explicit allowlist override."""

    def test_explicit_allowlist_allows_localhost(self):
        assert (
            is_allowed_url("http://localhost:8000/callback", allowed_domains={"localhost"}) is True
        )

    def test_explicit_allowlist_allows_127_0_0_1(self):
        assert is_allowed_url("http://127.0.0.1:9000/api", allowed_domains={"127.0.0.1"}) is True

    def test_validate_url_accepts_explicit_override(self):
        assert validate_url("http://localhost/x", allowed_domains={"localhost"}) is True

    def test_empty_explicit_allowlist_rejects_everything(self):
        assert is_allowed_url("https://github.com", allowed_domains=set()) is False

    def test_explicit_allowlist_does_not_leak_into_defaults(self):
        is_allowed_url("http://localhost:8000/callback", allowed_domains={"localhost"})
        assert is_allowed_url("http://localhost:8000/callback") is False
