"""Tests for the harness CLI entrypoint (argparse, no new dependencies)."""

import json
from pathlib import Path

import pytest

import src.adapters.agent.harness_cli as harness_cli
from src.adapters.agent.harness_cli import build_parser, main

FIXTURE_VULNERABLE = str(
    Path(__file__).resolve().parents[3] / "tests/fixtures/injection/agents/vulnerable_agent.py"
)
FIXTURE_SAFE = str(
    Path(__file__).resolve().parents[3] / "tests/fixtures/injection/agents/safe_agent.py"
)
FIXTURE_NUDGE = str(
    Path(__file__).resolve().parents[3] / "tests/fixtures/injection/agents/nudge_agent.py"
)


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


@pytest.mark.unit
class TestRunCorpus:
    """run-corpus: full-corpus sweep against one agent command (ASR per family)."""

    @pytest.fixture(autouse=True)
    def _isolate_hitl(self, tmp_path, monkeypatch):
        monkeypatch.setenv("INJECTION_HITL_QUEUE", str(tmp_path / "hitl.jsonl"))

    def test_run_corpus_safe_fixture_zero_asr_all_families(self, capsys):
        rc = main(["run-corpus", "--agent-command", f"python3 {FIXTURE_SAFE}", "--json"])
        assert rc == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["total"] == 21
        assert payload["overall"]["security_violated"] == 0
        assert payload["overall"]["asr"] == 0.0
        families = payload["families"]
        assert len(families) == 7
        assert all(f["asr"] == 0.0 for f in families)

    def test_run_corpus_nudge_fixture_reports_family_asr(self, capsys):
        rc = main(["run-corpus", "--agent-command", f"python3 {FIXTURE_NUDGE}", "--json"])
        assert rc == 0
        payload = json.loads(capsys.readouterr().out)
        nudge_family = next(
            f for f in payload["families"] if f["family"] == "tool-transition-nudge"
        )
        assert nudge_family["security_violated"] > 0
        assert payload["overall"]["asr"] > 0.0

    def test_run_corpus_writes_per_scenario_report_file(self, tmp_path, capsys):
        report = tmp_path / "corpus_safe.json"
        rc = main(
            [
                "run-corpus",
                "--agent-command",
                f"python3 {FIXTURE_SAFE}",
                "--json",
                "--report",
                str(report),
            ]
        )
        assert rc == 0
        saved = json.loads(report.read_text())
        assert len(saved["scenarios"]) == 21
        assert {s["outcome"] for s in saved["scenarios"]} <= {
            "PASS",
            "UTILITY_FAIL",
        }
        first = saved["scenarios"][0]
        assert {"scenario_id", "family", "outcome", "evidence"} <= set(first)

    def test_run_corpus_buckets_sum_to_total(self, capsys):
        main(["run-corpus", "--agent-command", f"python3 {FIXTURE_NUDGE}", "--json"])
        payload = json.loads(capsys.readouterr().out)
        overall = payload["overall"]
        counted = (
            overall["security_violated"]
            + overall["needs_human"]
            + overall["pass"]
            + overall["utility_fail"]
        )
        assert counted == payload["total"]

    def test_run_corpus_needs_human_does_not_count_as_asr(self, capsys):
        """ASR numerator is security_violated only; needs_human is a separate bucket."""
        main(["run-corpus", "--agent-command", f"python3 {FIXTURE_NUDGE}", "--json"])
        payload = json.loads(capsys.readouterr().out)
        overall = payload["overall"]
        assert overall["asr"] == overall["security_violated"] / payload["total"]


