"""
ExecuteWorkflow use case.

Recorre un workflow desde start_node_id, ejecuta cada nodo segun su tipo,
acumula resultados en ExecutionContext y termina al alcanzar un nodo END
o cuando no quedan aristas aplicables.

Decisiones de diseno:
- Proteccion anti-loop infinito mediante max_steps.
- DECISION: elige arista saliente cuyo condition coincide con el status
  del ultimo NodeResult (passed/failed).
- SEMANTIC_BRANCH: usa SemanticProcessor para elegir la arista cuyo
  condition es el mas similar a la query de entrada.
- Cualquier excepcion en NodeExecutor se captura y marca el workflow
  como FAILED con mensaje descriptivo.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import List, Optional

from ..entities import (
    ExecutionContext,
    Node,
    NodeResult,
    Workflow,
    WorkflowResult,
)
from ..interfaces import NodeExecutor, NullNodeExecutor, SemanticProcessor
from ..value_objects import NodeId, NodeStatus, NodeType, WorkflowId, WorkflowStatus


DEFAULT_MAX_STEPS = 1000
DEFAULT_SEMANTIC_THRESHOLD = 0.5


@dataclass
class ExecuteWorkflowInput:
    """Input del ExecuteWorkflow use case."""

    workflow: Workflow
    branch_query: str = ""
    max_steps: int = DEFAULT_MAX_STEPS
    initial_variables: dict = field(default_factory=dict)


@dataclass
class ExecuteWorkflowOutput:
    """Output del ExecuteWorkflow use case."""

    result: WorkflowResult
    success: bool
    error_message: Optional[str] = None


class ExecuteWorkflow:
    """
    Use case: ejecuta un workflow semantico.

    Recorre el grafo dirigido desde el nodo START, ejecuta cada nodo
    mediante un NodeExecutor y decide la siguiente arista segun el tipo
    de nodo (DECISION o SEMANTIC_BRANCH).
    """

    def __init__(
        self,
        node_executor: Optional[NodeExecutor] = None,
        semantic_processor: Optional[SemanticProcessor] = None,
        semantic_threshold: float = DEFAULT_SEMANTIC_THRESHOLD,
    ) -> None:
        # Si no se inyecta ejecutor, usar NullNodeExecutor (todo PASSED).
        self.node_executor: NodeExecutor = node_executor or NullNodeExecutor()
        self.semantic_processor = semantic_processor
        self.semantic_threshold = semantic_threshold

    def execute(self, input_data: ExecuteWorkflowInput) -> ExecuteWorkflowOutput:
        workflow = input_data.workflow
        started_at = time.time()

        # Validacion inicial: workflow debe tener start_node_id
        if not workflow.has_start_node:
            return self._fail(
                workflow.id,
                started_at,
                "Workflow has no start_node_id defined",
            )

        start_node = workflow.get_node(str(workflow.start_node_id))
        if start_node is None:
            return self._fail(
                workflow.id,
                started_at,
                f"start_node_id '{workflow.start_node_id}' does not exist",
            )

        context = ExecutionContext(
            workflow_id=workflow.id,
            variables=dict(input_data.initial_variables),
        )
        node_results: List[NodeResult] = []
        current_node: Optional[Node] = start_node
        steps = 0

        try:
            while current_node is not None:
                if steps >= input_data.max_steps:
                    return self._build_result(
                        workflow_id=workflow.id,
                        node_results=node_results,
                        started_at=started_at,
                        status=WorkflowStatus.FAILED,
                        error_message=(
                            f"Max steps ({input_data.max_steps}) exceeded: possible infinite loop"
                        ),
                    )

                # Ejecutar nodo actual y medir duracion
                t0 = time.time()
                result = self.node_executor.execute(current_node, context)
                elapsed_ms = int((time.time() - t0) * 1000)
                # Preservar la duracion real medida
                result = NodeResult(
                    node_id=result.node_id,
                    status=result.status,
                    output=result.output,
                    score=result.score,
                    error=result.error,
                    duration_ms=elapsed_ms if result.duration_ms == 0 else result.duration_ms,
                    executed_at=result.executed_at,
                )
                node_results.append(result)
                context.record_result(result)
                steps += 1

                # Nodo terminal: fin natural
                if current_node.is_terminal:
                    return self._build_result(
                        workflow_id=workflow.id,
                        node_results=node_results,
                        started_at=started_at,
                        status=WorkflowStatus.COMPLETED,
                    )

                # Si el nodo fallo y no es un DECISION/SEMANTIC_BRANCH,
                # abortar la ejecucion.
                if result.status is NodeStatus.FAILED and current_node.type not in (
                    NodeType.DECISION,
                    NodeType.SEMANTIC_BRANCH,
                ):
                    return self._build_result(
                        workflow_id=workflow.id,
                        node_results=node_results,
                        started_at=started_at,
                        status=WorkflowStatus.FAILED,
                        error_message=f"Node '{current_node.id}' failed: {result.error}",
                    )

                # Decidir siguiente nodo
                current_node = self._select_next_node(
                    workflow=workflow,
                    current=current_node,
                    last_result=result,
                    branch_query=input_data.branch_query,
                )

            # Sin mas nodos: completar
            return self._build_result(
                workflow_id=workflow.id,
                node_results=node_results,
                started_at=started_at,
                status=WorkflowStatus.COMPLETED,
            )

        except Exception as exc:
            return self._build_result(
                workflow_id=workflow.id,
                node_results=node_results,
                started_at=started_at,
                status=WorkflowStatus.FAILED,
                error_message=f"Exception during execution: {exc}",
            )

    # ------------------------------------------------------------------
    # Seleccion de siguiente nodo
    # ------------------------------------------------------------------

    def _select_next_node(
        self,
        workflow: Workflow,
        current: Node,
        last_result: NodeResult,
        branch_query: str,
    ) -> Optional[Node]:
        """
        Selecciona el siguiente nodo segun el tipo del actual.

        - START / ACTION / ASSERTION: primera arista saliente
          incondicional (o la de mayor prioridad).
        - DECISION: arista cuyo condition coincide con el status del
          ultimo resultado (passed/failed/skipped).
        - SEMANTIC_BRANCH: arista cuyo condition es el mas similar
          al branch_query segun el SemanticProcessor.
        """
        edges = workflow.outgoing_edges(str(current.id))
        if not edges:
            return None

        if current.type is NodeType.DECISION:
            return self._select_decision_edge(workflow, edges, last_result)
        if current.type is NodeType.SEMANTIC_BRANCH:
            return self._select_semantic_edge(workflow, edges, branch_query)
        # Comportamiento por defecto: primera arista con condition=None,
        # o la de mayor prioridad si todas son condicionales.
        return self._select_default_edge(workflow, edges)

    def _select_decision_edge(
        self,
        workflow: Workflow,
        edges: List,
        last_result: NodeResult,
    ) -> Optional[Node]:
        """Selecciona arista cuyo condition coincide con status."""
        target_status = last_result.status.value
        for edge in edges:
            if edge.condition == target_status:
                return workflow.get_node(str(edge.target))
        # Sin match: no hay siguiente nodo (workflow termina)
        return None

    def _select_semantic_edge(
        self,
        workflow: Workflow,
        edges: List,
        branch_query: str,
    ) -> Optional[Node]:
        """Selecciona arista por similitud semantica con branch_query."""
        if not branch_query or self.semantic_processor is None:
            # Sin processor o query: fallback a default
            return self._select_default_edge(workflow, edges)

        candidates = [e.condition for e in edges if e.condition]
        if not candidates:
            return self._select_default_edge(workflow, edges)

        match = self.semantic_processor.best_match(
            query=branch_query,
            candidates=candidates,
            threshold=self.semantic_threshold,
        )
        if not match.is_match:
            return None

        # Buscar la arista cuyo condition es el candidato ganador
        for edge in edges:
            if edge.condition == match.candidate:
                return workflow.get_node(str(edge.target))
        return None

    def _select_default_edge(self, workflow: Workflow, edges: List) -> Optional[Node]:
        """Primera arista incondicional, o la de mayor prioridad."""
        # Preferir incondicionales
        for edge in edges:
            if not edge.is_conditional:
                return workflow.get_node(str(edge.target))
        # Si todas son condicionales, tomar la de mayor prioridad
        # (outgoing_edges ya devuelve ordenadas por prioridad descendente)
        return workflow.get_node(str(edges[0].target))

    # ------------------------------------------------------------------
    # Helpers de construccion de resultado
    # ------------------------------------------------------------------

    def _build_result(
        self,
        workflow_id: WorkflowId,
        node_results: List[NodeResult],
        started_at: float,
        status: WorkflowStatus,
        error_message: Optional[str] = None,
    ) -> ExecuteWorkflowOutput:
        duration_ms = int((time.time() - started_at) * 1000)
        result = WorkflowResult(
            workflow_id=workflow_id,
            status=status,
            node_results=node_results,
            duration_ms=duration_ms,
            error_message=error_message,
        )
        return ExecuteWorkflowOutput(
            result=result,
            success=status is WorkflowStatus.COMPLETED,
            error_message=error_message,
        )

    def _fail(
        self,
        workflow_id: WorkflowId,
        started_at: float,
        message: str,
    ) -> ExecuteWorkflowOutput:
        return self._build_result(
            workflow_id=workflow_id,
            node_results=[],
            started_at=started_at,
            status=WorkflowStatus.FAILED,
            error_message=message,
        )
