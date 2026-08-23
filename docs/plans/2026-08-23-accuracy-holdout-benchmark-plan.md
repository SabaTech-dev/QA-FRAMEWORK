# Plan: Holdout Benchmark Support — Accuracy Testing Module

**Card:** ca3090d5-84bc-455d-a4f9-e2c62015a61b [P2]
**Branch:** `feat/accuracy-holdout-benchmark` (base: `feat/accuracy-testing-german-ai-liability`, que contiene el módulo — aún no mergeada en `main`)
**Date:** 2026-08-23
**Req. IDs:** F-ACC-006 (holdout split + anti-leak)

## 1. Problema

Benchmarks de accuracy observables (preguntas + ground truth + resultados por ítem)
permiten overfitting: un agente o equipo puede tunelear contra el eval set hasta
memorizarlo (ref: Dan Luu — agente que overfitteó el benchmark hasta el holdout;
HF: 6/11 modelos ASR memorizan tests públicos).

Diferenciador del producto: "evals que no se pueden gamear".

## 2. Brainstorming — 3 enfoques

### Enfoque A — Dominio puro: SplitPolicy + BenchmarkSplit + HoldoutSummary (SELECCIONADO)

- Split determinista por orden hash SHA-256(`salt:benchmark.id`), ratio exacto.
- `BenchmarkSplit` serializa/repr SOLO contadores (contenido del holdout nunca sale).
- `HoldoutEvaluationService` evalúa el holdout, agrega a `HoldoutSummary` (solo
  métricas agregadas: count, pass_rate, average_score, hallucinations) y
  **descarta** los resultados por ítem. Sin logging de contenido.
- `AccuracyTestSession.holdout_summary` opcional; `to_dict()` expone solo agregados.

**Pros:** cero dependencias nuevas; sigue Clean Architecture del módulo
(dataclasses + Protocols, sin persistencia aún); la garantía anti-leak vive en el
dominio, por lo que cualquier UI/API futura construida sobre `to_dict()` no puede
mostrar contenido del holdout; 100% testeable.
**Contras:** la protección es por construcción de serialización, no criptográfica.

### Enfoque B — Holdout gestionado por repositorio (infra)

- `IBenchmarkRepository.get_by_domain(subset="holdout")`; el holdout nunca sale
  de la capa de persistencia salvo por una ruta sellada.
- **Descartado:** no existe implementación de repositorio aún (solo interfaces) →
  código especulativo (YAGNI). Complejidad de consistencia split dominio/storage.
- Evolución natural cuando haya repositorios reales.

### Enfoque C — Holdout cifrado criptográficamente

- Ground truths cifrados; scoring sin revelar verdad.
- **Descartado:** el evaluador actual necesita `ground_truth` en claro; key
  management fuera de alcance; over-engineering para fase BETA.

## 3. Diseño (Enfoque A)

### 3.1 Nuevos componentes (`src/domain/accuracy_testing/`)

**`splitting.py`**

- `SplitPolicy` (frozen dataclass):
  - `holdout_ratio: float = 0.2` — validado en `(0.0, 1.0)` exclusivo.
  - `salt: str = ""` — permite splits distintos por tenant/deployment.
  - `min_eval_size: int = 1`, `min_holdout_size: int = 1` — > 0.
- `split_benchmarks(benchmarks, policy) -> BenchmarkSplit`:
  - Si `len(benchmarks) < 2`: todo a eval, holdout vacío (no hay nada que ocultar).
  - Si `>= 2`: `k = clamp(round(N * ratio), min_holdout, N - min_eval)`; si el
    rango es vacío → `ValueError`.
  - Orden determinista: ordenar por `(sha256(salt:id), id)`; holdout = primeros k;
    eval = resto. Determinista entre procesos (sha256, NO `hash()` nativo que está
    salted por proceso).
- `BenchmarkSplit`:
  - Invariantes en `__post_init__`: sin duplicados, eval/holdout disjuntos,
    tamaños >= mínimos del policy.
  - `to_dict()`: SOLO `eval_count`, `holdout_count`, `policy` (ratio/salt OMITIDO
    en dict público para no facilitar reconstrucción; se expone `holdout_ratio`
    numérico sin salt). Contenido: NUNCA.
  - `__repr__` redactado: `BenchmarkSplit(eval_count=N, holdout_count=M)` —
    anti-leak en logs accidentales.
