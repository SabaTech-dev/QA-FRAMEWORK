"""
Value Objects for SemanticFlow Testing Domain.

Define los value objects del sistema de workflows semanticos:
tipos de nodo, estados, matches semanticos e identificadores tipados.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from enum import Enum


class _StringEnum(str, Enum):
    """Base para enums de string con helpers de estado."""

    @property
    def is_terminal(self) -> bool:
        """Sobrescrito por subclases que definen estados terminales."""
        return False


class NodeType(_StringEnum):
    """Tipos de nodo disponibles en un workflow."""

    ACTION = "action"
    DECISION = "decision"
    ASSERTION = "assertion"
    SEMANTIC_BRANCH = "semantic_branch"
    START = "start"
    END = "end"


class WorkflowStatus(_StringEnum):
    """Estado global de la ejecucion de un workflow."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

    @property
    def is_terminal(self) -> bool:
        return self in (WorkflowStatus.COMPLETED, WorkflowStatus.FAILED, WorkflowStatus.CANCELLED)


class NodeStatus(_StringEnum):
    """Estado de la ejecucion de un nodo individual."""

    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"

    @property
    def is_terminal(self) -> bool:
        return self in (NodeStatus.PASSED, NodeStatus.FAILED, NodeStatus.SKIPPED)

    @property
    def is_success(self) -> bool:
        """Solo PASSED se considera exito (SKIPPED no cuenta)."""
        return self is NodeStatus.PASSED


@dataclass(frozen=True)
class SemanticMatch:
    """
    Resultado de una comparacion semantica.

    Almacena la query, el candidato seleccionado, el score obtenido y el
    umbral aplicado. El match se considera positivo cuando el score supera
    estrictamente el umbral.
    """

    query: str
    candidate: str
    score: float
    threshold: float

    @property
    def is_match(self) -> bool:
        """True si el score supera estrictamente el umbral."""
        return self.score > self.threshold

    @property
    def confidence_margin(self) -> float:
        """Diferencia entre score y umbral (negativa si por debajo)."""
        return self.score - self.threshold


class _TypedId:
    """
    Wrapper inmutable sobre un string identificador.

    Genera un UUID v4 por defecto, o acepta un valor explicito. Las
    subclases concretas (WorkflowId, NodeId, EdgeId) aportan tipado fuerte
    para evitar mezclar IDs de entidades distintas.
    """

    __slots__ = ("_value",)

    def __init__(self, value: str | None = None) -> None:
        if value is None or value == "":
            object.__setattr__(self, "_value", str(uuid.uuid4()))
        else:
            object.__setattr__(self, "_value", str(value))

    @classmethod
    def from_string(cls, value: str) -> "_TypedId":
        """Constructor explicito desde string."""
        return cls(value)  # type: ignore[return-value]

    def __str__(self) -> str:
        return self._value

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self._value!r})"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, _TypedId):
            return self._value == other._value and type(self) is type(other)
        return NotImplemented

    def __hash__(self) -> int:
        return hash((type(self).__name__, self._value))


class WorkflowId(_TypedId):
    """Identificador tipado de Workflow."""


class NodeId(_TypedId):
    """Identificador tipado de Node."""


class EdgeId(_TypedId):
    """Identificador tipado de Edge."""
