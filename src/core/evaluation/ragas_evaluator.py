"""
Evaluador de pipelines RAG basado en RAGAS.

Integra la libreria ``ragas`` para evaluar componentes RAG
(Retrieval-Augmented Generation) con las metricas estandar del dominio:
relevancia del contexto, fidelidad (faithfulness) y relevancia de la
respuesta.

Clean Architecture / SOLID:
    - DIP: ragas es un detalle de infraestructura que se carga de forma
      perezosa (lazy imports dentro de los metodos). El modulo es importable
      aunque ragas no este instalado; solo fallara al ejecutar una evaluacion,
      lanzando ``RagasNotAvailableError``.
    - SRP: cada metodo publico evalua una unica dimension. El seam interno
      ``_run_metric`` es el unico punto que acopla a ragas, lo que permite
      tests unitarios deterministas mockeando unicamente ese seam (sin API
      keys, sin llamadas a red).
    - OCP: nuevas metricas se anaden extendiendo el mapa de builders en
      ``_get_metric`` sin tocar los metodos publicos.

Uso basico (produccion):
    from src.core.evaluation.ragas_evaluator import RagasEvaluator

    evaluator = RagasEvaluator(llm=my_chat_model)
    score = evaluator.evaluate_faithfulness(answer, context)
    report = evaluator.evaluate_full_pipeline(question, context, answer)

Uso en tests (sin ragas real ni API keys):
    evaluator = RagasEvaluator()
    evaluator._run_metric = MagicMock(return_value=0.85)  # seam mockeado
    assert evaluator.evaluate_answer_relevance("q", "a") == 0.85
"""

from __future__ import annotations

import logging
import math
from typing import Any, Dict, List, Union

logger = logging.getLogger(__name__)

# Tipo de entrada para contextos: un unico fragmento (str) o varios (list).
ContextInput = Union[str, List[str], tuple[str, ...]]


class RagasNotAvailableError(RuntimeError):
    """
    Se lanza cuando se intenta evaluar pero ``ragas`` no es importable.

    Habitualmente se debe a conflictos de version entre ragas y langchain.
    El mensaje indica como resolverlo.
    """


# =============================================================================
# Helpers de normalizacion
# =============================================================================


def _normalize_context(context: ContextInput) -> List[str]:
    """
    Normaliza la entrada de contextos a ``list[str]``.

    ragas espera ``retrieved_contexts`` como una lista de fragmentos. Para
    comodidad del usuario aceptamos tambien un ``str`` suelto.
    """
    if isinstance(context, str):
        return [context]
    return list(context)


def _clip01(value: Any) -> float:
    """
    Convierte un score crudo de ragas a ``float`` en [0.0, 1.0].

    - ``None`` o valores no numericos -> 0.0.
    - ``NaN`` / ``inf`` -> 0.0 (no propagamos valores no representables).
    - Fuera de rango -> recorta al extremo mas cercano.

    ragas ya devuelve scores en [0,1], pero defendemos el contrato de
    QA-FRAMEWORK frente a metricas personalizadas o salidas inesperadas.
    """
    if value is None:
        return 0.0
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return 0.0
    if math.isnan(numeric) or math.isinf(numeric):
        return 0.0
    return max(0.0, min(1.0, numeric))


# =============================================================================
# RagasEvaluator
# =============================================================================


