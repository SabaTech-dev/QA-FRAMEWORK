"""Parseo del JSON de resultados de ``promptfoo eval``."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Union

from agentic_qa.promptfoo.errors import ResultError
from agentic_qa.promptfoo.models import PromptfooResult


def parse_result(raw: Union[Dict[str, Any], str, bytes]) -> PromptfooResult:
    """Parsea la salida JSON de ``promptfoo eval``.

    Args:
        raw: Dict ya parseado, str/bytes JSON, o path implícito.

    Returns:
        ``PromptfooResult`` con successes, failures, total y descripciones
        de los tests fallidos.

    Raises:
        ResultError: Si el JSON es inválido o falta la clave ``stats``.
    """
    data: Dict[str, Any]
    if isinstance(raw, (str, bytes)):
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ResultError(f"JSON inválido: {exc}") from exc
    else:
        data = raw

    if not isinstance(data, dict):
        raise ResultError(f"Se esperaba un mapping, recibido {type(data).__name__}")

    stats = data.get("stats")
    if not isinstance(stats, dict):
        raise ResultError("Falta la clave 'stats' (o no es un mapping) en el resultado")

    successes = int(stats.get("successes", 0))
    failures = int(stats.get("failures", 0))
    # `total` puede estar ausente en versiones viejas → se infiere.
    total = int(stats.get("total", successes + failures))

    failed_descriptions: List[str] = []
    for entry in data.get("results", []) or []:
        if isinstance(entry, dict) and not entry.get("success", False):
            test_case = entry.get("testCase") or {}
            desc = test_case.get("description") if isinstance(test_case, dict) else None
            failed_descriptions.append(desc or "<sin descripción>")

    return PromptfooResult(
        successes=successes,
        failures=failures,
        total=total,
        failed_descriptions=failed_descriptions,
    )
