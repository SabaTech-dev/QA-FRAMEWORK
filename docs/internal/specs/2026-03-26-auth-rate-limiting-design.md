# Auth Endpoints + Rate Limiting - Design Doc

**Fecha:** 2026-03-26
**Autor:** coder agent
**Task ID:** 115b1941-e7d7-45ce-ae0b-80e98e6ceaf3
**Referencia:** Security Audit QA-FRAMEWORK-SECURITY-AUDIT-2026-03-25.md

---

## Goal

Proteger endpoints GET que exponen datos sensibles con autenticación y activar rate limiting global.

---

## Current State

### CRITICAL #1: Endpoints sin autenticación

8 endpoints GET exponen datos sin verificar identidad:

| Endpoint | Línea | Archivo |
|----------|-------|---------|
| `/dashboard/stats` | ~170 | routes.py |
| `/dashboard/trends` | ~210 | routes.py |
| `/suites` (list) | ~280 | routes.py |
| `/suites/{id}` | ~315 | routes.py |
| `/cases` (list) | ~440 | routes.py |
| `/cases/{id}` | ~485 | routes.py |
| `/executions` (list) | ~620 | routes.py |
| `/executions/{id}` | ~685 | routes.py |

### MEDIUM #7: Rate Limiting

- ✅ **Existe:** `middleware/rate_limit.py` - implementación completa
  - Redis-backed con sliding window
  - Per-plan limits (Free: 100/hr, Pro: 1000/hr, Enterprise: 10000/hr)
  - Endpoint-specific limits (login: 20/min, executions: 60/min)
- ❌ **NO registrado:** Falta `app.add_middleware(RateLimitMiddleware)` en main.py

---

## Architecture

### Cambios mínimos

```
dashboard/backend/
├── main.py                    # Añadir RateLimitMiddleware
├── api/v1/routes.py           # Añadir Depends(get_current_user) a 8 endpoints
└── middleware/rate_limit.py   # YA EXISTE (no tocar)
```

---

## Tech Stack

- FastAPI Depends injection
- RateLimitMiddleware (ya implementado)
- Redis (ya disponible)

---

## Tasks Breakdown

### Task 1: Añadir autenticación a 8 endpoints GET
**Estimación:** 10 min

Añadir `current_user=Depends(get_current_user)` a:
1. `get_dashboard_stats`
2. `get_trends`
3. `list_suites`
4. `get_suite`
5. `list_cases`
6. `get_case`
7. `list_executions`
8. `get_execution`

### Task 2: Registrar RateLimitMiddleware
**Estimación:** 5 min

En `main.py`, añadir import y middleware:
```python
from middleware.rate_limit import RateLimitMiddleware
app.add_middleware(RateLimitMiddleware)
```

### Task 3: Verificar configuración de rate limits
**Estimación:** 5 min

Verificar que `core/rate_limit_config.py` existe con límites correctos.

### Task 4: Validación y commit
**Estimación:** 5 min

- Ejecutar tests existentes
- Commit con mensaje descriptivo

---

## Data Flow

```
Request → RateLimitMiddleware (check) → Endpoint → get_current_user (auth) → Response
```

---

## Error Handling

- **401 Unauthorized:** Si token inválido/falta en endpoints protegidos
- **429 Too Many Requests:** Si rate limit excedido
- **Rate limit headers:** `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`

---

## Risks

| Riesgo | Probabilidad | Mitigación |
|--------|--------------|------------|
| Tests existentes fallen | Baja | Ejecutar tests antes de commit |
| Redis no disponible | Baja | Rate limiter tiene fail-open |
| Conflictos con refactor-expert | Baja | Verificar que refactor terminó |

---

## Out of Scope

- ❌ Cambiar límites de rate limiting (ya configurados)
- ❌ Añadir rate limiting por IP (ya implementado)
- ❌ Modificar endpoints POST/PUT/DELETE (ya tienen auth)
