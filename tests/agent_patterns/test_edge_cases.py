"""Edge case tests for agent testing patterns.

Validates agent pipeline behaviour with adversarial and boundary inputs:
- Empty / whitespace inputs
- Very long inputs
- Special characters and Unicode
- Rate-limiting, timeouts, and API errors

All LLM responses are mocked — no real API calls.
"""

from __future__ import annotations

import time
from typing import Any
from unittest.mock import MagicMock, patch, PropertyMock

import pytest


# ---------------------------------------------------------------------------
# Helpers (mirrors test_golden_paths — kept self-contained on purpose)
# ---------------------------------------------------------------------------

class FakeLLMResponse:
    """Minimal stand-in for an LLM response object."""

    def __init__(self, content: str = "", *, tool_calls: list[dict] | None = None) -> None:
        self.content = content
        self.tool_calls = tool_calls or []


class AgentPipeline:
    """Simplified agent pipeline for testing purposes."""

    MAX_INPUT_LENGTH = 10_000

    def __init__(self, llm_client: MagicMock) -> None:
        self.llm = llm_client
        self.history: list[dict[str, str]] = []
        self._call_count = 0

    def run(self, user_input: str) -> str:
        self._call_count += 1
        if self._call_count > 5:
            raise RuntimeError("Rate limit exceeded")
        if not isinstance(user_input, str):
            raise TypeError("Input must be a string")
        if len(user_input) > self.MAX_INPUT_LENGTH:
            raise ValueError(f"Input exceeds max length of {self.MAX_INPUT_LENGTH}")
        self.history.append({"role": "user", "content": user_input})
        response = self.llm.chat(user_input)
        self.history.append({"role": "assistant", "content": response.content})
        return response.content

    def reset(self) -> None:
        self.history.clear()
        self._call_count = 0


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_llm() -> MagicMock:
    """Shared mock LLM client."""
    client = MagicMock()
    client.chat.return_value = FakeLLMResponse("OK")
    return client


@pytest.fixture
def pipeline(mock_llm: MagicMock) -> AgentPipeline:
    return AgentPipeline(mock_llm)


# ---------------------------------------------------------------------------
# 1. Empty and whitespace inputs
# ---------------------------------------------------------------------------

@pytest.mark.agent_patterns
class TestEdgeCaseEmptyInput:
    """Agent handles empty / whitespace-only input gracefully."""

    def test_empty_string_input(self, pipeline: AgentPipeline, mock_llm: MagicMock) -> None:
        """Empty string is forwarded to the LLM — the agent does not crash."""
        result = pipeline.run("")
        mock_llm.chat.assert_called_once_with("")
        assert result == "OK"

    def test_whitespace_only_input(self, pipeline: AgentPipeline) -> None:
        """Whitespace-only input is treated as valid text."""
        result = pipeline.run("   \t\n  ")
        assert result == "OK"

    def test_none_input_raises_type_error(self, pipeline: AgentPipeline) -> None:
        """Non-string input (None) raises TypeError immediately."""
        with pytest.raises(TypeError, match="must be a string"):
            pipeline.run(None)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# 2. Very long inputs
# ---------------------------------------------------------------------------

@pytest.mark.agent_patterns
class TestEdgeCaseLongInput:
    """Agent enforces input length boundaries."""

    def test_exactly_max_length(self, pipeline: AgentPipeline, mock_llm: MagicMock) -> None:
        """Input at exactly MAX_INPUT_LENGTH is accepted."""
        payload = "a" * AgentPipeline.MAX_INPUT_LENGTH
        result = pipeline.run(payload)
        assert result == "OK"
        mock_llm.chat.assert_called_once_with(payload)

    def test_exceeding_max_length_raises(self, pipeline: AgentPipeline) -> None:
        """Input one char over the limit raises ValueError."""
        payload = "a" * (AgentPipeline.MAX_INPUT_LENGTH + 1)
        with pytest.raises(ValueError, match="exceeds max length"):
            pipeline.run(payload)


