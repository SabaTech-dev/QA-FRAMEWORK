"""Unittests para el módulo de Playwright Test Agents.

Playwright Test Agents (``npx playwright init-agents``) define 3 agentes:
- planner: genera escenarios de test desde requisitos
- generator: crea código Playwright ejecutable
- healer: auto-repara selectores rotos por cambios del DOM

Este módulo Python expone las definiciones de los agentes, valida specs
TypeScript (sintácticamente) y construye los comandos ``npx`` para
orquestarlos. Los tests son herméticos (no arrancan navegador).
"""

from __future__ import annotations

import textwrap
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from agentic_qa.playwright_agents import (
    AgentRole,
    AGENTS,
    get_agent,
    validate_spec_file,
    SpecValidationError,
    build_init_agents_command,
    build_test_command,
    run_playwright_spec,
)


# ─────────────────────────── AgentSpec ──────────────────────────────
class TestAgentSpec:
    def test_agents_registry_has_three_roles(self) -> None:
        assert len(AGENTS) == 3
        roles = {a.role for a in AGENTS}
        assert roles == {AgentRole.PLANNER, AgentRole.GENERATOR, AgentRole.HEALER}

    def test_each_agent_has_non_empty_name_and_description(self) -> None:
        for agent in AGENTS:
            assert agent.name, f"{agent} sin nombre"
            assert agent.description, f"{agent} sin descripción"
            assert agent.loop in {"opencode", "none"}

    def test_get_agent_by_role(self) -> None:
        planner = get_agent(AgentRole.PLANNER)
        assert planner.role == AgentRole.PLANNER
        healer = get_agent(AgentRole.HEALER)
        assert healer.role == AgentRole.HEALER

    def test_get_agent_unknown_role_raises(self) -> None:
        with pytest.raises(KeyError):
            get_agent("not-a-role")  # type: ignore[arg-type]

    def test_agent_to_dict_roundtrip(self) -> None:
        agent = get_agent(AgentRole.GENERATOR)
        d = agent.to_dict()
        assert d["role"] == "generator"
        assert "name" in d and "description" in d and "loop" in d


# ──────────────────────── validate_spec_file ────────────────────────
class TestValidateSpecFile:
    def test_valid_spec_passes(self, tmp_path: Path) -> None:
        spec = tmp_path / "health.spec.ts"
        spec.write_text(
            textwrap.dedent(
                """
                import { test, expect } from '@playwright/test';
                test('health', async ({ request }) => {
                  const res = await request.get('/health/live');
                  expect(res.status()).toBe(200);
                });
                """
            )
        )
        # No lanza
        validate_spec_file(spec)

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(SpecValidationError, match="no existe"):
            validate_spec_file(tmp_path / "missing.spec.ts")

    def test_wrong_extension_raises(self, tmp_path: Path) -> None:
        spec = tmp_path / "spec.js"
        spec.write_text("test('x', () => 1)")
        with pytest.raises(SpecValidationError, match="extensión"):
            validate_spec_file(spec)

    def test_empty_spec_raises(self, tmp_path: Path) -> None:
        spec = tmp_path / "empty.spec.ts"
        spec.write_text("")
        with pytest.raises(SpecValidationError, match="vacío"):
            validate_spec_file(spec)

    def test_spec_without_playwright_import_raises(self, tmp_path: Path) -> None:
        spec = tmp_path / "noimport.spec.ts"
        spec.write_text("test('x', () => { expect(1).toBe(1); });")
        with pytest.raises(SpecValidationError, match="@playwright/test"):
            validate_spec_file(spec)

    def test_spec_without_test_call_raises(self, tmp_path: Path) -> None:
        spec = tmp_path / "notest.spec.ts"
        spec.write_text("import { expect } from '@playwright/test';\nexpect(1).toBe(1);\n")
        with pytest.raises(SpecValidationError, match="test\\("):
            validate_spec_file(spec)


# ──────────────────────── Command builders ─────────────────────────
class TestCommandBuilders:
    def test_init_agents_command_uses_official_subcommand(self) -> None:
        cmd = build_init_agents_command(loop="opencode")
        assert "npx" in cmd[0]
        assert "playwright" in cmd
        assert "init-agents" in cmd
        assert "--loop" in cmd
        assert "opencode" in cmd

    def test_init_agents_default_loop_is_opencode(self) -> None:
        cmd = build_init_agents_command()
        assert "--loop" in cmd
        idx = cmd.index("--loop")
        assert cmd[idx + 1] == "opencode"

    def test_test_command_with_spec_file(self, tmp_path: Path) -> None:
        spec = tmp_path / "x.spec.ts"
        spec.write_text("placeholder")
        cmd = build_test_command(spec_path=spec, base_url="http://localhost:8000")
        assert "test" in cmd
        assert str(spec) in cmd
        # --reporter y su valor van como elementos separados del argv
        assert "--reporter" in cmd
        idx = cmd.index("--reporter")
        assert cmd[idx + 1] == "list"

    def test_test_command_injects_base_url_env(self, tmp_path: Path) -> None:
        spec = tmp_path / "x.spec.ts"
        spec.write_text("x")
        cmd = build_test_command(spec_path=spec, base_url="http://localhost:8000")
        # La baseURL se inyecta vía flag --base-url en playwright >=1.60
        assert "--base-url" in cmd
        idx = cmd.index("--base-url")
        assert cmd[idx + 1] == "http://localhost:8000"


# ──────────────────────── run_playwright_spec ──────────────────────
class TestRunPlaywrightSpec:
    def _make_spec(self, tmp_path: Path) -> Path:
        spec = tmp_path / "ok.spec.ts"
        spec.write_text(
            "import { test, expect } from '@playwright/test';\n"
            "test('ok', async ({ request }) => {\n"
            "  expect(200).toBe(200);\n"
            "});\n"
        )
        return spec

    def test_run_returns_success_on_zero_exit(self, tmp_path: Path) -> None:
        spec = self._make_spec(tmp_path)
        fake = MagicMock(returncode=0, stdout="  1 passed", stderr="")
        with patch("agentic_qa.playwright_agents.runner._exec", return_value=fake):
            result = run_playwright_spec(spec, base_url="http://localhost:8000")
        assert result.success is True
        assert result.passed == 1
        assert result.failed == 0

    def test_run_returns_failure_on_nonzero_exit(self, tmp_path: Path) -> None:
        spec = self._make_spec(tmp_path)
        fake = MagicMock(returncode=1, stdout="  1 failed", stderr="err")
        with patch("agentic_qa.playwright_agents.runner._exec", return_value=fake):
            result = run_playwright_spec(spec, base_url="http://localhost:8000")
        assert result.success is False
        assert result.failed == 1

    def test_run_parses_mixed_output(self, tmp_path: Path) -> None:
        spec = self._make_spec(tmp_path)
        fake = MagicMock(
            returncode=1,
            stdout="  3 passed\n  2 failed\n  1 flaky",
            stderr="",
        )
        with patch("agentic_qa.playwright_agents.runner._exec", return_value=fake):
            result = run_playwright_spec(spec, base_url="http://localhost:8000")
        assert result.passed == 3
        assert result.failed == 2
        assert result.flaky == 1
