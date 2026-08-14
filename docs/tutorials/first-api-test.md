# Tutorial 2: Tu primer test de API

> **⏱️ Duración estimada:** 10 minutos
> **Nivel:** desde cero — solo necesitas Python 3.11+ instalado
> **Estado:** ✅ verificado contra un entorno limpio (2026-08-14, Python 3.12 + pip)

**Al terminar este tutorial tendrás:** el framework instalado localmente, un test de API ejecutándose (el de `examples/api_testing_example.py`), y tu primer test propio con assertions sobre el cuerpo de la respuesta.

---

## Lo que vas a aprender

1. Instalar QA-FRAMEWORK y ejecutar un test de ejemplo sin escribir nada
2. Entender la anatomía de un test de API (cliente, petición, assertions)
3. Escribir tu propio test y ejecutarlo

## Por qué tests de API primero

Los tests de API son rápidos, estables y no necesitan navegador: son la mejor primera inversión de una suite de calidad. Usaremos [JSONPlaceholder](https://jsonplaceholder.typicode.com), una API pública de prueba — no necesitas credenciales ni montar nada.

---

## Paso 1: Clona e instala (3 min)

```bash
git clone https://github.com/SabaTech-dev/QA-FRAMEWORK.git
cd QA-FRAMEWORK
```

El proyecto soporta [uv](https://docs.astral.sh/uv/) (hay `pyproject.toml` en el repo):

```bash
uv sync
```

Si no tienes uv, equivalente con pip (ruta verificada para este tutorial):

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

**✅ Checkpoint:**

```bash
python -c "import httpx; import pytest; print('ok')"
# Debe imprimir: ok
```

## Paso 2: Autoriza el dominio de pruebas (1 min)

El cliente HTTP del framework lleva **protección SSRF por allowlist** (OWASP): solo acepta peticiones a dominios de confianza. `jsonplaceholder.typicode.com` no está en la lista por defecto, así que antes de ejecutar debes autorizarlo:

```bash
export SSRF_ALLOWED_DOMAINS=jsonplaceholder.typicode.com
```

> Sin esta variable, todos los tests del ejemplo fallan con `URLValidationError: URL not in allowlist`. Es comportamiento esperado, no un bug — la allowlist se configura por entorno con `SSRF_ALLOWED_DOMAINS` (dominios separados por comas).

## Paso 3: Ejecuta el test de ejemplo (2 min)

Los ejemplos viven en `examples/`. Importante: ejecuta **desde la raíz del repo**, porque los ejemplos importan el framework como `from src...`:

```bash
python -m pytest examples/api_testing_example.py -v
```

Salida esperada (resumida):

```
examples/api_testing_example.py::TestAPIExample::test_get_users_from_jsonplaceholder PASSED
examples/api_testing_example.py::TestAPIExample::test_create_user PASSED
examples/api_testing_example.py::TestAPIExample::test_get_single_post PASSED
examples/api_testing_example.py::TestAPIExample::test_api_timeout_handling PASSED
examples/api_testing_example.py::TestBasicAssertions::test_status_code_assertions PASSED
examples/api_testing_example.py::TestBasicAssertions::test_json_path_assertions PASSED
========= 6 passed in 1.78s =========
```

> ℹ️ Verás un warning `PytestUnknownMarkWarning: Unknown pytest.mark.api` — es inofensivo (el marker `api` no está registrado en `pyproject.toml`). Puedes ignorarlo.

**✅ Checkpoint:** los 6 tests PASSED (incluido el de timeout, que tarda ~5s porque el endpoint de prueba responde con delay a propósito).

## Paso 4: Entiende la anatomía (2 min)

Abre `examples/api_testing_example.py` y mira el primer test — son 4 piezas:

```python
from src.adapters.http.httpx_client import HTTPXClient   # 1. El cliente HTTP del framework

@pytest.mark.asyncio
async def test_get_users_from_jsonplaceholder():
    client = HTTPXClient(base_url="https://jsonplaceholder.typicode.com")  # 2. Base URL
    try:
        response = await client.get("/users")              # 3. La petición

        # 4. Las assertions — aquí vive tu test
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert "email" in data[0]
    finally:
        await client.close()   # siempre cierra el cliente
```

Las dos reglas que debes copiar de este ejemplo:

1. **`async` + `await`**: el framework es asíncrono; todo test de API con `HTTPXClient` es asíncrono y lleva `@pytest.mark.asyncio`.
2. **`finally: await client.close()`**: libera la conexión aunque el test falle.

## Paso 5: Escribe tu propio test (3 min)

Crea el archivo `examples/mi_primer_test.py`:

```python
import pytest
from src.adapters.http.httpx_client import HTTPXClient


@pytest.mark.asyncio
async def test_todos_del_usuario_1():
    """Mi primer test: los todos del usuario 1 existen y el primero está bien formado."""
    client = HTTPXClient(base_url="https://jsonplaceholder.typicode.com")
    try:
        response = await client.get("/users/1/todos")

        # Status code correcto
        assert response.status_code == 200, f"Esperaba 200, recibí {response.status_code}"

        # El cuerpo es una lista con contenido
        todos = response.json()
        assert isinstance(todos, list) and len(todos) > 0

        # Cada todo tiene la estructura esperada
        for campo in ("userId", "id", "title", "completed"):
            assert campo in todos[0], f"Falta el campo {campo}"

        print(f"✅ {len(todos)} todos verificados")
    finally:
        await client.close()
```

Ejecútalo:

```bash
python -m pytest examples/mi_primer_test.py -v -s
```

La flag `-s` muestra tus `print()` — útil mientras aprendes.

**✅ Checkpoint:** `1 passed`.

### Rómpelo a propósito (1 min)

Cambia `assert campo in todos[0]` por `assert campo in todos[0] and False`. Ejecuta de nuevo. Lee el error: pytest te muestra exactamente qué assertion falló y los valores involucrados. Ese mensaje de error es tu herramienta principal — acostúmbrate a leerlo completo.

---

## Resumen

```
instalar → ejecutar ejemplo → leer su anatomía → escribir tu test → romperlo → leer el error
```

Ya sabes el ciclo completo de desarrollo de un test de API.

## Siguientes pasos

- [Tutorial 1: Tu primera suite de tests](first-test-suite.md) — si aún no tienes cuenta/dashbord, empieza aquí
- [Tutorial 3: Tu primer test E2E](first-e2e-test.md) — el mismo ciclo, pero con un navegador real
- [How-to: Performance Testing](../how-to/performance-testing.md) — tests de carga con Locust
- [How-to: Security Testing](../how-to/security-testing.md) — SQL injection, XSS, rate limiting

## Problemas frecuentes

- **`URLValidationError: URL not in allowlist`** — falta `export SSRF_ALLOWED_DOMAINS=jsonplaceholder.typicode.com` (ver Paso 2)
- **`ModuleNotFoundError: src`** — estás ejecutando desde otra carpeta; vuelve a la raíz del repo
- **`ImportError: pytest_asyncio`** — la instalación no completó; repite `uv sync` (o `pip install -r requirements.txt`)
- **Tests lentos o colgados** — el test de timeout usa un delay de 5s a propósito; si tu red bloquea JSONPlaceholder, monta una API local y añade su dominio a `SSRF_ALLOWED_DOMAINS`
