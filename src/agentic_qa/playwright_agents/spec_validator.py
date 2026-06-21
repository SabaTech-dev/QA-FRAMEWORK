"""Validación de specs TypeScript de Playwright (``.spec.ts``).

Validación **sintáctica** (no ejecuta el spec). Comprueba:
1. El fichero existe y tiene extensión ``.spec.ts``.
2. No está vacío.
3. Importa ``@playwright/test``.
4. Contiene al menos una llamada a ``test(...)``.

Esto basta para detectar specs mal generados por el generator agent antes
de intentar ejecutarlos.
"""

from __future__ import annotations

import re
from pathlib import Path

_PLAYWRIGHT_IMPORT_RE = re.compile(r"@playwright/test", re.MULTILINE)
_TEST_CALL_RE = re.compile(r"\btest\s*\(", re.MULTILINE)


class SpecValidationError(Exception):
    """El spec de Playwright no pasa la validación sintáctica."""


def validate_spec_file(path: Path | str) -> None:
    """Valida un fichero ``.spec.ts`` de Playwright.

    Args:
        path: Ruta al spec.

    Raises:
        SpecValidationError: Si el fichero no existe, no tiene extensión
            correcta, está vacío, no importa ``@playwright/test`` o no
            define ninguna llamada ``test(...)``.
    """
    spec = Path(path)
    if not spec.exists():
        raise SpecValidationError(f"El spec no existe: {spec}")
    if spec.suffix != ".ts" or ".spec" not in spec.name:
        raise SpecValidationError(f"El spec debe tener extensión .spec.ts, recibido: {spec.name}")
    content = spec.read_text(encoding="utf-8")
    if not content.strip():
        raise SpecValidationError(f"El spec está vacío: {spec}")
    if not _PLAYWRIGHT_IMPORT_RE.search(content):
        raise SpecValidationError(f"El spec debe importar '@playwright/test': {spec}")
    if not _TEST_CALL_RE.search(content):
        raise SpecValidationError(f"El spec debe definir al menos un test(...): {spec}")
