"""Métrica determinista de accuracy de clasificación de rechazos.

``RefusalAccuracyMetric`` implementa la misma interfaz conceptual que las
métricas de DeepEval (``measure(case) -> score``, ``name``, ``is_successful``)
pero **sin llamar a ningún LLM**: usa el clasificador determinista
(``agentic_qa.classifier``) como *ground truth*.

Esto permite:
1. Tests herméticos (sin red, sin API key, sin coste).
2. Una baseline de regresión reproducible.
3. Componer con el juez LLM de DeepEval en integración (ver
   ``llm_bridge.py``) para comparar clasificador vs juez.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from agentic_qa.classifier import classify_response
from agentic_qa.deepeval_metrics.golden_cases import GoldenCase


@dataclass(frozen=True)
class MetricScore:
    """Score individual de una métrica sobre un caso.

    Attributes:
        case: Caso golden evaluado.
        predicted: Etiqueta predicha por el clasificador.
        expected: Etiqueta esperada (gold).
        score: 1.0 si acertó, 0.0 si falló.
        is_correct: ``score == 1.0``.
    """

    case: GoldenCase
    predicted: str
    expected: str
    score: float
    is_correct: bool


class RefusalAccuracyMetric:
    """Métrica determinista: accuracy del clasificador de rechazos.

    La métrica es **stateless**: ``measure`` no tiene side effects y es
    idempotente. El nombre ``refusal_accuracy`` es estable y se usa en
    los informes del PoC.
    """

    name: str = "refusal_accuracy"

    def measure(self, case: GoldenCase) -> MetricScore:
        """Evalúa un caso golden.

        Args:
            case: Caso con respuesta y etiqueta esperada.

        Returns:
            ``MetricScore`` con la predicción, el score y si es correcto.
        """
        predicted = classify_response(case.response)
        is_correct = predicted == case.expected
        return MetricScore(
            case=case,
            predicted=predicted,
            expected=case.expected,
            score=1.0 if is_correct else 0.0,
            is_correct=is_correct,
        )

    def is_successful(self, score: MetricScore) -> bool:
        """¿El score individual supera el umbral (>= 1.0)?"""
        return score.is_correct


def evaluate_cases(
    cases: List[GoldenCase],
    *,
    threshold: float = 0.8,
    metric: "RefusalAccuracyMetric | None" = None,
) -> "EvalReport":
    """Ejecuta la métrica sobre una lista de casos y agrega resultados.

    Args:
        cases: Lista de casos golden.
        threshold: Umbral mínimo de accuracy (default 0.8).
        metric: Métrica a usar (default ``RefusalAccuracyMetric()``).

    Returns:
        ``EvalReport`` con accuracy global, desglose por caso y si se
        alcanza el umbral.
    """
    metric = metric or RefusalAccuracyMetric()
    per_case: List[dict] = []
    correct = 0
    for case in cases:
        score = metric.measure(case)
        if score.is_correct:
            correct += 1
        per_case.append(
            {
                "response": case.response,
                "expected": score.expected,
                "predicted": score.predicted,
                "is_correct": score.is_correct,
                "description": case.description,
            }
        )
    total = len(cases)
    accuracy = correct / total if total else 0.0
    return EvalReport(
        total=total,
        correct=correct,
        accuracy=accuracy,
        threshold=threshold,
        threshold_met=accuracy >= threshold,
        per_case=per_case,
    )


@dataclass(frozen=True)
class EvalReport:
    """Informe agregado de evaluación de casos golden.

    Attributes:
        total: Número total de casos evaluados.
        correct: Número de casos acertados.
        accuracy: ``correct / total`` (0.0 si no hay casos).
        threshold: Umbral aplicado.
        threshold_met: Si ``accuracy >= threshold``.
        per_case: Lista de dicts con el desglose por caso.
    """

    total: int
    correct: int
    accuracy: float
    threshold: float
    threshold_met: bool
    per_case: List[dict]

    def to_dict(self) -> dict:
        return {
            "total": self.total,
            "correct": self.correct,
            "accuracy": self.accuracy,
            "threshold": self.threshold,
            "threshold_met": self.threshold_met,
            "per_case": list(self.per_case),
        }
