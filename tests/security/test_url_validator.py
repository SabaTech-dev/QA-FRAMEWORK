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


class TestThirdPartySubdomainSuffixHardening:
    """H1 (card e34711f3): a host UNDER an allowlist base is not that base.

    ``github.com`` is in DEFAULT_ALLOWED_DOMAINS, but ``*.github.com`` (GitHub
    Pages) is registrable by anyone, so ``evil.github.com`` must NOT be
    allowed. The old parent/grandparent suffix checks granted it.
    """

    @pytest.mark.parametrize(
        "url",
        [
            "https://evil.github.com/poc",  # PoC §3 H1 — grandparent github.com
            "https://foo.api.stripe.com/v1",  # grandparent api.stripe.com
            "https://deep.sub.api.stripe.com/x",  # deeper suffix of the same base
        ],
    )
    def test_third_party_subdomain_suffix_rejected_by_default(self, url: str):
        assert is_allowed_url(url) is False

    def test_builtin_default_allowlist_never_grants_subdomain_trust(self):
        # Even if a caller passes allow_subdomains=True, the builtin default
        # list contains third-party domains: the flag must be hard-ignored.
        assert is_allowed_url("https://evil.github.com/poc", allow_subdomains=True) is False


class TestAllowlistNormalizationContract:
    """M1 (card e34711f3): allowlist and hostname must compare under the
    domain_normalizer contract (NFKC + lowercase + one root dot + IDNA),
    instead of raw string membership that silently kills valid rules."""

    def test_mixed_case_allowlist_entry_matches(self):
        assert (
            is_allowed_url("https://api.github.com/user", allowed_domains={"API.GitHub.COM"})
            is True
        )

    def test_trailing_dot_allowlist_entry_matches(self):
        assert (
            is_allowed_url("https://api.stripe.com/v1", allowed_domains={"api.stripe.com."}) is True
        )

    def test_fqdn_trailing_dot_url_matches(self):
        assert is_allowed_url("https://github.com./login") is True

    def test_fullwidth_host_matches_ascii_allowlist(self):
        # ｅｘａｍｐｌｅ.com NFKC-folds to example.com — the URL host IS example.com.
        assert (
            is_allowed_url("https://ｅｘａｍｐｌｅ.com/x", allowed_domains={"example.com"}) is True
        )

    def test_unicode_host_matches_punycode_allowlist(self):
        assert is_allowed_url("https://straße.de/x", allowed_domains={"xn--strae-oqa.de"}) is True

    def test_cyrillic_lookalike_still_rejected(self):
        # аpple.com (Cyrillic а) is a DIFFERENT domain: must not fold onto apple.com.
        assert is_allowed_url("https://аpple.com/x", allowed_domains={"apple.com"}) is False


class TestOperatorSubdomainOptIn:
    """§7.1 (card e34711f3): is_subdomain_of ONLY with operator-controlled bases.

    Subdomain semantics are opt-in per call: the operator declares the base
    zone by supplying the allowlist AND the flag. Without the flag there is
    no subdomain matching at all (fail-closed).
    """

    def test_operator_base_allows_subdomains_with_flag(self):
        assert (
            is_allowed_url(
                "https://ci.internal.corp/x",
                allowed_domains={"internal.corp"},
                allow_subdomains=True,
            )
            is True
        )

    def test_operator_label_boundary_respected(self):
        assert (
            is_allowed_url(
                "https://evilinternalcorp.com/x",
                allowed_domains={"internal.corp"},
                allow_subdomains=True,
            )
            is False
        )

    def test_without_flag_no_subdomain_match(self):
        assert (
            is_allowed_url("https://ci.internal.corp/x", allowed_domains={"internal.corp"}) is False
        )


class TestIPLiteralExplicitOverrideStillWorks:
    """IP literals cannot be IDNA-normalized; explicit overrides keep working."""

    def test_ipv6_loopback_explicit_override(self):
        assert is_allowed_url("http://[::1]:9000/api", allowed_domains={"::1"}) is True
