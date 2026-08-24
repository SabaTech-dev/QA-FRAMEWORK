# Accuracy API Wiring + Holdout Merge — Plan (card c9825844)

Follow-up de ca3090d5 (holdout benchmark, pipeline APPROVED 08-23). El módulo
`accuracy_testing` vive en ramas sin merge; esta card lo mergea a main y lo
monta en la API con los contracts de seguridad L-1/L-2.

## Contexto

- Base: `origin/main` @ 07f0f8e (post PR #108/#112/#115/#116/#117 — CI reparada,
  formateo black/isort repo-wide).
- Ramas reales: `feat/accuracy-testing-german-ai-liability` (f20ade6) es
  ANCESTRO de `feat/accuracy-holdout-benchmark` (dbb5243). Ambas divergen de
  main en 197b66f. Cero solapamiento de ficheros entre main y la rama desde
  el merge-base → conflictos de contenido improbables; sí verificar formateo
  con los pins de CI (black 24.1.1, isort 5.13.2 EXACTO, ruff 0.2.1).
- Patrón de auth a reutilizar (no copiar): `QAVisualPrincipal` del PR #118
  (branch `feature/qa-visual-owner-scoping`) — principal con owner+is_admin,
  router factory con dependencia inyectable, owner-scoping en storage,
  acceso admin bypass. NO tocar `src/infrastructure/qa_visual/` (zona ocupada).
- Restricciones: NO tocar `src/api/middleware/rate_limit.py`, workflows CI,
  ni `src/infrastructure/qa_visual/`. Suites root: `pytest tests/unit -o addopts=""`.

## Brainstorm — decisiones

### D1. Estrategia de merge
| Opción | Pros | Contras |
|---|---|---|
| A. 1 PR rebase rama completa (german commit incluido, es ancestro) | Historial preservado, ambos commits en orden natural, ya revisados en ca3090d5 | PR mixto módulo+limpieza |
| B. 2 PRs secuenciales | Review incremental | Duplica runs CI; german no está rebasada; trabajo extra sin valor |
| C. Squash | — | Pierde historia TDD del card anterior |

**Elección: A** para el módulo existente (rebase + cleanup) + **PR separado**
para el wiring nuevo (trabajo no revisado antes → unidad reviewable propia).

### D2. L-1 — SplitPolicy.salt per-tenant
| Opción | Pros | Contras |
|---|---|---|
| A. salt requerido (sin default) + validación no-vacío en dominio + derivación server-side HMAC(secret, tenant_id) | Defense in depth; salt nunca viaja por red ni la elige el cliente; footgun eliminado en dominio | Rotación de secret cambia splits (documentar) |
| B. Default "" en dominio, rechazo solo en API | Menos rotura | El footgun queda para cualquier caller futuro del dominio |
| C. Salt aleatorio persistido por tenant | — | Requiere persistencia nueva; overkill para wiring sin DB |

**Elección: A.** La API nunca acepta `salt` del cliente: lo deriva del
tenant del principal autenticado.

### D3. L-2 — to_dict_full() auth admin + owner-scoping
| Opción | Pros | Contras |
|---|---|---|
| A. full = SOLO admin; owner-scoping para visibilidad de recursos (patrón qa_visual) | ground_truth = answer key (IP de plataforma, benchmarks BGH built-in); un owner regular no debe verla | — |
| B. full = owner también | Owner "ya conoce" sus benchmarks | Los benchmarks built-in no son del owner; ver ground_truth del eval set permite tuneo |

**Elección: A.** `to_dict()` para owner/admin; `to_dict_full()` exclusivo admin.
Benchmarks y sesiones scoped por owner (tenant); admin ve todo.

### D4. Threshold threading
| Opción | Pros | Contras |
|---|---|---|
| A. `compute_overall(passing_threshold=None)` (default 0.6 backwards-compat); evaluator pasa siempre `benchmark.passing_threshold` | Conecta la config muerta; compatible con tests existentes | — |
| B. Eliminar `passing_threshold` | Menos superficie | Pierde configurabilidad por-benchmark que el dominio expresa |

**Elección: A**, con test que demuestre que un benchmark con threshold 0.8
falla con score 0.7 (antes pasaba por el 0.6 hardcodeado).

## Arquitectura del wiring

```
src/infrastructure/accuracy_testing/
├── endpoint.py        # NUEVO: create_accuracy_router() — router factory
├── security.py        # NUEVO: AccuracyPrincipal + derive_tenant_salt()
├── session_store.py   # NUEVO: store in-memory con owner-scoping
└── rule_based_evaluator.py, german_ai_liability_benchmarks.py (existentes)
```

Endpoints (prefijo `/accuracy`):
- `GET  /accuracy/benchmarks`        — lista `to_dict()` scoped por owner
- `GET  /accuracy/benchmarks/{id}`   — `to_dict()` owner / `to_dict_full()` admin (L-2)
- `POST /accuracy/sessions`          — split con salt derivado per-tenant (L-1),
  eval-set detallado + holdout AGREGADOS; devuelve session view
- `GET  /accuracy/sessions/{id}`     — session view (eval-set `to_dict()` +
  `holdout_summary.to_dict()` SOLO)
- `GET  /accuracy/sessions/{id}/holdout` — `HoldoutSummary.to_dict()` exclusivo

Montaje en `dashboard/backend/main.py` tras el patrón qa_visual
(opt-in `ACCURACY_TESTING_ENABLED=1` + `Depends(get_current_user)` +
principal derivado del User). NO tocar src/api/ middleware.

## TDD — orden RED→GREEN

1. RED: `tests/unit/accuracy/test_split_policy_salt_required.py` — salt "" lanza.
2. RED: `tests/unit/accuracy/test_compute_overall_threshold.py` — threshold por benchmark.
3. RED: `tests/unit/api/test_accuracy_endpoint_contracts.py` — AC2 canary:
   respuesta de session NO contiene claves `holdout_benchmarks`/`ground_truth`
   (non-admin) ni contenido de items holdout; L-2 admin-only; L-1 salt derivado.
4. GREEN por capa: dominio → seguridad → store → endpoint → montaje.

## Criterios de aceptación (de la card)

1. Branch merged con CI documentado.
2. Contract tests AC2 pasando (canary anti-leak en capa API).
3. L-1 salt per-tenant testeado.
4. L-2 auth+scoping testeado.
5. Threshold resuelto (conectado, justificado).
6. `reports/coder/npm-v12-migration-plan-2026-06-10.md` fuera del branch
   (+ SESSION-STATE.md: contaminación de workspace, misma categoría).

## Riesgos

- Formateo CI: verificar con pins exactos antes de push (le pasó al builder
  anterior con isort 8.x).
- PR #118 en vuelo: patrón reutilizado conceptualmente, cero dependencia de
  ficheros de qa_visual → sin conflicto esperado.
- Rotación de `ACCURACY_SPLIT_SECRET` cambia membresía holdout: documentar
  en docstring y README del módulo.
