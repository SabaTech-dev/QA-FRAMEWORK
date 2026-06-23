"""
Modulo de evaluacion RAG.

Integra RAGAS para evaluar componentes RAG (Retrieval-Augmented
Generation). ragas es un detalle de infraestructura que se carga de forma
perezosa (lazy imports dentro de los metodos de RagasEvaluator), de modo que
este modulo es importable aunque ragas no este instalado (Clean Architecture /
DIP).
"""

from src.core.evaluation.ragas_evaluator import (
    ContextInput,
    RagasEvaluator,
    RagasNotAvailableError,
)

__all__ = [
    "ContextInput",
    "RagasEvaluator",
    "RagasNotAvailableError",
]
