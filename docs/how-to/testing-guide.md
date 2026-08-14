# QA-FRAMEWORK - Manual Testing Guide

**Preparado por:** Alfred (CEO Agent)
**Fecha:** 2026-03-10
**Estado:** Scripts listos, listo para ejecución

---

## 🎯 Objetivo

Validar que QA-FRAMEWORK está listo para beta testing mediante:
1. Load Testing (100 usuarios concurrentes, <200ms)
2. Security Testing (0 vulnerabilidades críticas)
3. Regression Testing (100% passing)

---

## 📋 Prerrequisitos

### 1. Verificar Backend Corriendo
```bash
# Local
curl http://localhost:8000/health

# Producción (Railway)
curl https://qa-framework-backend.railway.app/health
```

### 2. Verificar Dependencias Instaladas
```bash
cd /home/ubuntu/.openclaw/workspace/QA-FRAMEWORK

# Verificar Python packages
pip list | grep -E "(locust|bandit|safety|pytest)"

# Si faltan, instalar:
pip install locust bandit safety pytest pytest-html pytest-xdist
```

---

## 1️⃣ LOAD TESTING

### Objetivo
- 100 usuarios concurrentes
- Response time <200ms (p95)
- 0 errores 5xx

### Ejecución

#### Opción A: Interactivo (Recomendado para primera vez)
```bash
cd /home/ubuntu/.openclaw/workspace/QA-FRAMEWORK

# Local testing
locust -f tests/load/locustfile.py --host http://localhost:8000

# Luego abrir: http://localhost:8089
# Configurar:
#   - Number of users: 100
#   - Spawn rate: 10
#   - Click "Start swarming"
```

#### Opción B: Headless (CI/CD)
```bash
cd /home/ubuntu/.openclaw/workspace/QA-FRAMEWORK

# 5 minutos de test con 100 usuarios
locust -f tests/load/locustfile.py \
    --host http://localhost:8000 \
    --users 100 \
    --spawn-rate 10 \
    --run-time 5m \
    --headless \
    --html reports/load-test-report.html
```

#### Opción C: Producción (⚠️ CAUTION)
```bash
# SOLO si estás seguro
locust -f tests/load/locustfile.py \
    --host https://qa-framework-backend.railway.app \
    --users 50 \
    --spawn-rate 5 \
    --run-time 3m \
    --headless \
    --html reports/load-test-prod.html
```

### Criterios de Éxito
- ✅ Total Requests: >10,000
- ✅ Failure Rate: <1%
- ✅ Average Response Time: <200ms
- ✅ 95th percentile: <500ms

---

## 2️⃣ SECURITY TESTING

### Objetivo
- 0 vulnerabilidades CRÍTICAS
- 0 vulnerabilidades HIGH
- Security headers configurados
- Rate limiting activo

### Ejecución

#### Automatizado (Recomendado)
```bash
cd /home/ubuntu/.openclaw/workspace/QA-FRAMEWORK

# Ejecutar script completo
./scripts/security_scan.sh

# Revisar reportes:
# - reports/security/zap_report_*.html (OWASP ZAP)
# - reports/security/bandit_*.json (Code vulnerabilities)
# - reports/security/safety_*.json (Dependency issues)
```

#### Manual (Si prefieres control paso a paso)

##### A. OWASP ZAP Scan
```bash
# Con Docker (recomendado)
docker run --rm -v $(pwd)/reports:/zap/wrk:rw \
    owasp/zap2docker-stable \
    zap-baseline.py -t http://localhost:8000 -r zap_report.html

# O con zap-cli (si está instalado)
zap-cli quick-scan --spider http://localhost:8000 -o reports/zap.html -f html
```

##### B. Bandit (Python Security)
```bash
# Escanear código fuente
bandit -r src/ -f json -o reports/bandit.json
bandit -r src/ -f txt -o reports/bandit.txt

# Ver reporte
cat reports/bandit.txt
```

##### C. Safety (Dependencies)
```bash
# Verificar dependencias vulnerables
safety check --json > reports/safety.json 2>&1
safety check > reports/safety.txt 2>&1

# Ver reporte
cat reports/safety.txt
```

##### D. Tests Manuales
```bash
# SQL Injection
curl -X POST http://localhost:8000/api/v1/test-runs \
    -H "Content-Type: application/json" \
    -d '{"test_id": "1 OR 1=1", "name": "test"}'

# XSS
curl -X POST http://localhost:8000/api/v1/test-runs \
    -H "Content-Type: application/json" \
    -d '{"name": "<script>alert(1)</script>", "test_id": "xss-test"}'

# Security Headers
curl -I http://localhost:8000 | grep -iE "x-frame-options|x-content-type-options|strict-transport-security"
```

### Criterios de Éxito
- ✅ ZAP: 0 HIGH/CRITICAL alerts
- ✅ Bandit: 0 HIGH/CRITICAL issues
- ✅ Safety: 0 known vulnerabilities
- ✅ Security headers present
- ✅ Rate limiting active

---

## 3️⃣ REGRESSION TESTING

### Objetivo
- 100% tests pasando
- 0 regresiones

### Ejecución

#### Completo (Recomendado)
```bash
cd /home/ubuntu/.openclaw/workspace/QA-FRAMEWORK

# Ejecutar suite completa
./scripts/regression_test.sh

# Reportes generados en:
# - reports/regression/regression_*.html (uno por suite)
```

#### Por Componente (Si necesitas debug)

##### A. Unit Tests
```bash
pytest tests/unit/ -v --html=reports/unit.html --self-contained-html
```

