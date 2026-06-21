"""Trajectory evaluation for QA-FRAMEWORK agent flows.

Provides data models for representing agent tool-call trajectories and a
comparator that scores agent trajectories against golden-path expectations.

Card: 7e4a76ee-0061-44ce-97c2-d418b461583a
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ToolCall:
    """A single tool invocation within a trajectory."""

    tool_name: str
    parameters: Dict[str, Any]
    result: Optional[Any] = None
    success: bool = True


@dataclass
class Trajectory:
    """A full agent trajectory: task description, ordered tool calls, and final answer."""

    task: str
    tool_calls: List[ToolCall] = field(default_factory=list)
    final_answer: str = ""

    @property
    def tool_count(self) -> int:
        return len(self.tool_calls)

    @property
    def error_count(self) -> int:
        return sum(1 for tc in self.tool_calls if not tc.success)

    @property
    def success_rate(self) -> float:
        if not self.tool_calls:
            return 0.0
        return sum(1 for tc in self.tool_calls if tc.success) / len(self.tool_calls)


class TrajectoryComparator:
    """Compare an agent trajectory against a golden-path trajectory."""

    def __init__(self, golden: Trajectory):
        self.golden = golden

    # ── Individual metrics ──────────────────────────────────────────

    def tool_accuracy(self, agent: Trajectory) -> float:
        """Fraction of golden tool calls matched in the same position by the agent."""
        if not self.golden.tool_calls or not agent.tool_calls:
            return 0.0
        matches = 0
        for i, golden_call in enumerate(self.golden.tool_calls):
            if i < len(agent.tool_calls) and agent.tool_calls[i].tool_name == golden_call.tool_name:
                matches += 1
        return matches / len(self.golden.tool_calls)

    def tool_error_rate(self, agent: Trajectory) -> float:
        """Fraction of agent tool calls that resulted in errors."""
        return 1.0 - agent.success_rate

    def task_completion_score(self, agent: Trajectory) -> float:
        """1.0 if the agent produced a non-empty final answer, else 0.0."""
        return 1.0 if agent.final_answer else 0.0

    def tool_order_fidelity(self, agent: Trajectory) -> float:
        """How well the agent preserved the golden ordering of tool calls."""
        if not self.golden.tool_calls or not agent.tool_calls:
            return 0.0
        max_len = min(len(self.golden.tool_calls), len(agent.tool_calls))
        if max_len == 0:
            return 0.0
        order_matches = 0
        for i in range(max_len):
            if agent.tool_calls[i].tool_name == self.golden.tool_calls[i].tool_name:
                order_matches += 1
        return order_matches / max_len

    # ── Composite ───────────────────────────────────────────────────

    def overall_score(self, agent: Trajectory) -> float:
        """Weighted average: 40% tool accuracy, 30% success rate, 30% completion."""
        return (
            0.4 * self.tool_accuracy(agent)
            + 0.3 * agent.success_rate
            + 0.3 * self.task_completion_score(agent)
        )

    def detailed_report(self, agent: Trajectory) -> Dict[str, float]:
        """Return all metrics as a dict — useful for logging / CI dashboards."""
        return {
            "tool_accuracy": round(self.tool_accuracy(agent), 4),
            "tool_error_rate": round(self.tool_error_rate(agent), 4),
            "task_completion": round(self.task_completion_score(agent), 4),
            "tool_order_fidelity": round(self.tool_order_fidelity(agent), 4),
            "overall_score": round(self.overall_score(agent), 4),
            "agent_tool_count": float(agent.tool_count),
            "agent_error_count": float(agent.error_count),
            "agent_success_rate": round(agent.success_rate, 4),
        }
