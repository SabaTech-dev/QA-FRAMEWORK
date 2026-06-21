"""Runner que orquesta los Playwright Test Agents vía ``npx``.

Construye los comandos oficiales:
- ``npx playwright init-agents --loop=opencode`` (scaffold de agentes)
- ``npx playwright test <spec> --base-url=... --reporter=list`` (ejecución)

Y parsea la salida de ``playwright test`` (``N passed``, ``N failed``).
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List

from agentic_qa.playwright_agents.spec_validator import validate_spec_file

_DEFAULT_TIMEOUT = 120  # 2 min; los specs del PoC son API requests rápidos

_PASSED_RE = re.compile(r"(\d+)\s+passed", re.IGNORECASE)
_FAILED_RE = re.compile(r"(\d+)\s+failed", re.IGNORECASE)
_FLAKY_RE = re.compile(r"(\d+)\s+flaky", re.IGNORECASE)


@dataclass(frozen=True)
class PlaywrightRunResult:
    """Resultado de ejecutar ``playwright test``.

    Attributes:
        success: True si el exit code fue 0.
        passed: Número de tests en verde.
        failed: Número de tests en rojo.
        flaky: Número de tests flaky.
        stdout: Salida estándar cruda.
        stderr: Salida de error cruda.
    """

    success: bool
    passed: int
    failed: int
    flaky: int
    stdout: str
    stderr: str


def build_init_agents_command(loop: str = "opencode") -> List[str]:
    """Comando oficial para scaffoldear los Playwright Test Agents.

    Args:
        loop: Agent loop destino (``opencode``, ``claude``, ``copilot``...).

    Returns:
        argv listo para ``subprocess.run``.
    """
    return ["npx", "--yes", "playwright", "init-agents", "--loop", loop]


def build_test_command(
    spec_path: Path,
    base_url: str = "http://localhost:8000",
    *,
    reporter: str = "list",
    extra_args: List[str] | None = None,
) -> List[str]:
    """Comando para ejecutar un spec concreto de Playwright.

    Args:
        spec_path: Ruta al ``.spec.ts``.
        base_url: URL base para los API requests.
        reporter: Reporter de Playwright (``list``, ``json``, ``html``...).
        extra_args: Argumentos adicionales.

    Returns:
        argv listo para ``subprocess.run``.
    """
    cmd = [
        "npx",
        "--yes",
        "playwright",
        "test",
        str(spec_path),
        "--base-url",
        base_url,
        "--reporter",
        reporter,
    ]
    if extra_args:
        cmd += list(extra_args)
    return cmd


def _exec(cmd: List[str], timeout: int) -> subprocess.CompletedProcess:
    """Ejecuta el comando. Aislado para facilitar mocking en tests."""
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)


def _count(pattern: re.Pattern[str], text: str) -> int:
    m = pattern.search(text)
    return int(m.group(1)) if m else 0


def run_playwright_spec(
    spec_path: Path | str,
    base_url: str = "http://localhost:8000",
    *,
    timeout: int = _DEFAULT_TIMEOUT,
    validate: bool = True,
) -> PlaywrightRunResult:
    """Ejecuta un spec de Playwright y parsea el resultado.

    Args:
        spec_path: Ruta al ``.spec.ts``.
        base_url: URL base para los API requests.
        timeout: Timeout en segundos.
        validate: Si True, valida el spec antes de ejecutarlo.

    Returns:
        ``PlaywrightRunResult`` con conteos y salida cruda.
    """
    spec = Path(spec_path)
    if validate:
        validate_spec_file(spec)

    cmd = build_test_command(spec, base_url=base_url)
    proc = _exec(cmd, timeout=timeout)
    output = f"{proc.stdout}\n{proc.stderr}"

    return PlaywrightRunResult(
        success=proc.returncode == 0,
        passed=_count(_PASSED_RE, output),
        failed=_count(_FAILED_RE, output),
        flaky=_count(_FLAKY_RE, output),
        stdout=proc.stdout,
        stderr=proc.stderr,
    )
