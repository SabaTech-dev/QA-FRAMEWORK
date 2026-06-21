"""Conftest local para los tests del PoC de QA agéntico.

Fixtures compartidas por unit e integration tests. Es ligero y
autocontenido (no depende de la infraestructura pesada del framework)
para mantener los tests rápidos y herméticos.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest

ASSETS_DIR = Path(__file__).parent / "assets"


# ───────────────────────── Paths a assets ──────────────────────────
@pytest.fixture(scope="session")
def promptfoo_config_path() -> Path:
    """Ruta al ``promptfooconfig.yaml`` real del PoC."""
    return ASSETS_DIR / "promptfoo" / "promptfooconfig.yaml"


@pytest.fixture(scope="session")
def playwright_spec_path() -> Path:
    """Ruta al spec TypeScript de Playwright (API requests)."""
    return ASSETS_DIR / "playwright" / "agents-health.spec.ts"


# ─────────────── Gates para tests de integración ───────────────────
@pytest.fixture(scope="session")
def openai_api_key() -> str | None:
    """API key de OpenAI (o None si no está definida)."""
    return os.getenv("OPENAI_API_KEY")


@pytest.fixture(scope="session")
def promptfoo_available() -> bool:
    """True si el binario ``promptfoo`` está en PATH."""
    return shutil.which("promptfoo") is not None


@pytest.fixture(scope="session")
def backend_base_url() -> str:
    """URL base del backend para los specs de Playwright."""
    return os.getenv("API_BASE_URL", "http://localhost:8000")
