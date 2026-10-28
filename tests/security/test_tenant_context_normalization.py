"""Tenant subdomain normalization tests (card e34711f3, finding L1).

L1: the Host header is attacker-controllable before the proxy; the tenant
subdomain label was extracted with no NFKC/case folding and the reserved
list was case-sensitive (``WWW`` was not treated as reserved).

Policy decision (documented in tenant_context): NFKC + lowercase only.
No punycode↔unicode translation is attempted — ``xn--`` labels stay
punycode and Unicode labels stay Unicode, so lookups fail closed against
ASCII slugs instead of silently mapping one identity onto another.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.api.middleware import tenant_context
from src.api.middleware.tenant_context import TenantContextMiddleware


def _middleware() -> TenantContextMiddleware:
    return TenantContextMiddleware(app=None, tenant_repository=None)


class TestExtractSubdomainNormalization:
    def test_uppercase_subdomain_folded(self):
        assert _middleware()._extract_subdomain("ACME.App.com:8000") == "acme"

    def test_mixed_case_reserved_label_folded(self):
        assert _middleware()._extract_subdomain("WWW.App.com") == "www"

    def test_fullwidth_subdomain_nfkc_folded(self):
        assert _middleware()._extract_subdomain("ＡＣＭＥ.app.com") == "acme"

    def test_ascii_subdomain_unchanged(self):
        assert _middleware()._extract_subdomain("acme.app.com:8000") == "acme"

    def test_plain_host_without_subdomain_is_none(self):
        assert _middleware()._extract_subdomain("app.com") is None

    def test_localhost_without_subdomain_is_none(self):
        assert _middleware()._extract_subdomain("localhost:8000") is None


class TestReservedSubdomainsConstant:
    def test_reserved_set_is_lowercase_and_exact(self):
        assert tenant_context.RESERVED_SUBDOMAINS == frozenset({"www", "api", "app"})