class RagasEvaluator:
    """
    Evaluador RAG basado en ragas.

    Args:
        llm: Modelo de lenguaje (objeto langchain BaseChatModel) que ragas
            usara como juez. En produccion debe inyectarse. Si es ``None``,
            el evaluador se construye igualmente (lazy); solo fallara al
            ejecutar una metrica que requiera LLM.
        embeddings: Modelo de embeddings opcional para metricas que lo
            necesitan (no usado por las metricas core de este modulo).

    Notas:
        Los tests unitarios no necesitan ``llm`` porque mockean el seam
        ``_run_metric``, eludiendo cualquier llamada al LLM.
    """

    # Nombres canonicos de las metricas en ragas 0.2.x.
    _CONTEXT_RELEVANCE = "context_relevance"
    _FAITHFULNESS = "faithfulness"
    _ANSWER_RELEVANCY = "answer_relevancy"

    def __init__(self, llm: Any = None, embeddings: Any = None) -> None:
        self.llm = llm
        self._embeddings = embeddings
        # Cache de metricas construidas (evita reimportar/reconstruir).
        self._metric_cache: Dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Seams internos (puntos de acoplamiento con ragas)
    # ------------------------------------------------------------------
    def _get_metric(self, name: str) -> Any:
        """
        Construye (y cachea) una metrica de ragas por nombre canonico.

        Lazy import: ragas solo se importa aqui. Si no es importable se
        lanza ``RagasNotAvailableError`` con instrucciones.
        """
        if name in self._metric_cache:
            return self._metric_cache[name]
        try:
            from ragas.metrics import AnswerRelevancy, ContextRelevance, Faithfulness
        except ImportError as exc:  # pragma: no cover - depende del entorno
            raise RagasNotAvailableError(
                "La libreria 'ragas' no es importable en este entorno "
                "(habitualmente por conflicto de versiones de langchain). "
                "Instala ragas y su stack langchain compatible (ver "
                "requirements.txt) o mockea el seam '_run_metric' en tests."
            ) from exc

        builders = {
            self._CONTEXT_RELEVANCE: lambda: ContextRelevance(llm=self.llm),
            self._FAITHFULNESS: lambda: Faithfulness(llm=self.llm),
            self._ANSWER_RELEVANCY: lambda: AnswerRelevancy(llm=self.llm),
        }
        if name not in builders:
            raise ValueError(f"Metrica no soportada: {name!r}")
        metric = builders[name]()
        self._metric_cache[name] = metric
        return metric

    def _build_sample(self, **fields: Any) -> Any:
        """Construye un SingleTurnSample de ragas con los campos indicados."""
        from ragas.dataset_schema import SingleTurnSample

        return SingleTurnSample(**fields)

    def _run_metric(self, metric: Any, sample: Any) -> Any:
        """
        Seam unico de ejecucion: invoca ragas y devuelve el score crudo.

        Es el unico metodo que llama a ragas para puntuar. En tests se
        reemplaza por un double (p.ej. MagicMock o una funcion) que
        devuelve un valor determinista, evitando cualquier llamada al LLM.

        Devuelve el valor CRUDO de ragas (sin normalizar): la normalizacion
        a [0, 1] y el tratamiento de None/NaN lo aplican los metodos
        publicos mediante ``_clip01``, de modo que dicha logica sea
        testeable incluso cuando este seam esta mockeado.

        ragas puede devolver ``float`` o ``dict``; en el segundo caso
        extraemos la clave ``score``.
        """
        raw = metric.single_turn_score(sample)
        if isinstance(raw, dict):
            raw = raw.get("score", 0.0)
        return raw

    # ------------------------------------------------------------------
    # API publica (especificacion del usuario)
    # ------------------------------------------------------------------
    def evaluate_context_relevance(
        self,
        question: str,
        context: ContextInput,
        answer: str,
    ) -> float:
        """
        Relevancia del contexto recuperado frente a la pregunta.

        Mide si los contextos recuperados contienen informacion util para
        responder a la pregunta. Score en [0.0, 1.0] (1.0 = muy relevante).

        Args:
            question: Pregunta del usuario.
            context: Contexto recuperado (str o list[str]).
            answer: Respuesta generada (algunas metricas la usan como pista).
        """
        metric = self._get_metric(self._CONTEXT_RELEVANCE)
        sample = self._build_sample(
            user_input=question,
            retrieved_contexts=_normalize_context(context),
            response=answer,
        )
        return _clip01(self._run_metric(metric, sample))

    def evaluate_faithfulness(self, answer: str, context: ContextInput) -> float:
        """
        Fidelidad (faithfulness) de la respuesta al contexto.

        Mide si la respuesta generada esta fundamentada en el contexto
        recuperado, sin alucinaciones. Score en [0.0, 1.0] (1.0 = totalmente
        fiel).

        Args:
            answer: Respuesta generada a evaluar.
            context: Contexto recuperado (str o list[str]) usado como verdad.
        """
        metric = self._get_metric(self._FAITHFULNESS)
        sample = self._build_sample(
            retrieved_contexts=_normalize_context(context),
            response=answer,
        )
        return _clip01(self._run_metric(metric, sample))

    def evaluate_answer_relevance(self, question: str, answer: str) -> float:
        """
        Relevancia de la respuesta respecto a la pregunta.

        Mide en que medida la respuesta aborda realmente la pregunta
        formulada. Score en [0.0, 1.0] (1.0 = muy relevante).

        Args:
            question: Pregunta del usuario.
            answer: Respuesta generada a evaluar.
        """
        metric = self._get_metric(self._ANSWER_RELEVANCY)
        sample = self._build_sample(
            user_input=question,
            response=answer,
        )
        return _clip01(self._run_metric(metric, sample))

    def evaluate_full_pipeline(
        self,
        question: str,
        context: ContextInput,
        answer: str,
    ) -> Dict[str, float]:
        """
        Evalua las tres dimensiones RAG y devuelve un informe agregado.

        Args:
            question: Pregunta del usuario.
            context: Contexto recuperado (str o list[str]).
            answer: Respuesta generada.

        Returns:
            Dict con:
                - ``context_relevance``: float en [0, 1].
                - ``faithfulness``: float en [0, 1].
                - ``answer_relevance``: float en [0, 1].
                - ``aggregated_score``: media aritmetica de las tres metricas.
        """
        context_relevance = self.evaluate_context_relevance(question, context, answer)
        faithfulness = self.evaluate_faithfulness(answer, context)
        answer_relevance = self.evaluate_answer_relevance(question, answer)
        aggregated_score = (context_relevance + faithfulness + answer_relevance) / 3.0
        return {
            "context_relevance": context_relevance,
            "faithfulness": faithfulness,
            "answer_relevance": answer_relevance,
            "aggregated_score": aggregated_score,
        }


__all__ = [
    "ContextInput",
    "RagasEvaluator",
    "RagasNotAvailableError",
]
