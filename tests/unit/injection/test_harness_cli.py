"""Tests for the harness CLI entrypoint (argparse, no new dependencies)."""

import json
from pathlib import Path

import pytest

from src.adapters.agent.harness_cli import build_parser, main

FIXTURE_VULNERABLE = str(Path(__file__).resolve().parents[3] / "tests/fixtures/injection/agents/vulnerable_agent.py")
FIXTURE_SAFE = str(Path(__file__).resolve().parents[3] / "tests/fixtures/injection/agents/safe_agent.py")


@pytest.mark.unit
class TestHarnessCli:
    def test_list_shows_seed_vectors(self, capsys):
        rc = main(["list"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "agentdojo-001" in out

    def test_run_against_safe_agent_is_pass(self, tmp_path):
        rc = main(
            [
                "run",
                "agentdojo-001",
                "--agent-command",
                f"python3 {FIXTURE_SAFE}",
                "--workspace",
                str(tmp_path),
                "--json",
            ]
        )
        assert rc == 0
        # rc 0 == PASS outcome

    def test_run_against_vulnerable_agent_fails_with_nonzero_rc(self, tmp_path):
        rc = main(
            [
                "run",
                "agentdojo-001",
                "--agent-command",
                f"python3 {FIXTURE_VULNERABLE}",
                "--workspace",
                str(tmp_path),
                "--json",
            ]
        )
        assert rc != 0
        assert rc == 2  # SECURITY_VIOLATED exit code

    def test_run_json_output_is_machine_readable(self, tmp_path, capsys):
        main(
            [
                "run",
                "agentdojo-001",
                "--agent-command",
                f"python3 {FIXTURE_SAFE}",
                "--workspace",
                str(tmp_path),
                "--json",
            ]
        )
        payload = json.loads(capsys.readouterr().out)
        assert payload["scenario_id"] == "agentdojo-001"
        assert payload["outcome"] == "PASS"
        assert "utility_ok" in payload and "security_violated" in payload

    def test_unknown_scenario_exits_2_with_error(self, capsys):
        rc = main(["run", "does-not-exist", "--json"])
        assert rc == 2

    def test_parser_has_run_and_list_subcommands(self):
        parser = build_parser()
        args = parser.parse_args(["list"])
        assert args.command == "list"
        args = parser.parse_args(["run", "agentdojo-001"])
        assert args.command == "run"
        assert args.scenario == "agentdojo-001"
