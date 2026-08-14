# Diagnóstico de Railway Deploy - 2026-03-08 23:20 UTC

## Problema

**El deploy de Railway falla consistentemente con healthcheck timeout.**

### Síntomas
- ✅ Docker build exitoso
- ✅ Docker image push exitoso
- ❌ Healthcheck falla 10 intentos en 5 minutos
- ❌ Service unavailable durante healthcheck

### Estado del Deploy

| Run ID | Status | Tiempo | Conclusion |
|---------|--------|---------|------------|
| 22832100808 | ❌ Failed | 5m28s | Healthcheck timeout |
| 22831715353 | ❌ Failed | 5m28s | Healthcheck timeout |
| 22830649143 | ❌ Failed | 6m12s | Healthcheck timeout |

### Configuración Actual

**Backend OLD (corriendo):**
- `/health` → 200 OK
- `/api/v1/*` → 404 NO existe

**Backend NEW (fallo al iniciar):**
- No responde al healthcheck
- Probable error en startup

---

## Análisis del Problema

### Posibles Causas

1. **Variables de entorno faltantes/incorrectas**
   - El backend requiere `DATABASE_URL`, `JWT_SECRET_KEY`, `STRIPE_API_KEY`, `STRIPE_WEBHOOK_SECRET`
   - Puede que Railway no tenga todas las variables configuradas

2. **Error en startup_event**
   - `await init_db()` puede estar fallando
   - Problema con conexión a PostgreSQL

3. **Configuración incorrecta de Settings**
   - Pydantic validation error
   - Variables extra no permitidas

4. **Problema con Redis**
   - `REDIS_URL` puede no estar configurado
   - Conexión a Redis fallando

---

## Soluciones Propuestas

### Solución 1: Desactivar Healthcheck Temporalmente

Modificar `railway.toml` para desactivar el healthcheck:

```toml
[deploy]
healthcheckPath = "/health"
healthcheckTimeout = 300
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 3
# Añadir esto:
healthcheckEnabled = false  # Desactivar temporalmente
```

### Solución 2: Cambiar Healthcheck Timeout

Aumentar el timeout para dar más tiempo al backend:

```toml
[deploy]
healthcheckTimeout = 600  # 10 minutos en lugar de 5
```

### Solución 3: Agregar Startup Logs

Modificar el Dockerfile para agregar logs de startup:

```dockerfile
# Agregar antes de CMD
RUN echo "Starting QA-FRAMEWORK Backend..." >> /tmp/startup.log
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} >> /tmp/startup.log 2>&1"]
```

### Solución 4: Verificar Variables en Railway Dashboard

1. Ir a Railway Dashboard → QA-FRAMEWORK → Variables
2. Verificar que existan:
   - `DATABASE_URL` = `${{Postgres.DATABASE_URL}}`
   - `REDIS_URL` = `${{Redis.REDIS_URL}}`
   - `JWT_SECRET_KEY` = `qa-framework-production-secret-key-change-in-production-2026`
   - `STRIPE_API_KEY` = `sk_live_...`
   - `STRIPE_WEBHOOK_SECRET` = `whsec_QcsmAtCAuUTtINlsrkDSjrynqgxpcrKJ`
   - `ENABLE_BILLING` = `true`
   - `ENVIRONMENT` = `production`

3. Verificar que NO haya variables extra que causen error de Pydantic

---

## Acción Inmediata Requerida

**Ir a Railway Dashboard manualmente y:**

1. **Ver variables de entorno:**
   - URL: https://railway.com/project/336a37f6-b853-46a3-9513-b60b672541b3/service/1f1c2f20-d399-4d1c-83d3-54c3de0f55f3?ref=variables
   - Verificar que todas las variables estén presentes
   - Eliminar variables extra no definidas en config.py

2. **Ver logs del servicio:**
   - URL: https://railway.com/project/336a37f6-b853-46a3-9513-b60b672541b3/service/1f1c2f20-d399-4d1c-83d3-54c3de0f55f3?ref=logs
   - Buscar errores de startup
   - Ver si hay mensajes de error de Python

3. **Trigger redeploy después de corrección:**
   - Railway Dashboard → Deployments → Redeploy

---

## Variables Configuradas (vía API)

Las siguientes variables se han configurado vía API GraphQL:

✅ `STRIPE_WEBHOOK_SECRET`
✅ `ENABLE_BILLING`
✅ `ENVIRONMENT`
✅ `JWT_SECRET_KEY`
✅ `FRONTEND_URL`
✅ `LOG_LEVEL`

---

## Documentación

- **Guía de variables:** `docs/RAILWAY_ENV_VARS.md`
- **Configuración del backend:** `dashboard/backend/config.py`
- **Startup del backend:** `dashboard/backend/main.py` → `startup_event()`

---

## Próximos Pasos

1. **Joker revisa logs en Railway Dashboard**
2. **Corrige variables o configura healthcheck**
3. **Trigger redeploy**
4. **Verificar `/api/v1/billing/webhook`**
5. **Beta launch**

---

**Última actualización:** 2026-03-08 23:20 UTC
**Estado:** ⏳ Esperando revisión manual de Railway Dashboard
