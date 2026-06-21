"""Excepciones del adaptador de Promptfoo."""

from __future__ import annotations


class PromptfooError(Exception):
    """Error base del adaptador de Promptfoo."""


class ConfigError(PromptfooError):
    """Error de carga/validación de ``promptfooconfig.yaml``."""


class ResultError(PromptfooError):
    """Error al ejecutar ``promptfoo eval`` o parsear su salida."""
