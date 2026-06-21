"""
InMemoryWorkflowRepository: persistencia en memoria para tests y desarrollo.

No thread-safe por diseno. Para produccion debe sustituirse por una
implementacion basada en PostgreSQL u otro almacen persistente.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from src.domain.semantic_flow.entities import Workflow
from src.domain.semantic_flow.interfaces import WorkflowRepository as IWorkflowRepository
from src.domain.semantic_flow.value_objects import WorkflowId


class InMemoryWorkflowRepository(IWorkflowRepository):
    """Repositorio en memoria con diccionario id -> Workflow."""

    def __init__(self) -> None:
        self._storage: Dict[str, Workflow] = {}

    def save(self, workflow: Workflow) -> Workflow:
        key = str(workflow.id)
        self._storage[key] = workflow
        return workflow

    def get_by_id(self, workflow_id: WorkflowId) -> Optional[Workflow]:
        return self._storage.get(str(workflow_id))

    def get_by_tenant(self, tenant_id: str, limit: int = 100) -> List[Workflow]:
        matches = [wf for wf in self._storage.values() if wf.tenant_id == tenant_id]
        return matches[:limit]
