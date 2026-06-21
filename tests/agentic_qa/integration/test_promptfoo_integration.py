"""Test de integración: ``promptfoo eval`` real contra el clasificador.

GATEADO por ``OPENAI_API_KEY`` y la presencia del binario ``promptfoo``.
No corre en CI sin secrets → no cuenta para el cálculo de cobertura pero
sí valida el pipeline extremo a extremo cuando hay entorno.

Ejecución manual::

    OPENAI_API_KEY=sk-... pytest tests/agentic_qa/integration/ \\
        -m promptfoo --no-cov -s
"""

from __future__ import annotations

import pytest

from agentic_qa.promptfoo import load_config, run_promptfoo_eval
from agentic_qa.promptfoo.errors import ResultError

# Marcas: agentic + promptfoo + integration + llm. Por defecto NO corren
# (hay que pedirlas explícitamente con `pytest -m promptfoo`).
pytestmark = [
    pytest.mark.agentic,
    pytest.mark.promptfoo,
    pytest.mark.integration,
    pytest.mark.llm,
]

# Patrones que indican un fallo del provider (quota / rate limit / auth),
# no un bug de nuestro código. En esos casos el test se saltará.
_PROVIDER_ERROR_PATTERNS = (
    "429",
    "quota",
    "insufficient_quota",
    "rate limit",
    "rate_limit",
    "401",
    "invalid_api_key",
    "authentication",
    "billing",
)


def _is_provider_error(message: str) -> bool:
    lowered = message.lower()
    return any(p in lowered for p in _PROVIDER_ERROR_PATTERNS)


def test_promptfoo_config_loads(promptfoo_config_path):
    """La config real del PoC carga y valida sin error."""
    cfg = load_config(promptfoo_config_path)
    assert cfg.test_count >= 5, "esperaba ≥5 tests en la config del PoC"
    assert cfg.prompts, "la config debe definir prompts"
    assert cfg.providers, "la config debe definir providers"


def test_promptfoo_eval_pass_rate_ge_80(
    promptfoo_config_path, tmp_path, openai_api_key, promptfoo_available
):
    """``promptfoo eval`` produce pass rate >= 80% sobre la config del PoC.

    Requiere ``OPENAI_API_KEY`` con cuota disponible y el binario ``promptfoo``.
    Si el provider rechaza por quota/rate-limit/auth, se salta (no es un bug
    de nuestro código).
    """
    if not openai_api_key:
        pytest.skip("OPENAI_API_KEY no definida — test de integración omitido")
    if not promptfoo_available:
        pytest.skip("binario promptfoo no disponible en PATH")

    out = tmp_path / "promptfoo_result.json"
    try:
        result = run_promptfoo_eval(promptfoo_config_path, output_path=out, no_cache=True)
    except ResultError as exc:
        if _is_provider_error(str(exc)):
            pytest.skip(f"provider rechazó la llamada (quota/auth/rate-limit): {str(exc)[:200]}")
        raise

    assert result.total >= 5, f"esperaba ≥5 tests, got {result.total}"
    assert result.meets_threshold(0.8), (
        f"pass rate {result.pass_rate:.0%} < 80%. Fallos: {result.failed_descriptions}"
    )
