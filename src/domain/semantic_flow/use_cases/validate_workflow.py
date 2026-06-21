"""
ValidateWorkflow use case.

Comprueba integridad estructural de un workflow:
- Existencia de nodo START y END.
- Ausencia de ciclos (DFS iterativo).
- Ausencia de aristas rotas (nodos inexistentes).
- Deteccion de nodos huerfanos (no alcanzables desde START).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set

from ..entities import Workflow
from ..value_objects import NodeType


class ValidationSeverity(str, Enum):
    """Severidad de un problema de validacion."""

    ERROR = "error"  # Bloqueante
    WARNING = "warning"  # Informativo


@dataclass(frozen=True)
class ValidationIssue:
    """
    Problema detectado durante la validacion.

    node_id identifica el nodo afectado (puede ser None para problemas
    globales como ausencia de START).
    """

    severity: ValidationSeverity
    message: str
    node_id: Optional[str] = None

    @property
    def is_error(self) -> bool:
        return self.severity is ValidationSeverity.ERROR

    @classmethod
    def error(cls, node_id: Optional[str], message: str) -> "ValidationIssue":
        return cls(severity=ValidationSeverity.ERROR, message=message, node_id=node_id)

    @classmethod
    def warning(cls, node_id: Optional[str], message: str) -> "ValidationIssue":
        return cls(severity=ValidationSeverity.WARNING, message=message, node_id=node_id)


@dataclass
class ValidateWorkflowInput:
    """Input del ValidateWorkflow use case."""

    workflow: Workflow


@dataclass
class ValidateWorkflowOutput:
    """Output del ValidateWorkflow use case."""

    issues: List[ValidationIssue] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        """True si no hay errores (los warnings son permitidos)."""
        return not any(i.is_error for i in self.issues)

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.is_error)

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if not i.is_error)


class ValidateWorkflow:
    """
    Use case: valida la estructura de un workflow.

    Ejecuta una serie de comprobaciones deterministas y devuelve una
    lista de issues con severidad. El workflow es considerado valido
    solo si no contiene errores (los warnings son informativos).
    """

    def execute(self, input_data: ValidateWorkflowInput) -> ValidateWorkflowOutput:
        workflow = input_data.workflow
        issues: List[ValidationIssue] = []

        issues.extend(self._check_empty(workflow))
        issues.extend(self._check_start_node(workflow))
        issues.extend(self._check_end_node(workflow))
        issues.extend(self._check_edge_integrity(workflow))
        issues.extend(self._check_orphans(workflow))
        issues.extend(self._check_cycles(workflow))

        return ValidateWorkflowOutput(issues=issues)

    # ------------------------------------------------------------------
    # Chequeos individuales
    # ------------------------------------------------------------------

    def _check_empty(self, workflow: Workflow) -> List[ValidationIssue]:
        if workflow.node_count == 0:
            return [ValidationIssue.error(None, "Workflow is empty: no nodes defined")]
        return []

    def _check_start_node(self, workflow: Workflow) -> List[ValidationIssue]:
        issues: List[ValidationIssue] = []
        if not workflow.has_start_node:
            issues.append(ValidationIssue.error(None, "Workflow has no start_node_id defined"))
            return issues
        # El start_node_id debe apuntar a un nodo existente con type=START
        start = workflow.get_node(str(workflow.start_node_id))
        if start is None:
            issues.append(
                ValidationIssue.error(
                    str(workflow.start_node_id),
                    "start_node_id references a non-existent node",
                )
            )
        elif start.type is not NodeType.START:
            issues.append(
                ValidationIssue.warning(
                    str(start.id),
                    f"Start node has type {start.type.value}, expected 'start'",
                )
            )
        return issues

    def _check_end_node(self, workflow: Workflow) -> List[ValidationIssue]:
        if not workflow.end_nodes:
            return [
                ValidationIssue.error(None, "Workflow has no END node: at least one is required")
            ]
        return []

    def _check_edge_integrity(self, workflow: Workflow) -> List[ValidationIssue]:
        issues: List[ValidationIssue] = []
        for edge in workflow.edges:
            if workflow.get_node(str(edge.source)) is None:
                issues.append(
                    ValidationIssue.error(
                        str(edge.source),
                        f"Edge {edge.id} references unknown source node '{edge.source}'",
                    )
                )
            if workflow.get_node(str(edge.target)) is None:
                issues.append(
                    ValidationIssue.error(
                        str(edge.target),
                        f"Edge {edge.id} references unknown target node '{edge.target}'",
                    )
                )
        return issues

    def _check_orphans(self, workflow: Workflow) -> List[ValidationIssue]:
        """
        Nodos no alcanzables desde START. Se reportan como WARNING
        porque no bloquean la ejecucion pero suelen indicar un error
        de diseno.
        """
        if not workflow.has_start_node:
            return []
        reachable = self._reachable_from(workflow, str(workflow.start_node_id))
        issues: List[ValidationIssue] = []
        for node_id, node in workflow.nodes.items():
            if node_id not in reachable and node.type is not NodeType.START:
                issues.append(
                    ValidationIssue.warning(
                        node_id,
                        f"Node '{node_id}' is not reachable from start",
                    )
                )
        return issues

    def _check_cycles(self, workflow: Workflow) -> List[ValidationIssue]:
        """
        Deteccion de ciclos mediante DFS iterativo con colores:
        - WHITE (0): no visitado
        - GRAY  (1): en progreso (en la pila actual)
        - BLACK (2): terminado

        Si encontramos un nodo GRAY durante la exploracion, hay un ciclo.
        Iterativo para evitar stack overflow en workflows grandes.
        """
        color: Dict[str, int] = {nid: 0 for nid in workflow.nodes}
        issues: List[ValidationIssue] = []

        for start_nid in workflow.nodes:
            if color[start_nid] != 0:
                continue
            stack: List[tuple] = [(start_nid, iter(workflow.outgoing_edges(start_nid)))]
            color[start_nid] = 1
            while stack:
                current_nid, edge_iter = stack[-1]
                advanced = False
                for edge in edge_iter:
                    target_id = str(edge.target)
                    if target_id not in color:
                        # Arista rota: ya reportada en _check_edge_integrity
                        continue
                    if color[target_id] == 1:
                        # Back-edge: ciclo detectado
                        issues.append(
                            ValidationIssue.error(
                                current_nid,
                                f"Cycle detected: {current_nid} -> {target_id}",
                            )
                        )
                        continue
                    if color[target_id] == 0:
                        color[target_id] = 1
                        stack.append((target_id, iter(workflow.outgoing_edges(target_id))))
                        advanced = True
                        break
                if not advanced:
                    color[current_nid] = 2
                    stack.pop()
        return issues

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _reachable_from(self, workflow: Workflow, start_id: str) -> Set[str]:
        """Conjunto de nodos alcanzables desde start_id (BFS)."""
        reachable: Set[str] = set()
        queue: List[str] = [start_id]
        while queue:
            current = queue.pop(0)
            if current in reachable:
                continue
            reachable.add(current)
            for edge in workflow.outgoing_edges(current):
                target_id = str(edge.target)
                if target_id not in reachable:
                    queue.append(target_id)
        return reachable
