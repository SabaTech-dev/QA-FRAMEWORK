"""
SemanticFlow Testing Domain Module.

Modulo agentic avanzado para workflows de testing complejos con
procesamiento semantico. Permite definir workflows como grafos
dirigidos (DAG) de nodos tipados (ACTION, DECISION, ASSERTION,
SEMANTIC_BRANCH, START, END) y ejecutarlos mediante un agente
orquestador que decide la siguiente rama en funcion del resultado
del nodo anterior o de similitud semantica entre textos.

Componentes principales:
- Entities: Workflow, Node, Edge, NodeResult, WorkflowResult, ExecutionContext
- Value objects: NodeType, WorkflowStatus, NodeStatus, SemanticMatch, IDs tipados
- Interfaces: SemanticProcessor, NodeExecutor, WorkflowRepository (Protocols)
- Use cases: ExecuteWorkflow, ValidateWorkflow
"""

from .value_objects import (
    EdgeId,
    NodeId,
    NodeStatus,
    NodeType,
    SemanticMatch,
    WorkflowId,
    WorkflowStatus,
)
from .entities import (
    Edge,
    ExecutionContext,
    Node,
    NodeResult,
    Workflow,
    WorkflowResult,
)
from .interfaces import (
    NodeExecutor,
    NullNodeExecutor,
    SemanticProcessor,
    WorkflowRepository,
)
from .use_cases import (
    ExecuteWorkflow,
    ExecuteWorkflowInput,
    ExecuteWorkflowOutput,
    ValidateWorkflow,
    ValidateWorkflowInput,
    ValidateWorkflowOutput,
    ValidationIssue,
    ValidationSeverity,
)

__all__ = [
    # Value objects
    "EdgeId",
    "NodeId",
    "NodeStatus",
    "NodeType",
    "SemanticMatch",
    "WorkflowId",
    "WorkflowStatus",
    # Entities
    "Edge",
    "ExecutionContext",
    "Node",
    "NodeResult",
    "Workflow",
    "WorkflowResult",
    # Interfaces
    "NodeExecutor",
    "NullNodeExecutor",
    "SemanticProcessor",
    "WorkflowRepository",
    # Use cases
    "ExecuteWorkflow",
    "ExecuteWorkflowInput",
    "ExecuteWorkflowOutput",
    "ValidateWorkflow",
    "ValidateWorkflowInput",
    "ValidateWorkflowOutput",
    "ValidationIssue",
    "ValidationSeverity",
]
