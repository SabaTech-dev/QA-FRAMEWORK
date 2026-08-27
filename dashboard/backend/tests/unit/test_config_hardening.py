"""Config hardening follow-ups from review R2 of card 2972521c (card f3231394).

Contracts under test:

- ENVIRONMENT is normalized (.strip().lower()) so case/space variants
  (" Production ", "PRODUCTION") cannot bypass production validation.
"""

import os
import subprocess
import sys

import pytest
from pydantic import SecretStr

from config import Settings

PROD = {
    "ENVIRONMENT": "production",
    "DATABASE_URL": "postgresql://u:p@h:5432/d",
    "SECRET_KEY": "unit-test-signing-key-0123456789abcdef",
}


def _scrub(monkeypatch):
    for var in (
        "SECRET_KEY",
        "JWT_SECRET_KEY",
        "DATABASE_URL",
        "ENVIRONMENT",
        "REDIS_PASSWORD",
        "STRIPE_API_KEY",
        "STRIPE_WEBHOOK_SECRET",
        "GROQ_API_KEY",
        "ENABLE_BILLING",
    ):
        monkeypatch.delenv(var, raising=False)


class TestEnvironmentNormalization:
    def test_uppercase_production_is_detected_as_production(self, monkeypatch):
        _scrub(monkeypatch)
        for k, v in PROD.items():
            monkeypatch.setenv(k, v)
        monkeypatch.setenv("ENVIRONMENT", "PRODUCTION")
        assert Settings().is_production

    def test_padded_mixed_case_production_is_detected_as_production(self, monkeypatch):
        _scrub(monkeypatch)
        for k, v in PROD.items():
            monkeypatch.setenv(k, v)
        monkeypatch.setenv("ENVIRONMENT", "  Production ")
        assert Settings().is_production

    def test_case_variant_production_still_fails_closed_without_database_url(self, monkeypatch):
        """The bug this fixes: ENVIRONMENT="Production " used to skip the
        production fail-closed validation entirely (dev insecure defaults)."""
        _scrub(monkeypatch)
        monkeypatch.setenv("ENVIRONMENT", " Production\t")
        monkeypatch.setenv("SECRET_KEY", "unit-test-signing-key-0123456789abcdef")
        with pytest.raises(ValueError, match="DATABASE_URL"):
            Settings()

    def test_uppercase_development_is_detected_as_development(self, monkeypatch):
        _scrub(monkeypatch)
        monkeypatch.setenv("ENVIRONMENT", "  DEVELOPMENT ")
        settings = Settings()
        assert settings.is_development
        assert not settings.is_production

    def test_normalized_value_is_stored(self, monkeypatch):
        _scrub(monkeypatch)
        monkeypatch.setenv("ENVIRONMENT", "Staging")
        assert Settings().ENVIRONMENT == "staging"


SECRET_FIELDS = (
    ("SECRET_KEY", "SECRET_KEY", "secret_key"),
    ("REDIS_PASSWORD", "REDIS_PASSWORD", "redis_password"),
    ("STRIPE_API_KEY", "STRIPE_API_KEY", "STRIPE_API_KEY"),
    ("STRIPE_WEBHOOK_SECRET", "STRIPE_WEBHOOK_SECRET", "STRIPE_WEBHOOK_SECRET"),
    ("GROQ_API_KEY", "GROQ_API_KEY", "GROQ_API_KEY"),
)