# ---------------------------------------------------------------------------
# 3. Special characters and Unicode
# ---------------------------------------------------------------------------

@pytest.mark.agent_patterns
class TestEdgeCaseSpecialChars:
    """Agent preserves special characters and Unicode without corruption."""

    @pytest.mark.parametrize(
        "label,payload",
        [
            ("emoji", "Hello 🌍🚀 pytest"),
            ("chinese", "你好世界"),
            ("arabic", "اختبار العميل"),
            ("mixed_scripts", "English — español — Deutsch — français"),
            ("control_chars", "Line1\nLine2\tTabbed\rCR"),
            ("sql_injection", "'); DROP TABLE users; --"),
            ("xss_attempt", "<script>alert('xss')</script>"),
            ("path_traversal", "../../../etc/passwd"),
        ],
        ids=["emoji", "chinese", "arabic", "mixed", "control", "sqli", "xss", "traversal"],
    )
    def test_special_content_preserved(
        self, pipeline: AgentPipeline, mock_llm: MagicMock, label: str, payload: str
    ) -> None:
        """Payloads with special chars reach the LLM verbatim."""
        pipeline.run(payload)
        actual = mock_llm.chat.call_args[0][0]
        assert actual == payload

    def test_null_byte_in_input(self, pipeline: AgentPipeline, mock_llm: MagicMock) -> None:
        """Null bytes are forwarded as-is (agent does not strip them)."""
        payload = "before\x00after"
        pipeline.run(payload)
        assert mock_llm.chat.call_args[0][0] == payload


# ---------------------------------------------------------------------------
# 4. Rate limiting
# ---------------------------------------------------------------------------

@pytest.mark.agent_patterns
class TestEdgeCaseRateLimit:
    """Agent enforces a call-rate limit."""

    def test_sixth_call_raises_rate_limit(self, pipeline: AgentPipeline) -> None:
        """After 5 calls the 6th raises RuntimeError."""
        for _ in range(5):
            pipeline.run("ok")
        with pytest.raises(RuntimeError, match="Rate limit exceeded"):
            pipeline.run("one more")

    def test_reset_clears_rate_counter(self, pipeline: AgentPipeline) -> None:
        """reset() zeroes the call counter so calls succeed again."""
        for _ in range(5):
            pipeline.run("ok")
        pipeline.reset()
        # Should not raise after reset
        result = pipeline.run("fresh start")
        assert result == "OK"


# ---------------------------------------------------------------------------
# 5. Timeouts and API errors
# ---------------------------------------------------------------------------

@pytest.mark.agent_patterns
class TestEdgeCaseApiErrors:
    """Agent surfaces LLM timeout and generic API errors."""

    def test_llm_timeout_raises(self, mock_llm: MagicMock) -> None:
        """Timeout exception from the LLM client propagates."""
        mock_llm.chat.side_effect = TimeoutError("LLM timed out after 30s")
        pipeline = AgentPipeline(mock_llm)
        with pytest.raises(TimeoutError, match="timed out"):
            pipeline.run("slow query")

    def test_llm_connection_error_raises(self, mock_llm: MagicMock) -> None:
        """Connection error from the LLM client propagates."""
        mock_llm.chat.side_effect = ConnectionError("Service unavailable")
        pipeline = AgentPipeline(mock_llm)
        with pytest.raises(ConnectionError, match="Service unavailable"):
            pipeline.run("hello")

    def test_llm_generic_exception_propagates(self, mock_llm: MagicMock) -> None:
        """Any unexpected exception from the LLM propagates unchanged."""
        mock_llm.chat.side_effect = RuntimeError("Internal LLM error")
        pipeline = AgentPipeline(mock_llm)
        with pytest.raises(RuntimeError, match="Internal LLM error"):
            pipeline.run("trigger bug")
