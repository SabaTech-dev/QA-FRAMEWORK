"""
Unit tests para RagasEvaluator (evaluacion de pipelines RAG con RAGAS).

Estrategia de mocking (sin API keys):
    Se mockea el seam interno ``_run_metric`` de RagasEvaluator, que es el
    unico punto que invoca a ragas. Asi los tests son deterministas, rapidos
    y no realizan llamadas a APIs de LLM. Se valida el contrato publico de
    QA-FRAMEWORK: firmas, rangos [0,1], normalizacion de entradas, agregacion
    de metricas y gestion de errores.

Cobertura:
    - Metodos publicos (4) con datos sinteticos.
    - Rangos de salida en [0.0, 1.0].
    - Normalizacion de context (str -> list[str]).
    - Manejo de None/NaN -> 0.0 y clip a [0,1].
    - Importabilidad del modulo sin ragas instalado (lazy import).
    - evaluate_full_pipeline devuelve dict con todas las claves esperadas.
"""

from __future__ import annotations

import math
from unittest.mock import MagicMock

import pytest


# ---------------------------------------------------------------------------
# Tests de construccion e importabilidad
# ---------------------------------------------------------------------------
class TestRagasEvaluatorConstruction:
    """Tests de construccion del evaluador."""

    def test_can_instantiate_without_llm(self, ragas_evaluator):
        """El evaluador debe poder construirse sin LLM (lazy config)."""
        assert ragas_evaluator is not None
        assert ragas_evaluator.llm is None

    def test_accepts_custom_llm(self):
        """Debe aceptar un LLM inyectado (Dependency Inversion)."""
        from src.core.evaluation.ragas_evaluator import RagasEvaluator

        fake_llm = object()  # cualquier objeto sirve como double
        evaluator = RagasEvaluator(llm=fake_llm)
        assert evaluator.llm is fake_llm

    def test_module_importable_without_ragas_installed(self, monkeypatch):
        """
        El modulo debe ser importable aunque ragas no este instalado
        (lazy import). Solo debe fallar al ejecutar una evaluacion.
        """
        import builtins
        import importlib

        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "ragas" or name.startswith("ragas."):
                raise ImportError("simulated: ragas not installed")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", fake_import)
        import src.core.evaluation.ragas_evaluator as mod

        importlib.reload(mod)
        # La clase sigue siendo accesible aun sin ragas
        assert hasattr(mod, "RagasEvaluator")


# ---------------------------------------------------------------------------
# Tests de evaluate_context_relevance
# ---------------------------------------------------------------------------
class TestEvaluateContextRelevance:
    """Tests para evaluate_context_relevance."""

    def test_returns_float_in_unit_range(
        self, ragas_evaluator, synthetic_question, synthetic_context, synthetic_answer
    ):
        """El score debe ser un float en [0.0, 1.0]."""
        ragas_evaluator._run_metric = MagicMock(return_value=0.82)

        score = ragas_evaluator.evaluate_context_relevance(
            synthetic_question, synthetic_context, synthetic_answer
        )

        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0
        assert score == pytest.approx(0.82)

    def test_context_string_normalized_to_list(
        self, ragas_evaluator, synthetic_question, synthetic_answer
    ):
        """Si context es un str, se normaliza a list[str] para ragas."""
        captured = {}

        def capture(metric, sample):
            captured["contexts"] = sample.retrieved_contexts
            return 0.5

        ragas_evaluator._run_metric = capture

        score = ragas_evaluator.evaluate_context_relevance(
            synthetic_question, "un solo string de contexto", synthetic_answer
        )

        assert isinstance(captured["contexts"], list)
        assert captured["contexts"] == ["un solo string de contexto"]
        assert score == pytest.approx(0.5)

    def test_context_list_preserved(
        self, ragas_evaluator, synthetic_question, synthetic_answer, synthetic_context_list
    ):
        """Si context ya es list[str], se pasa tal cual."""
        captured = {}

        def capture(metric, sample):
            captured["contexts"] = sample.retrieved_contexts
            return 0.6

        ragas_evaluator._run_metric = capture

        ragas_evaluator.evaluate_context_relevance(
            synthetic_question, synthetic_context_list, synthetic_answer
        )

        assert captured["contexts"] == synthetic_context_list


