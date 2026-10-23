"""TDD tests: sink integration — logger and LLM prompt scrubbing (S1)."""

import logging
import sys

from src.infrastructure.logger.logger import QALogger


class TestLoggerSink:
    def _file_content(self, tmp_path, use_json, monkeypatch):
        monkeypatch.setenv(
            "QAFW_PII_BRIDGE_COMMAND",
            f"{sys.executable} tests/security/fixtures/fake_redact_bridge.py",
        )
        log_file = tmp_path / "qa.log"
        logger = QALogger.get_logger("pii-sink-test")
        QALogger.setup_file_logging(log_file, use_json=use_json)
        logger.info("card 4111111111111111 in transcript")
        for h in logger.handlers:
            h.flush()
        return log_file.read_text()

    def test_file_log_masks_card_when_enabled(self, tmp_path, monkeypatch):
        monkeypatch.setenv("QAFW_PII_MASKING", "true")
        content = self._file_content(tmp_path, use_json=False, monkeypatch=monkeypatch)
        assert "4111111111111111" not in content
        assert "[CREDIT_CARD_1]" in content

    def test_file_log_untouched_when_disabled(self, tmp_path, monkeypatch):
        monkeypatch.delenv("QAFW_PII_MASKING", raising=False)
        content = self._file_content(tmp_path, use_json=False, monkeypatch=monkeypatch)
        assert "4111111111111111" in content


class TestLLMPromptSink:
    def test_requirement_prompt_masks_free_text_when_enabled(self, monkeypatch):
        import sys

        from src.infrastructure.test_generation.llm_adapter import LLMTestGenerator
        from src.security.pii_masking import config as cfg

        monkeypatch.setenv("QAFW_PII_MASKING", "true")
        gen = LLMTestGenerator(
            bridge_command_override=[
                sys.executable,
                "tests/security/fixtures/fake_redact_bridge.py",
            ]
        )
        prompt = gen.build_prompt_for_ingest(
            {"title": "login", "note": "Contact anna@example.com about it"}
        )
        assert "anna@example.com" not in prompt
        assert "[EMAIL_1]" in prompt

    def test_requirement_prompt_untouched_when_disabled(self, monkeypatch):
        import sys

        from src.infrastructure.test_generation.llm_adapter import LLMTestGenerator

        monkeypatch.delenv("QAFW_PII_MASKING", raising=False)
        gen = LLMTestGenerator(
            bridge_command_override=[
                sys.executable,
                "tests/security/fixtures/fake_redact_bridge.py",
            ]
        )
        text = "Contact anna@example.com about it"
        prompt = gen.build_prompt_for_ingest({"title": "login", "note": text})
        assert "anna@example.com" in prompt
