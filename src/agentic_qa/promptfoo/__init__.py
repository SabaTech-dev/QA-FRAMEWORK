"""Adaptador de Promptfoo — QA agéntico PoC Fase 1.

API pública:
- ``PromptfooConfig`` / ``PromptfooResult``: modelos de datos.
- ``load_config``: carga + valida ``promptfooconfig.yaml``.
- ``parse_result``: parsea el JSON de salida de ``promptfoo eval``.
- ``build_eval_command`` / ``run_promptfoo_eval``: ejecutan el binario.
- ``ConfigError`` / ``ResultError``: excepciones tipadas.
"""

from __future__ import annotations

from agentic_qa.promptfoo.errors import ConfigError, PromptfooError, ResultError
from agentic_qa.promptfoo.models import PromptfooConfig, PromptfooResult
from agentic_qa.promptfoo.config import load_config
from agentic_qa.promptfoo.parser import parse_result
from agentic_qa.promptfoo.runner import build_eval_command, run_promptfoo_eval

__all__ = [
    "PromptfooConfig",
    "PromptfooResult",
    "PromptfooError",
    "ConfigError",
    "ResultError",
    "load_config",
    "parse_result",
    "build_eval_command",
    "run_promptfoo_eval",
]
