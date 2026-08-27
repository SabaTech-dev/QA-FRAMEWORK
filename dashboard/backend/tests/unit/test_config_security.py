"""Security behaviour of dashboard/backend/config.py Settings (card 2972521c).

Incident 112853a6 (CWE-798): a committed SECRET_KEY default let anyone forge
JWTs against the public staging. Contracts under test:

- Production MUST crash at boot when JWT_SECRET_KEY / SECRET_KEY or
  DATABASE_URL are missing (_validate_production_config, fail closed).
- The development-only fallback secret must NOT be a committed constant:
  it is generated per-process (ephemeral, high-entropy, non-guessable) and
  only ever applied outside production.
"""

import pytest

from config import Settings

PROD = {"ENVIRONMENT": "production", "DATABASE_URL": "postgresql://u:p@h:5432/d"}


def _scrub(monkeypatch):
    for var in ("SECRET_KEY", "JWT_SECRET_KEY", "DATABASE_URL", "ENVIRONMENT"):
        monkeypatch.delenv(var, raising=False)


class TestProductionFailsClosed:
    def test_missing_secret_key_raises(self, monkeypatch):
        _scrub(monkeypatch)
        for k, v in PROD.items():
            monkeypatch.setenv(k, v)
        with pytest.raises(ValueError, match="JWT_SECRET_KEY"):
            Settings()

    def test_missing_database_url_raises(self, monkeypatch):
        _scrub(monkeypatch)
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("SECRET_KEY", "unit-test-signing-key-0123456789abcdef")
        with pytest.raises(ValueError, match="DATABASE_URL"):
            Settings()

    def test_with_explicit_env_boots(self, monkeypatch):
        _scrub(monkeypatch)
        expected = "unit-test-signing-key-0123456789abcdef"
        for k, v in PROD.items():
            monkeypatch.setenv(k, v)
        monkeypatch.setenv("SECRET_KEY", expected)
        settings = Settings()
        assert settings.is_production
        assert settings.secret_key.get_secret_value() == expected


class TestDevFallbackIsEphemeral:
    def test_fallback_is_random_and_long(self, monkeypatch):
        _scrub(monkeypatch)
        monkeypatch.setenv("ENVIRONMENT", "development")
        settings = Settings()
        assert settings.secret_key
        assert len(settings.secret_key.get_secret_value()) >= 32
        assert "dev-secret-key" not in settings.secret_key.get_secret_value()
        assert "dev-jwt-secret" not in settings.secret_key.get_secret_value()

    def test_fallback_differs_between_processes(self, monkeypatch):
        _scrub(monkeypatch)
        monkeypatch.setenv("ENVIRONMENT", "development")
        assert Settings().secret_key != Settings().secret_key

    def test_fallback_warns(self, monkeypatch):
        _scrub(monkeypatch)
        monkeypatch.setenv("ENVIRONMENT", "development")
        with pytest.warns(UserWarning, match="JWT_SECRET_KEY not set"):
            Settings()

    def test_explicit_dev_secret_is_preserved(self, monkeypatch):
        _scrub(monkeypatch)
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.setenv("SECRET_KEY", "explicit-dev-key-0123456789abcdef012345")
        settings = Settings()
        assert settings.secret_key.get_secret_value() == "explicit-dev-key-0123456789abcdef012345"


class TestProductionNeverFallsBack:
    def test_production_secret_is_never_replaced(self, monkeypatch):
        """The dev fallback must not touch a production instance."""
        _scrub(monkeypatch)
        expected = "prod-key-unit-test-0123456789abcdefghijklmnop"
        for k, v in PROD.items():
            monkeypatch.setenv(k, v)
        monkeypatch.setenv("SECRET_KEY", expected)
        settings = Settings()
        assert settings.secret_key.get_secret_value() == expected