class TestSecretsAreMasked:
    """Review R2 follow-up 3: pytest repr of Settings leaked GROQ_API_KEY."""

    def test_repr_does_not_leak_groq_api_key(self, monkeypatch):
        _scrub(monkeypatch)
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.setenv("GROQ_API_KEY", "gsk-leak-canary-abcdef0123456789")
        leaked = repr(Settings())
        assert "gsk-leak-canary-abcdef0123456789" not in leaked
        assert "GROQ_API_KEY" in leaked  # field still visible, value masked

    def test_repr_does_not_leak_any_secret(self, monkeypatch):
        _scrub(monkeypatch)
        monkeypatch.setenv("ENVIRONMENT", "development")
        canary = "canary-secret-value-0123456789abcdef"
        for env_var, _, _ in SECRET_FIELDS:
            monkeypatch.setenv(env_var, canary)
        leaked = repr(Settings())
        assert leaked.count(canary) == 0

    @pytest.mark.parametrize("env_var,attr", [(e, a) for _, e, a in SECRET_FIELDS])
    def test_secret_fields_are_secret_str(self, monkeypatch, env_var, attr):
        _scrub(monkeypatch)
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.setenv(env_var, "canary-secret-value-0123456789abcdef")
        settings = Settings()
        assert isinstance(getattr(settings, attr), SecretStr)

    def test_get_secret_value_returns_plaintext(self, monkeypatch):
        _scrub(monkeypatch)
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.setenv("GROQ_API_KEY", "gsk-plain-0123456789abcdef")
        settings = Settings()
        assert settings.GROQ_API_KEY.get_secret_value() == "gsk-plain-0123456789abcdef"


LONG_SECRET = "unit-test-signing-key-0123456789abcdef"
SHORT_SECRET = "short-secret-0123456789"


class TestMinimumSecretLength:
    """Review R2 follow-up 1: secrets shorter than 32 chars must fail closed
    in production (weak-key rejection), only when present."""

    def _prod_env(self, monkeypatch, **extra):
        _scrub(monkeypatch)
        for k, v in PROD.items():
            monkeypatch.setenv(k, v)
        for k, v in extra.items():
            monkeypatch.setenv(k, v)

    def test_short_jwt_secret_rejected_in_production(self, monkeypatch):
        self._prod_env(monkeypatch, SECRET_KEY=SHORT_SECRET)
        with pytest.raises(ValueError, match="JWT_SECRET_KEY"):
            Settings()

    def test_short_stripe_api_key_rejected_in_production(self, monkeypatch):
        self._prod_env(
            monkeypatch,
            SECRET_KEY=LONG_SECRET,
            ENABLE_BILLING="true",
            STRIPE_API_KEY=SHORT_SECRET,
            STRIPE_WEBHOOK_SECRET=LONG_SECRET,
            STRIPE_PRICE_FREE="price_unit_test",
            STRIPE_PRICE_PRO="price_unit_test",
            STRIPE_PRICE_ENTERPRISE="price_unit_test",
        )
        with pytest.raises(ValueError, match="STRIPE_API_KEY"):
            Settings()

    def test_short_webhook_secret_rejected_in_production(self, monkeypatch):
        self._prod_env(
            monkeypatch,
            SECRET_KEY=LONG_SECRET,
            ENABLE_BILLING="true",
            STRIPE_API_KEY=LONG_SECRET,
            STRIPE_WEBHOOK_SECRET=SHORT_SECRET,
            STRIPE_PRICE_FREE="price_unit_test",
            STRIPE_PRICE_PRO="price_unit_test",
            STRIPE_PRICE_ENTERPRISE="price_unit_test",
        )
        with pytest.raises(ValueError, match="STRIPE_WEBHOOK_SECRET"):
            Settings()

    def test_short_groq_api_key_rejected_in_production(self, monkeypatch):
        self._prod_env(monkeypatch, SECRET_KEY=LONG_SECRET, GROQ_API_KEY=SHORT_SECRET)
        with pytest.raises(ValueError, match="GROQ_API_KEY"):
            Settings()

    def test_short_redis_password_rejected_in_production(self, monkeypatch):
        self._prod_env(monkeypatch, SECRET_KEY=LONG_SECRET, REDIS_PASSWORD=SHORT_SECRET)
        with pytest.raises(ValueError, match="REDIS_PASSWORD"):
            Settings()

    def test_long_secrets_boot_in_production(self, monkeypatch):
        self._prod_env(
            monkeypatch,
            SECRET_KEY=LONG_SECRET,
            GROQ_API_KEY="gsk-long-0123456789abcdefghijklmnop",
            REDIS_PASSWORD="redis-long-0123456789abcdefghijkl",
        )
        settings = Settings()
        assert settings.is_production

    def test_short_secret_allowed_in_development(self, monkeypatch):
        """The 32-char floor is a production gate; dev keeps working."""
        _scrub(monkeypatch)
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.setenv("SECRET_KEY", SHORT_SECRET)
        settings = Settings()
        assert settings.secret_key.get_secret_value() == SHORT_SECRET


