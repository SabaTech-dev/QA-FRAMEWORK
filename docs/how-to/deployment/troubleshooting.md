# 🔧 Deployment Troubleshooting Guide

**Propósito:** Soluciones a problemas comunes de deployment
**Fecha:** 2026-02-24

---

## 🚨 Problemas Críticos

### 1. Build Failure - Docker

**Síntoma:** Build falla durante `docker build`

**Diagnóstico:**
```bash
# Build local para reproducir
docker build -t qaframework:test .

# Ver stages individualmente
docker build --target builder -t qaframework:builder .
docker build --target runtime -t qaframework:runtime .
```

**Soluciones Comunes:**

#### Error: "pip install failed"
```dockerfile
# ❌ MAL
RUN pip install -r requirements.txt

# ✅ BIEN
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt
```

#### Error: "out of memory during build"
```bash
# Aumentar memoria de build en railway.toml
[build]
memoryMB = 2048
```

#### Error: "COPY failed: file not found"
```bash
# Verificar .dockerignore
cat .dockerignore

# Verificar que archivos existen
ls -la src/
```

---

### 2. Health Check Timeout

**Síntoma:** Deploy muestra "Health check failed" después de 5 minutos

**Diagnóstico:**
```bash
# Verificar endpoint funciona localmente
curl http://localhost:8000/health

# Ver logs del contenedor
railway logs --tail

# Verificar puerto correcto
echo $PORT
```

**Soluciones:**

#### healthcheckPath incorrecto
```python
# ❌ MAL - Endpoint no existe
@app.get("/healthz")

# ✅ BIEN - Endpoint debe coincidir con config
@app.get("/health")
def health_check():
    return {"status": "healthy"}
```

#### Aplicación no inicia en PORT
```python
# ❌ MAL - Puerto hardcoded
uvicorn.run(app, host="0.0.0.0", port=8000)

# ✅ BIEN - Puerto dinámico
import os
port = int(os.getenv("PORT", 8000))
uvicorn.run(app, host="0.0.0.0", port=port)
```

#### Timeout muy corto
```toml
# railway.toml
[deploy]
healthcheckTimeout = 600  # 10 minutos
```

---

### 3. Database Connection Refused

**Síntoma:** `ConnectionRefusedError` o `could not connect to server`

**Diagnóstico:**
```bash
# Verificar DATABASE_URL existe
railway variables | grep DATABASE_URL

# Probar conexión
railway run python -c "
import os
from sqlalchemy import create_engine
engine = create_engine(os.getenv('DATABASE_URL'))
try:
    conn = engine.connect()
    print('✅ Connection OK')
    conn.close()
except Exception as e:
    print(f'❌ Connection failed: {e}')
"
```

**Soluciones:**

#### DATABASE_URL malformada
```bash
# Formato correcto
postgresql://user:password@host:port/database?sslmode=require

# Verificar estructura
railway variables get DATABASE_URL
```

#### SSL requerido pero no configurado
```python
# Agregar sslmode a URL
DATABASE_URL = os.getenv("DATABASE_URL")
if "?" in DATABASE_URL:
    DATABASE_URL += "&sslmode=require"
else:
    DATABASE_URL += "?sslmode=require"
```

#### Pool de conexiones agotado
```python
# Configurar pool adecuadamente
engine = create_engine(
    DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=3600
)
```

---

### 4. Application Crashes on Start

**Síntoma:** Contenedor reinicia constantemente

**Diagnóstico:**
```bash
# Ver logs de crash
railway logs --tail

# Ver eventos de restart
railway status

# Ejecutar manualmente para debug
railway run bash
> python -m dashboard.backend.main
```

**Soluciones Comunes:**

#### Missing environment variable
```python
# Agregar validación al inicio
import sys
required_vars = ["JWT_SECRET_KEY", "DATABASE_URL", "REDIS_URL"]
missing = [v for v in required_vars if not os.getenv(v)]
if missing:
    print(f"Missing required vars: {missing}")
    sys.exit(1)
```

#### Import error
```bash
# Verificar todas las dependencias están en requirements.txt
pip freeze > requirements_freeze.txt
diff requirements.txt requirements_freeze.txt
```

#### Syntax error
```bash
# Validar sintaxis antes de deploy
python -m py_compile src/**/*.py
```

---

## ⚠️ Problemas de Performance

### 5. Slow Response Times

**Síntoma:** Requests tardan >5 segundos

**Diagnóstico:**
```bash
# Verificar uso de recursos
railway status

# Ver métricas
# https://railway.app/project/<id>/metrics

# Profile en código
import time
start = time.time()
# ... código lento ...
print(f"Time: {time.time() - start}s")
```

**Soluciones:**

#### Sin caché
```python
# Agregar caché Redis
from functools import lru_cache
import redis

redis_client = redis.from_url(os.getenv("REDIS_URL"))

def get_with_cache(key, fetch_func, ttl=300):
    cached = redis_client.get(key)
    if cached:
        return cached
    value = fetch_func()
    redis_client.setex(key, ttl, value)
    return value
```

