# QA-FRAMEWORK - Unified QA Automation Platform

[![CI](https://github.com/llllJokerllll/QA-FRAMEWORK/actions/workflows/ci.yml/badge.svg)](https://github.com/llllJokerllll/QA-FRAMEWORK/actions/workflows/ci.yml)
[![CD](https://github.com/llllJokerllll/QA-FRAMEWORK/actions/workflows/cd.yml/badge.svg)](https://github.com/llllJokerllll/QA-FRAMEWORK/actions/workflows/cd.yml)
[![codecov](https://codecov.io/gh/llllJokerllll/QA-FRAMEWORK/branch/main/graph/badge.svg)](https://codecov.io/gh/llllJokerllll/QA-FRAMEWORK)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Node.js 18+](https://img.shields.io/badge/node.js-18+-green.svg)](https://nodejs.org/)
[![License](https://img.shields.io/badge/license-MIT-yellow.svg)](LICENSE)

Plataforma unificada de automatización de QA con arquitectura limpia, dashboard web moderno, y soporte multi-framework.

## 🚀 Características Principales

### Framework Core
- **Arquitectura Limpia** con principios SOLID
- **Multi-framework testing** (Selenium, Playwright, Appium, Cypress)
- **Adaptadores modulares** para diferentes tecnologías
- **Inyección de dependencias** y configuración flexible
- **Reporting avanzado** con múltiples formatos

### Dashboard Web
- **Interfaz moderna** con React + TypeScript + Material-UI
- **Backend robusto** con FastAPI + PostgreSQL
- **Gestión completa de pruebas** (CRUD)
- **Ejecución visual e interactiva**
- **Dashboard de resultados en tiempo real**
- **Integration Hub** (Jira, Zephyr, Azure DevOps, TestLink, HP ALM)

### Testing & Quality
- **82.59% code coverage** en backend
- **69 tests E2E** con Playwright
- **Tests de performance** con Locust
- **CI/CD automatizado** con GitHub Actions
- **Security scanning** integrado

## 📁 Estructura del Proyecto

```
QA-FRAMEWORK/
├── src/                    # Framework Core
│   ├── core/              # Lógica de negocio
│   ├── adapters/          # Adaptadores externos
│   │   ├── web/          # Selenium, Playwright
│   │   ├── mobile/       # Appium
│   │   ├── api/          # REST API testing
│   │   └── api_contract/ # Contract testing
│   └── entities/         # Modelos de dominio
├── dashboard/             # Dashboard Web (UI)
│   ├── backend/          # FastAPI backend
│   ├── frontend/         # React frontend
│   ├── tests/            # Tests del dashboard
│   ├── monitoring/       # Prometheus + Grafana
│   └── docker-compose.yml
├── config/               # Configuración del framework
├── docs/                 # Documentación completa
├── examples/             # Ejemplos de uso
├── tests/                # Tests del framework
└── .github/workflows/    # CI/CD pipelines
```

## 🛠️ Instalación

### Requisitos
- Python 3.11+
- Node.js 18+
- Docker y Docker Compose
- PostgreSQL 15+
- Redis 7+

### Configuración de Seguridad (IMPORTANTE)

**Antes de desplegar, genera keys seguras:**

```bash
# Generar JWT secret key
openssl rand -hex 32

# Crear archivo .env en dashboard/
cp dashboard/.env.example dashboard/.env

# Editar .env y añadir las keys generadas
nano dashboard/.env
```

**Variables críticas:**
- `JWT_SECRET_KEY` - Key para firmar tokens JWT
- `SECRET_KEY` - Key general de la aplicación
- `DATABASE_URL` - Conexión a PostgreSQL

### Desarrollo Local

```bash
# Clonar el repositorio
git clone https://github.com/llllJokerllll/QA-FRAMEWORK.git
cd QA-FRAMEWORK

# Opción 1: Usar Docker Compose (recomendado)
cd dashboard
docker-compose up -d

# Opción 2: Instalación manual
## Framework Core
pip install -e .

## Dashboard Backend
cd dashboard/backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload

## Dashboard Frontend
cd dashboard/frontend
npm install
npm run dev
```

### URLs de Acceso
- **Dashboard UI**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/api/v1/docs
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3001

## 🔧 Uso del Framework

### Ejemplo Básico

```python
from src.core.entities import TestCase, TestStep
from src.core.use_cases import ExecuteTest
from src.adapters.web import SeleniumAdapter

# Crear caso de prueba
test_case = TestCase(
    name="Login Test",
    steps=[
        TestStep(action="goto", target="/login"),
        TestStep(action="type", target="#username", value="user@example.com"),
        TestStep(action="type", target="#password", value="password123"),
        TestStep(action="click", target="#submit-button"),
        TestStep(action="assert", target=".welcome-message", value="Welcome!")
    ]
)

# Ejecutar con Selenium
adapter = SeleniumAdapter(browser="chrome")
executor = ExecuteTest(adapter)
result = executor.execute(test_case)
```

### Ejemplo con Dashboard

```bash
# Crear suite via API
curl -X POST http://localhost:8000/api/v1/suites \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Login Tests",
    "description": "Suite de pruebas de autenticación"
  }'

# Ejecutar via Dashboard UI
# 1. Acceder a http://localhost:3000
# 2. Crear Test Suite
# 3. Añadir Test Cases
# 4. Ejecutar y ver resultados en tiempo real
```

## 📊 Integration Hub

Conecta con herramientas populares de gestión de pruebas:

| Herramienta | Tipo | Usuarios Gratis | Estado |
|-------------|------|-----------------|--------|
| **Jira** | Issue Tracking | 10 | ✅ Soportado |
| **Zephyr Squad** | Test Management | 10 | ✅ Soportado |
| **Azure DevOps** | ALM Platform | 5 | ✅ Soportado |
| **TestLink** | Open Source | Ilimitado | ✅ Soportado |
| **HP ALM** | Enterprise | Pago | ✅ Soportado |

### Configurar Integración

```python
# Jira
POST /api/v1/integrations/configure
{
  "provider": "jira",
  "config": {
    "url": "https://your-domain.atlassian.net",
    "api_token": "your-token",
    "email": "user@example.com"
  }
}

# Sincronizar resultados
POST /api/v1/integrations/sync
{
  "provider": "jira",
  "execution_id": "123"
}
```

## 🧪 Testing

### Tests del Framework
```bash
# Tests unitarios
pytest tests/ -v --cov=src

# Tests específicos
pytest tests/unit/test_web_adapter.py -v
```

### Tests del Dashboard
```bash
cd dashboard

# Tests unitarios backend
cd backend
pytest tests/unit/ -v --cov=backend

# Tests E2E (Playwright)
cd ../tests/e2e
pytest test_login.py -v

# Tests de performance
cd ../performance
locust -f locustfile.py
```

### 🚀 Quick Start: Backend Local

Start the dashboard backend locally **without Docker**:

```bash
cd dashboard/backend

# 1. Create virtual environment (first time only)
python3 -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or .venv\Scripts\activate  # Windows
pip install -r requirements.txt

# 2. Start the backend (uses SQLite automatically when DATABASE_URL is unset)
ENVIRONMENT=development .venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8000

# Backend runs at: http://localhost:8000
# API docs at: http://localhost:8000/api/v1/docs
```

**Environment variables (all optional in development):**
- `DATABASE_URL` — PostgreSQL URL. If unset, falls back to SQLite (`./qafw.db`)
- `REDIS_URL` — Redis URL. If unset, defaults to `redis://localhost:6379/0`
- `JWT_SECRET_KEY` — JWT signing key. If unset, a dev fallback is used
- `ENVIRONMENT` — `development` or `production` (default: `development`)

### 🧪 Run Dashboard Backend Tests

```bash
cd dashboard/backend
source .venv/bin/activate

# Run all unit/integration/backend tests
ENVIRONMENT=development REDIS_URL="redis://localhost:6379/0" pytest tests/unit/ tests/core/ tests/services/ tests/middleware/ tests/integration/ tests/integration_clients/ tests/infrastructure/ -v

# Run only unit tests (fast, no external deps required)
ENVIRONMENT=development DATABASE_URL="" pytest tests/unit/ -v
```

**Notes:**
- Integration tests need PostgreSQL and Redis running.
- Stripe tests need valid `STRIPE_API_KEY`.
- Unit tests (164 tests) run without any external service.
- Railway service has expired — `REDIS_URL` pointing to Railway will fail;
  set it to a local Redis instance instead.

## 📈 Monitoreo y Observabilidad

### Métricas Disponibles
- **API Performance**: Latencia, throughput, errores
- **Database Metrics**: Conexiones, queries lentas
- **Cache Performance**: Hit rate, memoria
- **Test Metrics**: Tiempo de ejecución, tasa de éxito

### Dashboards Grafana
- API Performance Dashboard
- Database Metrics Dashboard
- Cache Performance Dashboard
- Alerts Dashboard

### Alertas
```yaml
# Ejemplo de alerta
- alert: HighErrorRate
  expr: rate(http_requests_total{status="500"}[5m]) > 0.1
  for: 5m
  annotations:
    summary: "Alta tasa de errores en API"
```

## 🚢 CI/CD Pipeline

### Workflows Automatizados
- **CI**: Tests, linting, security scanning en cada PR
- **CD**: Deploy automático a staging/production
- **Code Quality**: Análisis de calidad con Codecov
- **Nightly**: Tests de regresión nocturnos

### Badges
[![CI](https://github.com/llllJokerllll/QA-FRAMEWORK/actions/workflows/ci.yml/badge.svg)](https://github.com/llllJokerllll/QA-FRAMEWORK/actions/workflows/ci.yml)
[![CD](https://github.com/llllJokerllll/QA-FRAMEWORK/actions/workflows/cd.yml/badge.svg)](https://github.com/llllJokerllll/QA-FRAMEWORK/actions/workflows/cd.yml)

## 📚 Documentación

- **Framework**: `docs/ADVANCED_TEST_ARCHITECTURE.md`
- **Dashboard**: `dashboard/README.md`
- **Deployment**: `dashboard/DEPLOYMENT.md`
- **API**: `docs/api-guide.md`
- **Architecture**: `docs/architecture.md`
- **CI/CD**: `docs/CICD_PIPELINE.md`

## 🤝 Contribución

Ver [CONTRIBUTING.md](CONTRIBUTING.md) para:
- Código de conducta
- Flujo de trabajo Git
- Estándares de código
- Proceso de PR

## 📝 Licencia

MIT License - ver [LICENSE](LICENSE) para detalles.

## 🎯 Roadmap

### v1.0 (Actual)
- ✅ Framework Core completo
- ✅ Dashboard Web funcional
- ✅ Integration Hub
- ✅ CI/CD automatizado
- ✅ Monitoreo con Prometheus + Grafana

### v1.1 (Próximo)
- ⏳ Soporte para más frameworks de testing
- ⏳ AI-powered test generation
- ⏳ Mobile testing mejorado
- ⏳ Performance optimizations

### v2.0 (Futuro)
- ⏳ Cloud-native deployment
- ⏳ Multi-tenant support
- ⏳ Advanced analytics
- ⏳ ML-based test selection

## 👥 Autores

- **Joker** - *Initial work* - [llllJokerllll](https://github.com/llllJokerllll)
- **Alfred** - *Senior Project Manager & Lead Developer*

## 🔄 Historial de Fusiones

- **2026-02-16**: Fusionado `QA-FRAMEWORK-DASHBOARD` dentro de `QA-FRAMEWORK` como subdirectorio `dashboard/`
  - Dashboard web completo integrado
  - Docker Compose unificado
  - Documentación consolidada
  - Repositorio unificado: https://github.com/llllJokerllll/QA-FRAMEWORK

---

**Estado del Proyecto:** ✅ 100% Completado y en producción
**Última actualización:** 2026-02-16
