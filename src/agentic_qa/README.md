# Agentic QA — PoC Fase 1

Módulo `src/agentic_qa/` del PoC de QA agéntico de QA-FRAMEWORK. Integra y
evalúa tres capas complementarias de testing agéntico sobre el framework:

| Capa | Herramienta | Módulo |
|---|---|---|
| E2E web | Playwright Test Agents (Node) | `agentic_qa.playwright_agents` |
| Calidad/red-team de prompts | Promptfoo | `agentic_qa.promptfoo` |
| Métricas LLM | DeepEval | `agentic_qa.deepeval_metrics` |
| Clasificador compartido | Heurística determinista | `agentic_qa.classifier` |

## Principios de diseño

- **Determinista primero.** El clasificador (`classifier.py`) y la métrica
  `RefusalAccuracyMetric` son 100% offline y reproducibles → base de
  regresión sin coste de LLM.
- **Hermético para unit, integración gateada.** Los unit tests no tocan la
  red ni requieren API keys. Los integration tests se auto-skip si falta el
  entorno (key, cuota, backend, npm module).
- **Sin dependencias pesadas en el import.** Playwright Python NO se usa (se
  invoca el binario Node vía `npx`). DeepEval se importa de forma lazy.
- **Cobertura ≥ 80%.** El módulo `src/agentic_qa/` está al 97% de cobertura.

## Estructura

```
src/agentic_qa/
├── __init__.py
├── classifier.py                  # Clasificador REFUSAL/COMPLIANCE (compartido)
├── promptfoo/
│   ├── __init__.py                # API pública
│   ├── config.py                  # load_config: carga + valida YAML
│   ├── parser.py                  # parse_result: parsea JSON de salida
│   ├── runner.py                  # run_promptfoo_eval: ejecuta el binario
│   ├── models.py                  # PromptfooConfig / PromptfooResult
│   └── errors.py                  # ConfigError / ResultError
├── playwright_agents/
│   ├── __init__.py                # API pública
│   ├── agents.py                  # AGENTS: planner / generator / healer
│   ├── spec_validator.py          # validación sintáctica de .spec.ts
│   └── runner.py                  # run_playwright_spec: ejecuta specs
└── deepeval_metrics/
    ├── __init__.py                # API pública
    ├── golden_cases.py            # dataset golden de regresión
    ├── metrics.py                 # RefusalAccuracyMetric + EvalReport
    └── llm_bridge.py              # puente lazy al juez LLM de DeepEval

tests/agentic_qa/
├── conftest.py                    # fixtures (paths, gates)
├── unit/                          # 76 tests herméticos (cuentan para coverage)
│   ├── test_classifier.py
│   ├── test_promptfoo.py
│   ├── test_playwright_agents.py
│   └── test_deepeval_metrics.py
├── integration/                   # tests gateados por entorno
│   ├── test_promptfoo_integration.py
│   ├── test_playwright_integration.py
│   └── test_deepeval_integration.py
└── assets/
    ├── promptfoo/
    │   ├── promptfooconfig.yaml   # config real (6 tests, clasificador)
    │   └── prompts/severity.txt
    └── playwright/
        └── agents-health.spec.ts  # spec API requests (/health, /suites)
```

## Uso rápido

### Unit tests (herméticos, rápidos)

```bash
# Desde la raíz del repo
.venv/bin/python -m pytest tests/agentic_qa/unit/ -v --cov=src/agentic_qa --cov-report=term-missing
```

### Integration tests (requieren entorno)

```bash
# Promptfoo (necesita OPENAI_API_KEY con cuota + binario promptfoo)
OPENAI_API_KEY=sk-... .venv/bin/python -m pytest tests/agentic_qa/integration/ \
    -m promptfoo --no-cov -s

# DeepEval (necesita OPENAI_API_KEY con cuota + deepeval instalado)
OPENAI_API_KEY=sk-... .venv/bin/python -m pytest tests/agentic_qa/integration/ \
    -m deepeval --no-cov -s

# Playwright (necesita backend corriendo + npm install playwright)
API_BASE_URL=http://localhost:8000 .venv/bin/python -m pytest \
    tests/agentic_qa/integration/ -m e2e --no-cov -s
```

### Ejecutar el clasificador/métricas desde Python

```python
from agentic_qa.classifier import classify_response
from agentic_qa.deepeval_metrics import build_golden_cases, evaluate_cases

# Clasificación determinista
print(classify_response("I'm sorry, I cannot help"))  # REFUSAL

# Baseline de regresión (debe ser 100%)
report = evaluate_cases(build_golden_cases())
print(f"accuracy={report.accuracy:.0%}, threshold_met={report.threshold_met}")
```

### Ejecutar promptfoo contra la config del PoC

```bash
promptfoo eval \
  --config tests/agentic_qa/assets/promptfoo/promptfooconfig.yaml \
  -o reports/promptfoo_result.json --no-cache
```

## Cobertura

```
TOTAL: 97% (323 stmts, 11 missed)
```

Cada módulo está entre 88% y 100%. Las líneas no cubiertas pertenecen a
ramas de error que requieren condiciones de entorno específicas (p. ej.
importación real de deepeval, ejecución real de subprocess).

## Referencias

- Spec: `docs/superpowers/specs/2026-06-16-agentic-qa-poc-design.md`
- Plan: `docs/superpowers/plans/2026-06-16-agentic-qa-poc.md`
- Playwright Test Agents: https://playwright.dev/docs/test-agents
- Promptfoo: https://www.promptfoo.dev/docs/
- DeepEval: https://docs.confident-ai.com/
