"""L-1 contract: SplitPolicy salt must be a required, non-empty per-tenant value.

Knowing the salt reveals WHICH items belong to the holdout set, so a shared
or empty default salt collapses every tenant into one namespace — a tenant
could infer the global holdout membership. These tests pin the domain
contract: no insecure default, no empty value, server-side derivation.
"""

import pytest

from src.domain.accuracy_testing.splitting import SplitPolicy


class TestSplitPolicySaltRequired:
    def test_no_default_salt_missing_raises(self):
        """SplitPolicy() without salt must fail — the default was the vuln (L-1)."""
        with pytest.raises(TypeError):
            SplitPolicy(holdout_ratio=0.2)

    def test_empty_salt_rejected(self):
        with pytest.raises(ValueError, match="[Ss]alt"):
            SplitPolicy(holdout_ratio=0.2, salt="")

    def test_whitespace_salt_rejected(self):
        with pytest.raises(ValueError, match="[Ss]alt"):
            SplitPolicy(holdout_ratio=0.2, salt="   ")

    def test_valid_salt_accepted(self):
        p = SplitPolicy(holdout_ratio=0.2, salt="tenant-42")
        assert p.salt == "tenant-42"
