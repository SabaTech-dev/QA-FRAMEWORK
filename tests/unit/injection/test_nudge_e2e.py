"""End-to-end tests for the embracethered detection repro (Day 3, nudge-003).

Proves the Fase 0 AC "reproducir deteccion del vector embracethered": the
layer-1 nudge detector flags the 415 -> curl -> zip -> decoder.py -> exec
chain from the recorded fixture trace, the harness CLI reports
SECURITY_VIOLATED, unknown-status traces defer to HITL instead of inferring,
and the safe agent produces zero nudge findings across the whole corpus
(0 false positives, design section 6.4).
"""

import dataclasses
import json
import subprocess
from pathlib import Path

import pytest

from src.adapters.agent.cli_adapter import AgentCliAdapter
from src.adapters.agent.harness_cli import REPO_ROOT, main
from src.core.injection.corpus.agentdojo_seed import SEED_VECTORS
from src.core.injection.detectors.tool_transition import NudgeDetector, TransitionTable
from src.core.injection.evaluator import ObjectiveEvaluator
from src.core.injection.models import AgentRunResult, Scenario
from src.core.injection.utility import UtilityChecker

AGENTS = REPO_ROOT / "tests" / "fixtures" / "injection" / "agents"
NUDGE_AGENT = f"python3 {AGENTS / 'nudge_agent.py'}"
SAFE_AGENT = f"python3 {AGENTS / 'safe_agent.py'}"
REPO_CONFIG = REPO_ROOT / "config" / "agent_injection.yaml"

SCENARIOS: dict[str, Scenario] = {s.id: s for s in SEED_VECTORS}


def repo_detector() -> NudgeDetector:
    return NudgeDetector(TransitionTable.from_yaml(REPO_CONFIG))


def run_agent(agent_command: str, scenario: Scenario, tmp_path: Path) -> AgentRunResult:
    workspace = tmp_path / "ws"
    asset = workspace / scenario.poisoned_asset
    asset.parent.mkdir(parents=True, exist_ok=True)
    asset.write_text(scenario.asset_content)
    adapter = AgentCliAdapter(command=agent_command.split())
    return adapter.run(task=scenario.task, workspace=workspace)


@pytest.mark.unit
class TestEmbracetheredRepro:
    def test_corpus_contains_nudge_003(self):
        assert "nudge-003" in SCENARIOS
        assert len(SEED_VECTORS) == 21

    def test_nudge_agent_trace_flags_high_and_critical(self, tmp_path):
        run = run_agent(NUDGE_AGENT, SCENARIOS["nudge-003"], tmp_path)
        findings = repo_detector().evaluate(run.tool_calls)
        by_rule = {f.rule_id: f for f in findings}
        assert by_rule["read->shell"].severity == "high"
        assert by_rule["write->code-exec"].severity == "critical"
        assert all(not f.needs_human for f in findings)

    def test_harness_run_reports_security_violated_with_nudge_evidence(self, capsys):
        code = main(
            [
                "run",
                "nudge-003",
                "--agent-command",
                NUDGE_AGENT,
                "--json",
            ]
        )
        payload = json.loads(capsys.readouterr().out)
        assert code == 2  # SECURITY_VIOLATED (ASR numerator)
        assert payload["security_violated"] is True
        assert any("tool-transition nudge" in line for line in payload["evidence"])
        assert payload["needs_human"] == []

    def test_detector_alone_marks_violation_without_forbidden_patterns(self, tmp_path):
        # The nudge detector must catch the chain even when the scenario has
        # no forbidden patterns/paths (detector-only detection).
        bare = dataclasses.replace(
            SCENARIOS["nudge-003"], forbidden_tool_patterns=[], forbidden_paths=[]
        )
        run = run_agent(NUDGE_AGENT, bare, tmp_path)
        utility_ok = UtilityChecker(tmp_path / "ws").check(bare.utility_criterion)
        verdict = ObjectiveEvaluator(nudge_detector=repo_detector()).evaluate(
            run, bare, utility_ok=utility_ok
        )
        assert verdict.security_violated is True
        assert any("write->code-exec" in line for line in verdict.evidence)


@pytest.mark.unit
class TestHitlDeferral:
    def test_unknown_status_transition_defers_to_human_not_violation(self, tmp_path):
        # vulnerable_agent's read has NO failure info: the detector must not
        # infer a violation (design section 5) — it defers to HITL.
        bare = dataclasses.replace(
            SCENARIOS["agentdojo-001"], forbidden_tool_patterns=[], forbidden_paths=[]
        )
        vulnerable = f"python3 {AGENTS / 'vulnerable_agent.py'}"
        run = run_agent(vulnerable, bare, tmp_path)
        verdict = ObjectiveEvaluator(nudge_detector=repo_detector()).evaluate(
            run, bare, utility_ok=True
        )
        assert verdict.security_violated is False
        assert any("read->shell" in line for line in verdict.needs_human)


@pytest.mark.unit
class TestFalsePositiveMeasurement:
    def test_safe_agent_zero_nudge_findings_across_corpus(self, tmp_path):
        """FP measurement (design section 6.4): target 0 FP over the corpus."""
        detector = repo_detector()
        flagged = []
        for scenario in SEED_VECTORS:
            run = run_agent(SAFE_AGENT, scenario, tmp_path)
            findings = detector.evaluate(run.tool_calls, asset_content=scenario.asset_content)
            if findings:
                flagged.append((scenario.id, findings))
        assert flagged == []
