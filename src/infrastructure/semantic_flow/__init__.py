"""
SemanticFlow infrastructure adapters.

Implementaciones concretas de los Protocols definidos en el dominio:
- EmbeddingProcessor: SemanticProcessor basado en TF-IDF + cosine similarity
- InMemoryWorkflowRepository: WorkflowRepository en memoria para tests
- Node executors: implementaciones concretas por tipo de nodo
"""

from .embedding_processor import EmbeddingProcessor
from .in_memory_repository import InMemoryWorkflowRepository
from .node_executors import (
    ActionNodeExecutor,
    AssertionNodeExecutor,
    CompositeNodeExecutor,
)

__all__ = [
    "EmbeddingProcessor",
    "InMemoryWorkflowRepository",
    "ActionNodeExecutor",
    "AssertionNodeExecutor",
    "CompositeNodeExecutor",
]
