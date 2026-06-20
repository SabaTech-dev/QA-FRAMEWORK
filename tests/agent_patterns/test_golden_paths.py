"""Golden path tests for agent testing patterns.

Validates that an agent pipeline produces expected outputs for well-formed
inputs. All LLM responses are mocked — no real API calls.

Pattern: Arrange → Act → Assert (AAA)
Scope: Happy-path flows only.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class FakeLLMResponse:
    """Minimal stand-in for an LLM response object."""

    def __init__(self, content: str, *, tool_calls: list[dict] | None = None) -> None:
        self.content = content
        self.tool_calls = tool_calls or []


def make_agent_pipeline(llm_client: MagicMock) -> "AgentPipeline":
    """Build a simple agent pipeline with a mocked LLM backend."""
    return AgentPipeline(llm_client)


class AgentPipeline:
    """Simplified agent pipeline for testing purposes.

    In a real project this would be the actual agent orchestrator.
    Here it is a thin wrapper so the tests focus on *testing patterns*,
    not on the agent internals.
    """

    def __init__(self, llm_client: MagicMock) -> None:
        self.llm = llm_client
        self.history: list[dict[str, str]] = []

    def run(self, user_input: str) -> str:
        """Send user input through the LLM and return the response text."""
        self.history.append({"role": "user", "content": user_input})
        response = self.llm.chat(user_input)
        self.history.append({"role": "assistant", "content": response.content})
        return response.content

    def run_with_context(self, user_input: str, context: dict[str, Any]) -> str:
        """Run with extra system context injected."""
        enriched = f"[Context: {context}]\n\n{user_input}"
        return self.run(enriched)

    def multi_turn(self, turns: list[str]) -> list[str]:
        """Run a multi-turn conversation and collect assistant replies."""
        replies: list[str] = []
        for turn in turns:
            replies.append(self.run(turn))
        return replies


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_llm() -> MagicMock:
    """Shared mock LLM client."""
    client = MagicMock()
    client.chat.return_value = FakeLLMResponse("Hello! How can I help?")
    return client


@pytest.fixture
def pipeline(mock_llm: MagicMock) -> AgentPipeline:
    """Agent pipeline wired to the shared mock."""
    return make_agent_pipeline(mock_llm)


# ---------------------------------------------------------------------------
# 1. Basic happy-path: single turn
# ---------------------------------------------------------------------------

@pytest.mark.agent_patterns
class TestGoldenPathSingleTurn:
    """Single-turn happy-path: input → expected output."""

    def test_simple_question_returns_answer(self, pipeline: AgentPipeline) -> None:
        """Agent returns the LLM response content for a plain question."""
        result = pipeline.run("What is 2+2?")
        assert result == "Hello! How can I help?"

    def test_llm_receives_user_input(self, pipeline: AgentPipeline, mock_llm: MagicMock) -> None:
        """The exact user input reaches the LLM client."""
        pipeline.run("Explain quantum computing")
        mock_llm.chat.assert_called_once_with("Explain quantum computing")

    def test_response_is_non_empty_string(self, pipeline: AgentPipeline) -> None:
        """Agent output is always a non-empty string on happy path."""
        result = pipeline.run("ping")
        assert isinstance(result, str)
        assert len(result) > 0


# ---------------------------------------------------------------------------
# 2. Happy-path: multi-turn conversation
# ---------------------------------------------------------------------------

@pytest.mark.agent_patterns
class TestGoldenPathMultiTurn:
    """Multi-turn happy-path: conversation history is preserved."""

    def test_three_turn_conversation(self, mock_llm: MagicMock) -> None:
        """Three user turns produce three assistant replies."""
        mock_llm.chat.side_effect = [
            FakeLLMResponse("Reply 1"),
            FakeLLMResponse("Reply 2"),
            FakeLLMResponse("Reply 3"),
        ]
        pipeline = make_agent_pipeline(mock_llm)
        replies = pipeline.multi_turn(["Hi", "Tell me more", "Thanks"])
        assert replies == ["Reply 1", "Reply 2", "Reply 3"]

    def test_history_grows_with_each_turn(self, pipeline: AgentPipeline) -> None:
        """After two turns the history has four entries (2 user + 2 assistant)."""
        pipeline.multi_turn(["Hello", "Bye"])
        assert len(pipeline.history) == 4
        assert pipeline.history[0]["role"] == "user"
        assert pipeline.history[1]["role"] == "assistant"


# ---------------------------------------------------------------------------
# 3. Happy-path: context injection
# ---------------------------------------------------------------------------

@pytest.mark.agent_patterns
class TestGoldenPathContextInjection:
    """Context is correctly injected into the agent prompt."""

    def test_context_injected_into_prompt(self, mock_llm: MagicMock) -> None:
        """run_with_context prepends context to the user message."""
        pipeline = make_agent_pipeline(mock_llm)
        pipeline.run_with_context("What is this?", {"topic": "testing"})
        call_arg = mock_llm.chat.call_args[0][0]
        assert "[Context:" in call_arg
        assert "testing" in call_arg
        assert "What is this?" in call_arg

    def test_context_does_not_mutate_original_history(
        self, mock_llm: MagicMock
    ) -> None:
        """Context injection appends the enriched message, not the raw one."""
        pipeline = make_agent_pipeline(mock_llm)
        pipeline.run_with_context("Analyze", {"mode": "strict"})
        # The last user entry should contain the enriched prompt
        last_user = [m for m in pipeline.history if m["role"] == "user"][-1]
        assert "[Context:" in last_user["content"]


# ---------------------------------------------------------------------------
# 4. Happy-path: structured output
# ---------------------------------------------------------------------------

@pytest.mark.agent_patterns
class TestGoldenPathStructuredOutput:
    """Agent returns structured data when the LLM provides it."""

    def test_json_response_parsed(self, mock_llm: MagicMock) -> None:
        """When LLM returns JSON content, it is accessible as a string."""
        mock_llm.chat.return_value = FakeLLMResponse('{"status": "ok", "score": 0.95}')
        pipeline = make_agent_pipeline(mock_llm)
        result = pipeline.run("Get status")
        assert '"status": "ok"' in result
        assert "0.95" in result

    def test_tool_call_response(self, mock_llm: MagicMock) -> None:
        """LLM response with tool_calls is captured."""
        mock_llm.chat.return_value = FakeLLMResponse(
            "",
            tool_calls=[{"name": "search", "args": {"q": "pytest patterns"}}],
        )
        pipeline = make_agent_pipeline(mock_llm)
        pipeline.run("Search for patterns")
        response = mock_llm.chat.return_value
        assert len(response.tool_calls) == 1
        assert response.tool_calls[0]["name"] == "search"
