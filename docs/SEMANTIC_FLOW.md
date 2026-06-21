# SemanticFlow Testing

Framework agentic avanzado para orquestar workflows de testing complejos con
procesamiento semántico.

A diferencia de los tests lineales clásicos, SemanticFlow permite:

- **Ramificar** la ejecución en función del resultado de cada nodo.
- **Decidir** la siguiente rama mediante similitud semántica entre textos.
- **Reintentar** o **abortar** flujos según el estado observado.
- **Componer** workflows complejos como grafos dirigidos (DAG).

## Tabla de contenidos

- [Conceptos](#conceptos)
- [Arquitectura](#arquitectura)
- [Instalación](#instalación)
- [Uso rápido](#uso-rápido)
- [Tipos de nodo](#tipos-de-nodo)
- [Procesamiento semántico](#procesamiento-semántico)
- [Validación de workflows](#validación-de-workflows)
- [API de referencia](#api-de-referencia)
- [Limitaciones](#limitaciones)

## Conceptos

### Workflow

Un **workflow** es un grafo dirigido formado por:

- Un conjunto de **nodos** (`Node`).
- Una lista de **aristas** (`Edge`) que los conectan.
- Un **nodo inicial** (`start_node_id`).

### Nodo (`Node`)

Unidad atómica de un workflow. Cada nodo tiene un `type` que determina cómo
se ejecuta y cómo se elige la siguiente arista.

### Arista (`Edge`)

Conexión dirigida entre dos nodos. Puede ser:

- **Incondicional**: no tiene `condition`.
- **Condicional**: el `condition` (string) se compara con el estado del nodo
  origen (`passed`, `failed`, `skipped` para DECISION) o se evalúa como
  similitud semántica (para SEMANTIC_BRANCH).

La `priority` (entero) determina el orden de evaluación cuando varias aristas
salen del mismo nodo: mayor prioridad se evalúa primero.

## Arquitectura

```
src/domain/semantic_flow/                 # Capa de dominio (pure business)
├── value_objects.py                      # NodeType, NodeStatus, IDs tipados
├── entities.py                           # Node, Edge, Workflow, NodeResult, ...
├── interfaces.py                         # Protocols: SemanticProcessor, NodeExecutor
└── use_cases/
    ├── execute_workflow.py               # ExecuteWorkflow use case
    └── validate_workflow.py              # ValidateWorkflow use case

src/infrastructure/semantic_flow/         # Adaptadores concretos
├── embedding_processor.py                # SemanticProcessor con TF-IDF
├── in_memory_repository.py               # WorkflowRepository en memoria
└── node_executors.py                     # Executors por tipo de nodo
```

Sigue los principios de Clean Architecture:

- El **dominio** no depende de ninguna implementación concreta.
- Las **implementaciones** (infraestructura) implementan los Protocols
  definidos en el dominio (Dependency Inversion).

## Instalación

SemanticFlow está integrado en el paquete `qa-framework`. No requiere
dependencias adicionales: usa solo la librería estándar de Python.

```bash
pip install -e .
```

## Uso rápido

```python
from src.domain.semantic_flow import (
    Workflow, Node, Edge, NodeType, NodeId, EdgeId,
    ExecuteWorkflow, ExecuteWorkflowInput,
    ValidateWorkflow, ValidateWorkflowInput,
)
from src.infrastructure.semantic_flow import EmbeddingProcessor

# 1. Construir el workflow
wf = Workflow(
    name="login_error_classifier",
    nodes={
        "start": Node(id=NodeId("start"), type=NodeType.START, label="Inicio"),
        "branch": Node(id=NodeId("branch"), type=NodeType.SEMANTIC_BRANCH,
                       label="Clasificar error"),
        "auth": Node(id=NodeId("auth"), type=NodeType.ACTION,
                     label="authentication failure"),
        "network": Node(id=NodeId("network"), type=NodeType.ACTION,
                        label="network timeout"),
        "end": Node(id=NodeId("end"), type=NodeType.END, label="Fin"),
    },
    edges=[
        Edge(id=EdgeId("e1"), source=NodeId("start"), target=NodeId("branch")),
        Edge(id=EdgeId("e2"), source=NodeId("branch"), target=NodeId("auth"),
             condition="authentication failure"),
        Edge(id=EdgeId("e3"), source=NodeId("branch"), target=NodeId("network"),
             condition="network timeout"),
        Edge(id=EdgeId("e4"), source=NodeId("auth"), target=NodeId("end")),
        Edge(id=EdgeId("e5"), source=NodeId("network"), target=NodeId("end")),
    ],
    start_node_id=NodeId("start"),
)

# 2. Validar el workflow (recomendado antes de ejecutar)
validation = ValidateWorkflow().execute(ValidateWorkflowInput(workflow=wf))
assert validation.is_valid, f"Workflow inválido: {validation.issues}"

# 3. Ejecutar con un query semántico
processor = EmbeddingProcessor()
result = ExecuteWorkflow(semantic_processor=processor).execute(
    ExecuteWorkflowInput(
        workflow=wf,
        branch_query="authentication failure detected",
    )
)

print(f"Éxito: {result.success}")
print(f"Status: {result.result.status.value}")
print(f"Nodos visitados: {[str(r.node_id) for r in result.result.node_results]}")
print(f"Tasa de éxito: {result.result.success_rate:.0%}")
```

Salida esperada:

```
Éxito: True
Status: completed
Nodos visitados: ['start', 'branch', 'auth', 'end']
Tasa de éxito: 100%
```

## Tipos de nodo

| Tipo              | Comportamiento                                                |
|-------------------|---------------------------------------------------------------|
| `START`           | Punto de entrada. Debe existir exactamente uno.               |
| `END`             | Punto de salida. Termina la ejecución del workflow.           |
| `ACTION`          | Ejecuta una acción mediante el `NodeExecutor` inyectado.      |
| `DECISION`        | Elige la siguiente arista comparando `condition` con el estado |
|                   | del resultado (`passed`/`failed`/`skipped`).                  |
| `ASSERTION`       | Evalúa una aserción (callable en `inputs['assert']`).         |
| `SEMANTIC_BRANCH` | Elige la siguiente arista mediante similitud semántica entre  |
|                   | `branch_query` y los `condition` de las aristas salientes.    |

## Procesamiento semántico

El `EmbeddingProcessor` por defecto usa:

1. **Tokenización** por palabras (regex `[a-zA-Z0-9_]+`).
2. **TF (Term Frequency)** normalizado por longitud.
3. **Similitud coseno** entre vectores TF.
4. **Umbral** configurable (por defecto 0.5): la arista solo se toma si
   el score supera estrictamente el umbral.

Para reemplazarlo por un modelo de embeddings neuronal (sentence-transformers,
OpenAI, Vertex AI), basta con implementar el Protocol `SemanticProcessor`:

```python
from src.domain.semantic_flow.interfaces import SemanticProcessor
from src.domain.semantic_flow.value_objects import SemanticMatch

class MyNeuralProcessor(SemanticProcessor):
    def embed(self, text: str) -> list[float]:
        return self._model.encode(text).tolist()

    def similarity(self, a: str, b: str) -> float:
        return self._model.similarity(a, b).item()

    def best_match(self, query, candidates, threshold=0.5) -> SemanticMatch:
        # ... implementación con tu modelo
        ...
```

## Validación de workflows

El use case `ValidateWorkflow` comprueba:

| Chequeo                | Severidad | Descripción                                   |
|------------------------|-----------|-----------------------------------------------|
| Workflow vacío         | ERROR     | Sin nodos definidos.                          |
| Sin nodo START         | ERROR     | `start_node_id` es None o no existe.          |
| Sin nodo END           | ERROR     | No hay ningún nodo con `type=END`.            |
| Arista rota            | ERROR     | Source o target no existe.                    |
| Ciclo                  | ERROR     | Detectado por DFS iterativo.                  |
| Nodo huérfano          | WARNING   | No es alcanzable desde START.                 |

```python
from src.domain.semantic_flow import ValidateWorkflow, ValidateWorkflowInput

result = ValidateWorkflow().execute(ValidateWorkflowInput(workflow=wf))
if not result.is_valid:
    for issue in result.issues:
        if issue.is_error:
            print(f"ERROR  [{issue.node_id}] {issue.message}")
        else:
            print(f"WARN   [{issue.node_id}] {issue.message}")
```

## API de referencia

### Entities

- `Node(type, label, id?, inputs?, metadata?)` → `Node`
- `Edge(source, target, id?, condition?, priority?)` → `Edge`
- `Workflow(name, id?, nodes?, edges?, start_node_id?, tenant?)` → `Workflow`
- `NodeResult.passed(node_id, output?, score?)` / `.failed(...)` / `.skipped(...)`
- `WorkflowResult(workflow_id, status, node_results, duration_ms)`
- `ExecutionContext(workflow_id, variables?, history?)`

### Use cases

- `ExecuteWorkflow(node_executor?, semantic_processor?, semantic_threshold?)`
- `ValidateWorkflow()`

### Infraestructura

- `EmbeddingProcessor()` — TF-IDF + cosine similarity
- `InMemoryWorkflowRepository()` — persistencia en memoria
- `ActionNodeExecutor(handlers?)`, `AssertionNodeExecutor()`,
  `CompositeNodeExecutor()`

## Limitaciones

- **Bag-of-words**: el `EmbeddingProcessor` no captura orden ni contexto.
  Para mayor precisión, sustitúyelo por un modelo de embeddings neuronal.
- **No persistente**: `InMemoryWorkflowRepository` pierde los datos al
  terminar el proceso. Para producción, implementa una versión basada en
  PostgreSQL.
- **Sin paralelismo**: la ejecución es secuencial. Para workflows con
  ramas independientes puede paralelizarse envolviendo el `NodeExecutor`.

## Testing

```bash
# Ejecutar todos los tests del módulo
pytest tests/unit/domain/semantic_flow/ -v

# Con cobertura
pytest tests/unit/domain/semantic_flow/ -v \
    --cov=src/domain/semantic_flow \
    --cov=src/infrastructure/semantic_flow \
    --cov-report=term-missing
```

Cobertura actual: **97%** sobre los módulos `semantic_flow`.