# ---------------------------------------------------------------------------
# Tests de evaluate_faithfulness
# ---------------------------------------------------------------------------
class TestEvaluateFaithfulness:
    """Tests para evaluate_faithfulness."""

    def test_returns_float_in_unit_range(
        self, ragas_evaluator, synthetic_answer, synthetic_context
    ):
        """El score debe ser un float en [0.0, 1.0]."""
        ragas_evaluator._run_metric = MagicMock(return_value=0.93)

        score = ragas_evaluator.evaluate_faithfulness(synthetic_answer, synthetic_context)

        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0
        assert score == pytest.approx(0.93)

    def test_context_string_normalized(self, ragas_evaluator, synthetic_answer):
        """context str se normaliza a list."""
        captured = {}

        def capture(metric, sample):
            captured["contexts"] = sample.retrieved_contexts
            return 0.7

        ragas_evaluator._run_metric = capture

        ragas_evaluator.evaluate_faithfulness(synthetic_answer, "contexto plano")

        assert captured["contexts"] == ["contexto plano"]


# ---------------------------------------------------------------------------
# Tests de evaluate_answer_relevance
# ---------------------------------------------------------------------------
class TestEvaluateAnswerRelevance:
    """Tests para evaluate_answer_relevance."""

    def test_returns_float_in_unit_range(
        self, ragas_evaluator, synthetic_question, synthetic_answer
    ):
        """El score debe ser un float en [0.0, 1.0]."""
        ragas_evaluator._run_metric = MagicMock(return_value=0.77)

        score = ragas_evaluator.evaluate_answer_relevance(synthetic_question, synthetic_answer)

        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0
        assert score == pytest.approx(0.77)

    def test_builds_sample_with_question_and_answer(
        self, ragas_evaluator, synthetic_question, synthetic_answer
    ):
        """El sample debe contener la pregunta y la respuesta."""
        captured = {}

        def capture(metric, sample):
            captured["user_input"] = sample.user_input
            captured["response"] = sample.response
            return 0.5

        ragas_evaluator._run_metric = capture

        ragas_evaluator.evaluate_answer_relevance(synthetic_question, synthetic_answer)

        assert captured["user_input"] == synthetic_question
        assert captured["response"] == synthetic_answer


# ---------------------------------------------------------------------------
# Tests de evaluate_full_pipeline
# ---------------------------------------------------------------------------
class TestEvaluateFullPipeline:
    """Tests para evaluate_full_pipeline."""

    def test_returns_dict_with_all_metrics(
        self, ragas_evaluator, synthetic_question, synthetic_context, synthetic_answer
    ):
        """Debe devolver un dict con las 4 claves esperadas, todas float en [0,1]."""
        ragas_evaluator._run_metric = MagicMock(return_value=0.8)

        result = ragas_evaluator.evaluate_full_pipeline(
            synthetic_question, synthetic_context, synthetic_answer
        )

        assert isinstance(result, dict)
        expected_keys = {
            "context_relevance",
            "faithfulness",
            "answer_relevance",
            "aggregated_score",
        }
        assert set(result.keys()) == expected_keys
        for value in result.values():
            assert isinstance(value, float)
            assert 0.0 <= value <= 1.0

    def test_aggregated_is_mean_of_metrics(
        self, ragas_evaluator, synthetic_question, synthetic_context, synthetic_answer
    ):
        """aggregated_score debe ser la media aritmetica de las tres metricas."""
        scores = iter([0.6, 0.9, 0.3])  # context_relevance, faithfulness, answer_relevance

        def fake_run(metric, sample):
            return next(scores)

        ragas_evaluator._run_metric = fake_run

        result = ragas_evaluator.evaluate_full_pipeline(
            synthetic_question, synthetic_context, synthetic_answer
        )

        expected_mean = (0.6 + 0.9 + 0.3) / 3
        assert result["aggregated_score"] == pytest.approx(expected_mean)
        assert result["context_relevance"] == pytest.approx(0.6)
        assert result["faithfulness"] == pytest.approx(0.9)
        assert result["answer_relevance"] == pytest.approx(0.3)


