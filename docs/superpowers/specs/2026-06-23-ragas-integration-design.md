# Diseño: Integración de RAGAS para evaluación de pipelines RAG

**Fecha:** 2026-06-23
**Estado:** Aprobado
**Autor:** Build Agent (SDD)

## 1. Objetivo

Integrar RAGAS (Retrieval Augmented Generation Assessment) en QA-FRAMEWORK para
evaluar automáticamente la calidad de respuestas generadas por pipelines RAG,
cubriendo tres dimensiones: relevancia del contexto, fidelidad (faithfulness) y
relevancia de la respuesta.

## 2. Contexto y restricciones

- QA-FRAMEWORK es un framework de QA con Clean Architecture (interfaces ABC en
  `src/core/interfaces`, dominio con Protocols en `src/domain/<modulo>/`).
- Ya existe `deepeval==4.0.6` para evaluación LLM. RAGAS es complementario,
  especializado en métricas RAG.
- **Restricción dura:** los tests no pueden realizar llamadas a APIs de LLM
  (no se permiten API keys reales). Deben usar mocks y datos sintéticos.
- **Fragilidad de versión:** ragas depende de langchain y la API cambia entre
  versiones. Tras probar, la combinación coherente y funcional es:
  `ragas==0.2.15` + stack `langchain 0.3.x`. ragas 0.4.x y langchain-community
  0.4.x (sunset) son incompatibles a día de hoy.

## 3. Enfoques evaluados

| Enfoque | Descripción | Veredicto |
|---|---|---|
| A. FakeLLM inyectado | Métricas reales de ragas con FakeLLM que devuelve respuestas prefijadas | **Descartado:** frágil; las respuestas deben encajar el schema JSON interno de ragas; acoplado a versión |
| **B. Seam interno + mock** | `RagasEvaluator` envuelve ragas tras `_run_metric`; tests mockean esa frontera | **Elegido** |
| C. Heurísticas propias | Implementar métricas sin ragas en runtime | **Descartado:** contradice el objetivo de integrar RAGAS |

### Justificación del Enfoque B

- Integra ragas de verdad en producción (cuando se inyecta un LLM real).
- Tests deterministas, rápidos y sin API key (mock del seam).
- Desacoplado de la versión interna de ragas (solo depende de la firma pública
  de `single_turn_score`, que es estable en 0.2.x).
- Valida el contrato de QA-FRAMEWORK: rangos [0,1], validación de entradas,
  agregación de contextos, gestión de errores.
- Encaja con el estilo de mocking del proyecto (`unittest.mock.Mock` ya usado
  en `tests/unit/domain/test_generation/test_use_cases.py`).

## 4. Arquitectura

```
src/core/evaluation/
├── __init__.py            # exporta RagasEvaluator
└── ragas_evaluator.py     # clase RagasEvaluator (lazy-import de ragas)

tests/evaluation/
├── __init__.py
├── conftest.py            # fixtures de datos sintéticos
└── test_ragas_evaluator.py
```

### 4.1 Clase `RagasEvaluator`

```python
class RagasEvaluator:
    def __init__(self, llm=None): ...
    async def _run_metric(self, metric, sample) -> float: ...   # seam
    async def evaluate_context_relevance(self, question, context, answer) -> float: ...
    async def evaluate_faithfulness(self, answer, context) -> float: ...
    async def evaluate_answer_relevance(self, question, answer) -> float: ...
    async def evaluate_full_pipeline(self, question, context, answer) -> dict: ...
```

**Decisiones clave:**

- **Lazy import:** ragas se importa dentro de los métodos, no en la cabecera.
  Así el módulo carga aunque ragas no esté instalado; se lanza `ImportError`
  con mensaje claro solo al ejecutar una evaluación.
- **Seam `_run_metric`:** invoca `metric.single_turn_score(sample)` (sync) y
  normaliza el resultado a `float` en [0,1]. Es el punto único que toca ragas;
  en tests se mockea.
- **LLM inyectable (DIP):** `__init__(llm=None)`. Si es `None` en producción,
  ragas usará su LLM por defecto (requiere configuración de entorno). Los
  tests nunca llegan a este punto porque el seam está mockeado.
- **Normalización de contexto:** `context: str | list[str]` se convierte a
  `list[str]` para el campo `retrieved_contexts` de `SingleTurnSample`.
- **Clip de rango:** todo score se limita a `[0.0, 1.0]`. `None`/`NaN` → `0.0`.

### 4.2 Mapeo de métricas (ragas 0.2.15)

| Método público | Métrica ragas | Campos del sample |
|---|---|---|
| `evaluate_context_relevance` | `ContextRelevance` | `user_input`, `retrieved_contexts`, `response` |
| `evaluate_faithfulness` | `Faithfulness` | `retrieved_contexts`, `response` |
| `evaluate_answer_relevance` | `AnswerRelevancy` | `user_input`, `response` |
| `evaluate_full_pipeline` | las 3 + `aggregated_score` | — |

### 4.3 `evaluate_full_pipeline`

Devuelve:
```python
{
    "context_relevance": float,
    "faithfulness": float,
    "answer_relevance": float,
    "aggregated_score": float,  # media armónica de las 3
}
```

## 5. Tests (TDD)

- Datos sintéticos realistas (pregunta sobre RAG, contexto coherente, respuesta).
- Mock del seam `_run_metric` para devolver floats deterministas.
- Aserciones: rangos [0,1], keys del dict completo, normalización str→list,
  manejo de `None`/`NaN`, `ImportError` cuando ragas ausente (patch del import).
- Sin llamadas a red ni API keys.

## 6. Dependencias

Añadir a `requirements.txt` (stack coherente probado):

```
ragas==0.2.15
langchain==0.3.27
langchain-core==0.3.86
langchain-community==0.3.27
langchain-openai==0.3.28
langchain-text-splitters==0.3.11
```

**Conflictos conocidos (fuera de alcance):** la instalación de langchain
0.3.x puede entrar en conflicto con `deepeval` (requiere `click<8.4.0`) e
`instructor` (requiere `openai>=2.0.0`). No se modifican en esta tarea.

## 7. Criterios de aceptación

1. `RagasEvaluator` expone los 4 métodos con las firmas especificadas.
2. Todos los métodos devuelven floats en [0,1] (o dict con floats en [0,1]).
3. `pytest tests/evaluation/test_ragas_evaluator.py -v` pasa sin API keys.
4. Cobertura del módulo ≥ 80%.
5. El módulo importa correctamente aunque ragas no esté instalado (lazy import).
6. Sin llamadas a red en los tests.
