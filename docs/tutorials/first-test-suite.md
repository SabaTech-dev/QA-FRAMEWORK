# Tutorial 1: Tu primera suite de tests

> **⏱️ Duración estimada:** 15 minutos
> **Nivel:** desde cero — no necesitas conocer QA-FRAMEWORK
> **Estado:** ✅ verificado contra un entorno limpio (2026-08-14, branch `feat/diataxis-nav`)

**Al terminar este tutorial tendrás:** una cuenta, tu primera suite de tests con un caso de prueba, una ejecución completada, y sabrás leer el reporte.

---

## Lo que vas a aprender

1. Crear una cuenta en QA-FRAMEWORK (local)
2. Crear una suite de tests y añadirle un test case
3. Ejecutar la suite
4. Interpretar el reporte de resultados

No hace falta saber Python ni testing: usamos la API y el dashboard, que es lo mismo que hace la interfaz.

---

## Paso 0: Elige tu camino

| Camino | Cuándo usarlo | Qué necesitas |
|--------|---------------|---------------|
| **A. SaaS** | Pendiente de apertura pública en la beta — no disponible todavía | — |
| **B. Local** (Docker) | Quieres probar ya, en tu máquina | Docker + Docker Compose |

> ℹ️ Durante la beta el único camino operativo es el **local (Docker)**. El SaaS se abrirá cuando termine la beta.

### Camino B: levantar el stack local (5 min)

```bash
git clone https://github.com/SabaTech-dev/QA-FRAMEWORK.git
cd QA-FRAMEWORK
docker compose -f docker-compose.unified.yml up -d
```

Verifica que está levantado (nota: el compose publica el backend en el **puerto 8010** del host):

```bash
curl http://localhost:8010/health
# Respuesta esperada: {"status": "healthy", "service": "qa-framework-dashboard-api"}
```

Abre `http://localhost:3010` en tu navegador (el frontend se publica en el **puerto 3010** del host).

---

## Paso 1: Crea tu cuenta (2 min)

La cuenta se crea con **username + email + contraseña** (mínimo 8 caracteres, sin más requisitos). No hay verificación de email: la cuenta queda usable nada más crearla.

### Desde la API

```bash
curl -X POST http://localhost:8010/api/v1/users \
  -H "Content-Type: application/json" \
  -d '{
    "username": "tu_usuario",
    "email": "tu@email.com",
    "password": "BetaTest123"
  }'
# Respuesta esperada: 201 Created con el objeto usuario
# (si el username o email ya existen: 400 Bad Request)
```

### Desde el dashboard

1. Pulsa **Register** (o abre `/register`)
2. Rellena Username, Email y Password
3. Tu cuenta se crea al enviar el formulario

> ⚠️ **Issue conocido (beta):** el wizard de registro del dashboard muestra un paso final "Verify" con código por email. Ese endpoint aún no está activo y el paso falla. Tu cuenta **sí se ha creado**: ve directamente a **Login** e inicia sesión con tu username y contraseña.

**✅ Checkpoint:** tienes un `201 Created` (o el wizard completó el envío) y puedes hacer login.

---

## Paso 2: Crea tu primera suite (3 min)

Una **suite** es un contenedor de tests relacionados — piensa en ella como una carpeta de tests para una parte de tu producto (login, checkout, API pública...).

### Desde el dashboard

1. Ve a **Test Suites** en el menú lateral
2. Pulsa **Create Suite**
3. Rellena:
   - **Name:** `Mi Primera Suite`
   - **Description:** `Aprendiendo QA-FRAMEWORK`
   - **Framework Type:** `pytest`
4. Guarda

### Desde la API (equivalente)

Primero consigue tu token (el login va por **username**, no por email):

```bash
curl -X POST http://localhost:8010/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "tu_usuario", "password": "BetaTest123"}'
# Guarda el "access_token" de la respuesta
export TOKEN="el_token_de_la_respuesta"
```

Y crea la suite:

```bash
curl -X POST http://localhost:8010/api/v1/suites \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Mi Primera Suite",
    "description": "Aprendiendo QA-FRAMEWORK",
    "framework_type": "pytest"
  }'
# Respuesta esperada: 201 Created con "id": 11 (un entero)
# Guarda ese id:
export SUITE_ID="11"
```

**✅ Checkpoint:** la suite aparece en el listado de Test Suites con 0 tests (`GET /api/v1/suites` con tu token).

---

## Paso 3: Añade un test case (3 min)

Un **test case** en QA-FRAMEWORK lleva el **código del test** (`test_code`), su tipo (`test_type`: `api`, `ui`, `db`, `security`, `performance`, `mobile`) y una prioridad. Vamos a crear el "Hola Mundo": verificar que una API pública responde 200.

