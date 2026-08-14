# 🚂 Railway Deployment Templates - QA-FRAMEWORK

**Propósito:** Templates y comandos listos para usar con Railway CLI
**Fecha:** 2026-02-24

---

## 📋 Comandos Esenciales

### Setup Inicial

```bash
# Instalar CLI
npm install -g @railway/cli

# Login (abre browser)
railway login

# Verificar login
railway whoami
```

### Crear Proyecto

```bash
# Crear nuevo proyecto
railway init

# O con nombre específico
railway init --name qaframework-prod

# Ver proyectos
railway list
```

### Añadir Servicios

```bash
# PostgreSQL
railway add --plugin postgresql

# Redis
railway add --plugin redis

# MySQL (alternativa)
railway add --plugin mysql
```

### Variables de Entorno

```bash
# Variables individuales
railway variables set JWT_SECRET_KEY="$(openssl rand -hex 32)"
railway variables set JWT_ALGORITHM="HS256"
railway variables set JWT_EXPIRATION_HOURS="24"
railway variables set LOG_LEVEL="INFO"
railway variables set CORS_ORIGINS='["https://qaframework.io","https://www.qaframework.io"]'

# Referencias a servicios del proyecto
railway variables set DATABASE_URL='${{Postgres.DATABASE_URL}}'
railway variables set REDIS_URL='${{Redis.REDIS_URL}}'

# Desde archivo
railway variables import < .env.production

# Ver todas las variables
railway variables

# Eliminar variable
railway variables unset OLD_VAR
```

### Deploy

```bash
# Deploy desde directorio actual
railway up

# Deploy con Dockerfile específico
railway up --dockerfile Dockerfile.prod

# Ver logs
railway logs

# Logs en tiempo real
railway logs --tail

# Ver status
railway status
```

### Dominios

```bash
# Generar dominio automático
railway domain

# Dominio personalizado
railway domain add qaframework.io
railway domain add api.qaframework.io

# Ver dominios
railway domain
```

### Rollback y Management

```bash
# Ver deployments
railway status

# Rollback al anterior
railway rollback

# Rollback a específico
railway rollback <deployment-id>

# Abrir en browser
railway open

# Conectar shell
railway run bash

# Ejecutar comando
railway run python scripts/migrate.py
```

---

## 📄 railway.toml Template

Crear archivo `railway.toml` en la raíz del proyecto:

```toml
[build]
builder = "DOCKERFILE"
dockerfilePath = "Dockerfile"

[deploy]
startCommand = "uvicorn dashboard.backend.main:app --host 0.0.0.0 --port $PORT"
healthcheckPath = "/health"
healthcheckTimeout = 300
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 10
numReplicas = 1

[[deploy.env]]
name = "PORT"
value = "8000"

[[deploy.env]]
name = "LOG_LEVEL"
value = "INFO"
```

---

## 🔧 Configuración por Ambiente

### Staging

```bash
# Crear environment de staging
railway environment create staging

# Variables de staging
railway variables set --environment staging LOG_LEVEL="DEBUG"
railway variables set --environment staging CORS_ORIGINS='["https://staging.qaframework.io"]'

# Deploy a staging
railway up --environment staging

# Dominio de staging
railway domain --environment staging
```

### Production

```bash
# Crear environment de producción
railway environment create production

# Variables de producción (más restrictivas)
railway variables set --environment production LOG_LEVEL="INFO"
railway variables set --environment production CORS_ORIGINS='["https://qaframework.io","https://www.qaframework.io"]'

# Deploy a producción
railway up --environment production

# Dominio de producción
railway domain add api.qaframework.io --environment production
```

---

## 🗄️ Database Management

### PostgreSQL

```bash
# Conectar a PostgreSQL
railway connect postgres

# Ejecutar migraciones
railway run alembic upgrade head

# Backup
railway run pg_dump $DATABASE_URL > backup_$(date +%Y%m%d).sql

# Restaurar backup
railway run psql $DATABASE_URL < backup_20260224.sql

# Ver tablas
railway run psql $DATABASE_URL -c "\dt"
```

### Redis

```bash
# Conectar a Redis
railway connect redis

# Flush DB (¡CUIDADO!)
railway run redis-cli -u $REDIS_URL FLUSHDB

# Ver info
railway run redis-cli -u $REDIS_URL INFO
```

---

## 📊 Monitoreo

### Métricas

```bash
# Ver métricas en dashboard
railway open

# O ir directo a:
# https://railway.app/project/<project-id>/metrics
```

### Logs Estructurados

```bash
# Logs con filtro
railway logs | grep ERROR

# Logs en tiempo real con grep
railway logs --tail | grep --line-buffered "400\|500"

# Exportar logs
railway logs > logs_$(date +%Y%m%d).txt
```

---

## 🚨 Troubleshooting

### Error: "Build failed"

```bash
# Ver logs de build detallados
railway logs --build

# Verificar Dockerfile localmente
docker build -t test .

# Verificar .dockerignore
cat .dockerignore
```

### Error: "Health check failed"

```bash
# Verificar endpoint localmente
curl http://localhost:8000/health

# Aumentar timeout en railway.toml
healthcheckTimeout = 600

# Verificar startCommand
railway run curl http://localhost:$PORT/health
```

### Error: "Out of memory"

```bash
# Verificar uso de memoria
railway status

# Optimizar Dockerfile
# - Usar multi-stage builds
# - Reducir dependencias

# Escalar verticalmente (más RAM)
# En Railway dashboard: Settings > Resources
```

### Error: "Database connection failed"

```bash
# Verificar que PostgreSQL está corriendo
railway status

# Verificar DATABASE_URL
railway variables | grep DATABASE_URL

# Probar conexión
railway run python -c "import os; from sqlalchemy import create_engine; engine = create_engine(os.getenv('DATABASE_URL')); print(engine.connect())"
```

---

## 💰 Cost Management

### Ver Uso

```bash
# Ver uso actual
railway usage

# Ver breakdown
railway billing
```

### Optimizar Costes

1. **Reducir réplicas:** `numReplicas = 1` en railway.toml
2. **Usar free tier:** $5 crédito mensual
3. **Apagar staging:** Cuando no se usa
4. **Optimizar Docker:** Imágenes más pequeñas = menos storage

```bash
# Pausar servicio (no elimina)
railway down

# Reanudar
railway up
```

---

## 🔄 CI/CD con GitHub Actions

Ver archivo: `.github/workflows/deploy.yml`

```yaml
name: Deploy to Railway

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Install Railway CLI
        run: npm install -g @railway/cli
      
      - name: Deploy
        run: railway up --token ${{ secrets.RAILWAY_TOKEN }}
```

---

## 📚 Recursos

- [Railway Docs](https://docs.railway.app/)
- [Railway CLI Reference](https://docs.railway.app/reference/cli-api)
- [Railway Variables](https://docs.railway.app/develop/variables)
- [Railway Docker](https://docs.railway.app/deploy/docker)

---

**Nota:** Guarda `RAILWAY_TOKEN` en GitHub Secrets para CI/CD automatizado.
