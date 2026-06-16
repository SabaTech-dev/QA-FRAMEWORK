# Spec: PoC de QA Agéntico (Playwright Test Agents + Qodo Cover-Agent + EvalView + Promptfoo)

- **Fecha:** 2026-06-16
- **Workboard card:** `7fec0c5b`
- **Autor:** Build Agent (SabaTech) — pipeline SDD
- **Estado:** Aprobado para implementación (dispatch autónomo del workboard; revisión post-commit por Alfred)

## 1. Objetivo

Evaluar e integrar un stack de herramientas de QA "agéntico" sobre QA-FRAMEWORK mediante una Proof of Concept pequeña y verificable (TDD). El PoC debe:

1. Instalar y configurar las 4 herramientas citadas en el dispatch.
2. Demostrar cada herramienta sobre 1-2 endpoints reales del backend FastAPI.
3. Producir un informe con resultados, hallazgos y recomendaciones (incluyendo el estado de mantenimiento de cada herramienta).

## 2. Correcciones al plan original

El dispatch contenía 2 comandos erróneos, verificados durante la fase de brainstorming:

| Dispatch (incorrecto) | Real (verificado) |
|---|---|
| `npx playwright test-agents init` | `npx playwright init-agents --loop=opencode` (oficial Microsoft; 3 agentes: planner, generator, healer) |
| `pip install cover-agent` | `pip install git+https://github.com/qodo-ai/qodo-cover.git` (el paquete `cover-agent` NO existe en PyPI; el repo está **abandonado** desde 2025-06) |

EvalView (`pip install evalview`, v0.8.0) y Promptfoo (`npm i -g promptfoo`, v0.121.x, ahora parte de OpenAI) están confirmados y sanos.

## 3. Alcance (capas de QA cubiertas)

Cada herramienta cubre una capa distinta y complementaria:

| Herramienta | Capa | Objetivo del PoC |
|---|---|---|
| Playwright Test Agents | E2E web | Generar (planner) y validar (healer) un spec sobre `/health` y `/api/v1/suites` |
| Qodo Cover-Agent | Cobertura unitaria | Generar tests para un módulo backend y subir cobertura |
| Promptfoo | Calidad/red-team de prompts | Evaluar un prompt de clasificación de severidad de hallazgos |
| EvalView | Regresión de comportamiento | Snapshot + check del "agente" scan-LLM del framework |

## 4. Arquitectura del PoC

```
qa-framework/
└── agentic-qa-poc/                 # PoC autocontenido
    ├── README.md                   # Cómo ejecutar el PoC
    ├── requirements-poc.txt        # Dependencias Python del PoC
    ├── package-poc.json            # Dependencias Node del PoC
    ├── Makefile                    # Tareas: install, smoke, cover, promptfoo, evalview, all
    ├── tests/                      # Smoke tests del toolchain (TDD, pytest)
    │   ├── test_toolchain_playwright.py
    │   ├── test_toolchain_qodo.py
    │   ├── test_toolchain_promptfoo.py
    │   └── test_toolchain_evalview.py
    ├── playwright/                 # Salida de Playwright Test Agents
    │   └── specs/                  # planes generados por el planner
    ├── qodo/                       # Config + salida de Cover-Agent
    │   └── cover-agent.conf.yaml
    ├── promptfoo/                  # promptfooconfig.yaml + prompts/tests
    │   └── promptfooconfig.yaml
    ├── evalview/                   # Proyecto evalview (baseline + checks)
    │   └── evalview.yaml
    └── scripts/
        └── run_poc.sh              # Orquesta las 4 herramientas
```

### 4.1 Componentes y responsabilidades

- **`tests/` (smoke tests, pytest):** Un test por herramienta que verifica (a) el binario está instalado y responde a `--version`/`--help`, (b) la configuración mínima carga sin error. Estos son los tests TDD que se escriben PRIMERO (RED).
- **`scripts/run_poc.sh`:** Orquestador. Arranca el backend en dev (SQLite), ejecuta cada herramienta contra los endpoints objetivo, recoge artefactos en `reports/`.
- **`Makefile`:** Punto de entrada único: `make install && make all`.

### 4.2 Flujo de datos

