# Self-Healing Backend + Frontend Integration — Design

**Fecha:** 2026-06-27
**Estado:** Aprobado (spec del usuario)
**Patrón de referencia:** `suites_routes.py` / vertical slice `waitlist`

## Objetivo

Construir el vertical slice completo de Self-Healing: modelos, migración, servicio,
rutas API y conectar el frontend `SelfHealing.tsx` eliminando todos los datos mock.

## Alcance

- Backend: `models/self_healing.py`, migración Alembic, `services/healing_service.py`,
  `api/v1/healing_routes.py`, registro en `routes.py`.
- Frontend: `healingAPI` en `api/client.ts`, refactor de `SelfHealing.tsx`.
- Tests: backend CRUD + heal stub + auth 401.

## Arquitectura / Componentes

### 1. Modelos — `models/self_healing.py`

Usan el **`Base` compartido** de `models/__init__.py` (patrón `browser_use_task.py`),
NO un Base propio. Así quedan registrados en `Base.metadata` para `init_db()` y para
autogenerate de Alembic.

- **`HealingSelector`** (`self_healing_selectors`):
  - `id`, `value` (str, único, indexado), `selector_type` (id/css/xpath/data_attribute/text),
  - `description` (Text, opcional), `confidence_score` (Float), `confidence_level`
    (high/medium/low), `is_active` (Bool, default True), `usage_count` (Int default 0),
  - `success_rate` (Float default 0.0), `created_at`, `updated_at`.

- **`HealingSession`** (`self_healing_sessions`):
  - `id`, `status` (success/partial/failed/running), `total_selectors`,
  - `successful_heals`, `failed_heals`, `success_rate` (Float), `average_confidence` (Float),
  - `started_at`, `completed_at` (nullable).

- **`HealingResult`** (`self_healing_results`):
  - `id`, `selector_id` (FK → self_healing_selectors.id, nullable), `session_id`
    (FK → self_healing_sessions.id, nullable), `original_selector_value`, `healed_selector_value`
    (nullable), `status` (success/failed/skipped), `confidence_score` (Float),
  - `confidence_level`, `healing_time_ms` (Int), `attempts` (Int default 1), `created_at`.

### 2. Migración Alembic — `alembic/versions/20260627_add_self_healing.py`

Manual (patrón waitlist). `down_revision = '20260623_waitlist'` (head actual). Crea las 3
tablas con índices en `value`, `selector_type`, `status`, `session_id`, `selector_id`.

### 3. Schemas — se añaden en `schemas/__init__.py`

Pydantic v2 (`ConfigDict(from_attributes=True)`): `HealingSelectorCreate/Update/Response`,
`HealingSessionResponse`, `HealingResultResponse`, `HealRequest`/`HealResponse`.

### 4. Servicio — `services/healing_service.py`

CRUD async con `select()` + `heal_selector_service` **stub**: lógica determinista realista
(no mock): si `confidence_score >= 0.5` → status `skipped` (no necesita heal); si `< 0.5` →
genera `healed_selector_value` y status `success`. Crea `HealingResult` + `HealingSession`.

### 5. Rutas — `api/v1/healing_routes.py`

`APIRouter(prefix="/healing", tags=["Self-Healing"])`, auth `get_current_user`:

- `GET    /healing/selectors`          → lista paginada
- `POST   /healing/selectors`          → crear (201)
- `GET    /healing/selectors/{id}`     → detalle (404 si no existe)
- `PUT    /healing/selectors/{id}`     → actualizar (404 si no existe)
- `DELETE /healing/selectors/{id}`     → eliminar (204)
- `POST   /healing/selectors/{id}/heal`→ ejecuta heal stub → `HealResponse`
- `GET    /healing/sessions`           → lista sesiones
- `GET    /healing/results`            → lista resultados (filtable por `selector_id`)

Registro: `router.include_router(healing_routes.router)` en `api/v1/routes.py`.

### 6. Frontend

- `api/client.ts`: añadir `healingAPI` (selectors CRUD, heal, sessions, results).
- `SelfHealing.tsx`: eliminar TODO el mock, usar `healingAPI`, manejar errores y loading.

## Testing (TDD)

- `tests/unit/test_healing_service.py`: CRUD + heal stub (async, mocks de DB).
- `tests/integration/test_healing_routes.py`: endpoints + auth 401 (sin token → 401).
- Cobertura ≥ 80% (cumple `--cov-fail-under=80`).

## Criterios de aceptación

- Backend arranca, rutas registradas y visibles.
- Migración aplica (`alembic upgrade head`) sin romper head.
- `pytest` pasa con cobertura ≥ 80%.
- Frontend `vitest`/`tsc` sin errores; sin datos mock en `SelfHealing.tsx`.
- Commit conventional + push.
