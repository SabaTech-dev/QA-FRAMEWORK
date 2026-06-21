"""
Interfaces for SemanticFlow Testing Domain.

Define los contratos (Protocols) que las implementaciones de
infraestructura deben satisfacer. El dominio depende solo de estas
abstracciones, no de implementaciones concretas (DIP).
"""

from __future__ import annotations

from typing import List, Optional, Protocol

from .entities import ExecutionContext, Node, NodeResult, Workflow
from .value_objects import SemanticMatch, WorkflowId


class SemanticProcessor(Protocol):
    """
    Procesador semantico para ramificacion por similitud.

    Las implementaciones pueden usar embeddings (TF-IDF, sentence
    transformers, etc.). El dominio solo exige el contrato.
    """

    def embed(self, text: str) -> List[float]:
        """Vectoriza un texto en una lista de floats."""
        ...

    def similarity(self, a: str, b: str) -> float:
        """Similitud en [0.0, 1.0] entre dos textos."""
        ...

    def best_match(
        self,
        query: str,
        candidates: List[str],
        threshold: float = 0.5,
    ) -> SemanticMatch:
        """
        Selecciona el candidato mas similar a la query.

        Args:
            query: Texto de referencia (normalmente el output observado).
            candidates: Lista de candidatos (valores de condition).
            threshold: Umbral de aceptacion.

        Returns:
            SemanticMatch con el mejor candidato y su score.
        """
        ...


class NodeExecutor(Protocol):
    """
    Ejecutor de nodos.

    Cada tipo de nodo (ACTION, DECISION, ASSERTION) es ejecutado por
    una implementacion concreta. El ejecutor recibe el nodo y el
    contexto, y devuelve un NodeResult.
    """

    def execute(self, node: Node, context: ExecutionContext) -> NodeResult:
        """
        Ejecuta un nodo y devuelve su resultado.

        Args:
            node: Nodo a ejecutar.
            context: Contexto de ejecucion (variables, historial).

        Returns:
            NodeResult con el estado (PASSED/FAILED) y output.
        """
        ...


class WorkflowRepository(Protocol):
    """Repositorio para persistir workflows."""

    def save(self, workflow: Workflow) -> Workflow:
        """Persiste un workflow (create or update)."""
        ...

    def get_by_id(self, workflow_id: WorkflowId) -> Optional[Workflow]:
        """Recupera un workflow por id."""
        ...

    def get_by_tenant(self, tenant_id: str, limit: int = 100) -> List[Workflow]:
        """Recupera workflows de un tenant."""
        ...


class NullNodeExecutor:
    """
    Implementacion por defecto de NodeExecutor.

    No realiza ninguna accion real: marca todos los nodos como PASSED.
    Util para workflows donde solo interesa el flujo (START -> END).
    """

    def execute(self, node: Node, context: ExecutionContext) -> NodeResult:
        return NodeResult.passed(node_id=node.id)
