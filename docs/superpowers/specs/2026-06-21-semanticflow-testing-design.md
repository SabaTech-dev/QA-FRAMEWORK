# SemanticFlow Testing - Design Doc

**Fecha:** 2026-06-21
**Estado:** Aprobado (auto-aprobado según directiva del usuario)
**Autor:** Build Agent (SDD Pipeline)

## 1. Objetivo

Implementar **SemanticFlow Testing**: un framework agentic avanzado para orquestar
workflows de testing complejos mediante procesamiento semántico del contexto y
los resultados. A diferencia de los tests lineales clásicos, SemanticFlow permite
ramificar, decidir y autorregenerarse en base al significado semántico de las
respuestas observadas.

## 2. Brainstorming — 3 enfoques explorados

### Enfoque A: Workflow como Grafo Dirigido (DAG) + Agente Orquestador
**Idea:** Modelar el workflow como un DAG de nodos tipados (acción, decisión,
assertion, branch semántico). Un agente orquestador recorre el grafo usando
un procesador semántico para elegir la siguiente rama.

- **Pros:**
  - Representación natural de workflows complejos con bucles y ramas.
  - Decisiones basadas en similitud semántica (embeddings) o LLM.
  - Fácil de visualizar y razonar.
  - Extensible: nuevos tipos de nodos sin tocar el orquestador.
- **Cons:**
  - Más complejo de implementar que una secuencia lineal.
  - Requiere validación de ciclos/detección de ciclos.

### Enfoque B: State Machine Finita (FSM) con transiciones semánticas
**Idea:** Modelo FSM donde las transiciones se deciden por similitud semántica
entre el estado actual y los posibles estados destino.

- **Pros:**
  - Semántica formal bien definida.
  - Detección de estados no alcanzables trivial.
- **Cons:**
  - Menos expresivo que un DAG para workflows con datos contextuales.
  - Transiciones semánticas difíciles de serializar y testear.

### Enfoque C: Pipeline secuencial con pasos condicionales
**Idea:** Lista ordenada de pasos, cada uno con una precondición semántica que
decide si se ejecuta o se salta.

- **Pros:**
  - Muy simple de implementar y testear.
  - Bajo acoplamiento.
- **Cons:**
  - No soporta bifurcaciones reales ni paralelismo.
  - Limitado para workflows "complejos" (requisito explícito).

### Selección: **Enfoque A (DAG + Agente Orquestador)**

**Justificación:**
- El usuario pidió explícitamente "workflows complejos" → A es el más expresivo.
- Encaja con la arquitectura limpia del QA-FRAMEWORK (entidades, value objects,
  use cases, interfaces).
- Permite procesamiento semántico real (decisiones basadas en similitud
  coseno de embeddings, sin necesidad de LLM externo para los tests).
- Los nodos tipados (`ActionNode`, `DecisionNode`, `AssertionNode`,
  `SemanticBranchNode`) respetan OCP de SOLID.

## 3. Arquitectura

Sigue Clean Architecture como el resto del proyecto:

```
src/domain/semantic_flow/
├── __init__.py
├── value_objects.py      # Enums + frozen dataclasses (NodeId, EdgeId, ...)
├── entities.py           # Workflow, Node, Edge, ExecutionResult, ExecutionContext
├── interfaces.py         # Protocols: SemanticProcessor, NodeExecutor, WorkflowRepository
└── use_cases/
    ├── __init__.py
    ├── execute_workflow.py   # Caso de uso principal: ExecuteWorkflow
    └── validate_workflow.py  # Caso de uso: ValidateWorkflow (ciclos, nodos huérfanos)

src/infrastructure/semantic_flow/
├── __init__.py
├── embedding_processor.py    # SemanticProcessor con similitud coseno
├── node_executors.py         # Implementaciones concretas por tipo de nodo
└── in_memory_repository.py   # Repo en memoria para tests

tests/unit/domain/semantic_flow/
├── __init__.py
├── test_value_objects.py
├── test_entities.py
├── test_execute_workflow.py
├── test_validate_workflow.py
└── test_semantic_branch.py
```

## 4. Componentes clave

