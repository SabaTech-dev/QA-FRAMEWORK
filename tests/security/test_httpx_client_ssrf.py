"""SSRF regression tests for HTTPXClient (card e34711f3, findings H2 + M1).

H2: scheme detection in ``_resolve_url`` was case-sensitive
(``url.startswith(("http://", "https://"))``), so ``"HTTPS://evil.com/x"``
looked like a relative path: the validator approved the *base host* URL while
httpx (RFC 3986 — schemes are case-insensitive) sent the request to
evil.com. The validator checked one URL and the client requested another.

M1: ``SSRF_ALLOWED_DOMAINS`` env entries were used raw (strip only), so
mixed-case/Unicode/trailing-dot entries never matched any hostname.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.adapters.http.httpx_client import HTTPXClient, _load_allowed_domains
from src.core.security.url_validator import DEFAULT_ALLOWED_DOMAINS, URLValidationError


def _client(**kwargs) -> HTTPXClient:
    defaults: dict = {"base_url": "https://api.github.com", "ssrf_enabled": True}
    defaults.update(kwargs)
    return HTTPXClient(**defaults)


class TestResolveUrlSchemeCaseInsensitive:
    """H2 root cause: absolute-URL detection must not depend on scheme case."""

    def test_uppercase_scheme_is_absolute_not_relative(self):
        client = _client(ssrf_enabled=False)
        assert client._resolve_url("HTTPS://httpbin.org/get") == "HTTPS://httpbin.org/get"

    def test_mixed_case_scheme_is_absolute_not_relative(self):
        client = _client(ssrf_enabled=False)
        assert client._resolve_url("HtTpS://httpbin.org/get") == "HtTpS://httpbin.org/get"

    def test_relative_path_still_joins_base(self):
        client = _client(ssrf_enabled=False)
        assert client._resolve_url("/repos/foo") == "https://api.github.com/repos/foo"

    def test_lowercase_absolute_unchanged(self):
        client = _client(ssrf_enabled=False)
        assert client._resolve_url("https://httpbin.org/get") == "https://httpbin.org/get"


class TestSchemeCaseBypassBlocked:
    """The URL that httpx will really request is the one that gets validated."""

    def test_uppercase_scheme_external_target_blocked(self):
        client = _client()
        with pytest.raises(URLValidationError):
            client._validate_url("HTTPS://httpbin.org/get")

    def test_uppercase_scheme_subdomain_spoof_blocked(self):
        client = _client()
        with pytest.raises(URLValidationError):
            client._validate_url("HTTPS://evil.github.com/poc")

    def test_allowed_absolute_lowercase_still_passes(self):
        client = _client()  # must not raise
        client._validate_url("https://api.github.com/user")


class TestDefaultAllowlistNoSubdomainTrustViaClient:
    """H1 through the client path: defaults carry no subdomain trust."""

    def test_default_allowlist_grandparent_bypass_blocked(self):
        client = _client()
        with pytest.raises(URLValidationError):
            client._validate_url("https://evil.github.com/poc")


class TestEnvAllowlistNormalization:
    """M1: env entries are normalized with the domain_normalizer contract."""

    def test_env_entries_normalized(self, monkeypatch):
        monkeypatch.setenv("SSRF_ALLOWED_DOMAINS", "API.GitHub.COM, stripe.com., ,api.openai.com")
        assert _load_allowed_domains() == {"api.github.com", "stripe.com", "api.openai.com"}

    def test_env_fullwidth_entry_normalized(self, monkeypatch):
        monkeypatch.setenv("SSRF_ALLOWED_DOMAINS", "ｅｘａｍｐｌｅ.com")
        assert _load_allowed_domains() == {"example.com"}

    def test_no_env_returns_builtin_defaults(self, monkeypatch):
        monkeypatch.delenv("SSRF_ALLOWED_DOMAINS", raising=False)
        assert _load_allowed_domains() == DEFAULT_ALLOWED_DOMAINS
