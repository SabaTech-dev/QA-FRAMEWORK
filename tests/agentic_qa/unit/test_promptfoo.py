"""Unittests para el adaptador de Promptfoo.

Cubre:
- Carga y validación de ``promptfooconfig.yaml``.
- Parseo del JSON de resultados de ``promptfoo eval``.
- ``run_promptfoo_eval`` con subprocess mockeado (hermético).

Los tests de integración (que llaman al binario real de promptfoo) viven
en ``tests/agentic_qa/integration/`` y están gateados por entorno.
"""

from __future__ import annotations

import json
import textwrap
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from agentic_qa.promptfoo import (
    PromptfooConfig,
    PromptfooResult,
    load_config,
    parse_result,
    run_promptfoo_eval,
    build_eval_command,
)
from agentic_qa.promptfoo.errors import ConfigError, ResultError


# ───────────────────────── PromptfooConfig ──────────────────────────
class TestPromptfooConfig:
    def test_loads_valid_config(self, tmp_path: Path) -> None:
        cfg_path = tmp_path / "promptfooconfig.yaml"
        cfg_path.write_text(
            textwrap.dedent(
                """
                description: PoC clasificador
                prompts:
                  - file://prompts/severity.txt
                providers:
                  - id: openai:gpt-4o-mini
                tests:
                  - description: rechazo
                    vars: {response: "I cannot help"}
                    assert:
                      - type: icontains
                        value: REFUSAL
                """
            )
        )
        cfg = load_config(cfg_path)
        assert isinstance(cfg, PromptfooConfig)
        assert cfg.description == "PoC clasificador"
        assert cfg.prompts == ["file://prompts/severity.txt"]
        assert len(cfg.providers) == 1
        assert cfg.providers[0]["id"] == "openai:gpt-4o-mini"
        assert len(cfg.tests) == 1

    def test_missing_file_raises_config_error(self, tmp_path: Path) -> None:
        with pytest.raises(ConfigError, match="no existe"):
            load_config(tmp_path / "missing.yaml")

    def test_invalid_yaml_raises_config_error(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.yaml"
        bad.write_text("description: [unterminated\n  - a: b: c")
        with pytest.raises(ConfigError, match="YAML"):
            load_config(bad)

    def test_missing_required_fields_raises_config_error(self, tmp_path: Path) -> None:
        cfg = tmp_path / "c.yaml"
        # Sin prompts ni providers ni tests
        cfg.write_text("description: vacio\n")
        with pytest.raises(ConfigError, match="prompts"):
            load_config(cfg)

    def test_minimal_valid_config_has_default_description(self, tmp_path: Path) -> None:
        cfg = tmp_path / "c.yaml"
        cfg.write_text(
            textwrap.dedent(
                """
                prompts: ["Tell me: {{q}}"]
                providers: [{id: openai:gpt-4o-mini}]
                tests:
                  - vars: {q: hi}
                """
            )
        )
        loaded = load_config(cfg)
        assert loaded.description == "Promptfoo eval"  # default

    def test_test_count_property(self, valid_config_path: Path) -> None:
        cfg = load_config(valid_config_path)
        assert cfg.test_count == 2


# ───────────────────────── PromptfooResult ──────────────────────────
class TestPromptfooResult:
    def test_parse_full_result_json(self) -> None:
        raw = {
            "stats": {"successes": 5, "failures": 1, "total": 6},
            "results": [
                {"success": True, "testCase": {"description": "ok"}},
                {"success": False, "testCase": {"description": "bad"}},
            ],
        }
        result = parse_result(raw)
        assert isinstance(result, PromptfooResult)
        assert result.successes == 5
        assert result.failures == 1
        assert result.total == 6
        assert result.pass_rate == pytest.approx(5 / 6)

    def test_parse_result_with_zero_total(self) -> None:
        result = parse_result({"stats": {"successes": 0, "failures": 0, "total": 0}})
        assert result.total == 0
        assert result.pass_rate == 0.0

    def test_parse_result_missing_stats_raises(self) -> None:
        with pytest.raises(ResultError, match="stats"):
            parse_result({"results": []})

    def test_parse_result_from_json_string(self) -> None:
        raw_json = json.dumps({"stats": {"successes": 3, "failures": 0, "total": 3}})
        result = parse_result(raw_json)
        assert result.successes == 3
        assert result.pass_rate == 1.0

    def test_parse_invalid_json_raises_result_error(self) -> None:
        with pytest.raises(ResultError, match="JSON"):
            parse_result("{not json")

    def test_meets_threshold(self) -> None:
        result = PromptfooResult(successes=8, failures=2, total=10)
        assert result.meets_threshold(0.8) is True
        assert result.meets_threshold(0.9) is False

    def test_failed_descriptions_collected(self) -> None:
        raw = {
            "stats": {"successes": 1, "failures": 2, "total": 3},
            "results": [
                {"success": True, "testCase": {"description": "ok"}},
                {"success": False, "testCase": {"description": "bad1"}},
                {"success": False, "testCase": {"description": "bad2"}},
            ],
        }
        result = parse_result(raw)
        assert result.failed_descriptions == ["bad1", "bad2"]


# ─────────────────────── run_promptfoo_eval ─────────────────────────
class TestRunPromptfooEval:
    def test_build_eval_command_contains_required_flags(self, valid_config_path: Path) -> None:
        cmd = build_eval_command(
            config_path=valid_config_path,
            output_path=Path("/tmp/out.json"),
        )
        assert "promptfoo" in cmd[0] or cmd[0].endswith("promptfoo")
        assert "eval" in cmd
        assert "--config" in cmd
        assert str(valid_config_path) in cmd
        assert "-o" in cmd
        assert "/tmp/out.json" in cmd

    def test_build_eval_command_with_cache_flag(self, valid_config_path: Path) -> None:
        cmd = build_eval_command(
            config_path=valid_config_path,
            output_path=Path("/tmp/out.json"),
            no_cache=True,
        )
        assert "--no-cache" in cmd

    def test_build_eval_command_without_cache_flag_by_default(
        self, valid_config_path: Path
    ) -> None:
        cmd = build_eval_command(
            config_path=valid_config_path,
            output_path=Path("/tmp/out.json"),
        )
        assert "--no-cache" not in cmd

    def test_run_eval_returns_result_on_success(
        self, valid_config_path: Path, tmp_path: Path
    ) -> None:
        out_path = tmp_path / "out.json"
        out_path.write_text(json.dumps({"stats": {"successes": 2, "failures": 0, "total": 2}}))
        fake_proc = MagicMock(returncode=0, stdout="ok", stderr="")
        with patch("agentic_qa.promptfoo.runner._exec", return_value=fake_proc):
            result = run_promptfoo_eval(valid_config_path, output_path=out_path)
        assert result.successes == 2
        assert result.pass_rate == 1.0

    def test_run_eval_raises_on_nonzero_exit(self, valid_config_path: Path, tmp_path: Path) -> None:
        fake_proc = MagicMock(returncode=2, stdout="", stderr="boom")
        with patch("agentic_qa.promptfoo.runner._exec", return_value=fake_proc):
            with pytest.raises(ResultError, match="exit código 2"):
                run_promptfoo_eval(valid_config_path, output_path=tmp_path / "out.json")

    def test_run_eval_raises_when_output_missing(
        self, valid_config_path: Path, tmp_path: Path
    ) -> None:
        fake_proc = MagicMock(returncode=0, stdout="ok", stderr="")
        with patch("agentic_qa.promptfoo.runner._exec", return_value=fake_proc):
            with pytest.raises(ResultError, match="no se generó"):
                run_promptfoo_eval(valid_config_path, output_path=tmp_path / "missing.json")


# ───────────────────────── Fixtures ─────────────────────────────────
@pytest.fixture
def valid_config_path(tmp_path: Path) -> Path:
    cfg = tmp_path / "promptfooconfig.yaml"
    cfg.write_text(
        textwrap.dedent(
            """
            description: PoC
            prompts:
              - "Clasifica: {{response}}"
            providers:
              - id: openai:gpt-4o-mini
            tests:
              - description: uno
                vars: {response: "I cannot"}
                assert: [{type: icontains, value: REFUSAL}]
              - description: dos
                vars: {response: "Sure"}
                assert: [{type: icontains, value: COMPLIANCE}]
            """
        )
    )
    return cfg
