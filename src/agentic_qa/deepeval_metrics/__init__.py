"""Adaptador de DeepEval — QA agéntico PoC Fase 1.

API pública:
- ``GoldenCase`` / ``build_golden_cases``: dataset golden de regresión.
- ``RefusalAccuracyMetric`` / ``MetricScore``: métrica determinista.
- ``EvalReport`` / ``evaluate_cases``: evaluación agregada + umbral.
- ``DEFAULT_THRESHOLD``: umbral por defecto (0.8, alineado con la spec).
- ``LLMBridgeUnavailable``: excepción del puente al juez LLM.

Diseño hermético: la métrica por defecto (``RefusalAccuracyMetric``) es
100% determinista (sin LLM). El puente al juez LLM real de DeepEval vive
en ``agentic_qa.deepeval_metrics.llm_bridge`` y solo se usa en integración.
"""

from __future__ import annotations

from agentic_qa.deepeval_metrics.golden_cases import (
    GoldenCase,
    build_golden_cases,
)
from agentic_qa.deepeval_metrics.metrics import (
    EvalReport,
    MetricScore,
    RefusalAccuracyMetric,
    evaluate_cases,
)
from agentic_qa.deepeval_metrics.llm_bridge import LLMBridgeUnavailable

DEFAULT_THRESHOLD: float = 0.8

__all__ = [
    "GoldenCase",
    "build_golden_cases",
    "MetricScore",
    "RefusalAccuracyMetric",
    "EvalReport",
    "evaluate_cases",
    "DEFAULT_THRESHOLD",
    "LLMBridgeUnavailable",
]
