# Auth Endpoints + Rate Limiting - Implementation Plan

**Goal:** Proteger 8 endpoints GET + activar rate limiting
**Design Doc:** docs/specs/2026-03-26-auth-rate-limiting-design.md
**Estimación:** 25 min

---

## Task 1: Añadir Depends(get_current_user) a 8 endpoints

**Archivo:** `/home/ubuntu/qa-framework/dashboard/backend/api/v1/routes.py`

### Steps

- [ ] **Step 1.1:** Añadir auth a `get_dashboard_stats`
```python
# ANTES:
async def get_dashboard_stats(db: AsyncSession = Depends(get_db)):

# DESPUÉS:
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
```

- [ ] **Step 1.2:** Añadir auth a `get_trends`

- [ ] **Step 1.3:** Añadir auth a `list_suites`

- [ ] **Step 1.4:** Añadir auth a `get_suite`

- [ ] **Step 1.5:** Añadir auth a `list_cases`

- [ ] **Step 1.6:** Añadir auth a `get_case`

- [ ] **Step 1.7:** Añadir auth a `list_executions`

- [ ] **Step 1.8:** Añadir auth a `get_execution`

---

## Task 2: Registrar RateLimitMiddleware en main.py

**Archivo:** `/home/ubuntu/qa-framework/dashboard/backend/main.py`

### Steps

- [ ] **Step 2.1:** Añadir import
```python
from middleware.rate_limit import RateLimitMiddleware
```

- [ ] **Step 2.2:** Añadir middleware después de SecurityHeadersMiddleware
```python
app.add_middleware(RateLimitMiddleware)
```

---

## Task 3: Verificar configuración de rate limits

**Archivo:** `/home/ubuntu/qa-framework/dashboard/backend/core/rate_limit_config.py`

### Steps

- [ ] **Step 3.1:** Verificar que existe y tiene límites configurados

---

## Task 4: Validación y commit

### Steps

- [ ] **Step 4.1:** Verificar sintaxis con Python
- [ ] **Step 4.2:** Commit con mensaje descriptivo

---

## Rollback

```bash
cd /home/ubuntu/qa-framework && git checkout -- dashboard/backend/api/v1/routes.py dashboard/backend/main.py
```
