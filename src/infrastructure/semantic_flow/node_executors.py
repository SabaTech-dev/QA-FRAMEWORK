"""
Node executors concretos para SemanticFlow.

Cada tipo de nodo (ACTION, ASSERTION) puede tener un executor dedicado.
CompositeNodeExecutor permite combinar varios executors en uno solo.
"""

from __future__ import annotations

from typing import Callable, Dict, Optional

from src.domain.semantic_flow.entities import ExecutionContext, Node, NodeResult
from src.domain.semantic_flow.interfaces import NodeExecutor
from src.domain.semantic_flow.value_objects import NodeType


# Tipo callable para handlers de ACTION: (node, context) -> NodeResult
ActionHandler = Callable[[Node, ExecutionContext], NodeResult]


class ActionNodeExecutor(NodeExecutor):
    """
    Executor para nodos ACTION.

    Recibe un diccionario de handlers {node_id: callable}. Si un nodo
    no tiene handler registrado, se marca como PASSED sin output.
    """

    def __init__(self, handlers: Optional[Dict[str, ActionHandler]] = None) -> None:
        self.handlers: Dict[str, ActionHandler] = handlers or {}

    def register(self, node_id: str, handler: ActionHandler) -> None:
        self.handlers[node_id] = handler

    def execute(self, node: Node, context: ExecutionContext) -> NodeResult:
        handler = self.handlers.get(str(node.id))
        if handler is None:
            return NodeResult.passed(node_id=node.id)
        return handler(node, context)


class AssertionNodeExecutor(NodeExecutor):
    """
    Executor para nodos ASSERTION.

    Evalua una asercion definida en node.inputs['assert'] (callable
    (context) -> bool). Si devuelve True, PASSED; si False, FAILED.
    """

    def execute(self, node: Node, context: ExecutionContext) -> NodeResult:
        assertion = node.inputs.get("assert")
        if not callable(assertion):
            return NodeResult.passed(node_id=node.id)
        try:
            ok = bool(assertion(context))
        except Exception as exc:
            return NodeResult.failed(node_id=node.id, error=f"Assertion raised: {exc}")
        if ok:
            return NodeResult.passed(node_id=node.id, output={"assertion": True})
        return NodeResult.failed(
            node_id=node.id,
            error="Assertion returned False",
            output={"assertion": False},
        )


class CompositeNodeExecutor(NodeExecutor):
    """
    Compone varios executors y despacha segun el tipo de nodo.

    Permite registrar un executor por NodeType. Los tipos no registrados
    se marcan como PASSED (comportamiento por defecto).
    """

    def __init__(self) -> None:
        self._registry: Dict[NodeType, NodeExecutor] = {}

    def register(self, node_type: NodeType, executor: NodeExecutor) -> "CompositeNodeExecutor":
        self._registry[node_type] = executor
        return self

    def execute(self, node: Node, context: ExecutionContext) -> NodeResult:
        executor = self._registry.get(node.type)
        if executor is None:
            return NodeResult.passed(node_id=node.id)
        return executor.execute(node, context)
