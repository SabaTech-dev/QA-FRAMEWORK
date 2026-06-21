"""Modelos de datos del adaptador de Promptfoo."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass(frozen=True)
class PromptfooConfig:
    """Representación tipada de un ``promptfooconfig.yaml``.

    Attributes:
        description: Descripción humana de la evaluación.
        prompts: Lista de prompts (string o ``file://`` refs).
        providers: Lista de providers (dict con ``id``).
        tests: Lista de casos de test declarativos.
    """

    description: str
    prompts: List[str]
    providers: List[Dict[str, Any]]
    tests: List[Dict[str, Any]]
    raw: Dict[str, Any] = field(repr=False)

    @property
    def test_count(self) -> int:
        """Número de casos de test declarados."""
        return len(self.tests)


@dataclass(frozen=True)
class PromptfooResult:
    """Resultado parseado de ``promptfoo eval``.

    Attributes:
        successes: Número de tests en verde.
        failures: Número de tests en rojo.
        total: Total de tests ejecutados.
    """

    successes: int
    failures: int
    total: int
    failed_descriptions: List[str] = field(default_factory=list)

    @property
    def pass_rate(self) -> float:
        """Ratio de acierto en [0.0, 1.0]. 0.0 si no hay tests."""
        if self.total == 0:
            return 0.0
        return self.successes / self.total

    def meets_threshold(self, threshold: float) -> bool:
        """¿El pass rate alcanza el umbral (p. ej. 0.8)?"""
        return self.pass_rate >= threshold
