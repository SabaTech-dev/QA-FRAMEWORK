# Tutorial 3: Tu primer test E2E con Playwright

> **⏱️ Duración estimada:** 20 minutos
> **Nivel:** desde cero — solo necesitas Python 3.11+ (tutorial 2 instalado)
> **Estado:** ✅ verificado contra un entorno limpio (2026-08-14, Playwright 1.41 + Chromium)

**Al terminar este tutorial tendrás:** Playwright funcionando en tu máquina, los tests E2E de ejemplo ejecutándose contra webs reales, y tu primer test E2E propio que navega, interactúa y hace captura de pantalla.

---

## Lo que vas a aprender

1. Instalar Playwright y su navegador
2. Ejecutar los tests de UI de ejemplo (navegación, interacción, visibilidad)
3. Entender el patrón de `PlaywrightPage` del framework
4. Escribir tu propio test E2E: navegar → rellenar → verificar → capturar

## Qué es un test E2E (y por qué es el último, no el primero)

Un test E2E (end-to-end) maneja un navegador real como haría un usuario: navega, hace clic, rellena formularios y comprueba lo que ve. Es el tipo de test más realista — y el más frágil y lento. Por eso QA-FRAMEWORK lo pone al final de la pirámide: solo para los flujos críticos.

---

## Paso 1: Instala el navegador de Playwright (5 min)

Parte del [Tutorial 2](first-api-test.md) (repo clonado + dependencias instaladas). Playwright necesita además descargarse su navegador:

```bash
# Si usaste uv:
uv run playwright install chromium
# Si usaste pip:
playwright install chromium
```

Descarga ~150MB una sola vez. Si falla por dependencias del sistema en Linux, el propio mensaje de error de Playwright te da el comando exacto (`playwright install-deps chromium` — puede requerir sudo).

**✅ Checkpoint:**

```bash
playwright --version
# Cualquier versión 1.4x+ está bien
```

## Paso 2: Ejecuta los tests de ejemplo (5 min)

```bash
python -m pytest examples/ui_testing_example.py -v -k "not login and not element_interaction"
```

Salida esperada (resumida):

```
examples/ui_testing_example.py::TestUIBasic::test_page_navigation PASSED
examples/ui_testing_example.py::TestUIBasic::test_element_visibility PASSED
examples/ui_testing_example.py::TestUIBasic::test_screenshot_capture PASSED
examples/ui_testing_example.py::TestUIResponsive::test_desktop_viewport PASSED
examples/ui_testing_example.py::TestUIResponsive::test_tablet_viewport PASSED
examples/ui_testing_example.py::TestUIResponsive::test_mobile_viewport PASSED
========= 6 passed =========
```

> ⚠️ **Por qué el `-k`:** de los 9 tests del ejemplo, hoy fallan 3 y por eso los excluimos:
> - `test_element_interaction` — usa `#searchButton` en Wikipedia, un selector que **Wikipedia retiró** al cambiar de skin (demostración perfecta de la fragilidad E2E que veremos abajo).
> - `TestUILoginFlow` (2 tests) — usan selectores mock (`#login-button`) sobre `example.com`, que no tiene login: fallan por diseño.
>
> Si ejecutas sin `-k` verás `3 failed, 6 passed`. Lo importante: `TestUIBasic` (salvo el de Wikipedia) y `TestUIResponsive` en verde.

Qué hace cada uno (míralos en `examples/ui_testing_example.py`):

| Test | Demuestra |
|------|-----------|
| `test_page_navigation` | Navegar y leer texto (`goto`, `wait_for_selector`, `get_text`) |
| `test_element_interaction` | Rellenar y hacer clic (`fill`, `click`) — busca "Python programming" en Wikipedia *(hoy roto por selector retirado)* |
| `test_element_visibility` | Comprobar si algo es visible (`is_visible`), incluido el caso negativo |
| `test_screenshot_capture` | Guardar captura de pantalla (`screenshot`) |
| `TestUIResponsive` | Viewports desktop/tablet/móvil con el mismo test |

**✅ Checkpoint:** 6 passed.

## Paso 3: Entiende el patrón (3 min)

