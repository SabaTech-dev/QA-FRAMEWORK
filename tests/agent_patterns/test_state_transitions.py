"""State transition tests for agent testing patterns.

Validates that the agent pipeline correctly manages state across:
- Session reset
- Context switching
- Error recovery

All LLM responses are mocked — no real API calls.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest


# ---------------------------------------------------------------------------
# Helpers (self-contained)
# ---------------------------------------------------------------------------

class FakeLLMResponse:
    """Minimal stand-in for an LLM response object."""

    def __init__(self, content: str = "", *, tool_calls: list[dict] | None = None) -> None:
        self.content = content
        self.tool_calls = tool_calls or []


class AgentSession:
    """Agent pipeline with explicit session state management.

    States: IDLE → RUNNING → (DONE | ERROR) → IDLE
    """

    IDLE = "idle"
    RUNNING = "running"
    DONE = "done"
    ERROR = "error"

    def __init__(self, llm_client: MagicMock) -> None:
        self.llm = llm_client
        self.state = self.IDLE
        self.history: list[dict[str, str]] = []
        self.context: dict[str, Any] = {}
        self._error_count = 0

    # --- transitions -------------------------------------------------------

    def start(self) -> None:
        if self.state != self.IDLE:
            raise RuntimeError(f"Cannot start from state {self.state}")
        self.state = self.RUNNING

    def send(self, user_input: str) -> str:
        """Send a message. Must be in RUNNING state."""
        if self.state != self.RUNNING:
            raise RuntimeError(f"Cannot send from state {self.state}")
        try:
            self.history.append({"role": "user", "content": user_input})
            response = self.llm.chat(user_input)
            self.history.append({"role": "assistant", "content": response.content})
            self.state = self.DONE
            return response.content
        except Exception:
            self.state = self.ERROR
            self._error_count += 1
            raise

    def reset(self) -> None:
        """Clear all session state and return to IDLE."""
        self.history.clear()
        self.context.clear()
        self._error_count = 0
        self.state = self.IDLE

    def recover(self) -> None:
        """Recover from ERROR state back to IDLE."""
        if self.state != self.ERROR:
            raise RuntimeError(f"Cannot recover from state {self.state}")
        self.state = self.IDLE

    def switch_context(self, new_context: dict[str, Any]) -> None:
        """Replace the active context."""
        self.context = new_context

    @property
    def error_count(self) -> int:
        return self._error_count


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_llm() -> MagicMock:
    client = MagicMock()
    client.chat.return_value = FakeLLMResponse("Response")
    return client


@pytest.fixture
def session(mock_llm: MagicMock) -> AgentSession:
    return AgentSession(mock_llm)


# ---------------------------------------------------------------------------
# 1. Session reset
# ---------------------------------------------------------------------------

@pytest.mark.agent_patterns
class TestStateSessionReset:
    """reset() clears history, context, and returns to IDLE."""

    def test_reset_after_done(self, session: AgentSession) -> None:
        """After a completed exchange, reset returns to IDLE with empty history."""
        session.start()
        session.send("hello")
        assert session.state == AgentSession.DONE
        session.reset()
        assert session.state == AgentSession.IDLE
        assert len(session.history) == 0

    def test_reset_clears_context(self, session: AgentSession) -> None:
        """reset() wipes any stored context."""
        session.switch_context({"topic": "qa"})
        assert session.context == {"topic": "qa"}
        session.reset()
        assert session.context == {}

    def test_idempotent_reset(self, session: AgentSession) -> None:
        """Calling reset() twice is safe — no side effects."""
        session.start()
        session.send("hi")
        session.reset()
        session.reset()  # second reset should not raise
        assert session.state == AgentSession.IDLE


# ---------------------------------------------------------------------------
# 2. Context switching
# ---------------------------------------------------------------------------

@pytest.mark.agent_patterns
class TestStateContextSwitch:
    """switch_context replaces the active context without corrupting state."""

    def test_switch_context_preserves_history(self, session: AgentSession) -> None:
        """Switching context does not wipe conversation history."""
        session.start()
        session.send("first message")
        session.reset()
        session.start()
        session.switch_context({"lang": "es"})
        assert session.context == {"lang": "es"}

    def test_multiple_context_switches(self, session: AgentSession) -> None:
        """Rapid context switches keep only the latest context."""
        for ctx in [{"a": 1}, {"b": 2}, {"c": 3}]:
            session.switch_context(ctx)
        assert session.context == {"c": 3}

    def test_context_reflected_in_prompt(self, session: AgentSession, mock_llm: MagicMock) -> None:
        """The active context is available when building the next prompt."""
        session.start()
        session.switch_context({"user_role": "admin"})
        # Simulate the agent using context
        prompt = f"[{session.context}] tell me about X"
        session.send(prompt)
        call_arg = mock_llm.chat.call_args[0][0]
        assert "admin" in call_arg


# ---------------------------------------------------------------------------
# 3. Error recovery
# ---------------------------------------------------------------------------

@pytest.mark.agent_patterns
class TestStateErrorRecovery:
    """Agent transitions to ERROR on failure and recovers to IDLE."""

    def test_llm_failure_sets_error_state(self, mock_llm: MagicMock) -> None:
        """When the LLM raises, the session enters ERROR state."""
        mock_llm.chat.side_effect = RuntimeError("LLM crashed")
        session = AgentSession(mock_llm)
        session.start()
        with pytest.raises(RuntimeError):
            session.send("trigger")
        assert session.state == AgentSession.ERROR
        assert session.error_count == 1

    def test_recover_returns_to_idle(self, mock_llm: MagicMock) -> None:
        """recover() transitions ERROR → IDLE."""
        mock_llm.chat.side_effect = RuntimeError("fail")
        session = AgentSession(mock_llm)
        session.start()
        try:
            session.send("boom")
        except RuntimeError:
            pass
        assert session.state == AgentSession.ERROR
        session.recover()
        assert session.state == AgentSession.IDLE

    def test_full_recovery_cycle(self, mock_llm: MagicMock) -> None:
        """After error → recover → reset, the agent can process messages again."""
        mock_llm.chat.side_effect = RuntimeError("fail")
        session = AgentSession(mock_llm)
        session.start()
        try:
            session.send("crash")
        except RuntimeError:
            pass
        # Fix the LLM and recover
        mock_llm.chat.side_effect = None
        mock_llm.chat.return_value = FakeLLMResponse("Back online")
        session.recover()
        session.reset()
        session.start()
        result = session.send("are you there?")
        assert result == "Back online"
        assert session.state == AgentSession.DONE
        assert session.error_count == 0  # reset clears error count


# ---------------------------------------------------------------------------
# 4. Invalid transitions
# ---------------------------------------------------------------------------

@pytest.mark.agent_patterns
class TestStateInvalidTransitions:
    """Invalid state transitions raise clear errors."""

    def test_send_from_idle_raises(self, session: AgentSession) -> None:
        """send() without start() raises RuntimeError."""
        with pytest.raises(RuntimeError, match="Cannot send from state idle"):
            session.send("premature")

    def test_double_start_raises(self, session: AgentSession) -> None:
        """start() while already running raises."""
        session.start()
        with pytest.raises(RuntimeError, match="Cannot start from state running"):
            session.start()

    def test_recover_from_idle_raises(self, session: AgentSession) -> None:
        """recover() from a non-ERROR state raises."""
        with pytest.raises(RuntimeError, match="Cannot recover from state idle"):
            session.recover()
