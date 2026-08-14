# Allure Reporting Setup Guide

Guía completa para configurar y utilizar el sistema de reporting con Allure en QA-FRAMEWORK.

## Tabla de Contenidos

- [Visión General](#visión-general)
- [Instalación](#instalación)
- [Configuración](#configuración)
- [Uso Básico](#uso-básico)
- [Formatos de Reporte](#formatos-de-reporte)
- [Captura Automática de Screenshots](#captura-automática-de-screenshots)
- [Integración con Pytest](#integración-con-pytest)
- [Mejores Prácticas](#mejores-prácticas)
- [Solución de Problemas](#solución-de-problemas)

## Visión General

El sistema de reporting con Allure proporciona:

- **Múltiples formatos de reporte**: HTML, JSON, XML (JUnit)
- **Captura automática de screenshots** en fallos
- **Documentación paso a paso** de tests
- **Clasificación y organización** mediante features, stories, tags
- **Niveles de severidad** para priorización
- **Adjuntos** de texto, JSON e imágenes
- **Enlaces** a issues, casos de prueba y documentación
- **Integración nativa** con pytest

## Instalación

### 1. Dependencias Python

Las dependencias ya están incluidas en `requirements.txt`:

```txt
allure-pytest==2.13.2
allure-python-commons==2.13.2
```

Instalar con:

```bash
pip install -r requirements.txt
```

### 2. Allure Command Line Tool (Opcional pero recomendado)

Para generar reportes HTML completos, instalar Allure CLI:

**Linux:**
```bash
# Descargar desde GitHub releases
curl -o allure-2.24.0.tgz -OL https://github.com/allure-framework/allure2/releases/download/2.24.0/allure-2.24.0.tgz
tar -zxvf allure-2.24.0.tgz
sudo mv allure-2.24.0 /opt/allure
sudo ln -s /opt/allure/bin/allure /usr/bin/allure
```

**macOS:**
```bash
brew install allure
```

**Windows:**
```powershell
# Usando Scoop
scoop install allure

# O descargar manualmente desde GitHub releases
```

Verificar instalación:
```bash
allure --version
```

## Configuración

### Configuración Básica

El archivo `config/qa.yaml` ya incluye configuración para Allure:

```yaml
reporting:
  allure:
    enabled: true
    results_dir: "allure-results"
    report_dir: "reports/allure-report"
    screenshots_on_failure: true
    clean_results: true
```

### Opciones de Configuración

| Opción | Tipo | Descripción | Default |
|--------|------|-------------|---------|
| `enabled` | bool | Habilitar/deshabilitar Allure | `true` |
| `results_dir` | str | Directorio para archivos de resultados | `"allure-results"` |
| `report_dir` | str | Directorio para reportes generados | `"reports/allure-report"` |
| `screenshots_on_failure` | bool | Capturar screenshots automáticamente | `true` |
| `clean_results` | bool | Limpiar resultados anteriores | `true` |

### Configuración por Ambiente

Crear configuraciones específicas por ambiente:

**config/qa.development.yaml:**
```yaml
reporting:
  allure:
    enabled: true
    clean_results: true
    screenshots_on_failure: true
```

**config/qa.production.yaml:**
```yaml
reporting:
  allure:
    enabled: true
    clean_results: false  # Mantener historial
    screenshots_on_failure: true
```

## Uso Básico

### Inicialización del Reporter

```python
from src.adapters.reporting.allure_reporter import AllureReporter

# Crear instancia del reporter
reporter = AllureReporter(
    results_dir="allure-results",
    screenshots_on_failure=True,
    clean_results=True
)
```

### Reporte de Tests Básico

```python
# Iniciar test
reporter.start_test(
    test_name="test_user_login",
    description="Verify user can login with valid credentials"
)

# Agregar pasos
reporter.add_step("Navigate to login page")
reporter.add_step("Enter username")
reporter.add_step("Enter password")
reporter.add_step("Click login button")

# Finalizar test
reporter.end_test(status="passed", message="Login successful")
```

### Uso con Context Manager (Recomendado)

```python
async with AllureReporter(
    results_dir="allure-results",
    screenshots_on_failure=True
) as reporter:
    reporter.start_test(test_name="test_example")
    reporter.add_step("Step 1")
    reporter.end_test(status="passed")
    # Cleanup automático al salir del contexto
```

## Formatos de Reporte

### Generar Reporte HTML

```python
# Generar reporte HTML
report_path = reporter.generate_report(
    output_dir="reports",
    report_format="html"
)
print(f"Report generated: {report_path}")
```

**Usando Allure CLI:**
```bash
# Generar y abrir reporte
allure serve allure-results

# Generar reporte estático
allure generate allure-results -o reports/allure-report --clean

# Abrir reporte generado
allure open reports/allure-report
```

### Generar Reporte JSON

```python
report_path = reporter.generate_report(
    output_dir="reports",
    report_format="json"
)
```

Estructura del reporte JSON:
```json
{
  "report_name": "QA Framework Test Report",
  "results": [...],
  "total_tests": 10
}
```

### Generar Reporte XML (JUnit)

```python
report_path = reporter.generate_report(
    output_dir="reports",
    report_format="xml"
)
```

Formato compatible con Jenkins, GitLab CI, y otras herramientas CI/CD.

## Captura Automática de Screenshots

### Configuración

```python
reporter = AllureReporter(
    results_dir="allure-results",
    screenshots_on_failure=True  # Habilitar captura automática
)
```

### Uso Manual

```python
try:
    # Test logic
    await page.click("#submit-button")
except Exception as e:
    # Capturar screenshot en fallo
    screenshot_path = await page.screenshot(path="failure.png")
    reporter.capture_failure_screenshot(
        lambda: screenshot_path
    )
    reporter.end_test(status="failed", message=str(e))
    raise
```

### Screenshots Condicionales

```python
# Capturar solo en ambiente de desarrollo
screenshots_enabled = config.reporting.allure.screenshots_on_failure

reporter = AllureReporter(
    results_dir="allure-results",
    screenshots_on_failure=screenshots_enabled
)
```

## Integración con Pytest

### Decoradores de Allure

```python
import allure
import pytest

@allure.feature("Authentication")
@allure.story("User Login")
@allure.severity(allure.severity_level.CRITICAL)
@allure.tag("regression", "smoke")
async def test_user_login():
    """Test user login functionality."""
    # Test implementation
    pass
```

### Ejecución con Pytest

```bash
# Ejecutar tests con Allure
pytest tests/ -v --alluredir=allure-results

# Ejecutar con categorías específicas
pytest tests/ -v --alluredir=allure-results -m "critical"

# Ejecutar tests en paralelo con Allure
pytest tests/ -n auto --alluredir=allure-results
```

### Fixtures de Pytest

```python
import pytest
from src.adapters.reporting.allure_reporter import AllureReporter

@pytest.fixture
def allure_reporter():
    """Fixture para Allure reporter."""
    reporter = AllureReporter(
        results_dir="allure-results",
        clean_results=False
    )
    yield reporter
    reporter.cleanup()

async def test_with_reporter(allure_reporter):
    """Test usando fixture de Allure."""
    allure_reporter.start_test("test_example")
    # ... test logic ...
    allure_reporter.end_test("passed")
```

## Mejores Prácticas

### 1. Organización de Tests

```python
@allure.epic("User Management")
@allure.feature("Authentication")
@allure.story("Login")
@allure.severity(allure.severity_level.CRITICAL)
class TestAuthentication:
    """Test suite for authentication functionality."""

    @allure.title("Login with valid credentials")
    @allure.description("Verify user can login with valid username and password")
    async def test_valid_login(self):
        """Test login with valid credentials."""
        pass
```

### 2. Documentación de Pasos

```python
reporter.start_test("test_checkout_process")

with reporter.step("Add item to cart"):
    # Logic here
    pass

with reporter.step("Proceed to checkout"):
    # Logic here
    pass

with reporter.step("Complete payment"):
    # Logic here
    pass
```

### 3. Uso de Attachments

```python
# Adjuntar datos JSON
response_data = {"id": 123, "status": "active"}
reporter.attach_json(response_data, name="api_response")

# Adjuntar texto
reporter.attach_text("Execution log entry", name="log")

# Adjuntar screenshot
reporter.attach_screenshot("/path/to/screenshot.png", name="checkout_page")
```

### 4. Manejo de Errores

```python
try:
    reporter.start_test("test_critical_feature")
    reporter.add_severity("blocker")
    # Test logic
    reporter.end_test("passed")
except Exception as e:
    reporter.attach_text(str(e), name="error_details")
    reporter.end_test("failed", message=str(e))
    raise
finally:
    reporter.cleanup()
```

### 5. Links y Referencias

```python
@allure.issue("https://jira.company.com/PROJ-123", "PROJ-123")
@allure.testcase("https://testcase.manager/TC-456", "TC-456")
@allure.link("https://docs.company.com/feature", name="Documentation")
async def test_with_references():
    """Test with external references."""
    pass
```

## Solución de Problemas

### Problema: Allure CLI no encontrado

**Error:**
```
FileNotFoundError: [Errno 2] No such file or directory: 'allure'
```

**Solución:**
1. Instalar Allure CLI según las instrucciones de instalación
2. Verificar que `allure` está en el PATH:
   ```bash
   which allure  # Linux/macOS
   where allure  # Windows
   ```

### Problema: Reporte HTML vacío

**Causa:** No se encontraron archivos de resultados

**Solución:**
1. Verificar que los tests se ejecutaron correctamente:
   ```bash
   ls allure-results/
   ```
2. Asegurar que se usa el directorio correcto:
   ```python
   reporter = AllureReporter(results_dir="allure-results")
   ```

### Problema: Screenshots no aparecen

**Causa:** Ruta de screenshot incorrecta o archivo no existe

**Solución:**
```python
# Verificar que el archivo existe antes de adjuntar
screenshot_path = Path("screenshot.png")
if screenshot_path.exists():
    reporter.attach_screenshot(str(screenshot_path))
```

### Problema: Configuración no cargada

**Solución:**
```python
from src.infrastructure.config.config_manager import ConfigManager

config_manager = ConfigManager(config_path="config/qa.yaml")
config = config_manager.get_config()

reporter = AllureReporter(
    results_dir=config.reporting.allure.results_dir,
    screenshots_on_failure=config.reporting.allure.screenshots_on_failure
)
```

## Ejemplos Completos

Ver archivo de ejemplos:
- `examples/allure_reporting_example.py` - Ejemplos completos de uso

Ejecutar ejemplos:
```bash
# Ejecutar todos los ejemplos
pytest examples/allure_reporting_example.py -v --alluredir=allure-results

# Generar reporte
allure serve allure-results
```

## Referencias

- [Allure Framework](https://docs.qameta.io/allure/)
- [Allure Python](https://github.com/allure-framework/allure-python)
- [Pytest Allure](https://pypi.org/project/allure-pytest/)
- [QA-FRAMEWORK README](https://github.com/SabaTech-dev/QA-FRAMEWORK/blob/main/README.md)
