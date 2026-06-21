"""Runner que invoca al binario ``promptfoo`` y parsea su salida.

Diseño:
- ``build_eval_command`` es puro (sin E/S) → testeable herméticamente.
- ``_exec`` aísla ``subprocess.run`` para poder mockearlo en tests.
- ``run_promptfoo_eval`` orquesta: ejecuta, valida exit code, valida output,
  parsea y devuelve ``PromptfooResult``.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import List, Optional

from agentic_qa.promptfoo.errors import ResultError
from agentic_qa.promptfoo.parser import parse_result
from agentic_qa.promptfoo.models import PromptfooResult

_DEFAULT_TIMEOUT = 300  # 5 min; promptfoo puede tardar con LLMs remotos


def build_eval_command(
    config_path: Path,
    output_path: Path,
    *,
    no_cache: bool = False,
    extra_args: Optional[List[str]] = None,
) -> List[str]:
    """Construye el argv para ``promptfoo eval``.

    Args:
        config_path: Ruta al ``promptfooconfig.yaml``.
        output_path: Ruta donde promptfoo escribirá el JSON de resultados.
        no_cache: Si True, añade ``--no-cache``.
        extra_args: Argumentos adicionales (p. ej. ``["--env-file", ".env"]``).

    Returns:
        Lista de argumentos lista para ``subprocess.run``.
    """
    binary = shutil.which("promptfoo") or "npx"
    cmd: List[str]
    if binary == "npx":
        cmd = ["npx", "--yes", "promptfoo", "eval"]
    else:
        cmd = [binary, "eval"]
    cmd += [
        "--config",
        str(config_path),
        "-o",
        str(output_path),
    ]
    if no_cache:
        cmd.append("--no-cache")
    if extra_args:
        cmd += list(extra_args)
    return cmd


def _exec(cmd: List[str], timeout: int) -> subprocess.CompletedProcess:
    """Ejecuta el comando. Aislado para facilitar mocking en tests."""
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def run_promptfoo_eval(
    config_path: Path | str,
    *,
    output_path: Path | str,
    no_cache: bool = True,
    timeout: int = _DEFAULT_TIMEOUT,
    extra_args: Optional[List[str]] = None,
) -> PromptfooResult:
    """Ejecuta ``promptfoo eval`` y devuelve el resultado parseado.

    Args:
        config_path: Ruta al ``promptfooconfig.yaml``.
        output_path: Ruta donde promptfoo escribirá el JSON.
        no_cache: Desactiva caché de promptfoo (default True para
            reproducibilidad en CI).
        timeout: Timeout en segundos.
        extra_args: Args extra para promptfoo.

    Returns:
        ``PromptfooResult`` con las métricas de la evaluación.

    Raises:
        ResultError: Si promptfoo falla (exit != 0), no genera el JSON
            de salida, o el JSON es inválido.
    """
    cfg = Path(config_path)
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    cmd = build_eval_command(cfg, out, no_cache=no_cache, extra_args=extra_args)
    proc = _exec(cmd, timeout=timeout)

    if proc.returncode != 0:
        # promptfoo muestra el detalle de errores en stdout (tabla de
        # resultados) y los warnings de Node en stderr. Incluimos ambos
        # para que el caller pueda detectar fallos de provider (quota,
        # auth, rate-limit) y reaccionar (p. ej. skip en tests de integración).
        combined = f"{proc.stdout}\n{proc.stderr}"
        tail = combined[-1500:]
        raise ResultError(f"promptfoo eval falló con exit código {proc.returncode}: {tail}")

    if not out.exists():
        raise ResultError(f"promptfoo finalizó OK pero no se generó el JSON en {out}")

    return parse_result(out.read_text(encoding="utf-8"))
