"""Definiciones de los Playwright Test Agents.

Playwright Test Agents (Microsoft, Apache 2.0) define 3 agentes que se
inicializan con ``npx playwright init-agents --loop=<loop>``:

- **planner**: genera escenarios de test desde una descripción de requisito.
- **generator**: crea código Playwright ejecutable a partir de un escenario.
- **healer**: auto-repara selectores rotos por cambios del DOM.

Aquí exponemos esas definiciones como datos (sin dependencia del binario
Node) para que sean inspeccionables, validables y documentables desde
Python y los informes del PoC.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List


class AgentRole(str, Enum):
    """Roles canónicos de los Playwright Test Agents."""

    PLANNER = "planner"
    GENERATOR = "generator"
    HEALER = "healer"


@dataclass(frozen=True)
class AgentSpec:
    """Definición tipada de un Playwright Test Agent.

    Attributes:
        role: Rol del agente (``AgentRole``).
        name: Nombre para mostrar.
        description: Responsabilidad del agente.
        loop: Agente loop para el que se configura (p. ej. ``opencode``).
    """

    role: AgentRole
    name: str
    description: str
    loop: str = "opencode"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role.value,
            "name": self.name,
            "description": self.description,
            "loop": self.loop,
        }


# Registro canónico de los 3 agentes (fuente de verdad del PoC).
AGENTS: List[AgentSpec] = [
    AgentSpec(
        role=AgentRole.PLANNER,
        name="Playwright Planner",
        description=(
            "Genera escenarios de test (casos de uso + pasos) a partir de una "
            "descripción de requisito funcional."
        ),
    ),
    AgentSpec(
        role=AgentRole.GENERATOR,
        name="Playwright Generator",
        description=(
            "Crea código Playwright ejecutable (.spec.ts) a partir de un "
            "escenario generado por el planner."
        ),
    ),
    AgentSpec(
        role=AgentRole.HEALER,
        name="Playwright Healer",
        description=(
            "Auto-repara selectores y localizadores rotos por cambios del DOM, "
            "manteniendo los specs en verde."
        ),
    ),
]

_AGENTS_BY_ROLE: Dict[AgentRole, AgentSpec] = {a.role: a for a in AGENTS}


def get_agent(role: AgentRole) -> AgentSpec:
    """Devuelve la spec del agente para el rol dado.

    Raises:
        KeyError: Si el rol no existe en el registro.
    """
    return _AGENTS_BY_ROLE[role]
