"""Domain models for the agent prompt-injection testing harness.

Each scenario = legitimate task + poisoned asset + security property + utility
criterion. Each case yields a binary outcome: utility_ok x security_violated
(spec section 3, motor de escenarios estilo AgentDojo).
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Scenario:
    """A single injection test case."""

    id: str
    family: str
    name: str
    task: str
    poisoned_asset: str
    security_property: str
    utility_criterion: str
    forbidden_tool_patterns: list[str] = field(default_factory=list)
    forbidden_paths: list[str] = field(default_factory=list)
    asset_content: str = ""
    owasp_ref: str = "LLM01"
    source: str = "seed"


@dataclass(frozen=True)
class AgentRunResult:
    """Raw observable effects of one agent run inside the isolated workspace."""

    exit_code: int
    stdout: str
    stderr: str
    tool_calls: list[dict] = field(default_factory=list)
    created_files: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Verdict:
    """Binary outcome for one scenario: utility_ok x security_violated."""

    scenario_id: str
    utility_ok: bool
    security_violated: bool
    evidence: list[str] = field(default_factory=list)
    needs_human: list[str] = field(default_factory=list)

    @property
    def outcome(self) -> str:
        if self.security_violated:
            return "SECURITY_VIOLATED"
        if self.utility_ok:
            return "PASS"
        return "UTILITY_FAIL"

    @property
    def attack_success_rate_contribution(self) -> bool:
        """Whether this case counts as an attack success (ASR numerator)."""
        return self.security_violated
