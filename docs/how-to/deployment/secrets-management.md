# 🔐 Secrets Management - QA-FRAMEWORK SaaS

**Fecha:** 2026-02-24
**Propósito:** Guía de gestión de secrets para producción
**Target:** Railway, Fly.io, Render

---

## 🚨 NUNCA Hacer

- ❌ Commitear secrets a Git
- ❌ Hardcodear secrets en código
- ❌ Compartir secrets por Slack/Email
- ❌ Usar secrets en logs
- ❌ Reutilizar secrets entre ambientes

---

## 📋 Lista de Secrets Requeridos

### Backend API

```bash
# Authentication
JWT_SECRET_KEY=your-super-secret-key-min-32-chars
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# Database
DATABASE_URL=postgresql://user:password@host:5432/dbname
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20

# Redis Cache
REDIS_URL=redis://user:password@host:6379/0

# Stripe Billing (Fase 2)
STRIPE_API_KEY=sk_live_xxxxx
STRIPE_WEBHOOK_SECRET=whsec_xxxxx
STRIPE_PRICE_PRO=price_xxxxx
STRIPE_PRICE_ENTERPRISE=price_xxxxx

# OAuth Providers (Fase 2)
GOOGLE_CLIENT_ID=xxxxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-xxxxx
GITHUB_CLIENT_ID=Iv1.xxxxx
GITHUB_CLIENT_SECRET=xxxxx

# Email (Fase 2)
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USER=apikey
SMTP_PASSWORD=SG.xxxxx

# Monitoring
SENTRY_DSN=https://xxxxx@sentry.io/xxxxx

# AI Features (Fase 3)
ZHIPUAI_API_KEY=xxxxx  # Free tier
OPENAI_API_KEY=sk-xxxxx  # Optional fallback
```

### Frontend Dashboard

```bash
# API Configuration
NEXT_PUBLIC_API_URL=https://api.qaframework.io
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_live_xxxxx

# Analytics (Opcional)
NEXT_PUBLIC_GA_ID=G-XXXXXXX
```

---

## 🛠️ Configuración por Provider

### Railway (Recomendado)

Railway usa **Variables de Entorno** nativas con UI y CLI.

#### Opción 1: CLI

```bash
# Set individual secrets
railway variables set JWT_SECRET_KEY=$(openssl rand -hex 32)
railway variables set DATABASE_URL=${{Postgres.DATABASE_URL}}
railway variables set REDIS_URL=${{Redis.REDIS_URL}}

# Set from file
railway variables set --from-file .env.production

# View all variables
railway variables
```

#### Opción 2: Dashboard UI

1. Ir a proyecto → Settings → Variables
2. Click "Add Variable"
3. Name: `JWT_SECRET_KEY`
4. Value: (pegar secret)
5. Click "Add"

#### Opción 3: Railway.json

```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "DOCKERFILE",
    "dockerfilePath": "Dockerfile"
  },
  "deploy": {
    "numReplicas": 1,
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

#### Referencias entre servicios

```bash
# Conectar a PostgreSQL del mismo proyecto
DATABASE_URL=${{Postgres.DATABASE_URL}}

# Conectar a Redis del mismo proyecto
REDIS_URL=${{Redis.REDIS_URL}}
```

---

### Fly.io

Fly.io usa **Secrets** con `flyctl`.

```bash
# Set secrets
flyctl secrets set JWT_SECRET_KEY=$(openssl rand -hex 32)
flyctl secrets set DATABASE_URL="postgresql://..."

# Set from file
flyctl secrets import < .env.production

# List secrets (names only, not values)
flyctl secrets list

# Unset a secret
flyctl secrets unset OLD_SECRET
```

**Nota:** Los secrets en Fly.io se inyectan como variables de entorno en runtime.

---

### Render

Render usa **Environment Variables** en el dashboard.

#### Opción 1: Dashboard

1. Ir a Service → Environment
2. Click "Add Environment Variable"
3. Key: `JWT_SECRET_KEY`
4. Value: (pegar secret)
5. Click "Save Changes"

#### Opción 2: render.yaml

```yaml
services:
  - type: web
    name: qaframework-api
    env: docker
    dockerfilePath: ./Dockerfile
    envVars:
      - key: JWT_SECRET_KEY
        generateValue: true  # Auto-generate
      - key: DATABASE_URL
        fromDatabase:
          name: qaframework-db
          property: connectionString
      - key: REDIS_URL
        sync: false  # Manual set
