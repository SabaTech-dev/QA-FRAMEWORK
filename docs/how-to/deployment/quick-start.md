# 🚀 Quick Start Guide - QA-FRAMEWORK

## ⚡ Configuración Rápida (35 minutos)

Esta guía te permite configurar todo lo necesario para desbloquear el proyecto.

### 📋 Prerequisitos

- [ ] Cuenta en [Railway](https://railway.app) (gratuita)
- [ ] Cuenta en [Stripe](https://dashboard.stripe.com) (modo test)
- [ ] Acceso al repositorio en GitHub

---

## 🔧 Paso 1: PostgreSQL en Railway (15 minutos)

### 1.1 Crear Base de Datos

```bash
# Ir a Railway dashboard
https://railway.app

# Crear nuevo proyecto
New Project → Provision PostgreSQL
```

### 1.2 Obtener URL de Conexión

```bash
# En Railway dashboard → PostgreSQL → Variables
# Copiar el valor de DATABASE_URL

# Ejemplo:
postgresql://postgres:PASSWORD@containers-us-west-xxx.railway.app:PORT/railway
```

### 1.3 Configurar en Backend

```bash
# En Railway dashboard → QA-FRAMEWORK-BACKEND → Variables
# Añadir variable:
DATABASE_URL=postgresql://postgres:PASSWORD@HOST:PORT/railway

# O en archivo .env local:
echo "DATABASE_URL=postgresql://..." > dashboard/backend/.env
```

### 1.4 Verificar Conexión

```bash
python3 scripts/validate_environment.py
# Debe mostrar: ✅ PostgreSQL - Connection successful
```

---

## 🔧 Paso 2: Redis en Railway (10 minutos)

### 2.1 Crear Instancia Redis

```bash
# En Railway dashboard
New Project → Provision Redis
```

### 2.2 Obtener URL de Conexión

```bash
# En Railway dashboard → Redis → Variables
# Copiar el valor de REDIS_URL

# Ejemplo:
redis://default:PASSWORD@containers-us-west-xxx.railway.app:PORT
```

### 2.3 Configurar en Backend

```bash
# En Railway dashboard → QA-FRAMEWORK-BACKEND → Variables
# Añadir variable:
REDIS_URL=redis://default:PASSWORD@HOST:PORT

# O en archivo .env local:
echo "REDIS_URL=redis://..." >> dashboard/backend/.env
```

### 2.4 Verificar Conexión

```bash
python3 scripts/validate_environment.py
# Debe mostrar: ✅ Redis - Connection successful
```

---

## 💳 Paso 3: Stripe Setup (10 minutos)

### 3.1 Crear Cuenta Stripe

```bash
# Ir a Stripe
https://dashboard.stripe.com

# Crear cuenta (modo test por defecto)
```

### 3.2 Obtener API Keys

```bash
# En Stripe Dashboard → Developers → API Keys
# Copiar:
- Publishable key (pk_test_...)
- Secret key (sk_test_...)
```

### 3.3 Configurar en Backend

```bash
# En Railway dashboard → QA-FRAMEWORK-BACKEND → Variables
# Añadir variables:
STRIPE_API_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...  # (ver paso 3.4)
```

### 3.4 Configurar Webhooks

```bash
# En Stripe Dashboard → Developers → Webhooks
# Add endpoint: 
https://qa-framework-backend.railway.app/webhooks/stripe

# Events to listen:
- checkout.session.completed
- invoice.paid
- invoice.payment_failed
- customer.subscription.updated
- customer.subscription.deleted

# Copiar el webhook secret (whsec_...)
```

### 3.5 Verificar Configuración

```bash
python3 scripts/validate_environment.py
# Debe mostrar: ✅ Stripe API - API key valid
```

---

## ✅ Paso 4: Verificación Final

### 4.1 Validar Entorno

```bash
# Ejecutar validador
python3 scripts/validate_environment.py

# Debe mostrar:
# ✅ Passed: 27
# 🎉 Environment is ready for deployment!
```

### 4.2 Ejecutar Migrations

```bash
cd dashboard/backend
alembic upgrade head
```

### 4.3 Reiniciar Backend

```bash
# En Railway dashboard → QA-FRAMEWORK-BACKEND
# Settings → Restart
```

---

## 📊 Checklist Final

```bash
# Ejecutar este checklist
python3 scripts/validate_environment.py
```

- [ ] PostgreSQL configurado
- [ ] Redis configurado
- [ ] Stripe API key configurado
- [ ] Stripe webhook secret configurado
- [ ] Migrations ejecutadas
- [ ] Backend reiniciado
- [ ] Tests pasando

---

## 🔍 Troubleshooting

### Error: "DATABASE_URL not set"

```bash
# Verificar que la variable está en Railway
Railway → Backend → Variables → DATABASE_URL

# O en .env local
cat dashboard/backend/.env | grep DATABASE_URL
```

### Error: "Connection refused"

```bash
# Verificar que los servicios están corriendo en Railway
Railway Dashboard → PostgreSQL → Status (debe ser "Running")
Railway Dashboard → Redis → Status (debe ser "Running")
```

### Error: "Stripe API call failed"

```bash
# Verificar que la API key es válida
# En Stripe Dashboard → Developers → API Keys
# Regenerar si es necesario
```

---

## 🎯 Próximos Pasos

Una vez configurado todo:

1. **Ejecutar tests E2E**:
   ```bash
   pytest tests/e2e/ -v
   ```

2. **Lanzar beta program**:
   ```bash
   # Seguir BETA_TESTING_MATERIALS.md
   ```

3. **Crear demo video**:
   ```bash
   # Seguir DEMO_VIDEO_SCRIPT.md
   ```

---

## 📞 Soporte

Si tienes problemas:
1. Revisar logs: `Railway → Backend → Logs`
2. Ejecutar validador: `python3 scripts/validate_environment.py`
3. Consultar documentación: `docs/`

---

**Tiempo total estimado:** 35 minutos
**Estado actual:** 🔴 BLOQUEADO - Requiere configuración manual
**Estado después:** ✅ DESBLOQUEADO - Listo para producción
