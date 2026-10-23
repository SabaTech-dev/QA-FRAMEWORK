"""TDD tests for PII masking opt-in flag (S1: DEFAULT OFF)."""

import sys


class TestOptInFlagDefaultOff:
    """S1: the masking flag is opt-in and defaults to OFF."""

    def test_default_config_is_disabled(self):
        from src.security.pii_masking.config import PiiMaskingConfig

        config = PiiMaskingConfig()
        assert config.enabled is False

    def test_default_env_flag_resolves_off(self, monkeypatch):
        monkeypatch.delenv("QAFW_PII_MASKING", raising=False)
        from src.security.pii_masking.config import PiiMaskingConfig

        assert PiiMaskingConfig.from_env().enabled is False

    def test_env_flag_enables_masking(self, monkeypatch):
        monkeypatch.setenv("QAFW_PII_MASKING", "true")
        from src.security.pii_masking.config import PiiMaskingConfig

        assert PiiMaskingConfig.from_env().enabled is True

    def test_hook_is_noop_when_disabled(self, monkeypatch):
        monkeypatch.delenv("QAFW_PII_MASKING", raising=False)
        from src.security.pii_masking.config import PiiMaskingConfig
        from src.security.pii_masking.hook import PiiMaskingHook

        hook = PiiMaskingHook(PiiMaskingConfig.from_env())
        payload = {"message": "email anna@example.com", "card": "4111111111111111"}
        masked = hook.process(payload)
        assert masked is payload or masked == payload
        assert "anna@example.com" in str(masked)

    def test_hook_masks_when_enabled(self, monkeypatch):
        monkeypatch.setenv("QAFW_PII_MASKING", "true")
        from src.security.pii_masking.config import PiiMaskingConfig
        from src.security.pii_masking.hook import PiiMaskingHook

        hook = PiiMaskingHook(PiiMaskingConfig.from_env())
        masked = hook.process({"card": "4111111111111111"})
        assert "4111111111111111" not in str(masked)
