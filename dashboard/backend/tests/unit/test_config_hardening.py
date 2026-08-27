"""Config hardening follow-ups from review R2 of card 2972521c (card f3231394).

Contracts under test:

- ENVIRONMENT is normalized (.strip().lower()) so case/space variants
  (" Production ", "PRODUCTION") cannot bypass production validation.
"""

import pytest

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