### Desde la API

```bash
curl -X POST http://localhost:8010/api/v1/cases \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "suite_id": 11,
    "name": "JSONPlaceholder responde 200",
    "test_code": "import httpx\n\ndef test_jsonplaceholder():\n    r = httpx.get(\"https://jsonplaceholder.typicode.com/users\")\n    assert r.status_code == 200\n",
    "test_type": "api",
    "priority": "medium",
    "tags": ["tutorial", "smoke"]
  }'
# Respuesta esperada: 201 Created con "id" entero
```

### Desde el dashboard

1. Ve a **Test Cases** (o entra en tu suite y pulsa **Add Test Case**)
2. Rellena Name, selecciona la suite, `test_type: api` y pega el `test_code` de arriba
3. Guarda

**✅ Checkpoint:** tu suite muestra `total_tests: 1` al crear la próxima ejecución.

---

## Paso 4: Ejecuta la suite (1 min)

Las ejecuciones se crean con `POST /api/v1/executions` apuntando a la suite:

```bash
curl -X POST http://localhost:8010/api/v1/executions \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"suite_id": 11, "execution_type": "manual", "environment": "staging"}'

# Respuesta: 201 Created con {"id": 2, "status": "running", "total_tests": 1, ...}
export EXEC_ID="2"
```

Y se arrancan:

```bash
curl -X POST http://localhost:8010/api/v1/executions/$EXEC_ID/start \
  -H "Authorization: Bearer $TOKEN"
```

> ⚠️ **Issue conocido (beta):** hoy `POST /executions/{id}/start` devuelve `500 Internal Server Error`, pero **la ejecución sí arranca en background** y completa en unos segundos (ver `docker compose -f docker-compose.unified.yml logs backend`). Además, `GET /api/v1/executions` y `GET /api/v1/executions/{id}` devuelven 500 sobre ejecuciones ya completadas (el estado `completed` no está en el enum de la respuesta). La lectura del reporte por API/dashboard se restaurará con el fix; abajo puedes ver el reporte esperado.

Consulta el estado (cuando el issue anterior esté resuelto; hoy también 500 en completadas):

```bash
curl http://localhost:8010/api/v1/executions/$EXEC_ID \
  -H "Authorization: Bearer $TOKEN"
```

**✅ Checkpoint:** en los logs del backend aparece `Test case completed successfully` y `status: passed` para tu test case.

---

## Paso 5: Lee el reporte (3 min)

El resumen de una ejecución completada tiene esta forma (campos `*_tests` en la ejecución, y `results_summary` como desglose):

```json
{
  "status": "completed",
  "total_tests": 1,
  "passed_tests": 1,
  "failed_tests": 0,
  "skipped_tests": 0,
  "results_summary": {
    "total": 1,
    "passed": 1,
    "failed": 0,
    "skipped": 0
  }
}
```

Qué significa cada estado:

| Estado | Significado |
|--------|-------------|
| `passed` | El test se ejecutó y todas sus assertions se cumplieron |
| `failed` | Una assertion falló — abre el detalle para ver el error |
| `skipped` | El test no llegó a ejecutarse (precondiciones no cumplidas) |
| `error` | El test no pudo ejecutarse por un error de infraestructura |

> ℹ️ **Nota beta:** el ejecutor actual registra la ejecución de forma simulada (marca los casos activos como `passed` tras un segundo); la integración real con pytest está en desarrollo.

---

## Resumen

En 15 minutos has hecho el ciclo completo de QA-FRAMEWORK:

```
cuenta → suite → test case → ejecución → reporte
```

## Siguientes pasos

- [Tutorial 2: Tu primer test de API](first-api-test.md) — escribe tests con assertions sobre el cuerpo de la respuesta, no solo el status code
- [Tutorial 3: Tu primer test E2E](first-e2e-test.md) — automatiza un navegador con Playwright
- [How-to: Deployment](../how-to/deployment/index.md) — si quieres desplegar tu propia instancia

## Problemas frecuentes

- **`400 Username/Email already registered`** — inicia sesión directamente con Login
- **`401` en las llamadas API** — el token expira; vuelve a hacer login
- **`404` en `/executions/{id}/start`** — comprueba que el id es el entero devuelto al crear la ejecución (no el id de la suite)
- **Dashboard no carga (camino B)** — `docker compose -f docker-compose.unified.yml logs backend` para ver el error; comprueba que PostgreSQL y Redis están sanos (`docker compose -f docker-compose.unified.yml ps`)
- **Puertos:** el stack unificado publica backend en `8010` y frontend en `3010` (no en 8000/3000)