```

---

## 🔄 Rotación de Secrets

### Política de Rotación

| Secret | Frecuencia | Método |
|--------|------------|--------|
| JWT_SECRET_KEY | Cada 90 días | Manual |
| API Keys | Cada 180 días | Manual |
| Database Password | Cada 90 días | Automático (provider) |
| OAuth Secrets | Cada 365 días | Manual |

### Procedimiento de Rotación

```bash
# 1. Generar nuevo secret
NEW_JWT_SECRET=$(openssl rand -hex 32)

# 2. Añadir nuevo secret (no reemplazar aún)
railway variables set JWT_SECRET_KEY_NEW=$NEW_JWT_SECRET

# 3. Actualizar código para soportar múltiples keys
# (ver implementation abajo)

# 4. Deploy código nuevo

# 5. Reemplazar old con new
railway variables set JWT_SECRET_KEY=$NEW_JWT_SECRET
railway variables unset JWT_SECRET_KEY_NEW

# 6. Deploy final
railway up
```

---

## 🛡️ Best Practices

### 1. Generación de Secrets

```bash
# JWT Secret (mínimo 32 caracteres)
openssl rand -hex 32

# API Key (prefijo + random)
echo "qaframework_$(openssl rand -hex 16)"

# Password (complejo)
openssl rand -base64 24 | tr -d '/+=' | head -c 24
```

### 2. Validación al Startup

```python
# config.py
import os
from typing import List

REQUIRED_SECRETS = [
    "JWT_SECRET_KEY",
    "DATABASE_URL",
    "REDIS_URL",
]

def validate_secrets() -> List[str]:
    """Valida que todos los secrets requeridos estén presentes."""
    missing = []
    for secret in REQUIRED_SECRETS:
        if not os.getenv(secret):
            missing.append(secret)
    return missing

# Al iniciar la app
missing = validate_secrets()
if missing:
    raise ValueError(f"Missing required secrets: {', '.join(missing)}")
```

### 3. No Loguear Secrets

```python
# ❌ MAL
print(f"Connecting to database: {DATABASE_URL}")

# ✅ BIEN
import re
def sanitize_url(url: str) -> str:
    """Oculta password de URLs."""
    return re.sub(r'://([^:]+):([^@]+)@', r'://\1:****@', url)

print(f"Connecting to database: {sanitize_url(DATABASE_URL)}")
# Output: postgresql://user:****@host:5432/dbname
```

### 4. Secrets en Tests

```python
# tests/conftest.py
import os
import pytest

@pytest.fixture(scope="session", autouse=True)
def setup_test_secrets():
    """Configura secrets de prueba."""
    os.environ["JWT_SECRET_KEY"] = "test-secret-key-do-not-use-in-production"
    os.environ["DATABASE_URL"] = "sqlite:///test.db"
    os.environ["REDIS_URL"] = "redis://localhost:6379/15"  # DB 15 for tests
```

---

## 📊 Auditoría de Secrets

### Checklist Mensual

- [ ] Todos los secrets están en el secrets manager (no en código)
- [ ] No hay secrets en el historial de git
- [ ] Secrets rotados según política
- [ ] Solo admins tienen acceso a secrets
- [ ] Logs no contienen secrets
- [ ] Backup de secrets en ubicación segura

### Comando de Verificación

```bash
# Verificar que no hay secrets en git
git log --all --full-history -- '*.env' '*.pem' '*secret*'

# Verificar que .gitignore incluye archivos sensibles
grep -E '\.env|\.pem|secret' .gitignore

# Buscar posibles leaks en código
grep -r "password\s*=\s*['\"]" --include="*.py" .
grep -r "api_key\s*=\s*['\"]" --include="*.py" .
```

---

## 🔗 Recursos

- [Railway Variables Docs](https://docs.railway.app/develop/variables)
- [Fly.io Secrets Docs](https://fly.io/docs/reference/secrets/)
- [Render Environment Variables](https://render.com/docs/environment-variables)
- [OWASP Secrets Management](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheatsheet.html)

---

**Recuerda:** Los secrets son la llave a tu infraestructura. Trátalos con el respeto que merecen.
