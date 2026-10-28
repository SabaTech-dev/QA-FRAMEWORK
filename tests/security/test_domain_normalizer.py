"""Tests for the domain normalization helper (card 2eab7e70).

Hostile-domain suite for the security hardening of domain comparisons:
IDNA homographs (Cyrillic аpple.com, Greek λambda.com), Unicode format
characters (zero-width, RTLO), fullwidth compatibility forms, trailing-dot
FQDN forms, case variants, and label-boundary suffix attacks.

Run: pytest tests/security/test_domain_normalizer.py -v
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.security.domain_normalizer import (
    DomainNormalizationError,
    domains_equal,
    is_subdomain_of,
    normalize_allowlist,
    normalize_domain,
    url_hostname,
)


class TestAsciiNormalization:
    """Case, whitespace and trailing-dot forms must converge."""

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("example.com", "example.com"),
            ("Apple.COM", "apple.com"),
            ("ExAmPlE.CoM.", "example.com"),
            ("  api.stripe.com  ", "api.stripe.com"),
            ("github.com.", "github.com"),
        ],
    )
    def test_ascii_forms_converge(self, raw: str, expected: str):
        assert normalize_domain(raw) == expected

    def test_double_trailing_dot_stays_invalid(self):
        # One trailing dot = FQDN root marker; two = empty label → invalid.
        with pytest.raises(DomainNormalizationError):
            normalize_domain("example.com..")


class TestUnicodeCompatibility:
    """NFKC must fold compatibility forms to their ASCII equivalents."""

    def test_fullwidth_ascii_folds(self):
        assert normalize_domain("ｅｘａｍｐｌｅ.com") == "example.com"

    def test_fullwidth_and_ascii_are_equal(self):
        assert domains_equal("ｅｘａｍｐｌｅ.com", "example.com") is True


class TestIdnaHomographs:
    """Unicode lookalikes must NOT merge with their ASCII targets."""

    def test_cyrillic_apple_is_not_ascii_apple(self):
        # 'а' here is Cyrillic U+0430 (classic homograph attack domain).
        cyrillic = normalize_domain("аpple.com")
        assert cyrillic != "apple.com"
        assert cyrillic.startswith("xn--")

    def test_cyrillic_apple_case_variants_converge(self):
        assert normalize_domain("АPPLE.com") == normalize_domain("аpple.com")

    def test_domains_equal_rejects_homograph_pair(self):
        assert domains_equal("аpple.com", "apple.com") is False

    def test_greek_lambda_is_not_ascii_l(self):
        # λambda.com — card-mandated hostile domain.
        lam = normalize_domain("λambda.com")
        assert lam != "lambda.com"
        assert lam.startswith("xn--")
        assert normalize_domain("ΛAMBDA.com") == lam

    def test_domains_equal_rejects_lambda_pair(self):
        assert domains_equal("λambda.com", "lambda.com") is False

    def test_sharp_s_is_not_double_s(self):
        # Non-transitional IDNA2008/UTS46: ß is kept, so the two distinct
        # registered domains stay distinct (pin the canonical punycode).
        assert normalize_domain("straße.de") == "xn--strae-oqa.de"
        assert domains_equal("straße.de", "strasse.de") is False

    def test_same_unicode_domain_in_different_scripts_never_matches_ascii(self):
        for hostile in ("аpple.com", "λambda.com", "аррle.com"):  # cyrillic а / greek λ / cyrillic а+р
            assert domains_equal(hostile, "apple.com") is False


class TestFormatCharacterSpoofing:
    """Zero-width / bidi format chars must be REJECTED, not stripped."""

    @pytest.mark.parametrize(
        "hostile",
        [
            "ap\u200bple.com",  # zero-width space
            "ap\u200dple.com",  # zero-width joiner
            "ex\u00adample.com",  # soft hyphen
            "go\ufeffogle.com",  # BOM
            "\u202eevil.com",  # RTLO override (classic display spoof)
        ],
    )
    def test_format_characters_rejected(self, hostile: str):
        with pytest.raises(DomainNormalizationError):
            normalize_domain(hostile)

    def test_format_char_domain_never_equals_target(self):
        assert domains_equal("ap\u200bple.com", "apple.com") is False


class TestInvalidDomains:
    """Structurally invalid input must fail closed."""

    @pytest.mark.parametrize(
        "invalid",
        [
            "",
            "   ",
            "not a domain",  # space inside
            "example..com",  # empty label
            ".example.com",  # leading empty label
            "-bad.example.com",  # label starting with hyphen
            "a" * 64 + ".com",  # label > 63 octets
            "exa mple.com",
        ],
    )
    def test_invalid_inputs_raise(self, invalid: str):
        with pytest.raises(DomainNormalizationError):
            normalize_domain(invalid)

    @pytest.mark.parametrize("bad", [None, 123, b"apple.com", ["apple.com"]])
    def test_non_string_input_raises(self, bad):
        with pytest.raises(DomainNormalizationError):
            normalize_domain(bad)

    def test_domains_equal_fails_closed_on_invalid(self):
        assert domains_equal("apple.com", "not a domain") is False
        assert domains_equal(None, "apple.com") is False


class TestSubdomainMatching:
    """Suffix logic must respect label boundaries."""

    def test_subdomain_matches(self):
        assert is_subdomain_of("api.github.com", "github.com") is True
        assert is_subdomain_of("API.GitHub.COM.", "github.com") is True
        assert is_subdomain_of("a.b.example.com", "example.com") is True

    def test_base_is_trivially_subdomain_of_itself(self):
        assert is_subdomain_of("github.com", "github.com") is True

    def test_label_boundary_not_violated(self):
        # The attack the suffix logic must not enable:
        assert is_subdomain_of("evilstripe.com", "stripe.com") is False
        assert is_subdomain_of("notgithub.com", "github.com") is False

    def test_fails_closed_on_invalid(self):
        assert is_subdomain_of("api.github.com", "not a domain") is False

    def test_case_and_dot_insensitive(self):
        assert is_subdomain_of("API.Example.COM.", "EXAMPLE.com") is True


class TestUrlHostnameExtraction:
    """URL → normalized hostname for allowlist comparison."""

    def test_case_port_trailing_dot(self):
        # Host is api.example.com (3 labels): case folded, root dot stripped,
        # port ignored. v1 of this test wrongly expected "example.com" — the
        # helper was right; caught by Alfred review run 46/48 (card 2eab7e70).
        assert url_hostname("https://API.Example.COM.:8443/p?q=1") == "api.example.com"

    def test_userinfo_does_not_poison_hostname(self):
        assert url_hostname("https://user:pass@api.github.com/user") == "api.github.com"

    def test_unicode_host_encoded(self):
        host = url_hostname("https://аpple.com/x")
        assert host != "apple.com"
        assert host.startswith("xn--")

    def test_homograph_url_not_equal_to_allowlisted(self):
        assert domains_equal(url_hostname("https://аpple.com/x"), "apple.com") is False

    def test_no_hostname_raises(self):
        with pytest.raises(DomainNormalizationError):
            url_hostname("not a url")

    def test_non_string_raises(self):
        with pytest.raises(DomainNormalizationError):
            url_hostname(123)


class TestAllowlistNormalization:
    """Allowlist entries must be normalized; dead rules become live."""

    def test_mixed_case_and_dot_entries_converge(self):
        assert normalize_allowlist(["API.Stripe.COM.", "GitHub.com", "  appleid.apple.com "]) == {
            "api.stripe.com",
            "github.com",
            "appleid.apple.com",
        }

    def test_invalid_entries_skipped_not_fatal(self):
        assert normalize_allowlist(["github.com", "not a domain", ""]) == {"github.com"}

    def test_drop_in_comparison_contract(self):
        # Contract the future url_validator integration must satisfy:
        allowlist = normalize_allowlist({"api.stripe.com"})
        for variant in ("API.STRIPE.COM", "api.stripe.com.", "ａpi.stripe.com"):
            assert url_hostname(f"https://{variant}/v1/charges") in allowlist
        for hostile in ("аpi.stripe.com", "evil.github.com"):
            assert url_hostname(f"https://{hostile}/") not in allowlist