- `HoldoutSummary` (frozen dataclass): `holdout_count`, `pass_rate`,
  `average_score`, `hallucination_count`, `evaluated_at`; property
  `accuracy_level`; `to_dict()` solo agregados — sin ids, preguntas, respuestas
  ni ground truth.

**`holdout_service.py`**

- `HoldoutEvaluationService(evaluator: IAccuracyEvaluator)`:
  - `run_holdout(split, response_provider, ai_model="") -> HoldoutSummary`
  - Itera `split.holdout_benchmarks`: `provider.get_response(b.question)` →
    `evaluator.evaluate(b, response)` → acumula métricas → **descarta** el
    detalle por ítem.
  - No loguea contenido (módulo sin logging por diseño).
  - Holdout vacío → summary con `holdout_count=0`.

### 3.2 Modificaciones

- `entities.py` — `AccuracyTestSession`:
  - Nuevo campo `holdout_summary: Optional[HoldoutSummary] = None`.
  - Propagado en `add_evaluation()` y `complete()` (patrón immutable).
  - Nuevo `with_holdout_summary(summary)` (immutable).
  - `to_dict()` incluye `holdout_summary.to_dict()` — solo agregados (F-ACC-006).
- `__init__.py`: exports nuevos.

### 3.3 Anti-leak — garantías (F-ACC-006)

1. `BenchmarkSplit.to_dict()`/`__repr__`: solo contadores.
2. `HoldoutSummary.to_dict()`: solo métricas agregadas.
3. `AccuracyTestSession.to_dict()`: holdout solo como summary agregado.
4. `HoldoutEvaluationService`: no persiste ni retorna resultados por ítem del
   holdout; no loguea.
5. Sin UI/API consumiendo el módulo aún → la redacción a nivel de serialización
   del dominio ES la protección de UI (contrato para capas superiores).

## 4. Tests

- **Unit** `tests/test_accuracy_holdout.py`:
  - SplitPolicy: validación ratio/mins; defaults.
  - split_benchmarks: determinismo (misma entrada+policy → ids idénticos y mismo
    orden), estabilidad implícita entre procesos (sha256), disjuntos + unión
    completa, ratio exacto, mínimos respetados, salt cambia split, N<2 → holdout
    vacío, infeasible → ValueError, duplicados → ValueError.
  - Redacción: to_dict/repr sin preguntas, ground truth, ids de holdout.
  - HoldoutSummary: propiedades, to_dict keys exactas.
  - HoldoutEvaluationService: aggregación correcta (pass_rate, avg,
    hallucinations), no expone respuestas, holdout vacío → count 0, usa las
    preguntas del holdout contra el provider.
  - Session: with_holdout_summary, propagación en add_evaluation/complete,
    to_dict contiene solo agregados del holdout.
- **Integration** `tests/integration/test_accuracy_holdout_integration.py`:
  - Flujo E2E con `create_german_ai_liability_benchmarks()` reales → split →
    eval set evaluado → holdout vía servicio → sesión completa → `to_dict()` →
    JSON dump: (a) serializable, (b) sin ground truth de ningún benchmark,
    (c) sin pregunta/respuesta de ningún benchmark del holdout.
- **Cobertura:** ≥80% sobre `splitting.py` + `holdout_service.py` + líneas
  nuevas de `entities.py`.

## 5. Criterios de aceptación

1. Split eval/holdout determinista y reproducible con política configurable.
2. Contenido del holdout (preguntas, ground truth, respuestas, resultados por
   ítem) ausente de: `to_dict()`/`to_dict_full()` de split y sesión, `__repr__`,
   y output del servicio.
3. Tests unit + integration ≥80% cobertura del código nuevo, suite existente
   (56 tests) sigue verde.
4. Commits convencionales, rama pusheada, sin marcar card done.

## 6. Riesgos

- **R1:** hash() nativo no determinista entre procesos → mitigado: SHA-256.
- **R2:** conocer `salt` permite reconstruir qué items son holdout (no su
  contenido/feedback) → aceptado; documentado; el split por ítem sin feedback
  no permite tunelear por caso.
- **R3:** merges futuros con main → la base aún no está mergeada; la rama se
  rebaseará/mezclará junto con la base.
