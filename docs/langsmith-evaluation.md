# Evaluación LangSmith vs Langfuse — Trajectory Evaluation para Pipeline de Agentes QA

**Generated:** 2026-06-23 | **Version:** 1.0 | **Author:** Build Agent (SDD Pipeline)
**Workboard card:** `c2f82a85` — [P1] Configurar LangSmith trajectory evaluation

---

## Decisión

**Mantener Langfuse como plataforma de observabilidad y evaluación de agentes. No adoptar LangSmith.**

LangSmith ofrece un conjunto de capacidades de evaluación de trayectoria **funcionalmente equivalente** al de Langfuse, pero su modelo comercial (autohosteo restringido a Enterprise, pricing pay-as-you-go que escala con el volumen de trazas) lo hace **más caro y menos alineado** con la naturaleza autohosteada y open-source de QA-FRAMEWORK. Langfuse cubre el 100 % de los requisitos de *trajectory evaluation* del pipeline de agentes QA sin coste de licencia y sin vendor lock-in.

| Dimensión | Veredicto |
|---|---|
| ¿Aporta LangSmith valor **funcional** sobre Langfuse? | **No** — paridad de capacidades en evaluación de trayectoria. |
| ¿Aporta valor **económico/estratégico**? | **No** — autohosteo de pago, dependencia comercial, coste recurrente. |
| ¿Crear PoC de LangSmith? | **No** — no se justifica el coste de integración frente al beneficio marginal. |
| Acción recomendada | Integrar Langfuse en el pipeline `src/agentic_qa` (tracing + LLM-as-judge sobre trazas). |

---

## Contexto

### El pipeline de agentes QA

QA-FRAMEWORK incluye un pipeline de agentes (`src/agentic_qa`) compuesto por:

- **`classifier`** — clasificación de intenciones de test.
- **`promptfoo`** — evaluación offline de prompts (runner, parser, config).
- **`deepeval_metrics`** — métricas LLM-as-judge (golden cases, llm_bridge).
- **`playwright_agents`** — agentes de ejecución E2E (agents, runner, spec_validator).

El agente de navegador se integra con `browser-use` + `langchain-groq` (ver `dashboard/backend/services/ai/browser_use_service.py`).

### Observabilidad actual

- **structlog** para logging estructurado (dashboard).
- **Prometheus + Grafana** para métricas de infraestructura.
- **promptfoo + deepeval** para evaluación de prompts/modelos.
- **Ni Langfuse ni LangSmith están integrados actualmente.** Langfuse es el baseline planificado para observabilidad de LLM/agentes (este documento valida esa decisión).

### Por qué importa la evaluación de trayectoria

Un agente QA ejecuta una **secuencia de pasos** (decisión → selección de herramienta → llamada → observación → siguiente decisión). Esta secuencia es la *trayectoria*. Evaluar solo el resultado final (pass/fail del test) es insuficiente: dos ejecuciones pueden llegar al mismo resultado con eficiencias muy distintas (número de pasos, coste en tokens, herramientas innecesarias, alucinaciones intermedias). La evaluación de trayectoria permite medir la **calidad del proceso** del agente, no solo su output.

---

## Qué ofrece LangSmith (Trajectory Evaluation)

LangSmith trata la evaluación como un proceso de dos fases: **offline** (pre-deploy, sobre datasets) y **online** (producción, sobre trazas reales).

### Modelo de datos para trayectorias

- **Run**: traza de una ejecución. Contiene inputs, outputs y **intermediate steps** (todas las *child runs*: llamadas LLM, tool calls). Esta secuencia de *child runs* **es la trayectoria**.
- **Thread**: colección de *runs* relacionados (conversación multi-turno o ejecución multi-agente).
- Un agente que ejecuta N pasos produce un *run* raíz con N *child runs* anidados; los evaluadores reciben el *run* completo y pueden inspeccionar toda la trayectoria.

### Evaluadores (scorers)

| Tipo | Descripción | Útil para trayectoria |
|---|---|---|
| **LLM-as-judge** | Un LLM puntúa según una rúbrica codificada en el prompt. Referenced o reference-free. | Sí — juzgar si la secuencia de pasos fue eficiente/correcta. |
| **Code** | Funciones deterministas (estructura, compilación, match exacto). | Sí — contar pasos, validar formato de args, aserciones. |
| **Human** | Revisión manual vía *annotation queues* (single-run y pairwise). | Sí — inspección cualitativa de la trayectoria. |
| **Pairwise** | Comparación A/B entre dos versiones del agente. | Sí — decidir qué versión recorre mejor trayectoria. |

### Capacidades adicionales

- **Datasets / Examples / Experiments**: conversión de trazas reales en casos de test; comparación lado a lado de experimentos.
- **Online evaluators**: reglas automáticas sobre tráfico en producción con *sampling rate* para controlar costes.
- **LangSmith Engine** (Plus/Enterprise): detección autónoma de fallos recurrentes y diagnóstico de causa raíz.
- **Prompt Hub / Playground**: iteración de prompts.

