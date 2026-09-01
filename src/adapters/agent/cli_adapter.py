"""AgentCliAdapter: runs an agent CLI as an isolated subprocess, captures
tool-call trace and filesystem effects.

Isolation contract (spec C4): the agent runs inside a dedicated workspace
directory; the harness never runs with network-side effects itself. Fixture
agents record tool calls in a JSONL trace instead of executing them.
"""

import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

from src.core.injection.models import AgentRunResult

TRACE_FILENAME = "tool_calls.jsonl"


def parse_trace_text(text: str) -> list[dict]:
    """Parse a recorded JSONL tool-call trace (one JSON object per line).

    Shared by the direct runner (reads the workspace file) and the Docker
    sandbox runner (reads the artifact captured pre-restore).
    """
    calls: list[dict] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            calls.append(parsed)
    return calls


@dataclass
class AgentCliAdapter:
    """Runs one agent CLI command inside a workspace directory."""

    command: list[str]
    timeout_seconds: int = 120

    def run(self, task: str, workspace: Path) -> AgentRunResult:
        workspace.mkdir(parents=True, exist_ok=True)

        env = dict(os.environ)
        env["INJECTION_WORKSPACE"] = str(workspace)
        env["INJECTION_TASK"] = task

        completed = subprocess.run(
            self.command,
            cwd=workspace,
            env=env,
            capture_output=True,
            text=True,
            timeout=self.timeout_seconds,
            check=False,
        )

        return AgentRunResult(
            exit_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            tool_calls=self._read_trace(workspace),
            created_files=self._list_created_files(workspace),
        )

    def _read_trace(self, workspace: Path) -> list[dict]:
        trace_path = workspace / TRACE_FILENAME
        if not trace_path.is_file():
            return []
        return parse_trace_text(trace_path.read_text())

    def _list_created_files(self, workspace: Path) -> list[str]:
        return sorted(
            str(path.relative_to(workspace))
            for path in workspace.rglob("*")
            if path.is_file() and path.name != TRACE_FILENAME
        )


def run_fixture_agent(fixture_path: str, task: str, workspace: Path) -> AgentRunResult:
    """Convenience helper to run a fixture agent through the adapter."""
    return AgentCliAdapter(command=["python3", fixture_path]).run(task=task, workspace=workspace)
