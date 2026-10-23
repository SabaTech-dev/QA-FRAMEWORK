"""TDD tests for the Node redact bridge protocol (S4)."""

import pathlib
import subprocess
import sys

import pytest

from src.security.pii_masking.redact_bridge import RedactBridge

FAKE_BRIDGE = pathlib.Path(__file__).parent / "fixtures" / "fake_redact_bridge.py"


class FakeBridge(RedactBridge):
    """Bridge that uses a deterministic python stand-in for the SDK."""

    def __init__(self) -> None:
        super().__init__(bridge_command=[sys.executable, str(FAKE_BRIDGE)])


class TestBridgeProtocol:
    def test_redact_text_replaces_free_text_pii(self):
        with FakeBridge() as bridge:
            out, items = bridge.redact_text("Email Anna at anna@example.com.")
            assert "anna@example.com" not in out
            assert "[EMAIL_1]" in out
            assert items and items[0]["label"] == "email"

    def test_bridge_recovers_after_bad_line(self):
        with FakeBridge() as bridge:
            bridge.redact_text("first")
            out, _ = bridge.redact_text("Email Anna at anna@example.com.")
            assert "anna@example.com" not in out

    def test_context_manager_terminates_process(self):
        bridge = FakeBridge()
        with bridge:
            proc = bridge._proc
            assert proc is not None and proc.poll() is None
        assert proc is not None and proc.poll() is not None

    def test_missing_bridge_command_raises(self):
        bridge = RedactBridge(bridge_command=["definitely-not-a-real-binary-xyz"])
        with pytest.raises(RuntimeError):
            with bridge:
                bridge.redact_text("hello")


class TestHookFreeText:
    """S4/S1/S2: the hook routes free text through the bridge."""

    def _hook(self, monkeypatch, anonymize=False):
        from src.security.pii_masking.config import MaskingMode, PiiMaskingConfig
        from src.security.pii_masking.hook import PiiMaskingHook

        mode = MaskingMode.ANONYMIZE if anonymize else MaskingMode.MASK
        config = PiiMaskingConfig(
            enabled=True, mode=mode, bridge_command=[sys.executable, str(FAKE_BRIDGE)]
        )
        return PiiMaskingHook(config)

    def test_hook_masks_free_text_and_keeps_map(self, monkeypatch):
        hook = self._hook(monkeypatch)
        result = hook.process({"note": "Email Anna at anna@example.com."})
        assert "anna@example.com" not in result["note"]
        assert hook.placeholder_map is not None
        restored = hook.placeholder_map.restore(result["note"])
        assert "anna@example.com" in restored

    def test_hook_anonymize_discards_map(self, monkeypatch):
        hook = self._hook(monkeypatch, anonymize=True)
        result = hook.process({"note": "Email Anna at anna@example.com."})
        assert "anna@example.com" not in result["note"]
        assert hook.placeholder_map is not None
        assert hook.placeholder_map.placeholder_log() == []
        with pytest.raises(RuntimeError):
            hook.placeholder_map.restore(result["note"])

    def test_hook_structured_fields_use_regex_not_bridge(self, monkeypatch):
        hook = self._hook(monkeypatch)
        result = hook.process({"card": "4111111111111111"})
        assert "4111111111111111" not in result["card"]
        assert "[CREDIT_CARD_1]" in result["card"]