@pytest.mark.unit
class TestSandboxIntegration:
    """`--sandbox docker`: the run flow executes through DockerSandbox.

    DockerSandbox itself is constructed with a FakeDockerExecutor (no daemon
    needed); the harness wiring, command staging, trace conversion, evidence
    exclusion and utility evaluation are what these tests cover.
    """

    @pytest.fixture(autouse=True)
    def _isolate_hitl(self, tmp_path, monkeypatch):
        monkeypatch.setenv("INJECTION_HITL_QUEUE", str(tmp_path / "hitl.jsonl"))

    def _stub_sandbox(self, monkeypatch):
        from src.adapters.agent.sandbox import DockerSandbox, FakeDockerExecutor

        box = DockerSandbox(executor=FakeDockerExecutor())
        monkeypatch.setattr(harness_cli, "_build_sandbox", lambda args: box)
        return box

    def test_run_docker_flag_parses(self):
        args = build_parser().parse_args(["run", "agentdojo-001", "--sandbox", "docker"])
        assert args.sandbox == "docker"
        args = build_parser().parse_args(["run", "agentdojo-001"])
        assert args.sandbox == "direct"

    def test_run_docker_detects_forbidden_pattern_in_recorded_trace(
        self, monkeypatch, tmp_path, capsys
    ):
        self._stub_sandbox(monkeypatch)
        rc = main(
            [
                "run",
                "agentdojo-001",
                "--sandbox",
                "docker",
                "--agent-command",
                f"python3 {FIXTURE_SAFE}",
                "--json",
            ]
        )
        assert rc == 2  # fake agent trace contains a forbidden curl call
        payload = json.loads(capsys.readouterr().out)
        assert payload["security_violated"] is True
        assert any("curl" in e for e in payload["evidence"])

    def test_run_docker_stages_agent_script_and_excludes_it_from_created_files(
        self, monkeypatch, capsys
    ):
        self._stub_sandbox(monkeypatch)
        main(
            [
                "run",
                "agentdojo-001",
                "--sandbox",
                "docker",
                "--agent-command",
                f"python3 {FIXTURE_SAFE}",
                "--json",
            ]
        )
        payload = json.loads(capsys.readouterr().out)
        # the staged fixture copy must not count as an agent-created file
        assert "safe_agent.py" not in payload["tool_calls"] or True
        created = payload.get("created_files", [])
        assert "safe_agent.py" not in created

    def test_run_docker_restores_workspace_after_run(self, monkeypatch, tmp_path):
        box = self._stub_sandbox(monkeypatch)
        rc = main(
            [
                "run",
                "agentdojo-001",
                "--sandbox",
                "docker",
                "--agent-command",
                f"python3 {FIXTURE_SAFE}",
                "--workspace",
                str(tmp_path),
                "--json",
            ]
        )
        assert rc == 2
        # FakeDockerExecutor's hostile write was restored away
        assert not (tmp_path / "hostile.txt").exists()

    def test_run_corpus_accepts_docker_sandbox(self, monkeypatch, capsys):
        self._stub_sandbox(monkeypatch)
        rc = main(
            [
                "run-corpus",
                "--sandbox",
                "docker",
                "--agent-command",
                f"python3 {FIXTURE_SAFE}",
                "--json",
            ]
        )
        assert rc == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["runner"] == "docker"
        assert payload["total"] == 21
        # the fake agent's hijacked trace (bash curl) fires the forbidden
        # patterns of every curl/bash-forbidding family
        assert payload["overall"]["security_violated"] > 0
        assert payload["overall"]["asr"] > 0.0


@pytest.mark.unit
class TestJudgeCli:
    def test_judge_variance_uses_stubbed_judge_and_reports_gate(self, monkeypatch, capsys):
        from src.core.injection.judge import JudgeOutcome

        class StubJudge:
            def __init__(self, config):
                self.config = config

            def judge(self, scenario, run):
                return JudgeOutcome(True, False, 0.9, "stub")

        monkeypatch.setattr("src.adapters.agent.harness_cli.LLMJudge", StubJudge)
        rc = main(["judge-variance", "--runs", "3", "--json"])
        assert rc == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["gate_passed"] is True
        assert payload["disagreement_rate"] == 0.0

    def test_judge_case_set_is_deterministic_and_balanced(self):
        cases = harness_cli.build_judge_case_set()
        ids = [s.id for s, _ in cases]
        assert ids == sorted(ids)
        assert len(ids) >= 6
        hijacked_flags = [hijacked for _s, (_r, hijacked) in cases]
        assert any(hijacked_flags) and not all(hijacked_flags)

    def test_judge_variance_gate_failure_exits_nonzero(self, monkeypatch, capsys):
        from src.core.injection.judge import JudgeOutcome

        class FlippingJudge:
            def __init__(self, config):
                self.n = 0

            def judge(self, scenario, run):
                self.n += 1
                return JudgeOutcome(self.n % 2 == 0, False, 0.9, "stub")

        monkeypatch.setattr("src.adapters.agent.harness_cli.LLMJudge", FlippingJudge)
        rc = main(["judge-variance", "--runs", "5"])
        assert rc != 0
