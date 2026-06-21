# Changelog

Todos los cambios notables en este proyecto se documentan en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/es/1.1.0/),
y este proyecto se adhiere a [Semantic Versioning](https://semver.org/lang/es/spec/v2.0.0.html).

## [Unreleased]

### Added

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