### Pricing (factor decisivo)

| Plan | Precio | Trazas base | Autohosteo |
|---|---|---|---|
| Developer | $0/seat + pay-as-you-go | 5k/mes | No |
| Plus | $39/seat/mes + pay-as-you-go | 10k/mes incluidas | No |
| Enterprise | Custom | Custom | Sí (hibrido/on-prem) |

**Implicación para QA-FRAMEWORK:** cada ejecución de suite de tests genera múltiples trazas (un agente playwright con 10 pasos = 1 run + 10 child runs). Un volumen medio de QA puede superar fácilmente las 5k–10k traces/mes, activando el pricing variable. El autohosteo —requerido para entornos on-prem/air-gapped— exige el plan Enterprise.

---

## Qué ofrece Langfuse

Langfuse es **open source** (autohosteable con el mismo codebase que su cloud) y framework-agnostic.

### Modelo de datos para trayectorias

- **Trace**: la unidad de observabilidad (equivalente al *run* de LangSmith).
- **Observation**: unidad anidada dentro de un trace (tipos: `SPAN`, `GENERATION`, `EVENT`). Un agente que ejecuta N pasos produce un trace con N observations anidadas — **esta jerarquía es la trayectoria**, equivalente directa a los *intermediate steps* de LangSmith.
- **Session**: agrupación de traces multi-turno (equivalente a *thread*).

### Evaluación

Langfuse soporta el mismo conjunto de métodos de evaluación:

- **LLM-as-a-Judge** sobre trazas en producción (online) y sobre datasets (offline).
- **Code Evaluators** deterministas.
- **Annotation Queues** para evaluación humana.
- **Datasets & Experiments** para evaluación offline con comparación lado a lado.
- **CI/CD experiments** para bloquear deploys ante regresiones.
- **Score Analytics** y **custom dashboards** para tendencias temporales.

### Arquitectura y autohosteo

Stack 100 % open source: **Postgres** (OLTP) + **ClickHouse** (OLAP, donde viven trazas y scores) + **Redis** (cache/cola) + **S3/Blob** (eventos crudos). Ingestión asíncrona encolada (sin impacto en latencia de la aplicación). Despliegue vía Docker Compose, Kubernetes (Helm), AWS/Azure/GCP (Terraform) o Railway.

### Pricing

- **Self-hosted**: gratuito (algunas features avanzadas requieren *license key* para uso no personal, pero el núcleo de tracing + evaluación es libre).
- **Langfuse Cloud**: tier generoso con pricing asequible.

---

## Tabla comparativa

| Criterio | LangSmith | Langfuse | Ganador para QA-FRAMEWORK |
|---|---|---|---|
| Captura de trayectoria (pasos intermedios) | Runs + child runs | Trace + nested observations | **Empate** (equivalentes) |
| LLM-as-judge sobre trayectoria | Sí (referenced/free) | Sí (referenced/free) | **Empate** |
| Code evaluators deterministas | Sí | Sí | **Empate** |
| Evaluación humana (annotation queues) | Single-run + pairwise | Annotation queues + experiments | **Empate** |
| Offline (datasets/experiments) | Sí | Sí | **Empate** |
| Online (scoring en producción) | Sí (reglas + sampling) | Sí (LLM-as-judge + SDK) | **Empate** |
| Prompt management + playground | Prompt Hub/Playground | Prompt management | **Empate** |
| Detección autónoma de fallos | LangSmith Engine (pago) | — | LangSmith (si se valora y se paga) |
| Integración con LangChain/Groq | Nativa (ecosistema propio) | Vía integración LangChain/OTEL | LangSmith (ligera ventaja) |
| Framework-agnostic | Integraciones amplias | Nativamente agnostic | **Langfuse** |
| **Licencia** | Propietario | **Open source (MIT)** | **Langfuse** |
| **Autohosteo gratuito** | No (Enterprise = custom $) | **Sí** | **Langfuse** |
| **Coste recurrente** | Pay-as-you-go + seats | $0 self-hosted | **Langfuse** |
| Alineación con stack del proyecto | Añade dependencia comercial | Encaja con Docker/Coolify/OSS | **Langfuse** |

---

## Análisis específico para QA-FRAMEWORK

La decisión no se basa solo en paridad de features, sino en el **encaje con el contexto del proyecto**:

1. **Volumen de trazas alto y predecible.** Un framework de QA ejecuta suites repetidamente (CI, regresión, nightly). Cada test instrumentado emite trazas. El modelo pay-as-you-go de LangSmith convierte la observabilidad en un **coste operativo que crece con el uso del producto**, penalizando precisamente el éxito (más tests ejecutados = más factura). Langfuse autohosteado tiene coste marginal cero.

