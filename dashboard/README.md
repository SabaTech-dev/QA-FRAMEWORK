# QA-Framework Dashboard

[![CI](https://github.com/anomalyco/QA-FRAMEWORK-DASHBOARD/actions/workflows/ci.yml/badge.svg)](https://github.com/anomalyco/QA-FRAMEWORK-DASHBOARD/actions/workflows/ci.yml)
[![CD](https://github.com/anomalyco/QA-FRAMEWORK-DASHBOARD/actions/workflows/cd.yml/badge.svg)](https://github.com/anomalyco/QA-FRAMEWORK-DASHBOARD/actions/workflows/cd.yml)
[![Code Quality](https://github.com/anomalyco/QA-FRAMEWORK-DASHBOARD/actions/workflows/code-quality.yml/badge.svg)](https://github.com/anomalyco/QA-FRAMEWORK-DASHBOARD/actions/workflows/code-quality.yml)
[![codecov](https://codecov.io/gh/anomalyco/QA-FRAMEWORK-DASHBOARD/branch/main/graph/badge.svg)](https://codecov.io/gh/anomalyco/QA-FRAMEWORK-DASHBOARD)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Node.js 18+](https://img.shields.io/badge/node.js-18+-green.svg)](https://nodejs.org/)
[![License](https://img.shields.io/badge/license-MIT-yellow.svg)](LICENSE)

Dashboard unificada para el framework de testing QA-FRAMEWORK, permitiendo gestión visual de pruebas, ejecución interactiva y visualización de resultados.

## Características

- Gestión completa de pruebas (CRUD)
- Ejecución visual e interactiva
- Dashboard de resultados en tiempo real
- Integración con todos los adaptadores de QA-FRAMEWORK
- Multi-framework testing
- Reporting avanzado
- **Nuevo**: Integration Hub con soporte para Jira, Zephyr Squad, TestLink, Azure DevOps y HP ALM

## Tecnología

- Backend: FastAPI
- Frontend: React con TypeScript
- Base de datos: PostgreSQL
- Cache: Redis
- Autenticación: JWT
- UI: Material-UI

## Dependencias del backend (lockfile determinista)

`backend/requirements.txt` declara los rangos; `backend/requirements.lock` es el lockfile exacto
(181 pines con hashes SHA-256) que garantiza resolución reproducible y cierra la ventana de
supply-chain drift (fuente: gate security 2834cce9).

Regenerar el lockfile tras editar `requirements.txt`:

```bash
cd dashboard/backend
uv pip compile requirements.txt -o requirements.lock --python-version 3.11 --generate-hashes
```

El floor `starlette>=1.3.1` incluye el parche de CVE-2026-54283 (GHSA-82w8-qh3p-5jfq);
verificado compatible con `fastapi==0.141.1`, que declara `starlette>=0.46.0` sin techo superior.

Auditoría de vulnerabilidades sobre el lockfile (nice-to-have, sin integración en CI):

```bash
pipx run pip-audit -r dashboard/backend/requirements.lock --require-hashes
```


## Integration Hub

El QA-FRAMEWORK Dashboard incluye un Integration Hub modular que permite conectar con múltiples herramientas de gestión de pruebas:

### Proveedores Soportados

1. **Jira (Atlassian)** - Gratis hasta 10 usuarios
   - Creación automática de bugs desde tests fallidos
   - Sincronización de resultados como issues
   - Enlace con historias/épicas

2. **Zephyr Squad** - Gratis hasta 10 usuarios, tests ilimitados
   - Gestión completa de test cases
   - Test cycles y ejecuciones
   - Importación de resultados JUnit

3. **Azure DevOps** - Gratis hasta 5 usuarios
   - Work items (stories, tasks, bugs)
   - Test plans y suites
   - Integración CI/CD

4. **TestLink** - Open source y gratuito
   - Gestión de test cases
   - Seguimiento de ejecución
   - Trazabilidad de requisitos

5. **HP ALM / OpenText ALM** - Herramienta enterprise (pago)
   - Gestión completa de pruebas
   - Test lab y ciclos
   - Defectos y trazabilidad

### Arquitectura Modular

El Integration Hub utiliza el patrón Adapter para garantizar interfaces consistentes:

```
┌─────────────────────────────────────────────────────────────┐
│                  QA-FRAMEWORK DASHBOARD                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │   JIRA API   │  │ ZEPHYR API   │  │   ALM API    │       │
│  │   Client     │  │   Client     │  │   Client     │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │ TESTLINK API │  │ AZURE DEVOPS │  │   CUSTOM     │       │
│  │   Client     │  │   Client     │  │   Client     │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
│                                                             │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
               ┌─────────────────────────┐
               │   INTEGRATION MANAGER   │
               │  (Orquesta todo)        │
               └─────────────────────────┘
```

### API Endpoints

Los endpoints están disponibles en `/api/v1/integrations/`:

- `GET /providers` - Lista proveedores disponibles
- `POST /configure` - Configura un proveedor
- `POST /sync` - Sincroniza resultados de tests
- `GET /health/{provider}` - Verifica estado
- `POST /{provider}/test-cases` - Crea test cases
- `POST /{provider}/bugs` - Crea bugs

## Arquitectura

### Backend

- `main.py` - Punto de entrada de la aplicación
- `config.py` - Configuración de la aplicación
- `database.py` - Configuración de base de datos
- `models/` - Modelos ORM
- `schemas/` - Esquemas Pydantic
- `services/` - Lógica de negocio
- `api/v1/` - Rutas API

### Frontend

- `src/main.tsx` - Punto de entrada
- `src/App.tsx` - Router principal
- `src/components/` - Componentes reutilizables
- `src/pages/` - Páginas de la aplicación
- `src/stores/` - Stores de Zustand
- `src/api/` - Cliente API

## Instalación

### Requisitos

- Docker y Docker Compose
- Node.js 18+
- Python 3.11+

### Desarrollo

1. Clonar el repositorio
2. Copiar `.env.example` a `.env` y ajustar las variables
3. Iniciar los servicios:

```bash
docker-compose up
```

Los servicios estarán disponibles en:
- Backend: http://localhost:8000
- Frontend: http://localhost:3000
- PostgreSQL: puerto 5432
- Redis: puerto 6379

## API Endpoints

### Autenticación
- `POST /api/v1/auth/login` - Iniciar sesión
- `GET /api/v1/auth/me` - Obtener información del usuario

### Test Suites
- `POST /api/v1/suites` - Crear suite
- `GET /api/v1/suites` - Listar suites
- `GET /api/v1/suites/{id}` - Obtener suite
- `PUT /api/v1/suites/{id}` - Actualizar suite
- `DELETE /api/v1/suites/{id}` - Eliminar suite

### Test Cases
- `POST /api/v1/cases` - Crear caso
- `GET /api/v1/cases` - Listar casos
- `GET /api/v1/cases/{id}` - Obtener caso
- `PUT /api/v1/cases/{id}` - Actualizar caso
- `DELETE /api/v1/cases/{id}` - Eliminar caso

### Ejecuciones
- `POST /api/v1/executions` - Crear ejecución
- `GET /api/v1/executions` - Listar ejecuciones
- `GET /api/v1/executions/{id}` - Obtener ejecución
- `POST /api/v1/executions/{id}/start` - Iniciar ejecución
- `POST /api/v1/executions/{id}/stop` - Detener ejecución

### Dashboard
- `GET /api/v1/dashboard/stats` - Estadísticas
- `GET /api/v1/dashboard/trends` - Tendencias
- `GET /api/v1/dashboard/recent-executions` - Ejecuciones recientes

## Frontend Pages

- `/` - Dashboard principal
- `/login` - Página de login
- `/suites` - Gestión de suites
- `/suites/:suiteId/cases` - Gestión de casos de prueba
- `/executions` - Historial de ejecuciones

## Variables de Entorno

- `DATABASE_URL` - URL de conexión a la base de datos
- `SECRET_KEY` - Clave secreta para JWT
- `REDIS_HOST` - Host de Redis
- `REDIS_PORT` - Puerto de Redis
- `VITE_API_URL` - URL del backend (frontend)

## Scripts

- `npm run dev` - Iniciar en modo desarrollo
- `npm run build` - Construir para producción
- `npm run lint` - Lintear el código
- `npm run test` - Ejecutar tests

## Contribución

1. Hacer fork del repositorio
2. Crear una rama (`git checkout -b feature/nueva-caracteristica`)
3. Hacer commit (`git commit -am 'Añadir nueva característica'`)
4. Hacer push (`git push origin feature/nueva-caracteristica`)
5. Crear un Pull Request# Trigger deploy manual
