"""Unit tests for QA Visual configuration (spike conditions C1-C5)."""

import pytest

from src.infrastructure.qa_visual.config import QAVisualConfig


class TestQAVisualConfigDefaults:
    """Default values match the Fase A spike findings."""

    def test_default_model_is_experimental_id(self):
        # C4: model id monitored, overridable via config (no hardcode in callers)
        config = QAVisualConfig()
        assert config.model == "deepseek-v4-flash-vision-exp"

    def test_default_gateway_url(self):
        config = QAVisualConfig()
        assert config.gateway_url == "https://opencode.ai/zen/go/v1/chat/completions"

    def test_default_user_agent_is_browser(self):
        # C3: browser UA to avoid Cloudflare 1010
        config = QAVisualConfig()
        assert "Mozilla/5.0" in config.user_agent
        assert "Chrome" in config.user_agent

    def test_default_thinking_disabled(self):
        # C1: thinking always disabled for QA loops (4.37s vs 10-23s)
        config = QAVisualConfig()
        assert config.thinking_enabled is False

    def test_default_pricing_snapshot(self):
        # C5: pricing pin 2026-08-22 (off-peak)
        config = QAVisualConfig()
        assert config.cost_input_per_1m_usd == 0.22
        assert config.cost_output_per_1m_usd == 0.66
        assert config.pricing_snapshot_date == "2026-08-22"

    def test_default_score_threshold(self):
        config = QAVisualConfig()
        assert config.score_threshold == 80

    def test_default_max_tokens(self):
        config = QAVisualConfig()
        assert config.max_tokens == 4000

    def test_default_reports_dir(self):
        config = QAVisualConfig()
        assert config.reports_dir == "reports/qa-visual"


class TestQAVisualConfigEnv:
    """Configuration loaded from environment variables."""

    def test_model_override_via_env(self, monkeypatch):
        # C4: prepare exp->GA transition via config, never hardcode
        monkeypatch.setenv("QA_VISUAL_MODEL", "deepseek-v4-flash-vision")
        config = QAVisualConfig.from_env()
        assert config.model == "deepseek-v4-flash-vision"

    def test_threshold_override_via_env(self, monkeypatch):
        monkeypatch.setenv("QA_VISUAL_THRESHOLD_SCORE", "70")
        config = QAVisualConfig.from_env()
        assert config.score_threshold == 70

    def test_api_key_from_env(self, monkeypatch):
        monkeypatch.setenv("OPENCODE_GO_API_KEY", "test-key-123")
        config = QAVisualConfig.from_env()
        assert config.api_key == "test-key-123"

    def test_api_key_missing_is_none(self, monkeypatch):
        monkeypatch.delenv("OPENCODE_GO_API_KEY", raising=False)
        config = QAVisualConfig.from_env()
        assert config.api_key is None

    def test_from_env_uses_defaults_when_unset(self, monkeypatch):
        monkeypatch.delenv("QA_VISUAL_MODEL", raising=False)
        monkeypatch.delenv("QA_VISUAL_THRESHOLD_SCORE", raising=False)
        config = QAVisualConfig.from_env()
        assert config.model == "deepseek-v4-flash-vision-exp"
        assert config.score_threshold == 80

    def test_invalid_threshold_falls_back_to_default(self, monkeypatch):
        monkeypatch.setenv("QA_VISUAL_THRESHOLD_SCORE", "not-a-number")
        config = QAVisualConfig.from_env()
        assert config.score_threshold == 80


class TestQAVisualConfigGuards:
    """Spike guards C1/C2 enforced at config level."""

    def test_thinking_enabled_with_max_tokens_ok(self):
        config = QAVisualConfig(thinking_enabled=True, max_tokens=4000)
        assert config.thinking_enabled is True

    def test_thinking_enabled_with_low_max_tokens_raises(self):
        # C2: max_tokens >= 4000 required when thinking is ON
        with pytest.raises(ValueError, match="max_tokens"):
            QAVisualConfig(thinking_enabled=True, max_tokens=1000)

    def test_threshold_must_be_valid_score(self):
        with pytest.raises(ValueError):
            QAVisualConfig(score_threshold=150)

    def test_threshold_zero_allowed(self):
        config = QAVisualConfig(score_threshold=0)
        assert config.score_threshold == 0


class TestCostCalculation:
    """Cost tracking per analysis (C5)."""

    def test_calculate_cost(self):
        config = QAVisualConfig()
        cost = config.calculate_cost_usd(prompt_tokens=1_000_000, completion_tokens=1_000_000)
        assert cost == pytest.approx(0.22 + 0.66)

    def test_calculate_cost_small_usage(self):
        config = QAVisualConfig()
        # Typical screenshot analysis: ~1000 in / ~800 out
        cost = config.calculate_cost_usd(prompt_tokens=1000, completion_tokens=800)
        assert cost == pytest.approx((1000 * 0.22 + 800 * 0.66) / 1_000_000)

    def test_calculate_cost_zero_tokens(self):
        config = QAVisualConfig()
        assert config.calculate_cost_usd(prompt_tokens=0, completion_tokens=0) == 0.0