# ---------------------------------------------------------------------------
# Tests de robustez (rangos, None, NaN, clip)
# ---------------------------------------------------------------------------
class TestScoreNormalization:
    """Tests de normalizacion y clipping de scores."""

    def test_clips_score_above_one(self, ragas_evaluator):
        """Un score > 1.0 se clipea a 1.0."""
        ragas_evaluator._run_metric = MagicMock(return_value=1.5)
        assert ragas_evaluator.evaluate_answer_relevance("q", "a") == pytest.approx(1.0)

    def test_clips_score_below_zero(self, ragas_evaluator):
        """Un score < 0.0 se clipea a 0.0."""
        ragas_evaluator._run_metric = MagicMock(return_value=-0.3)
        assert ragas_evaluator.evaluate_answer_relevance("q", "a") == pytest.approx(0.0)

    def test_none_score_becomes_zero(self, ragas_evaluator):
        """Un score None se convierte en 0.0."""
        ragas_evaluator._run_metric = MagicMock(return_value=None)
        assert ragas_evaluator.evaluate_answer_relevance("q", "a") == pytest.approx(0.0)

    def test_nan_score_becomes_zero(self, ragas_evaluator):
        """Un score NaN se convierte en 0.0."""
        ragas_evaluator._run_metric = MagicMock(return_value=float("nan"))
        score = ragas_evaluator.evaluate_answer_relevance("q", "a")
        assert not math.isnan(score)
        assert score == pytest.approx(0.0)

    def test_non_numeric_score_becomes_zero(self, ragas_evaluator):
        """Un score no numerico (p.ej. un string) se convierte en 0.0."""
        ragas_evaluator._run_metric = MagicMock(return_value="not-a-number")
        assert ragas_evaluator.evaluate_answer_relevance("q", "a") == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Tests del seam _run_metric (extraccion de dict)
# ---------------------------------------------------------------------------
class TestRunMetricDictExtraction:
    """Tests de como _run_metric maneja salidas dict de ragas."""

    def test_dict_with_score_key_is_extracted(self, ragas_evaluator):
        """Si ragas devuelve {'score': x, 'reason': ...}, _run_metric usa x."""
        from src.core.evaluation.ragas_evaluator import _clip01

        fake_metric = MagicMock()
        fake_metric.single_turn_score.return_value = {"score": 0.42, "reason": "ok"}

        raw = ragas_evaluator._run_metric(fake_metric, sample=object())

        assert raw == 0.42
        # Y el metodo publico lo normaliza al mismo valor.
        ragas_evaluator._get_metric = MagicMock(return_value=fake_metric)
        ragas_evaluator._build_sample = MagicMock(return_value=object())
        assert ragas_evaluator.evaluate_answer_relevance("q", "a") == _clip01(raw)


# ---------------------------------------------------------------------------
# Test de integracion real (smoke, marcado como integration)
# ---------------------------------------------------------------------------
@pytest.mark.integration
class TestRagasIntegrationSmoke:
    """
    Smoke test de integracion con ragas real (metrica sin LLM ni embeddings).

    Usa ``NonLLMStringSimilarity`` (no requiere LLM ni embeddings, ni llamadas
    a red) para verificar que el adapter invoca ragas correctamente a traves
    de ``_run_metric``. Marcado como integration para poder excluirlo en CI
    rapido si se desea.
    """

    def test_run_metric_calls_ragas_single_turn_score(self, ragas_evaluator):
        """_run_metric (sin mockear) debe invocar ragas y devolver un score."""
        # Skip condicional: ragas (y su stack langchain) puede no ser importable
        # en el entorno por conflictos de version. Ver spec 2026-06-23-ragas.
        pytest.importorskip("ragas")
        from ragas.dataset_schema import SingleTurnSample
        from ragas.metrics import NonLLMStringSimilarity

        metric = NonLLMStringSimilarity()
        sample = SingleTurnSample(response="hola mundo", reference="hola mundo")

        raw = ragas_evaluator._run_metric(metric, sample)

        # NonLLMStringSimilarity devuelve 1.0 para strings identicos.
        assert isinstance(raw, float)
        assert raw == pytest.approx(1.0)