Todos los tests siguen la misma forma:

```python
from src.adapters.ui.playwright_page import PlaywrightPage

@pytest.mark.asyncio
async def test_page_navigation():
    async with PlaywrightPage(browser_type="chromium", headless=True) as page:  # 1. El navegador
        await page.goto("https://example.com")          # 2. Navegar
        await page.wait_for_selector("h1")              # 3. Esperar (E2E es asíncrono: NUNCA adivines)
        title = await page.get_text("h1")               # 4. Leer
        assert "Example" in title                       # 5. Verificar
```

Tres reglas de oro de este patrón:

1. **`async with ... as page`** abre y cierra el navegador por ti — nunca gestiones eso a mano.
2. **`wait_for_selector` antes de interactuar.** El 90% de los flakes de E2E vienen de interactuar con un elemento que aún no cargó. Espera siempre.
3. **`headless=True`** para CI; si quieres *ver* el navegador mientras aprendes, cámbialo a `False`.

## Paso 4: Escribe tu propio test E2E (7 min)

Crea `examples/mi_primer_e2e.py`. El flujo: navegar a Wikipedia, buscar, verificar el resultado y capturar pantalla:

```python
import pytest
from src.adapters.ui.playwright_page import PlaywrightPage


@pytest.mark.asyncio
async def test_buscar_en_wikipedia():
    """Mi primer E2E: buscar 'QA Framework' en Wikipedia y capturar el resultado."""
    async with PlaywrightPage(browser_type="chromium", headless=True) as page:
        # 1. Navegar
        await page.goto("https://es.wikipedia.org")

        # 2. Rellenar el buscador y enviar
        #    (nota: Wikipedia retiró #searchButton al cambiar de skin;
        #     el botón actual es .cdx-search-input__end-button —
        #     lección de por qué los E2E contra terceros se rompen solos)
        await page.fill("#searchInput", "automatización de pruebas")
        await page.click(".cdx-search-input__end-button")

        # 3. Esperar el resultado (patrón: esperar ANTES de verificar)
        await page.wait_for_selector("#firstHeading")

        # 4. Verificar
        heading = await page.get_text("#firstHeading")
        assert "Automatización" in heading or "automatización" in heading, \
            f"El título inesperado fue: {heading}"

        # 5. Evidencia: captura de pantalla
        await page.screenshot("mi_primer_e2e.png")
        print(f"✅ E2E completado — título: {heading}")
```

Ejecútalo:

```bash
python -m pytest examples/mi_primer_e2e.py -v -s
```

**✅ Checkpoint:** `1 passed` y aparece `mi_primer_e2e.png` en la raíz del repo. Ábrela — esa captura es exactamente lo que el test vio.

### Hazlo visible (recomendado)

Cambia `headless=False` y ejecuta de nuevo: verás el navegador abrirse, escribir y hacer clic solo. Es el mejor modo de depurar un E2E que falla.

### Prueba un viewport móvil (2 min)

```python
async with PlaywrightPage(browser_type="chromium", headless=True, viewport=(375, 667)) as page:
    ...
```

Mismo test, pantalla de móvil. Así se comprueba responsive sin duplicar código.

---

## Resumen

```
instalar navegador → ejecutar ejemplos → patrón (async with + esperar + verificar) → tu test → captura
```

## Siguientes pasos

- [How-to: Testing Guide](../how-to/testing-guide.md) — organización de suites completas
- [How-to: Security Testing](../how-to/security-testing.md) — SQLi/XSS automatizado sobre tu app
- [Reference: API](../reference/api.md) — orquestar ejecuciones desde la API del dashboard

## Problemas frecuentes

- **`Executable doesn't exist at .../chromium`** — te falta `playwright install chromium`
- **`TimeoutError` en Wikipedia** — casi siempre un selector que el sitio cambió (lección en vivo: `#searchButton` existía y hoy no). En tus tests reales apunta a *tu* app
- **Flakes aleatorios** — casi siempre falta un `wait_for_selector` antes de `click`/`fill`
- **Linux sin headless** — en servidores sin X usa `headless=True`; para ver el navegador instala `xvfb`
