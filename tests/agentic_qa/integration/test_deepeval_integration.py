"""Test de integración: métrica LLM de DeepEval (juez real).

GATEADO por ``OPENAI_API_KEY``. Compara el clasificador determinista
contra el juez LLM de DeepEval (GEval) para medir acuerdo.

Ejecución manual::

    OPENAI_API_KEY=sk-... pytest tests/agentic_qa/integration/ \\
        -m deepeval --no-cov -s
"""

from __future__ import annotations

import pytest

from agentic_qa.deepeval_metrics import (
    DEFAULT_THRESHOLD,
    build_golden_cases,
    evaluate_cases,
)
from agentic_qa.deepeval_metrics.llm_bridge import require_llm_bridge

pytestmark = [
    pytest.mark.agentic,
    pytest.mark.deepeval,
    pytest.mark.integration,
    pytest.mark.llm,
]


def test_deterministic_baseline_is_100_percent():
    """La baseline determinista debe acertar el 100% del dataset golden.

    Hermético: usa la métrica determinista, no el juez LLM.
    """
    report = evaluate_cases(build_golden_cases())
    assert report.accuracy == 1.0
    assert report.threshold_met


def test_deterministic_meets_default_threshold():
    """La métrica determinista cumple el umbral por defecto (0.8)."""
    report = evaluate_cases(build_golden_cases(), threshold=DEFAULT_THRESHOLD)
    assert report.threshold_met


def test_llm_bridge_requires_api_key(monkeypatch):
    """Sin API key, el puente LLM levanta ``LLMBridgeUnavailable``."""
    for key in ("OPENAI_API_KEY", "DEEPEVAL_API_KEY", "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    from agentic_qa.deepeval_metrics.llm_bridge import LLMBridgeUnavailable

    with pytest.raises(LLMBridgeUnavailable):
        require_llm_bridge()


def test_deepeval_geval_runs_against_golden_cases(openai_api_key):
    """GEval de DeepEval corre sobre el dataset golden (juez LLM real).

    Requiere ``OPENAI_API_KEY`` con cuota y deepeval instalado. Si el
    provider rechaza por quota/rate-limit/auth, se salta (no es un bug
    de nuestro código).
    """
    if not openai_api_key:
        pytest.skip("OPENAI_API_KEY no definida — test de integración omitido")
    from agentic_qa.deepeval_metrics.llm_bridge import run_deepeval_metric

    try:
        results = run_deepeval_metric(build_golden_cases()[:3], metric_name="GEval")
    except ImportError as exc:
        pytest.skip(f"deepeval no instalado o API cambiada: {exc}")
    except Exception as exc:  # noqa: BLE001
        # Errores de provider (quota, rate-limit, auth) → skip, no fail.
        msg = str(exc).lower()
        if any(
            p in msg
            for p in (
                "429",
                "quota",
                "rate limit",
                "rate_limit",
                "insufficient_quota",
                "401",
                "billing",
            )
        ):
            pytest.skip(f"provider rechazó la llamada (quota/rate-limit): {msg[:200]}")
        raise

    assert len(results) == 3
    assert all("response" in r and "metric" in r for r in results)