#### Database queries lentas
```python
# Agregar índices
# migration.sql
CREATE INDEX idx_tests_project_id ON tests(project_id);
CREATE INDEX idx_results_test_id ON test_results(test_id);

# Usar EXPLAIN ANALYZE
EXPLAIN ANALYZE SELECT * FROM tests WHERE project_id = 'xxx';
```

#### Sin connection pooling
```python
# Ya mencionado arriba - usar pool_pre_ping
engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True
)
```

---

### 6. Memory Issues (OOM Killed)

**Síntoma:** Container killed por "Out of Memory"

**Diagnóstico:**
```bash
# Verificar memory limit
railway status

# Verificar memory usage actual
railway logs | grep -i memory

# Profile memory en código
import tracemalloc
tracemalloc.start()
# ... código ...
snapshot = tracemalloc.take_snapshot()
top_stats = snapshot.statistics('lineno')
for stat in top_stats[:10]:
    print(stat)
```

**Soluciones:**

#### Memory leaks
```python
# Cerrar conexiones explícitamente
# ❌ MAL
def get_data():
    conn = engine.connect()
    return conn.execute(query)

# ✅ BIEN
def get_data():
    with engine.connect() as conn:
        return conn.execute(query)
```

#### Cargar datasets grandes en memoria
```python
# ❌ MAL - Cargar todo
results = session.query(Test).all()

# ✅ BIEN - Usar generators
def get_tests_batch(batch_size=100):
    offset = 0
    while True:
        batch = session.query(Test).offset(offset).limit(batch_size).all()
        if not batch:
            break
        yield from batch
        offset += batch_size
```

#### Aumentar memoria
```toml
# railway.toml
[deploy]
# Escalar verticalmente
memoryMB = 1024
```

---

## 🔐 Problemas de Seguridad

### 7. CORS Errors

**Síntoma:** Browser bloquea requests con error CORS

**Diagnóstico:**
```bash
# Verificar configuración CORS
railway variables get CORS_ORIGINS

# Test con curl
curl -H "Origin: https://qaframework.io" \
     -H "Access-Control-Request-Method: GET" \
     -X OPTIONS \
     https://api.qaframework.io/health
```

**Soluciones:**

#### Configuración incorrecta
```python
# ❌ MAL - Too permissive
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
)

# ✅ BIEN - Specific origins
import json
origins = json.loads(os.getenv("CORS_ORIGINS", '["http://localhost:3000"]'))
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)
```

---

### 8. Authentication Failing

**Síntoma:** 401 Unauthorized en requests con token válido

**Diagnóstico:**
```bash
# Verificar JWT_SECRET_KEY es el mismo
railway variables get JWT_SECRET_KEY

# Decodificar token (sin verificar)
# Usar jwt.io o:
python -c "
import jwt
token = 'YOUR_TOKEN_HERE'
print(jwt.decode(token, options={'verify_signature': False}))
"
```

**Soluciones:**

#### Secret key diferente entre servicios
```bash
# Asegurar que todos los servicios usan la misma key
railway variables set JWT_SECRET_KEY="same-key-everywhere"
```

#### Token expirado
```python
# Manejar expiración gracefully
from fastapi import HTTPException

try:
    payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
except jwt.ExpiredSignatureError:
    raise HTTPException(401, "Token expired - please login again")
except jwt.InvalidTokenError:
    raise HTTPException(401, "Invalid token")
```

---

## 🔄 Rollback y Recovery

### Rollback Rápido

```bash
# Ver deployments previos
railway status

# Rollback al anterior
railway rollback

# Rollback a específico
railway rollback <deployment-id>

# Verificar rollback
railway logs --tail
```

### Database Recovery

```bash
# Restaurar desde backup
railway run psql $DATABASE_URL < backup_20260224.sql

# O restaurar tabla específica
railway run pg_restore -d $DATABASE_URL -t tests backup.dump
```

### Recovery Completo

```bash
# 1. Rollback código
railway rollback

# 2. Restaurar variables si cambiaron
railway variables set DATABASE_URL="previous_value"

# 3. Restaurar DB si hubo migración
railway run alembic downgrade -1
# o
railway run psql $DATABASE_URL < backup.sql

# 4. Verificar
curl https://api.qaframework.io/health

# 5. Notificar
# - Slack
# - Status page
# - Email stakeholders
```

---

## 📞 Escalation Path

Si no puedes resolver el problema:

1. **Logs:** `railway logs > incident_logs.txt`
2. **Status:** `railway status > incident_status.txt`
3. **Variables:** `railway variables > incident_vars.txt` (sin valores sensibles)
4. **Railway Status Page:** https://status.railway.app/
5. **Railway Discord:** https://discord.gg/railway
6. **Railway Support:** support@railway.app

---

**Recuerda:** Documenta cada incidente en `.learnings/INCIDENTS.md` para prevenir futuros problemas.