class TestStripePriceIdsFromEnv:
    """Review R2 follow-up 5: Stripe price IDs move to env (hygiene —
    no production price IDs committed as defaults)."""

    def test_price_ids_have_no_committed_default(self, monkeypatch):
        for var in ("STRIPE_PRICE_FREE", "STRIPE_PRICE_PRO", "STRIPE_PRICE_ENTERPRISE"):
            monkeypatch.delenv(var, raising=False)
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.delenv("SECRET_KEY", raising=False)
        monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
        settings = Settings()
        assert settings.STRIPE_PRICE_FREE is None
        assert settings.STRIPE_PRICE_PRO is None
        assert settings.STRIPE_PRICE_ENTERPRISE is None

    def test_price_ids_come_from_environment(self, monkeypatch):
        _scrub(monkeypatch)
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.setenv("STRIPE_PRICE_FREE", "price_env_free")
        monkeypatch.setenv("STRIPE_PRICE_PRO", "price_env_pro")
        monkeypatch.setenv("STRIPE_PRICE_ENTERPRISE", "price_env_ent")
        settings = Settings()
        assert settings.STRIPE_PRICE_FREE == "price_env_free"
        assert settings.STRIPE_PRICE_PRO == "price_env_pro"
        assert settings.STRIPE_PRICE_ENTERPRISE == "price_env_ent"

    def test_production_billing_requires_price_ids(self, monkeypatch):
        _scrub(monkeypatch)
        for k, v in PROD.items():
            monkeypatch.setenv(k, v)
        monkeypatch.setenv("ENABLE_BILLING", "true")
        monkeypatch.setenv("STRIPE_API_KEY", LONG_SECRET)
        monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", LONG_SECRET)
        for var in ("STRIPE_PRICE_FREE", "STRIPE_PRICE_PRO", "STRIPE_PRICE_ENTERPRISE"):
            monkeypatch.delenv(var, raising=False)
        with pytest.raises(ValueError, match="STRIPE_PRICE"):
            Settings()


class TestBrowserUseFieldsContract:
    """Review R2 follow-up 4: the duplicated BROWSER_USE_* block was removed;
    the surviving fields (incl. GROQ_API_KEY) must stay on the model."""

    def test_browser_use_and_groq_fields_exist(self):
        fields = Settings.model_fields
        for name in ("BROWSER_USE_LLM_PROVIDER", "BROWSER_USE_MODEL", "GROQ_API_KEY"):
            assert name in fields, f"missing field after dedupe: {name}"

    def test_browser_use_defaults(self, monkeypatch):
        _scrub(monkeypatch)
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.setenv("GROQ_API_KEY", "gsk-defaults-0123456789abcdef")
        settings = Settings()
        assert settings.BROWSER_USE_LLM_PROVIDER == "groq"
        assert settings.BROWSER_USE_MODEL == "llama-3.3-70b-versatile"


class TestDefaultsNotFrozenAtImport:
    """Secret defaults must be None, never os.getenv() captured at import time.

    Under pytest, `config` is imported while the developer's shell exports
    real secrets; a frozen default resurrects the import-time value even
    after the test scrubs the variable (unvalidated str, bypassing SecretStr).
    """

    _PROBE = (
        "from pydantic import SecretStr\n"
        "import os, sys; sys.path.insert(0, '.'); "
        "from config import Settings  # imported while REDIS_PASSWORD is set\n"
        "os.environ.pop('REDIS_PASSWORD', None); "
        "os.environ['ENVIRONMENT'] = 'development'; "
        "s = Settings(); "
        "print('REDIS=' + (s.redis_password.get_secret_value() "
        "if s.redis_password is not None and isinstance(s.redis_password, SecretStr) "
        "else str(s.redis_password)))"
    )

    def test_secret_default_not_captured_from_import_time_env(self):
        result = subprocess.run(
            [sys.executable, "-c", self._PROBE],
            env={**os.environ, "REDIS_PASSWORD": "frozen-canary-0123456789abcdef"},
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert result.returncode == 0, result.stderr
        assert "frozen-canary" not in result.stdout
        assert "REDIS=None" in result.stdout
