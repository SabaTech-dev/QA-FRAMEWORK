# Variables de Entorno para Railway - QA-FRAMEWORK Backend

**Fecha:** 2026-03-08
**Proyecto:** QA-FRAMEWORK
**Servicio:** qa-framework-backend

> **🔐 Secretos externalizados (card d870cafa, 2026-11-13):** los valores reales NUNCA viven en git — `${VAULT:<NOMBRE>}` referencia el gestor de secretos (owner-lane). Sanitizado por security; commit pendiente de review.

---

## Variables Requeridas

Estas variables DEBEN estar configuradas en Railway Dashboard para que el backend funcione correctamente.

### Base de Datos (PostgreSQL)

| Variable | Valor | Descripción |
|----------|-------|-------------|
| `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` | Referencia al servicio PostgreSQL de Railway |

### Cache (Redis)

| Variable | Valor | Descripción |
|----------|-------|-------------|
| `REDIS_URL` | `${{Redis.REDIS_URL}}` | Referencia al servicio Redis de Railway |

**NOTA:** El backend también acepta `REDIS_HOST`, `REDIS_PORT`, `REDIS_PASSWORD` individualmente, pero `REDIS_URL` es preferido.

### Autenticación (JWT)

| Variable | Valor | Descripción |
|----------|-------|-------------|
| `JWT_SECRET_KEY` | `${VAULT:JWT_SECRET_KEY}` | Clave secreta para JWT tokens |

### Pagos (Stripe)

| Variable | Valor | Descripción |
|----------|-------|-------------|
| `STRIPE_API_KEY` | `${VAULT:STRIPE_API_KEY}` | API key de Stripe (LIVE) |
| `STRIPE_WEBHOOK_SECRET` | `${VAULT:STRIPE_WEBHOOK_SECRET}` | Secreto del webhook de Stripe |
| `ENABLE_BILLING` | `true` | Habilitar funcionalidades de billing |

### Configuración General

| Variable | Valor | Descripción |
|----------|-------|-------------|
| `ENVIRONMENT` | `production` | Entorno de ejecución |
| `FRONTEND_URL` | `https://frontend-phi-three-52.vercel.app` | URL del frontend (CORS) |
| `QA_FRAMEWORK_API_URL` | `http://localhost:8001` | URL de la API de QA Framework |
| `LOG_LEVEL` | `INFO` | Nivel de logging |

---

## Cómo Configurar en Railway

### Opción 1: Variables de Referencia (Recomendado)

Para `DATABASE_URL` y `REDIS_URL`, usar referencias a servicios de Railway:

```toml
[[services.env]]
name = "DATABASE_URL"
value = "${{Postgres.DATABASE_URL}}"

[[services.env]]
name = "REDIS_URL"
value = "${{Redis.REDIS_URL}}"
```

### Opción 2: Variables Manuales

Ir a Railway Dashboard → Proyecto → Servicio → Variables y añadir manualmente:

```
JWT_SECRET_KEY=${VAULT:JWT_SECRET_KEY}
STRIPE_API_KEY=${VAULT:STRIPE_API_KEY}
STRIPE_WEBHOOK_SECRET=${VAULT:STRIPE_WEBHOOK_SECRET}
ENABLE_BILLING=true
ENVIRONMENT=production
FRONTEND_URL=https://frontend-phi-three-52.vercel.app
LOG_LEVEL=INFO
```

---

## Verificación

Para verificar que las variables están configuradas correctamente:

```bash
# Health check
curl https://qa-framework-backend.railway.app/health

# Billing endpoint
curl https://qa-framework-backend.railway.app/api/v1/billing/plans
```

---

## Troubleshooting

### Error: "Extra inputs are not permitted"

Si el backend falla al iniciar con este error, significa que hay variables extra en Railway que no están definidas en `config.py`. Solución:

1. Ir a Railway Dashboard → Variables
2. Eliminar variables que NO estén en la lista de arriba
3. Redeploy

### Error: "Missing required environment variables"

Si el backend falla al iniciar con este error, significa que faltan variables requeridas. Solución:

1. Verificar que todas las variables de arriba estén configuradas
2. Redeploy

---

## Última Actualización

**Fecha:** 2026-03-08 23:15 UTC
**Sanitizado:** 2026-11-13 (card d870cafa) — secretos → `${VAULT:*}`
**Commit:** (pending review)
**Estado:** Variables documentadas, pendiente configuración en Railway
