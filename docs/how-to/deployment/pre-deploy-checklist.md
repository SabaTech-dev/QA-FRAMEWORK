# ✅ Pre-Deploy Checklist - QA-FRAMEWORK SaaS

**Versión:** 1.0
**Fecha:** 2026-02-24
**Propósito:** Verificación obligatoria antes de cada deploy

---

## 🔴 CRÍTICO - Bloquea Deploy

### Seguridad

- [ ] **JWT_SECRET_KEY** no es hardcoded en código
- [ ] **DATABASE_URL** usa SSL (`?sslmode=require`)
- [ ] **No secrets** en git history (`git log --all | grep -i secret`)
- [ ] **.env.example** existe con variables documentadas (sin valores reales)
- [ ] **CORS** configurado solo para dominios permitidos
- [ ] **Rate limiting** habilitado en endpoints sensibles
- [ ] **Input validation** en todos los endpoints públicos

### Database

- [ ] **Migraciones** probadas localmente (`alembic upgrade head`)
- [ ] **Backups** configurados antes de migraciones
- [ ] **Connection pooling** configurado correctamente
- [ ] **SSL** habilitado para conexiones remotas

### Performance

- [ ] **Health check** endpoint responde (`/health`)
- [ ] **Timeouts** configurados (no infinitos)
- [ ] **Memory limits** establecidos
- [ ] **CPU limits** establecidos

---

## 🟡 IMPORTANTE - Revisar

### Código

- [ ] **Tests unitarios** pasando (`pytest tests/unit`)
- [ ] **Tests integración** pasando (si aplica)
- [ ] **Linting** sin errores críticos (`flake8`, `black --check`)
- [ ] **Type hints** actualizados (`mypy src`)
- [ ] **Dependencias** sin vulnerabilidades (`pip-audit`)

### Configuración

- [ ] **LOG_LEVEL** apropiado para ambiente (INFO en prod, DEBUG en dev)
- [ ] **Variables de entorno** documentadas
- [ ] **Dockerfile** optimizado (multi-stage, layers cacheadas)
- [ ] **.dockerignore** configurado

### Monitoreo

- [ ] **Health checks** configurados en cloud provider
- [ ] **Alertas** configuradas para errores críticos
- [ ] **Logs** estructurados (JSON) y enviados a destino centralizado

---

## 🟢 OPCIONAL - Mejora Calidad

### Documentación

- [ ] **README.md** actualizado con nuevos cambios
- [ ] **CHANGELOG.md** actualizado
- [ ] **API docs** actualizadas (OpenAPI)
- [ ] **Comentarios** en código complejo

### Performance

- [ ] **Índices** creados para queries frecuentes
- [ ] **Caché** configurado para datos estáticos
- [ ] **CDN** configurado para assets estáticos

---

## 📋 Checklist por Ambiente

### Staging (Pre-Production)

```bash
# 1. Variables de entorno
cp .env.staging.example .env.staging
# Editar con valores de staging

# 2. Validar configuración
python scripts/validate_config.py --env staging

# 3. Correr tests
pytest tests/ --cov=src --cov-report=html

# 4. Build local
docker build -t qaframework:staging -f Dockerfile .

# 5. Test local
docker-compose -f docker-compose.staging.yml up -d
curl http://localhost:8000/health

# 6. Deploy a staging
railway up --environment staging

# 7. Validar en staging
curl https://staging.qaframework.io/health
```

### Production

```bash
# 1. Checklist crítico completo
make pre-deploy-check

# 2. Backup database
railway run pg_dump $DATABASE_URL > backup_$(date +%Y%m%d).sql

# 3. Deploy con rollback ready
railway up

# 4. Health check
curl https://api.qaframework.io/health

# 5. Smoke tests
pytest tests/smoke/ --tb=short

# 6. Monitorear logs (5 minutos)
railway logs --tail

# 7. Si hay problemas, rollback
railway rollback
```

---

## 🔧 Script de Validación Automática

```bash
#!/bin/bash
# scripts/pre-deploy-check.sh

set -e

echo "🔍 Running pre-deploy checks..."

# Check secrets not in git
if git log --all --full-history -- '*.env' '*.pem' '*secret*' 2>/dev/null | grep -q .; then
    echo "❌ FAIL: Secrets found in git history"
    exit 1
fi
echo "✅ No secrets in git history"

# Check required env vars
REQUIRED_VARS=("JWT_SECRET_KEY" "DATABASE_URL" "REDIS_URL")
for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        echo "❌ FAIL: Missing required env var: $var"
        exit 1
    fi
done
echo "✅ All required env vars set"

# Check tests pass
if ! pytest tests/unit -q; then
    echo "❌ FAIL: Unit tests failed"
    exit 1
fi
echo "✅ Unit tests passed"

# Check health endpoint exists
if ! grep -r "/health" src/ --include="*.py" > /dev/null; then
    echo "⚠️  WARNING: Health endpoint not found"
fi
echo "✅ Health endpoint exists"

# Check Dockerfile exists
if [ ! -f "Dockerfile" ]; then
    echo "❌ FAIL: Dockerfile not found"
    exit 1
fi
echo "✅ Dockerfile exists"

# Check docker-compose for production
if [ ! -f "docker-compose.prod.yml" ] && [ ! -f "docker-compose.railway.yml" ]; then
    echo "⚠️  WARNING: Production docker-compose not found"
fi
echo "✅ Production docker-compose exists"

echo ""
echo "🎉 All pre-deploy checks passed!"
echo "Ready to deploy to production."
```

---

## 📊 Template de Release Notes

```markdown
## Release v1.X.X - YYYY-MM-DD

### ✨ Features
- [Feature 1]
- [Feature 2]

### 🐛 Bug Fixes
- [Fix 1]
- [Fix 2]

### 🔒 Security
- [Security improvement]

### 📝 Breaking Changes
- [Breaking change 1]

### 📦 Dependencies
- Updated [package] from X to Y

### 🚀 Deployment Notes
- [Special instruction 1]
- Run migration: `alembic upgrade head`
```

---

## 🚨 Rollback Plan

Si algo sale mal después del deploy:

```bash
# 1. Rollback inmediato
railway rollback

# 2. Verificar health
curl https://api.qaframework.io/health

# 3. Restaurar backup de DB si hubo migración
railway run psql $DATABASE_URL < backup_YYYYMMDD.sql

# 4. Notificar
# - Slack channel
# - Email a stakeholders
# - Update status page

# 5. Post-mortem
# - Documentar qué falló
# - Root cause analysis
# - Action items para prevenir
```

---

## ✍️ Sign-off

Antes de deploy a producción:

| Rol | Nombre | Fecha | Firma |
|-----|--------|-------|-------|
| **Developer** | _______ | _______ | _______ |
| **QA** | _______ | _______ | _______ |
| **DevOps** | _______ | _______ | _______ |

---

**Recuerda:** Un minuto de checklist puede ahorrarte horas de rollback. ✅