##### B. Integration Tests
```bash
pytest tests/integration/ -v --html=reports/integration.html --self-contained-html
```

##### C. Security Tests
```bash
pytest tests/security/ -v -m security --html=reports/security_tests.html --self-contained-html
```

##### D. Performance Tests
```bash
pytest tests/performance/ -v -m performance --html=reports/performance.html --self-contained-html
```

##### E. E2E Tests
```bash
pytest tests/e2e/ -v -m e2e --html=reports/e2e.html --self-contained-html
```

##### F. Todos en Paralelo (Rápido)
```bash
pytest tests/ -v -n 4 --html=reports/all_parallel.html --self-contained-html
```

### Criterios de Éxito
- ✅ Pass Rate: 100%
- ✅ 0 FAILED tests
- ✅ Coverage: ≥85%

---

## 📊 Validación Final

### Checklist Pre-Beta
```bash
# 1. Load Testing
[ ] Ejecutado load test con 100 usuarios
[ ] Response time <200ms (p95)
[ ] 0 errores 5xx
[ ] Reporte guardado: reports/load-test-report.html

# 2. Security Testing
[ ] OWASP ZAP scan completado
[ ] Bandit scan sin CRITICAL/HIGH issues
[ ] Safety check sin vulnerabilidades
[ ] Security headers verificados
[ ] Rate limiting funcionando
[ ] Reportes guardados: reports/security/

# 3. Regression Testing
[ ] 100% tests pasando
[ ] Coverage ≥85%
[ ] Reportes guardados: reports/regression/

# 4. Backend Health
[ ] /health endpoint OK
[ ] /docs accessible
[ ] Database connected
[ ] Redis connected
[ ] Stripe configured

# 5. Frontend Health
[ ] https://frontend-phi-three-52.vercel.app accessible
[ ] Login flow works
[ ] Dashboard loads
[ ] API calls successful
```

---

## 🚀 Ejecución Rápida (Todo en Uno)

```bash
cd /home/ubuntu/.openclaw/workspace/QA-FRAMEWORK

# Crear directorio de reportes
mkdir -p reports/{load,security,regression}

# 1. Load Testing (5 min)
echo "1️⃣ Load Testing..."
locust -f tests/load/locustfile.py --host http://localhost:8000 \
    --users 100 --spawn-rate 10 --run-time 5m --headless \
    --html reports/load/load-test-report.html

# 2. Security Testing (10 min)
echo "2️⃣ Security Testing..."
./scripts/security_scan.sh

# 3. Regression Testing (15 min)
echo "3️⃣ Regression Testing..."
./scripts/regression_test.sh

# 4. Generar resumen
echo "4️⃣ Generating summary..."
cat <<EOF > reports/TEST_SUMMARY.md
# QA-FRAMEWORK Testing Summary

**Date:** $(date)
**Environment:** $(git rev-parse --abbrev-ref HEAD) @ $(git rev-parse --short HEAD)

## Load Testing
- Report: reports/load/load-test-report.html
- Status: [Check manually]

## Security Testing
- ZAP: reports/security/zap_report_*.html
- Bandit: reports/security/bandit_*.json
- Safety: reports/security/safety_*.json
- Status: [Check manually]

## Regression Testing
- Reports: reports/regression/*.html
- Status: [Check manually]

## Next Steps
1. Review all HTML reports
2. Fix any CRITICAL/HIGH issues
3. Re-run failed tests
4. Update SESSION-STATE.md with results
EOF

echo "✅ All tests completed!"
echo "Reports saved to: reports/"
```

---

## 📝 Reportar Resultados

Después de ejecutar los tests, actualizar:

### SESSION-STATE.md
```markdown
## 🧪 Testing Results - 2026-03-10

### Load Testing
- **Status:** ✅ PASSED
- **Users:** 100 concurrent
- **Response Time:** 145ms (avg), 198ms (p95)
- **Failures:** 0.2%
- **Report:** reports/load/load-test-report.html

### Security Testing
- **Status:** ✅ PASSED
- **ZAP:** 0 CRITICAL, 0 HIGH
- **Bandit:** 0 CRITICAL, 0 HIGH
- **Safety:** 0 vulnerabilities
- **Reports:** reports/security/

### Regression Testing
- **Status:** ✅ PASSED
- **Pass Rate:** 100% (62/62 tests)
- **Coverage:** 87%
- **Reports:** reports/regression/

### Conclusion
✅ **BETA LAUNCH READY**
```

---

## 🆘 Troubleshooting

### Load Testing Falla
```bash
# Verificar que backend está corriendo
curl http://localhost:8000/health

# Verificar logs
tail -f logs/backend.log

# Reducir usuarios si es necesario
locust -f tests/load/locustfile.py --host http://localhost:8000 --users 50 --spawn-rate 5
```

### Security Testing Falla
```bash
# Verificar ZAP instalado
which zap-cli || docker pull owasp/zap2docker-stable

# Verificar Bandit/Safety
pip install bandit safety

# Ejecutar tests manuales
curl -X POST http://localhost:8000/api/v1/test-runs -H "Content-Type: application/json" -d '{"test_id": "1 OR 1=1"}'
```

### Regression Testing Falla
```bash
# Verificar dependencias
pip install pytest pytest-html pytest-xdist

# Ejecutar tests individualmente
pytest tests/unit/ -v
pytest tests/integration/ -v

# Ver con más detalle
pytest tests/ -v --tb=long
```

---

**Preparado por Alfred - CEO Agent**
**Fecha:** 2026-03-10 05:45 UTC
**Estado:** ✅ Scripts listos, esperando ejecución de Joker
