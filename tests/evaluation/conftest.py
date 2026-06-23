"""
Fixtures para los tests del evaluador RAGAS.

Datos sinteticos realistas (sin API keys) para validar el contrato de
RagasEvaluator. El evaluador se construye sin LLM: los tests mockean el
seam interno _run_metric y nunca llegan a invocar ragas real.
"""

from __future__ import annotations

import pytest

from src.core.evaluation.ragas_evaluator import RagasEvaluator


@pytest.fixture
def ragas_evaluator() -> RagasEvaluator:
    """Instancia fresca de RagasEvaluator sin LLM (lazy config)."""
    return RagasEvaluator()


@pytest.fixture
def synthetic_question() -> str:
    """Pregunta sintetica coherente con el contexto."""
    return "¿Que es Retrieval-Augmented Generation?"


@pytest.fixture
def synthetic_context() -> str:
    """Contexto sintetico unico (str)."""
    return (
        "Retrieval-Augmented Generation (RAG) combina un retriever de "
        "documentos con un modelo generativo para producir respuestas "
        "fundamentadas en fuentes externas."
    )


@pytest.fixture
def synthetic_context_list() -> list[str]:
    """Contexto sintetico como lista de fragmentos."""
    return [
        "RAG combina retrieval y generacion.",
        "El retriever selecciona documentos relevantes.",
        "El generador produce la respuesta final.",
    ]


@pytest.fixture
def synthetic_answer() -> str:
    """Respuesta sintetica fundamentada en el contexto."""
    return (
        "RAG es una tecnica que combina un retriever de documentos con un "
        "modelo generativo para producir respuestas fundamentadas."
    )
