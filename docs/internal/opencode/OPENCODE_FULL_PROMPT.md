# OpenCode Prompt - QA-FRAMEWORK Development

## Contexto

Voy a desarrollar un framework moderno de automatización de QA en Python 3.12 llamado **QA-FRAMEWORK**.

## Arquitectura

**Clean Architecture** con **Principios SOLID**:

```
qa-framework/
├── src/
│   ├── core/
│   │   ├── interfaces/          # Interfaces/Contratos (SOLID DIP)
│   │   ├── entities/            # Reglas de negocio
│   │   ├── use_cases/           # Lógica de aplicación (SOLID SRP)
│   │   └── repositories/        # Implementaciones de interfaces
│   ├── adapters/
│   │   ├── http/              # HTTPX, Requests para API testing
│   │   ├── ui/                # Playwright, Selenium para UI testing
│   │   ├── reporting/         # Allure, HTML, JSON
│   │   ├── performance/       # Locust, benchmarks
│   │   └── security/          # Bandit, Safety
│   └── infrastructure/
│       ├── config/             # Configuration (YAML, JSON, ENV)
│       ├── logger/             # Logging estructurado
│       └── utils/              # Generators, utilities
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── e2e/
│   └── fixtures/
├── docs/
├── examples/
├── requirements.txt
├── setup.py
├── pyproject.toml
├── Dockerfile
├── docker-compose.yml
└── .github/workflows/
```

## Principios SOLID Estrictos

### S - Single Responsibility
- Cada clase tiene **una única responsabilidad**
- Cada método hace **una sola cosa**

### O - Open/Closed
- Abierto para **extensión**
- Cerrado para **modificación**

### L - Liskov Substitution
- Subclases pueden **substituir** superclases

### I - Interface Segregation
- Interfaces **pequeñas y específicas**

### D - Dependency Inversion
- Depender de **abstracciones**, no implementaciones

## Tecnologías

- **Python 3.12+**
- **Pytest** (test framework)
- **HTTPX** (async HTTP client)
- **Playwright** (browser automation)
- **Allure** (reporting)
- **Type hints** (100%)
- **Clean Architecture**
- **SOLID principles**

## TASKS A COMPLETAR

### Phase 1: Foundation (Tasks 1.1 - 1.5)

**Task 1.1: Project Setup (15min)**

Crea:
1. Estructura completa de directorios
2. `requirements.txt` con dependencias:
   ```
   pytest==7.4.0
   pytest-asyncio==0.21.0
   pytest-xdist==3.5.0
   pytest-cov==4.1.0
   pytest-allure==2.13.0
   httpx==0.25.0
   requests==2.31.0
   playwright==1.40.0
   faker==20.1.0
   pydantic==2.5.0
   pyyaml==6.0.1
   python-dotenv==1.0.0
   black==23.12.0
   ruff==0.1.0
   mypy==1.7.0
   pre-commit==3.6.0
   ```

3. `setup.py` con metadata del paquete
4. `pyproject.toml` con configuración de herramientas
5. `.gitignore` para Python

**Task 1.2: Clean Architecture Structure (30min)**

Crea interfaces y abstracciones:
- `src/core/interfaces/test_runner.py` - ITestRunner interface
- `src/core/interfaces/test_case.py` - ITestCase interface
- `src/core/interfaces/assertion.py` - IAssertion interface
- `src/core/entities/test_result.py` - TestResult entity
- `src/core/base/test_base.py` - BaseTest class

Todas las interfaces deben usar ABC (Abstract Base Classes).

**Task 1.3: Configuration System (30min)**

Crea sistema de configuración flexible:
- `src/infrastructure/config/config_manager.py` - ConfigManager class
- `src/infrastructure/config/validators.py` - Validación de config
- `config/qa.yaml` - Configuración por defecto
- `config/qa.development.yaml` - Configuración dev
- `config/qa.staging.yaml` - Configuración staging

Config YAML debe incluir:
```yaml
test:
  environment: staging
  parallel_workers: 4
  timeout: 30
  retry_failed: 2

api:
  base_url: https://api.example.com
  auth:
    type: bearer
    token: ${API_TOKEN}

ui:
  browser: chromium
  headless: true
  viewport: 1920x1080

reporting:
  allure: true
  html: true
  screenshots: on_failure
```

**Task 1.4: Logging Infrastructure (30min)**

Crea sistema de logging estructurado:
- `src/infrastructure/logger/logger.py` - Logger class
- `src/infrastructure/logger/formatters.py` - JSON y console formatters