### Value Objects
- `NodeType` (enum): `ACTION`, `DECISION`, `ASSERTION`, `SEMANTIC_BRANCH`, `START`, `END`.
- `WorkflowStatus` (enum): `PENDING`, `RUNNING`, `COMPLETED`, `FAILED`, `CANCELLED`.
- `NodeStatus` (enum): `PENDING`, `RUNNING`, `PASSED`, `FAILED`, `SKIPPED`.
- `SemanticMatch` (frozen dataclass): `query`, `candidate`, `score`, `threshold`.
- `WorkflowId`, `NodeId`, `EdgeId`: typed strings.

### Entities
- `Node` (dataclass): `id`, `type`, `label`, `action` (callable spec), `inputs`, `metadata`.
- `Edge` (dataclass): `id`, `source`, `target`, `condition` (opcional), `priority`.
- `Workflow` (dataclass): `id`, `name`, `nodes: dict`, `edges: list`, `start_node_id`,
  `tenant_id`. Inmutable con métodos `add_node`, `add_edge`, `with_status`.
  Propiedades: `is_valid_dag`, `end_nodes`, `has_cycle` (Lazy/validador externo).
- `ExecutionContext` (dataclass): `workflow_id`, `current_node_id`, `variables`,
  `history` (lista de NodeResult), `started_at`.
- `NodeResult` (dataclass): `node_id`, `status`, `output`, `score`, `error`.
- `WorkflowResult` (dataclass): `workflow_id`, `status`, `node_results`,
  `duration_ms`, `success_rate`.

### Interfaces (Protocols)
- `SemanticProcessor`: `embed(text) -> list[float]`, `similarity(a, b) -> float`,
  `best_match(query, candidates) -> SemanticMatch`.
- `NodeExecutor`: `execute(node, context) -> NodeResult`.
- `WorkflowRepository`: `save`, `get_by_id`, `get_by_tenant`.

### Use Cases
- `ExecuteWorkflow.execute(input) -> output`: Recorre el grafo desde `start_node_id`,
  ejecuta cada nodo según su tipo, delega decisiones semánticas al `SemanticProcessor`,
  acumula resultados en `ExecutionContext`, termina en nodo `END` o si no hay más
  aristas aplicables.
- `ValidateWorkflow.execute(workflow) -> ValidationResult`: Detecta ciclos (DFS),
  nodos huérfanos, ausencia de nodo START/END, aristas rotas.

## 5. Procesamiento semántico

Implementación por defecto (`EmbeddingProcessor`):
- Vectorización simple basada en bag-of-words + TF-IDF (sin dependencias externas).
- Similitud coseno entre vectores.
- `best_match` devuelve el candidato con mayor score superando el umbral.

Esto permite que los tests sean deterministas y no requieran red neuronal ni API
externa, manteniendo cobertura y velocidad.

## 6. Testing Strategy (TDD)

### RED — Tests que fallan primero
1. `test_value_objects.py`: enums, factory methods, validaciones.
2. `test_entities.py`: construcción de Workflow, add_node/add_edge, inmutabilidad.
3. `test_validate_workflow.py`: detección de ciclos, nodos huérfanos.
4. `test_execute_workflow.py`: ejecución lineal (START → ACTION → END).
5. `test_semantic_branch.py`: ramificación por similitud semántica.

### GREEN — Implementación mínima
- Solo el código necesario para pasar todos los tests.

### REFACTOR
- Extracción de helpers, eliminación de duplicados, type hints estrictos.

**Cobertura objetivo:** ≥80% sobre `src/domain/semantic_flow/` y
`src/infrastructure/semantic_flow/`.

## 7. Criterios de aceptación

- [x] Branch `feature/semanticflow-testing` creada.
- [x] Módulo `src/domain/semantic_flow/` con entities, value_objects, interfaces,
      use_cases siguiendo las convenciones del proyecto.
- [x] Módulo `src/infrastructure/semantic_flow/` con implementaciones concretas.
- [x] Tests unitarios en `tests/unit/domain/semantic_flow/` con cobertura ≥80%.
- [x] Todos los tests pasan: `pytest tests/unit/domain/semantic_flow/ -v`.
- [x] Commit conventional: `feat(semantic-flow): ...`.
- [x] Push al origin.

## 8. Dependencias y riesgos

- **Dependencias:** Ninguna nueva. Solo stdlib (math, dataclasses, uuid, enum).
- **Riesgos:**
  - Detección de ciclos en workflows grandes → algoritmo DFS iterativo (no
    recursivo) para evitar stack overflow.
  - Embeddings sin librerías externas → bag-of-words es suficiente para la
    v1, documentar como limitación.
