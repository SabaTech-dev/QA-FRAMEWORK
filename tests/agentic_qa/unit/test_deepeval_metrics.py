"""Unittests para el módulo de métricas DeepEval.

Estrategia hermética: la métrica ``RefusalAccuracyMetric`` usa el
clasificador determinista (``agentic_qa.classifier``) como *ground truth*
→ no requiere LLM ni red. El adaptador al juez LLM de DeepEval (que sí
llama a un modelo) vive en ``LLMJudgeAdapter`` y solo se usa en los tests
de integración gateados por ``OPENAI_API_KEY``.
"""

from __future__ import annotations

import pytest

from agentic_qa.classifier import REFUSAL, COMPLIANCE
from agentic_qa.deepeval_metrics import (
    GoldenCase,
    EvalReport,
    RefusalAccuracyMetric,
    LLMBridgeUnavailable,
    evaluate_cases,
    build_golden_cases,
    DEFAULT_THRESHOLD,
)


# ─────────────────────────── GoldenCase ─────────────────────────────
class TestGoldenCase:
    def test_construction(self) -> None:
        case = GoldenCase(
            response="I cannot help",
            expected=REFUSAL,
            description="rechazo claro",
        )
        assert case.response == "I cannot help"
        assert case.expected == REFUSAL
        assert case.description == "rechazo claro"

    def test_default_description_when_missing(self) -> None:
        case = GoldenCase(response="Sure", expected=COMPLIANCE)
        assert case.description == ""

    def test_invalid_expected_label_raises(self) -> None:
        with pytest.raises(ValueError, match="expected"):
            GoldenCase(response="x", expected="MAYBE")

    def test_to_dict(self) -> None:
        case = GoldenCase("I can't", REFUSAL, "d")
        assert case.to_dict() == {
            "response": "I can't",
            "expected": REFUSAL,
            "description": "d",
        }


# ──────────────────────── RefusalAccuracyMetric ─────────────────────
class TestRefusalAccuracyMetric:
    def test_measure_correct_refusal(self) -> None:
        metric = RefusalAccuracyMetric()
        score = metric.measure(GoldenCase("I cannot help", REFUSAL))
        assert score.is_correct is True
        assert score.predicted == REFUSAL
        assert score.expected == REFUSAL
        assert score.score == 1.0

    def test_measure_incorrect(self) -> None:
        # El clasificador devuelve COMPLIANCE para "Sure" → esperado REFUSAL → fallo
        metric = RefusalAccuracyMetric()
        score = metric.measure(GoldenCase("Sure, here you go", REFUSAL))
        assert score.is_correct is False
        assert score.predicted == COMPLIANCE
        assert score.expected == REFUSAL
        assert score.score == 0.0

    def test_measure_compliance_correct(self) -> None:
        metric = RefusalAccuracyMetric()
        score = metric.measure(GoldenCase("Sure, here you go", COMPLIANCE))
        assert score.is_correct is True
        assert score.score == 1.0

    def test_metric_name_is_stable(self) -> None:
        assert RefusalAccuracyMetric().name == "refusal_accuracy"

    def test_metric_is_deterministic(self) -> None:
        # Misma entrada → misma salida, siempre
        metric = RefusalAccuracyMetric()
        case = GoldenCase("I'm sorry, I can't", REFUSAL)
        s1 = metric.measure(case)
        s2 = metric.measure(case)
        assert s1 == s2


# ──────────────────────── evaluate_cases ────────────────────────────
class TestEvaluateCases:
    def test_all_correct(self) -> None:
        cases = [
            GoldenCase("I cannot help", REFUSAL),
            GoldenCase("Sure, here you go", COMPLIANCE),
            GoldenCase("no puedo", REFUSAL),
        ]
        report = evaluate_cases(cases)
        assert isinstance(report, EvalReport)
        assert report.total == 3
        assert report.correct == 3
        assert report.accuracy == 1.0
        assert report.threshold_met is True
        assert len(report.per_case) == 3

    def test_partial_accuracy(self) -> None:
        cases = [
            GoldenCase("I cannot help", REFUSAL),  # ok
            GoldenCase("Sure", REFUSAL),  # fallo: classifier → COMPLIANCE
            GoldenCase("Sure, here you go", COMPLIANCE),  # ok
            GoldenCase("no puedo", REFUSAL),  # ok
        ]
        report = evaluate_cases(cases)
        assert report.total == 4
        assert report.correct == 3
        assert report.accuracy == pytest.approx(0.75)
        assert report.threshold_met is False  # 0.75 < 0.8 default

    def test_empty_cases_returns_zero_accuracy(self) -> None:
        report = evaluate_cases([])
        assert report.total == 0
        assert report.accuracy == 0.0
        assert report.threshold_met is False

    def test_custom_threshold(self) -> None:
        cases = [
            GoldenCase("I cannot", REFUSAL),
            GoldenCase("Sure", REFUSAL),  # fallo
        ]
        report = evaluate_cases(cases, threshold=0.4)
        assert report.accuracy == 0.5
        assert report.threshold_met is True  # 0.5 >= 0.4

    def test_report_to_dict_serializable(self) -> None:
        cases = [GoldenCase("I cannot", REFUSAL)]
        report = evaluate_cases(cases)
        d = report.to_dict()
        assert d["total"] == 1
        assert d["correct"] == 1
        assert d["accuracy"] == 1.0
        assert "per_case" in d
        assert d["threshold"] == DEFAULT_THRESHOLD

    def test_per_case_includes_description(self) -> None:
        cases = [GoldenCase("I cannot", REFUSAL, description="mi desc")]
        report = evaluate_cases(cases)
        assert report.per_case[0]["description"] == "mi desc"
        assert report.per_case[0]["is_correct"] is True


# ──────────────────────── Dataset por defecto ───────────────────────
class TestDefaultGoldenCases:
    def test_default_dataset_has_at_least_six_cases(self) -> None:
        cases = build_golden_cases()
        assert len(cases) >= 6
        labels = {c.expected for c in cases}
        assert REFUSAL in labels
        assert COMPLIANCE in labels

    def test_default_dataset_all_labels_valid(self) -> None:
        cases = build_golden_cases()
        for c in cases:
            assert c.expected in (REFUSAL, COMPLIANCE)

    def test_default_dataset_passes_threshold(self) -> None:
        # El dataset por defecto debe ser 100% acertado por el clasificador
        # (es la baseline de regresión del PoC).
        report = evaluate_cases(build_golden_cases())
        assert report.accuracy == 1.0, (
            "El dataset golden por defecto debe ser 100% acertado por el "
            "clasificador determinista. Si añades un caso, asegúrate de que "
            "la heurística del classifier lo resuelve bien."
        )


# ──────────────────── LLMBridge (lazy / unavailable) ─────────────────
class TestLLMBridge:
    def test_llm_bridge_raises_when_no_key(self, monkeypatch) -> None:
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        with pytest.raises(LLMBridgeUnavailable):
            from agentic_qa.deepeval_metrics.llm_bridge import require_llm_bridge

            require_llm_bridge()

    def test_llm_bridge_module_is_lazily_importable(self) -> None:
        # El módulo debe importarse sin tener deepeval instalado activamente
        # (lazy import dentro de las funciones).
        from agentic_qa.deepeval_metrics import llm_bridge

        assert hasattr(llm_bridge, "require_llm_bridge")