1. `run_poc.sh` arranca `uvicorn main:app` (env `ENVIRONMENT=development`) → backend en `http://localhost:8000` con SQLite.
2. Playwright Test Agents (planner) genera un plan en `playwright/specs/`; se valida con un spec mínimo ejecutado vía API request de Playwright contra `/health` y `/api/v1/suites`.
3. Cover-Agent recibe un módulo backend + `coverage.xml` previo → genera `test_*_generated.py` → re-ejecuta pytest → reporta delta de cobertura.
4. Promptfoo evalúa el prompt de clasificación sobre un set de 5-8 test cases declarativos → genera matriz de resultados.
5. EvalView hace `snapshot` del comportamiento del agente scan-LLM (tool calls + output) → `check` compara contra baseline.

## 5. Decisiones técnicas

- **Ubicación:** `agentic-qa-poc/` en la raíz. No acopla a `dashboard/` ni a `src/`. Fácil de archivar/borrar.
- **Endpoints objetivo:** `GET /health` (smoke, siempre disponible) + `GET/POST /api/v1/suites` (CRUD real definido en `dashboard/backend/api/v1/routes.py`).
- **Backend en dev:** SQLite fallback (`DATABASE_URL` sin setear), sin Redis/Postgres obligatorios para el PoC.
- **LLM providers:**
  - Promptfoo y Cover-Agent → `OPENAI_API_KEY` (disponible en el entorno).
  - EvalView → **Ollama local** (`nomic-embed-text` para embeddings, `saba-gemma4-2b-v3-q8` o `llm-rubric` vía Ollama como judge) → 0 coste, offline.
- **Qodo Cover:** se instala desde git y se documenta su estado abandonado + alternativa recomendada en el informe.
- **Aislamiento de dependencias:** el PoC NO modifica `requirements.txt` ni `package.json` del proyecto. Usa sus propios ficheros `*-poc.*`. Instalación en venv dedicado `.venv-poc`.

## 6. Criterios de aceptación

- [ ] Los 4 smoke tests (`tests/test_toolchain_*.py`) pasan en verde.
- [ ] Cada herramienta produce al menos un artefacto verificable:
  - Playwright: ≥1 plan generado + ≥1 spec ejecutado verde.
  - Cover-Agent: ≥1 test generado que pasa y sube o mantiene cobertura.
  - Promptfoo: ≥1 `promptfoo eval` con matriz de resultados (≥5 test cases, ≥80% pass).
  - EvalView: 1 snapshot creado + 1 `check` con estado `PASSED` o `TOOLS_CHANGED`.
- [ ] `make all` ejecuta el pipeline completo sin intervención manual.
- [ ] Cobertura del código nuevo del PoC ≥80%.
- [ ] Informe `agentic-qa-poc/REPORT.md` con resultados, hallazgos y recomendaciones.
- [ ] Sin secretos en git (las keys se leen de entorno, nunca se commitean).

## 7. Tests (estrategia TDD)

Por herramienta, orden RED → GREEN → REFACTOR:

1. **RED:** smoke test que falla porque la herramienta no está instalada.
2. **GREEN:** instalar + configurar mínima → smoke test pasa.
3. **Integración:** añadir test de integración que use la herramienta contra el endpoint real.
4. **REFACTOR:** extraer helpers comunes (arranque backend, fixtures).

## 8. Riesgos y mitigaciones

| Riesgo | Probabilidad | Mitigación |
|---|---|---|
| Qodo Cover roto por abandono | Media | Instalar HEAD de git; si falla, registrar el fallo en el informe como hallazgo válido (es parte de la evaluación) |
| Playwright `init-agents` requiere frontend corriendo | Media | Usar API requests de Playwright contra el backend (no requiere UI renderizada) |
| Coste de API de OpenAI | Baja | Promptfoo/Cover con nº bajo de iteraciones; EvalView 100% Ollama |
| Backend no arranca por dependencias rotas | Media | Usar SQLite + `ENVIRONMENT=development`; si falla, aislar en `conftest` con `TestClient` de FastAPI |
| Comandos de las herramientas cambian entre versiones | Baja | Fijar versiones en `requirements-poc.txt`/`package-poc.json` |

## 9. Fuera de alcance

- Integración en CI/CD (`.github/workflows`) — se evalúa en el informe como siguiente paso.
- Sustituir la suite de tests existente del proyecto.
- Desplegar el PoC en producción.
- Entrenar/fine-tunar modelos.

## 10. Entregables

1. `agentic-qa-poc/` con todo el código y configuración (commiteado).
2. `agentic-qa-poc/REPORT.md` — informe ejecutivo con resultados por herramienta, hallazgos (incl. estado de Qodo) y recomendaciones.
3. Commit(s) con conventional commits + push al remote.
