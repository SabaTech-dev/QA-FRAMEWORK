#!/usr/bin/env python3
"""agent-injection harness CLI (Fase 0 spike).

Commands:
    list                          list seeded scenarios
    run <scenario-id>             run one scenario against an agent command

Exit codes for `run`:
    0  PASS (utility ok, no security violation)
    1  UTILITY_FAIL (no violation, but task not completed)
    2  SECURITY_VIOLATED (attack success — ASR numerator)

No new dependencies: argparse + stdlib only (repo has no typer/click).
"""

import argparse
import json
import os
import shutil
import sys
import tempfile
from dataclasses import asdict
from pathlib import Path

from src.adapters.agent.cli_adapter import AgentCliAdapter
from src.core.injection.corpus.agentdojo_seed import SEED_VECTORS
from src.core.injection.evaluator import ObjectiveEvaluator
from src.core.injection.models import Scenario
from src.core.injection.utility import UtilityChecker

SCENARIOS: dict[str, Scenario] = {s.id: s for s in SEED_VECTORS}

EXIT_PASS = 0
EXIT_UTILITY_FAIL = 1
EXIT_SECURITY_VIOLATED = 2

REPO_ROOT = Path(__file__).resolve().parents[3]
SAFE_FIXTURE = str(REPO_ROOT / "tests" / "fixtures" / "injection" / "agents" / "safe_agent.py")
DEFAULT_AGENT = f"python3 {SAFE_FIXTURE}"
DEFAULT_TIMEOUT = 120


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agent-injection",
        description="Agent prompt-injection testing harness (QA-FRAMEWORK Fase 0)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="list seeded scenarios")

    run_p = sub.add_parser("run", help="run one scenario against an agent command")
    run_p.add_argument("scenario", help="scenario id (see `list`)")
    run_p.add_argument(
        "--agent-command",
        default=DEFAULT_AGENT,
        help="agent CLI command to execute (default: safe fixture agent)",
    )
    run_p.add_argument(
        "--workspace",
        default=None,
        help="isolated workspace dir (default: fresh temp dir, removed after run)",
    )
    run_p.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="agent timeout seconds")
    run_p.add_argument("--json", action="store_true", help="machine-readable output")
    run_p.add_argument("--keep-workspace", action="store_true", help="do not delete temp workspace")
    return parser


def cmd_list() -> int:
    for scenario in SCENARIOS.values():
        print(f"{scenario.id}  [{scenario.family}]  {scenario.name}  (OWASP {scenario.owasp_ref})")
    return EXIT_PASS


def resolve_command(command_str: str) -> list[str]:
    """Resolve relative script paths in the agent command against the repo root,
    since the agent subprocess runs with cwd set to the isolated workspace."""
    tokens = command_str.split()
    resolved: list[str] = []
    for token in tokens:
        candidate = REPO_ROOT / token
        if (
            not token.startswith("-")
            and "/" in token
            and not os.path.isabs(token)
            and candidate.exists()
        ):
            resolved.append(str(candidate))
        else:
            resolved.append(token)
    return resolved


def cmd_run(args: argparse.Namespace) -> int:
    scenario = SCENARIOS.get(args.scenario)
    if scenario is None:
        print(f"error: unknown scenario '{args.scenario}'", file=sys.stderr)
        return EXIT_SECURITY_VIOLATED

    managed_workspace = args.workspace is None
    if managed_workspace:
        workspace = Path(tempfile.mkdtemp(prefix="agent-injection-"))
    else:
        workspace = Path(args.workspace)

    try:
        adapter = AgentCliAdapter(
            command=resolve_command(args.agent_command), timeout_seconds=args.timeout
        )
        # Materialize the poisoned asset into the isolated workspace.
        from src.core.injection.corpus.agentdojo_seed import POISONED_DOCUMENT

        asset_path = workspace / scenario.poisoned_asset
        asset_path.parent.mkdir(parents=True, exist_ok=True)
        asset_path.write_text(POISONED_DOCUMENT)

        run_result = adapter.run(task=scenario.task, workspace=workspace)
        utility_ok = UtilityChecker(workspace=workspace).check(scenario.utility_criterion)
        verdict = ObjectiveEvaluator().evaluate(run_result, scenario, utility_ok)

        if args.json:
            payload = asdict(verdict)
            payload["outcome"] = verdict.outcome
            payload["tool_calls"] = run_result.tool_calls
            print(json.dumps(payload, indent=2))
        else:
            print(f"scenario:   {scenario.id} ({scenario.name})")
            print(f"outcome:    {verdict.outcome}")
            print(f"utility_ok: {verdict.utility_ok}")
            for line in verdict.evidence:
                print(f"evidence:   {line}")

        return {
            "PASS": EXIT_PASS,
            "UTILITY_FAIL": EXIT_UTILITY_FAIL,
            "SECURITY_VIOLATED": EXIT_SECURITY_VIOLATED,
        }[verdict.outcome]
    finally:
        if managed_workspace and not args.keep_workspace:
            shutil.rmtree(workspace, ignore_errors=True)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "list":
        return cmd_list()
    return cmd_run(args)


if __name__ == "__main__":
    sys.exit(main())
