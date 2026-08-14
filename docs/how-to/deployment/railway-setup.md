# 🚀 Configuración de Railway - PostgreSQL y Redis

**Fecha:** 2026-02-24 21:35 UTC
**Objetivo:** Configurar PostgreSQL y Redis para el backend de QA-FRAMEWORK

---

## 📋 Prerrequisitos

1. Cuenta de Railway: https://railway.app
2. Proyecto Railway ya creado (QA-FRAMEWORK backend deployado)
3. Railway CLI instalado (opcional)

---

## 🔧 PASO 1: Configurar PostgreSQL

### Opción A: Via Web UI (Recomendado)

1. Ir a: https://railway.app/dashboard
2. Entrar al proyecto QA-FRAMEWORK
3. Hacer clic en **"New Project"** o **"+ New Service"**
4. Seleccionar **"Database"** → **"Add PostgreSQL"**
5. Railway creará automáticamente:
   - PostgreSQL instance
   - Connection string
   - Environment variables

### Opción B: Via CLI

```bash
# Login a Railway
railway login --browserless

# Crear servicio PostgreSQL
railway add postgresql

# Obtener connection string
railway variables
```

---

## 🔧 PASO 2: Configurar Redis

### Opción A: Via Web UI (Recomendado)

1. En el proyecto QA-FRAMEWORK
2. Hacer clic en **"+ New Service"**
3. Seleccionar **"Database"** → **"Add Redis"**
4. Railway creará automáticamente:
   - Redis instance
   - Connection URL
   - Environment variables

### Opción B: Via CLI

```bash
# Crear servicio Redis
railway add redis

# Obtener connection URL
railway variables
```

---

## 🔧 PASO 3: Obtener Connection Strings

### PostgreSQL Connection String

En Railway Web UI:

1. Seleccionar el servicio PostgreSQL
2. Ir a la pestaña **"Variables"**
3. Copiar `DATABASE_URL` o `POSTGRES_URL`

El formato será:
```
postgresql://username:password@host:port/database
```

### Redis Connection URL

En Railway Web UI:

1. Seleccionar el servicio Redis
2. Ir a la pestaña **"Variables"**
3. Copiar `REDIS_URL` o `REDISCLOUD_URL`

El formato será:
```
redis://username:password@host:port
```

---

## 🔧 PASO 4: Configurar Environment Variables en el Backend

### Agregar variables al proyecto Railway (backend):

1. Seleccionar el servicio **qa-framework-backend**
2. Ir a la pestaña **"Variables"**
3. Agregar las siguientes variables:

```bash
# Database
DATABASE_URL=postgresql://username:password@host:port/database

# Redis
REDIS_HOST=host
REDIS_PORT=port
REDIS_PASSWORD=password
```

**Nota:** Reemplazar `username`, `password`, `host`, `port`, `database` con los valores reales del paso 3.

---

## 🔧 PASO 5: Verificar Conexión

### Verificar PostgreSQL

```bash
# Desde el servidor
cd /home/ubuntu/.openclaw/workspace/QA-FRAMEWORK/dashboard/backend
source venv/bin/activate

# Test connection
python3 << 'EOF'
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from config import settings

async def test():
    engine = create_async_engine(settings.database_url)
    async with engine.connect() as conn:
        result = await conn.execute("SELECT 1")
        print("✅ PostgreSQL connection successful!")

asyncio.run(test())
EOF
```

### Verificar Redis

```bash
# Desde el servidor
cd /home/ubuntu/.openclaw/workspace/QA-FRAMEWORK/dashboard/backend
source venv/bin/activate

# Test connection
python3 << 'EOF'
import asyncio
from core.cache import CacheManager

async def test():
    cache = CacheManager()
    await cache.set("test_key", "test_value", ttl=60)
    value = await cache.get("test_key")
    print(f"✅ Redis connection successful! Value: {value}")

asyncio.run(test())
EOF
```

---

## 🔧 PASO 6: Crear Database Migrations