Deben soportar:
- Múltiples niveles (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- File logging
- Console logging
- Structured logging (JSON)

**Task 1.5: Data Generators (45min)**

Crea generadores de datos de prueba:
- `src/infrastructure/utils/generators.py` - Generators usando Faker
- `src/infrastructure/utils/factory.py` - Factory pattern

Deben incluir:
- User generator
- Product generator
- Order generator
- Customizable generators

### Phase 2: Core Functionality (Tasks 2.1 - 2.5)

**Task 2.1: Test Runner (45min)**

Implementa:
- `src/core/use_cases/test_runner.py` - TestRunner class
- `src/core/use_cases/test_execution.py` - TestExecution use case

Deben incluir:
- Pytest integration
- Lifecycle hooks (setup, teardown)
- Timeout handling
- Retry mechanism

**Task 2.2: API Testing Module (60min)**

Implementa:
- `src/adapters/http/http_client.py` - HTTPClient interface
- `src/adapters/http/httpx_client.py` - HTTPXClient (async)
- `src/adapters/http/requests_client.py` - RequestsClient (sync)
- `src/core/use_cases/api_testing.py` - APITesting use case

Deben incluir:
- HTTP methods (GET, POST, PUT, DELETE, PATCH)
- Headers management
- Auth handling
- JSON responses
- Assertion helpers

**Task 2.3: UI Testing Module (60min)**

Implementa:
- `src/adapters/ui/playwright_page.py` - PlaywrightPage base
- `src/adapters/ui/selenium_page.py` - SeleniumPage base
- `src/core/entities/page_object.py` - PageObject entity
- `src/core/use_cases/ui_testing.py` - UITesting use case

Deben incluir:
- Page Object Model
- Element locators
- Actions (click, fill, hover, etc.)
- Assertions (visible, text, etc.)

**Task 2.4: Assertions Library (30min)**

Implementa:
- `src/core/interfaces/assertions.py` - IAssertion interface
- `src/core/use_cases/assertions.py` - Assertions class

Deben incluir:
- API response assertions (status_code, json_path, schema)
- UI element assertions (visible, text, attribute)
- Database assertions
- Performance assertions

**Task 2.5: Fixtures & Helpers (45min)**

Crea fixtures de pytest:
- `tests/fixtures/api.py` - API client fixture
- `tests/fixtures/ui.py` - UI page fixture
- `tests/fixtures/database.py` - Database fixture
- `tests/fixtures/data.py` - Test data fixtures

### Phase 3: Advanced Features (Tasks 3.1 - 3.5)

**Task 3.1: Parallel Execution (30min)**

Configura:
- `conftest.py` con pytest-xdist
- `src/core/use_cases/parallel_execution.py` - ParallelExecution use case

**Task 3.2: Reporting System (30min)**

Implementa:
- `src/adapters/reporting/allure_reporter.py` - AllureReporter
- `src/adapters/reporting/html_reporter.py` - HTMLReporter
- `src/adapters/reporting/json_reporter.py` - JSONReporter

**Task 3.3: Performance Testing (20min)**

Implementa:
- `src/adapters/performance/locust_runner.py` - LocustRunner
- `src/core/use_cases/performance_testing.py` - PerformanceTesting use case

**Task 3.4: Security Testing (20min)**

Implementa:
- `src/adapters/security/bandit_runner.py` - BanditRunner
- `src/core/use_cases/security_testing.py` - SecurityTesting use case

**Task 3.5: CI/CD Integration (30min)**

Crea:
- `.github/workflows/ci.yml` - CI workflow
- `.github/workflows/cd.yml` - CD workflow
- `Dockerfile` - Container definition
- `docker-compose.yml` - Services orchestration

### Phase 4: Quality & Polish (Tasks 4.1 - 4.2)

**Task 4.1: Testing the Framework (20min)**

Escribe tests para el framework:
- Unit tests para core modules
- Integration tests para adapters
- Verifica coverage >90%

**Task 4.2: Documentation (30min)**

Crea documentación completa:
- `README.md` - Main README
- `docs/GETTING_STARTED.md` - Getting started guide
- `docs/API_DOCUMENTATION.md` - API documentation
- `examples/api_testing_example.py` - API testing example
- `examples/ui_testing_example.py` - UI testing example

## INSTRUCCIONES

1. **COMIENZA con Task 1.1** y continua secuencialmente
2. **Aplica SOLID principles estrictamente** en cada fase
3. **Usa type hints** 100%
4. **Añade docstrings** a todas las clases y métodos (Google style)
5. **Crea tests** para cada módulo
6. **Asegúrate de que todo compile y ejecute** correctamente
7. **Mantén clean architecture** en todo momento

## IMPORTANTE

- **NO uses código legacy** o patrones anticuados
- **Aplica SOLID principles** explícitamente
- **Type hints 100%** obligatorio
- **Clean architecture** es obligatorio
- **Tests son obligatorios** para cada módulo

Comienza ahora y completa todas las fases en orden secuencial.
