"""Adaptador de Playwright Test Agents — QA agéntico PoC Fase 1.

API pública:
- ``AgentRole`` / ``AgentSpec`` / ``AGENTS``: definiciones de los 3 agentes.
- ``get_agent``: lookup por rol.
- ``validate_spec_file`` / ``SpecValidationError``: validación sintáctica.
- ``build_init_agents_command`` / ``build_test_command`` / ``run_playwright_spec``:
  orquestación vía ``npx``.

Notas:
- No depende del paquete Python ``playwright``: usa el binario Node vía ``npx``.
- Los specs son TypeScript (``.spec.ts``) y se ejecutan con ``playwright test``.
"""

from __future__ import annotations

from agentic_qa.playwright_agents.agents import (
    AGENTS,
    AgentRole,
    AgentSpec,
    get_agent,
)
from agentic_qa.playwright_agents.spec_validator import (
    SpecValidationError,
    validate_spec_file,
)
from agentic_qa.playwright_agents.runner import (
    PlaywrightRunResult,
    build_init_agents_command,
    build_test_command,
    run_playwright_spec,
)

__all__ = [
    "AgentRole",
    "AgentSpec",
    "AGENTS",
    "get_agent",
    "SpecValidationError",
    "validate_spec_file",
    "PlaywrightRunResult",
    "build_init_agents_command",
    "build_test_command",
    "run_playwright_spec",
]