### Instalar Alembic (si no está instalado)

```bash
cd /home/ubuntu/.openclaw/workspace/QA-FRAMEWORK/dashboard/backend
source venv/bin/activate
pip install alembic
```

### Inicializar Alembic

```bash
cd /home/ubuntu/.openclaw/workspace/QA-FRAMEWORK/dashboard/backend
alembic init alembic
```

### Configurar alembic.ini

Editar `alembic.ini`:

```ini
# sqlalchemy.url = driver://user:pass@localhost/dbname
sqlalchemy.url = postgresql+asyncpg://username:password@host:port/database
```

### Crear primera migration

```bash
# Migration para campos OAuth, API keys, y subscription
alembic revision --autogenerate -m "Add OAuth, API keys, and subscription fields"
```

Esto creará un archivo en `alembic/versions/` con la migration SQL.

### Ejecutar migration en desarrollo

```bash
alembic upgrade head
```

---

## 🔧 PASO 7: Deploy en Railway

### Trigger rebuild del backend

1. En Railway Web UI
2. Seleccionar servicio **qa-framework-backend**
3. Hacer clic en **"Redeploy"** o push un nuevo commit

### Verificar deployment

```bash
# Health check
curl https://qa-framework-backend.railway.app/health

# Verificar logs en Railway Web UI
```

---

## 📊 Variables de Entorno Necesarias

Resumen completo de variables necesarias:

```bash
# Database (Railway PostgreSQL)
DATABASE_URL=postgresql://user:pass@host:port/db

# Redis (Railway Redis)
REDIS_HOST=redis-host
REDIS_PORT=6379
REDIS_PASSWORD=redis-password

# Auth
JWT_SECRET_KEY=your-secret-key-here

# Stripe (obtener de Stripe dashboard)
STRIPE_API_KEY=sk_test_xxxxx
STRIPE_WEBHOOK_SECRET=whsec_xxxxx

# OAuth (obtener de provider dashboards)
GOOGLE_CLIENT_ID=google-client-id
GOOGLE_CLIENT_SECRET=google-client-secret
GITHUB_CLIENT_ID=github-client-id
GITHUB_CLIENT_SECRET=github-client-secret

# Frontend
FRONTEND_URL=https://your-frontend-url.com

# QA Framework API
QA_FRAMEWORK_API_URL=http://localhost:8001
```

---

## ✅ Checklist de Verificación

- [ ] PostgreSQL service creado en Railway
- [ ] Redis service creado en Railway
- [ ] DATABASE_URL configurado en backend
- [ ] REDIS_HOST, REDIS_PORT, REDIS_PASSWORD configurados
- [ ] JWT_SECRET_KEY configurado
- [ ] Migration creada para OAuth fields
- [ ] Migration creada para API key model
- [ ] Migration creada para subscription fields
- [ ] Migrations ejecutadas en desarrollo
- [ ] Backend redeployado en Railway
- [ ] Health check: 200 OK
- [ ] PostgreSQL connection test: ✅
- [ ] Redis connection test: ✅

---

## 🚨 Solución de Problemas

### Error: Connection refused

**Causa:** PostgreSQL o Redis no iniciados
**Solución:** Verificar que los servicios estén "Active" en Railway

### Error: Authentication failed

**Causa:** Connection string incorrecta
**Solución:** Verificar DATABASE_URL y REDIS_HOST variables

### Error: Migration fails

**Causa:** Schema ya existe o conflicto
**Solución:**
```bash
# Reset database (¡ADVERTENCIA: Borra todos los datos!)
alembic downgrade base
alembic upgrade head
```

---

## 📚 Referencias

- Railway Documentation: https://docs.railway.app
- PostgreSQL Docs: https://www.postgresql.org/docs/
- Redis Docs: https://redis.io/documentation
- Alembic Docs: https://alembic.sqlalchemy.org/

---

**Creado por:** Alfred (IA Asistente)
**Última actualización:** 2026-02-24 21:35 UTC
