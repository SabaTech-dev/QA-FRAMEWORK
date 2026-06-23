# Changelog

Todos los cambios notables en este proyecto se documentan en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/es/1.1.0/),
y este proyecto se adhiere a [Semantic Versioning](https://semver.org/lang/es/spec/v2.0.0.html).

## [Unreleased]

### Added

- **Evaluador RAG con RAGAS** (`src/core/evaluation/ragas_evaluator.py`): integración
  de RAGAS para evaluar pipelines RAG (Retrieval-Augmented Generation) en tres
  dimensiones estandar.
  - **Métodos públicos**: `evaluate_context_relevance`, `evaluate_faithfulness`,
    `evaluate_answer_relevance` y `evaluate_full_pipeline` (este último devuelve un
    dict con `context_relevance`, `faithfulness`, `answer_relevance` y
    `aggregated_score` = media aritmética de las tres).
  - **Seam `_run_metric`**: único punto de acoplamiento con ragas; los tests lo
    mockean con `MagicMock` para ser deterministas y no requerir API keys de LLM.
  - **Lazy imports**: ragas se importa dentro de los métodos; el módulo es importable
    aunque ragas no esté instalado (solo lanza `RagasNotAvailableError` al evaluar).
  - **Normalización defensiva**: `context` admite `str | list[str]`; todo score se
    limita a `[0.0, 1.0]`; `None`/`NaN`/`inf` se tratan como `0.0`.
  - Excepción de dominio `RagasNotAvailableError` y helpers `_normalize_context` /
    `_clip01`.
  - **19 tests** en `tests/evaluation/test_ragas_evaluator.py` con 97% de cobertura
    sobre el nuevo módulo; smoke test de integración con skip condicional
    (`pytest.importorskip`) para no romper cuando ragas no es importable.
  - Documentación de diseño en
    `docs/superpowers/specs/2026-06-23-ragas-integration-design.md`.
  - **Nota de entorno**: ragas 0.4.x es incompatible con `langchain-community`
    0.4.x (sunset, sin `chat_models.vertexai`). Stack coherente fijado en
    `requirements.txt`: `ragas==0.2.15` + `langchain 0.3.x`. Conflictos conocidos
    (fuera de alcance): `deepeval` requiere `click<8.4.0` e `instructor` requiere
    `openai>=2.0.0`.

- **SemanticFlow Testing** (`src/domain/semantic_flow/`): framework agentic avanzado
  para orquestar workflows de testing complejos mediante procesamiento semántico.
  - **Modelo de grafo dirigido (DAG)** con 6 tipos de nodo: `ACTION`, `DECISION`,
    `ASSERTION`, `SEMANTIC_BRANCH`, `START`, `END`.
  - **Use case `ExecuteWorkflow`**: recorre el DAG desde el nodo START, ejecuta
    cada nodo con un `NodeExecutor` inyectado y decide la siguiente rama según
    el tipo de nodo (condicional o semántica).
  - **Use case `ValidateWorkflow`**: detecta ciclos (DFS iterativo), nodos
    huérfanos, aristas rotas y ausencia de START/END.
  - **`EmbeddingProcessor`** (`src/infrastructure/semantic_flow/`): procesador
    semántico basado en TF-IDF + similitud coseno, sin dependencias externas.
  - **`InMemoryWorkflowRepository`**: repositorio en memoria para tests y
    desarrollo.
  - **Executores concretos**: `ActionNodeExecutor`, `AssertionNodeExecutor`,
    `CompositeNodeExecutor`.
  - **121 tests unitarios** con 97% de cobertura sobre el nuevo módulo.
  - Documentación de diseño en
    `docs/superpowers/specs/2026-06-21-semanticflow-testing-design.md`.
  - Documentación de usuario en `docs/SEMANTIC_FLOW.md`.
  - Ejemplo de uso en `examples/semantic_flow_demo.py`.

## [1.0.0] - 2026-02-16

### Added

- Framework Core con arquitectura limpia y principios SOLID.
- Multi-framework testing (Selenium, Playwright, Appium, Cypress).
- Dashboard Web con React + TypeScript + Material-UI.
- Integration Hub (Jira, Zephyr, Azure DevOps, TestLink, HP ALM).
- CI/CD automatizado con GitHub Actions.
- Monitoreo con Prometheus + Grafana.
- Cobertura del 82.59% en backend.
- 69 tests E2E con Playwright.
