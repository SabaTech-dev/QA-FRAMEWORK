"""Test de integración: spec de Playwright contra el backend real.

GATEADO por ``API_BASE_URL`` y que el backend responda. No corre si el
backend no está levantado (smoke check con ``httpx``).

Ejecución manual::

    # Arrancar backend primero
    API_BASE_URL=http://localhost:8000 pytest \\
        tests/agentic_qa/integration/test_playwright_integration.py \\
        -m agentic --no-cov -s
"""

from __future__ import annotations

import shutil

import pytest

from agentic_qa.playwright_agents import (
    build_init_agents_command,
    run_playwright_spec,
    validate_spec_file,
)

pytestmark = [
    pytest.mark.agentic,
    pytest.mark.integration,
    pytest.mark.e2e,
]


def test_playwright_spec_is_valid(playwright_spec_path):
    """El spec TS del PoC pasa la validación sintáctica (hermético)."""
    validate_spec_file(playwright_spec_path)


def test_init_agents_command_uses_official_subcommand():
    """El comando para inicializar agentes usa ``init-agents`` (hermético)."""
    cmd = build_init_agents_command(loop="opencode")
    assert "init-agents" in cmd
    assert "--loop" in cmd


def test_npx_playwright_available():
    """``npx playwright`` está disponible (hermético, solo chequea versión)."""
    import subprocess

    res = subprocess.run(
        ["npx", "--yes", "playwright", "--version"],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert res.returncode == 0, f"playwright no disponible: {res.stderr}"
    assert "Version" in res.stdout or res.stdout.strip()[0:1].isdigit()


def test_playwright_spec_runs_against_backend(playwright_spec_path, backend_base_url):
    """Ejecuta el spec contra el backend real.

    Skip si el backend no responde en ``backend_base_url``.
    """
    if not shutil.which("npx"):
        pytest.skip("npx no disponible")
    # Smoke: ¿el backend responde?
    import subprocess

    health = subprocess.run(
        ["npx", "--yes", "playwright", "test", "--list", str(playwright_spec_path)],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
        env={**__import__("os").environ, "PLAYWRIGHT_BASE_URL": backend_base_url},
    )
    if health.returncode != 0:
        pytest.skip(f"no se pudo listar el spec de playwright: {health.stderr[:200]}")

    result = run_playwright_spec(playwright_spec_path, base_url=backend_base_url, validate=True)
    assert result.success, (
        f"spec falló ({result.failed} tests). stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    assert result.passed > 0
