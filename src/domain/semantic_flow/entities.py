"""
Entities for SemanticFlow Testing Domain.

Entidades principales: Node, Edge, Workflow (aggregate root),
ExecutionContext, NodeResult y WorkflowResult.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .value_objects import (
    EdgeId,
    NodeId,
    NodeStatus,
    NodeType,
    WorkflowId,
    WorkflowStatus,
)


def _utcnow() -> datetime:
    """Helper para obtener UTC now (facilmente mockeable."""
    return datetime.now(timezone.utc)


@dataclass
class Node:
    """
    Nodo individual dentro de un workflow.

    Cada nodo tiene un tipo (ACTION, DECISION, etc.), una etiqueta
    descriptiva, inputs arbitrarios y metadata adicional.
    """

    type: NodeType
    label: str = ""
    id: NodeId = field(default_factory=NodeId)
    inputs: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_terminal(self) -> bool:
        """True si el nodo es terminal (END)."""
        return self.type is NodeType.END

    @property
    def is_semantic(self) -> bool:
        """True si el nodo requiere procesamiento semantico."""
        return self.type is NodeType.SEMANTIC_BRANCH

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "type": self.type.value,
            "label": self.label,
            "inputs": dict(self.inputs),
            "metadata": dict(self.metadata),
            "is_terminal": self.is_terminal,
            "is_semantic": self.is_semantic,
        }


@dataclass
class Edge:
    """
    Arista dirigida entre dos nodos.

    Puede ser incondicional (condition=None) o condicional. La prioridad
    determina el orden de evaluacion cuando existen varias aristas
    salientes del mismo nodo (mayor prioridad se evalua primero).
    """

    source: NodeId
    target: NodeId
    id: EdgeId = field(default_factory=EdgeId)
    condition: Optional[str] = None
    priority: int = 0

    @property
    def is_conditional(self) -> bool:
        return self.condition is not None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "source": str(self.source),
            "target": str(self.target),
            "condition": self.condition,
            "priority": self.priority,
            "is_conditional": self.is_conditional,
        }


@dataclass
class Workflow:
    """
    Aggregate root que representa un workflow semantico completo.

    Inmutable: las mutaciones (with_status, etc.) devuelven una nueva
    instancia. El grafo se almacena como diccionario de nodos + lista
    de aristas para permitir acceso O(1) por id y orden determinista.
    """

    name: str
    id: WorkflowId = field(default_factory=WorkflowId)
    nodes: Dict[str, Node] = field(default_factory=dict)
    edges: List[Edge] = field(default_factory=list)
    start_node_id: Optional[NodeId] = None
    status: WorkflowStatus = WorkflowStatus.PENDING
    tenant_id: Optional[str] = None
    created_at: datetime = field(default_factory=_utcnow)

    @property
    def node_count(self) -> int:
        return len(self.nodes)

    @property
    def edge_count(self) -> int:
        return len(self.edges)

    @property
    def has_start_node(self) -> bool:
        return self.start_node_id is not None

    @property
    def end_nodes(self) -> List[Node]:
        """Nodos marcados explicitamente como END."""
        return [n for n in self.nodes.values() if n.type is NodeType.END]

    def get_node(self, node_id: str) -> Optional[Node]:
        """Recupera un nodo por su id (string)."""
        return self.nodes.get(node_id)

    def outgoing_edges(self, node_id: str) -> List[Edge]:
        """
        Aristas salientes de un nodo, ordenadas por prioridad descendente.

        Cuando varias aristas compiten (p.ej. en un DECISION), la de mayor
        prioridad se evalua primero.
        """
        matches = [e for e in self.edges if str(e.source) == node_id]
        return sorted(matches, key=lambda e: e.priority, reverse=True)

    def with_status(self, status: WorkflowStatus) -> "Workflow":
        """Devuelve una copia con el estado actualizado (inmutable)."""
        return replace(self, status=status)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "name": self.name,
            "node_count": self.node_count,
            "edge_count": self.edge_count,
            "status": self.status.value,
            "start_node_id": str(self.start_node_id) if self.start_node_id else None,
            "tenant_id": self.tenant_id,
            "nodes": [n.to_dict() for n in self.nodes.values()],
            "edges": [e.to_dict() for e in self.edges],
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class NodeResult:
    """
    Resultado de ejecutar un nodo.

    Factory methods (passed/failed/skipped) para construccion expresiva.
    duration_ms mide el tiempo de ejecucion del nodo.
    """

    node_id: NodeId
    status: NodeStatus = NodeStatus.PENDING
    output: Dict[str, Any] = field(default_factory=dict)
    score: float = 0.0
    error: Optional[str] = None
    duration_ms: int = 0
    executed_at: datetime = field(default_factory=_utcnow)

    @classmethod
    def passed(
        cls,
        node_id: NodeId,
        output: Optional[Dict[str, Any]] = None,
        score: float = 0.0,
        duration_ms: int = 0,
    ) -> "NodeResult":
        return cls(
            node_id=node_id,
            status=NodeStatus.PASSED,
            output=output or {},
            score=score,
            duration_ms=duration_ms,
        )

    @classmethod
    def failed(
        cls,
        node_id: NodeId,
        error: str,
        output: Optional[Dict[str, Any]] = None,
        duration_ms: int = 0,
    ) -> "NodeResult":
        return cls(
            node_id=node_id,
            status=NodeStatus.FAILED,
            error=error,
            output=output or {},
            duration_ms=duration_ms,
        )

    @classmethod
    def skipped(cls, node_id: NodeId) -> "NodeResult":
        return cls(node_id=node_id, status=NodeStatus.SKIPPED)

    @property
    def is_success(self) -> bool:
        return self.status.is_success

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": str(self.node_id),
            "status": self.status.value,
            "output": dict(self.output),
            "score": self.score,
            "error": self.error,
            "duration_ms": self.duration_ms,
            "executed_at": self.executed_at.isoformat(),
        }


@dataclass
class WorkflowResult:
    """
    Resultado global de la ejecucion de un workflow.

    Agrega todos los NodeResult y calcula metricas derivadas
    (success_rate, passed_count, etc.).
    """

    workflow_id: WorkflowId
    status: WorkflowStatus = WorkflowStatus.PENDING
    node_results: List[NodeResult] = field(default_factory=list)
    duration_ms: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None

    @property
    def passed_count(self) -> int:
        return sum(1 for r in self.node_results if r.status is NodeStatus.PASSED)

    @property
    def failed_count(self) -> int:
        return sum(1 for r in self.node_results if r.status is NodeStatus.FAILED)

    @property
    def skipped_count(self) -> int:
        return sum(1 for r in self.node_results if r.status is NodeStatus.SKIPPED)

    @property
    def success_rate(self) -> float:
        """Fraccion de nodos exitosos sobre el total ejecutado."""
        total = len(self.node_results)
        if total == 0:
            return 0.0
        return self.passed_count / total

    @property
    def is_terminal(self) -> bool:
        return self.status.is_terminal

    def to_dict(self) -> Dict[str, Any]:
        return {
            "workflow_id": str(self.workflow_id),
            "status": self.status.value,
            "duration_ms": self.duration_ms,
            "passed_count": self.passed_count,
            "failed_count": self.failed_count,
            "skipped_count": self.skipped_count,
            "success_rate": self.success_rate,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message,
            "node_results": [r.to_dict() for r in self.node_results],
        }


@dataclass
class ExecutionContext:
    """
    Estado mutable que acompana la ejecucion de un workflow.

    Mantiene variables compartidas entre nodos y el historial ordenado
    de resultados. Es el unico componente mutable del dominio.
    """

    workflow_id: WorkflowId
    variables: Dict[str, Any] = field(default_factory=dict)
    history: List[NodeResult] = field(default_factory=list)
    current_node_id: Optional[NodeId] = None
    started_at: datetime = field(default_factory=_utcnow)

    def set_variable(self, key: str, value: Any) -> None:
        self.variables[key] = value

    def get_variable(self, key: str, default: Any = None) -> Any:
        return self.variables.get(key, default)

    def record_result(self, result: NodeResult) -> None:
        """Anade un resultado al historial y actualiza current_node_id."""
        self.history.append(result)
        self.current_node_id = result.node_id

    @property
    def last_result(self) -> Optional[NodeResult]:
        if not self.history:
            return None
        return self.history[-1]

    @property
    def total_duration_ms(self) -> int:
        """Suma de duraciones de todos los nodos ejecutados."""
        return sum(r.duration_ms for r in self.history)