2. **Filosofía autohosteada.** El proyecto despliega en Docker, Coolify y Railway; ya opera su propio stack de observabilidad (Prometheus/Grafana). Langfuse encaja en ese patrón (un compose más); LangSmith rompe el modelo al exigir cloud o Enterprise para autohosteo.

3. **Vendor lock-in al ecosistema LangChain.** El agente actual usa `langchain-groq` + `browser-use`, pero el dominio (`src/domain`) y el resto del framework son agnostic. Atar la observabilidad/evaluación a LangSmith aumenta la dependencia de un único vendor. Langfuse es neutral y sobrevive a futuras migraciones de framework.

4. **Open source como valor del proyecto.** El repo ya integra múltiples herramientas OSS y mantiene SBOM, scans Trivy/Bandit y pipelines abiertos. Añadir una dependencia propietaria para una función que OSS cubre es incongruente.

5. **La paridad funcional es real.** Ninguna capacidad de *trajectory evaluation* requerida (capturar pasos intermedios, puntuar con LLM-as-judge, comparar experimentos, evaluar en producción) es exclusiva de LangSmith. La única funcionalidad diferencial —LangSmith Engine (auto-mejora de agentes)— es de pago, opcional y no bloqueante para los objetivos de QA.

### Análisis de coste orientativo

| Escenario (traces/mes) | LangSmith Developer | Langfuse Self-hosted |
|---|---|---|
| 5 000 (incluidas) | $0 | $0 (+ infra propia) |
| 50 000 (~10× umbral) | Pay-as-you-go significativo | $0 (+ infra propia) |
| 500 000 (QA a escala) | Coste elevado recurrente | $0 (+ infra propia, escalable con ClickHouse) |

> Nota: los importes exactos de LangSmith dependen de la tarifa vigente por traza; el punto relevante es la **estructura del modelo**: Langfuse desacopla coste de volumen, LangSmith no.

---

## Cuándo reconsiderar LangSmith

Esta decisión se reevaluaría si se cumple **alguna** de estas condiciones:

- [ ] Se adopta LangGraph/LangChain como núcleo **exclusivo** del pipeline de agentes y se quiere aprovechar la integración nativa + Studio.
- [ ] Se requiere **LangSmith Engine** (detección autónoma de fallos y auto-mejora) y se aprueba su coste.
- [ ] Aparece un requisito de *trajectory evaluation* que Langfuse no pueda cubrir (hoy no existe tal requisito).
- [ ] El equipo decide externalizar la observabilidad y aceptar el TCO del plan Plus/Enterprise.

Mientras tanto, **Langfuse es la opción por defecto**.

---

## Camino de integración de Langfuse (próximo paso)

Dado que Langfuse es la herramienta elegida, la integración en el pipeline de agentes QA seguiría estos pasos (fuera del alcance de esta card; tarea separada):

1. **Despliegue**: añadir `langfuse` al `docker-compose.unified.yml` (web + worker + ClickHouse + Postgres + Redis). UI en `:3001`.
2. **Instrumentación**: usar el SDK Python de Langfuse (`langfuse` package) o la integración OpenTelemetry para envolver `classifier`, `playwright_agents` y `browser_use_service`. Cada paso del agente = una *observation* anidada bajo un *trace* por ejecución de test.
3. **Evaluación**:
   - *Online*: LLM-as-judge automático sobre traces en producción (eficiencia de pasos, uso de herramientas, alucinaciones).
   - *Offline*: convertir traces fallidos en un dataset y lanzar experiments para comparar versiones del agente antes de promocionarlas.
4. **CI/CD gate*: usar *CI/CD experiments* de Langfuse para bloquear merges que degraden métricas de trayectoria.
5. **Dashboards**: exponer tendencias de coste/tokens/pasos en custom dashboards, complementando Grafana.

---

## Conclusión

LangSmith es un producto sólido cuya propuesta de *trajectory evaluation* es **indistinguible** de la de Langfuse en lo funcional. La diferencia es de **modelo**: LangSmith es comercial con autohosteo de pago y coste que escala con el uso; Langfuse es open source, autohosteable y framework-agnostic. Para un framework de QA —alto volumen de trazas, filosofía self-hosted, stack OSS existente— Langfuse es la elección técnicamente correcta y económicamente sensata.

**No se crea PoC de LangSmith.** Se documenta esta justificación y se confirma Langfuse como plataforma de evaluación de agentes.

---

## Fuentes

- LangSmith — Evaluation: https://docs.smith.langchain.com/evaluation
- LangSmith — Evaluation concepts (runs, threads, evaluators): https://docs.smith.langchain.com/evaluation/concepts
- LangSmith — Pricing: https://www.langchain.com/pricing
- LangSmith — Observability: https://docs.smith.langchain.com/observability-quickstart
- Langfuse — Tracing (traces, sessions, observations): https://langfuse.com/docs/tracing
- Langfuse — Evaluation overview: https://langfuse.com/docs/evaluation/overview
- Langfuse — Self-hosting (arquitectura, licencia): https://langfuse.com/self-hosting
