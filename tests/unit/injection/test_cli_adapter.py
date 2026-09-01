"""Tests for the AgentCliAdapter: isolated subprocess execution with trace capture."""

import json
from pathlib import Path
import subprocess

import pytest

from src.adapters.agent.cli_adapter import AgentCliAdapter, run_fixture_agent


FIXTURE_VULNERABLE = str(
    Path(__file__).resolve().parents[3] / "tests/fixtures/injection/agents/vulnerable_agent.py"
)
FIXTURE_SAFE = str(
    Path(__file__).resolve().parents[3] / "tests/fixtures/injection/agents/safe_agent.py"
)
FIXTURE_DOCUMENT = "tests/fixtures/injection/assets/poisoned_document.md"


@pytest.mark.unit
class TestAgentCliAdapter:
    def test_runs_agent_in_isolated_workspace(self, tmp_path):
        adapter = AgentCliAdapter(command=["python3", FIXTURE_SAFE])
        result = adapter.run(task="Summarize the document", workspace=tmp_path)
        assert result.exit_code == 0

    def test_captures_tool_call_trace_jsonl(self, tmp_path):
        adapter = AgentCliAdapter(command=["python3", FIXTURE_VULNERABLE])
        result = adapter.run(task="Summarize the document", workspace=tmp_path)
        assert any(
            call.get("tool") == "bash" and "curl" in " ".join(map(str, call.get("args", [])))
            for call in result.tool_calls
        )

    def test_captures_created_files(self, tmp_path):
        adapter = AgentCliAdapter(command=["python3", FIXTURE_SAFE])
        result = adapter.run(task="Summarize the document", workspace=tmp_path)
        assert "output/summary.md" in result.created_files

    def test_timeout_kills_runaway_agent(self, tmp_path):
        adapter = AgentCliAdapter(
            command=["python3", "-c", "import time; time.sleep(60)"], timeout_seconds=1
        )
        with pytest.raises(subprocess.TimeoutExpired):
            adapter.run(task="t", workspace=tmp_path)

    def test_agent_receives_task_via_env(self, tmp_path):
        adapter = AgentCliAdapter(
            command=[
                "python3",
                "-c",
                "import os,pathlib;pathlib.Path('task.txt').write_text(os.environ['INJECTION_TASK'])",
            ]
        )
        result = adapter.run(task="Summarize the document", workspace=tmp_path)
        assert (tmp_path / "task.txt").read_text() == "Summarize the document"


@pytest.mark.unit
class TestTraceParsing:
    def test_missing_trace_file_yields_empty_tool_calls(self, tmp_path):
        adapter = AgentCliAdapter(command=["python3", "-c", "pass"])
        result = adapter.run(task="t", workspace=tmp_path)
        assert result.tool_calls == []

    def test_malformed_trace_lines_are_skipped(self, tmp_path):
        trace = tmp_path / "tool_calls.jsonl"
        trace.write_text('{"tool": "read", "args": ["x"]}\nNOT JSON\n')
        adapter = AgentCliAdapter(command=["python3", "-c", "pass"])
        result = adapter.run(task="t", workspace=tmp_path)
        assert len(result.tool_calls) == 1
        assert json.dumps(result.tool_calls[0])
