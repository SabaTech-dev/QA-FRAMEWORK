"""Config hardening follow-ups from review R2 of card 2972521c (card f3231394).

Contracts under test:

- ENVIRONMENT is normalized (.strip().lower()) so case/space variants
  (" Production ", "PRODUCTION") cannot bypass production validation.
"""

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
