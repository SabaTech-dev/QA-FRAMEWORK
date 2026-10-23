"""TDD tests for the reversible placeholder map and anonymize mode (S2)."""

import json

import pytest

from src.security.pii_masking.placeholder_map import PlaceholderMap


class TestPlaceholderMap:
    """S2: reversible map for LLM round-trips + placeholder log."""

    def test_register_and_restore_round_trip(self):
        pm = PlaceholderMap()
        pm.register("email", "anna@example.com", "[EMAIL_1]")
        pm.register("credit_card", "4111111111111111", "[CREDIT_CARD_1]")
        restored = pm.restore("Mail [EMAIL_1] about card [CREDIT_CARD_1] please")
        assert restored == "Mail anna@example.com about card 4111111111111111 please"

    def test_restore_is_idempotent_on_placeholder_free_text(self):
        pm = PlaceholderMap()
        assert pm.restore("no placeholders here") == "no placeholders here"

    def test_placeholder_log_records_entries(self):
        pm = PlaceholderMap()
        pm.register("email", "anna@example.com", "[EMAIL_1]")
        log = pm.placeholder_log()
        assert log == [{"placeholder": "[EMAIL_1]", "type": "email"}]
        # The log must never contain the original value.
        assert all("anna@example.com" not in json.dumps(e) for e in log)

    def test_anonymize_discards_map(self):
        pm = PlaceholderMap(anonymize=True)
        pm.register("email", "anna@example.com", "[EMAIL_1]")
        assert pm.placeholder_log() == []
        with pytest.raises(RuntimeError):
            pm.restore("[EMAIL_1]")
        assert pm.to_json() == "{}"

    def test_to_json_round_trip(self):
        pm = PlaceholderMap()
        pm.register("email", "anna@example.com", "[EMAIL_1]")
        pm2 = PlaceholderMap.from_json(pm.to_json())
        assert pm2.restore("[EMAIL_1]") == "anna@example.com"

    def test_unknown_placeholder_raises(self):
        pm = PlaceholderMap()
        with pytest.raises(KeyError):
            pm.restore("[UNKNOWN_1]")

    def test_map_does_not_leak_originals_in_str(self):
        pm = PlaceholderMap()
        pm.register("email", "anna@example.com", "[EMAIL_1]")
        assert "anna@example.com" not in str(pm.placeholder_log())
