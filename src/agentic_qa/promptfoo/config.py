"""Carga y validación de configuración de Promptfoo."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import yaml

from agentic_qa.promptfoo.errors import ConfigError
from agentic_qa.promptfoo.models import PromptfooConfig

_REQUIRED_FIELDS = ("prompts", "providers", "tests")
_DEFAULT_DESCRIPTION = "Promptfoo eval"


def load_config(path: Path | str) -> PromptfooConfig:
    """Carga y valida un ``promptfooconfig.yaml``.

    Args:
        path: Ruta al fichero YAML.

    Returns:
        ``PromptfooConfig`` tipado.

    Raises:
        ConfigError: Si el fichero no existe, el YAML es inválido o
            faltan campos obligatorios (``prompts``, ``providers``, ``tests``).
    """
    cfg_path = Path(path)
    if not cfg_path.exists():
        raise ConfigError(f"El fichero de configuración no existe: {cfg_path}")

    try:
        data: Dict[str, Any] = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise ConfigError(f"YAML inválido en {cfg_path}: {exc}") from exc

    if not isinstance(data, dict):
        raise ConfigError(f"La raíz del YAML debe ser un mapping, no {type(data).__name__}")

    for field_name in _REQUIRED_FIELDS:
        if field_name not in data:
            raise ConfigError(f"Campo obligatorio '{field_name}' ausente en {cfg_path}")

    return PromptfooConfig(
        description=data.get("description") or _DEFAULT_DESCRIPTION,
        prompts=list(data["prompts"]),
        providers=list(data["providers"]),
        tests=list(data["tests"]),
        raw=data,
    )
