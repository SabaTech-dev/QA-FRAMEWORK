# Changelog

Registro de cambios del proyecto QA-FRAMEWORK. Sigue el formato
[Keep a Changelog](https://keepachangelog.com/es-1.1.0/) con versionado
semántico.

## [Unreleased]

### Added — PoC de QA Agéntico (Fase 1)

- **Módulo `src/agentic_qa/`**: PoC de QA agéntico con 3 capas integradas.
  - `agentic_qa.classifier`: clasificador determinista REFUSAL/COMPLIANCE
    (heurística de keywords, offline, compartido por las 3 capas).
  - `agentic_qa.promptfoo`: adaptador de Promptfoo — `load_config`,
    `parse_result`, `run_promptfoo_eval`, `build_eval_command`.
  - `agentic_qa.playwright_agents`: adaptador de Playwright Test Agents —
    definiciones de los 3 agentes (planner/generator/healer), validador de
    specs `.spec.ts`, runner vía `npx`.
  - `agentic_qa.deepeval_metrics`: métrica determinista
    `RefusalAccuracyMetric` + dataset golden + puente lazy al juez LLM
    real de DeepEval (GEval).
- **Assets del PoC**: `promptfooconfig.yaml` (6 tests del clasificador de
  severidad) y `agents-health.spec.ts` (API requests contra `/health/live`
  y `/api/v1/suites`).
- **Suite de tests** (83 unit + 6 integration): cobertura del 97% sobre
  `src/agentic_qa/`. Integration tests auto-skip sin entorno (key, cuota,
  backend, npm module).
- **Markers de pytest**: `agentic`, `promptfoo`, `deepeval`, `llm` para
  filtrar la ejecución.
- **Dependency-groups (PEP 735)**: deepeval, pytest-cov, pyyaml declarados
  en el grupo `dev` de `pyproject.toml`.

### Fixed

- `tests/conftest.py`: el plugin `tests.fixtures.adapters` se carga ahora
  condicionalmente (solo si Playwright-Python está disponible). Antes
  rompía la colección de toda la suite en entornos sin Playwright-Python.
- `tests/fixtures/adapters.py`: el import de `playwright.async_api` es
  ahora opcional (guard con try/except) para degradación graceful.
