# Security Gate Report — card 4920f947 (iteración 2): /auth/change-password

- **Fecha:** 2026-09-28
- **Branch:** `fix/auth-change-password-4920f947`
- **Commits (esta iteración):** `7296f52` (sobre `deed2d0`, `e6101f9` de la iteración 1)
- **Alcance:** remediación de los hallazgos del gate de security de la iteración 1 (1 Medium + 1 Low).

## M-1 — CWE-613 (CVSS 6.8) — RESUELTO

**Hallazgo:** `/auth/change-password` actualizaba el hash pero no revocaba los refresh
tokens emitidos con la contraseña antigua; una sesión (o token robado) sobrevivía al
cambio de contraseña hasta 7 días.

**Fix (commit `7296f52`):**

1. `RefreshTokenStore.register_family(username, family_id, ttl)` (nuevo): el login
   indexa cada familia nueva en un set Redis por usuario (`qa:auth:rt:user:{username}:fams`,
   TTL = vida máxima de la familia).
2. `RefreshTokenStore.revoke_families_for_user(username, ttl)` (nuevo): tombstonea todas
   las familias indexadas y consume el índice (los logins posteriores registran familias
   nuevas que quedan vivas).
3. `/auth/change-password` llama a `revoke_user_refresh_tokens(username)` **después** del
   `db.commit()` exitoso — un 200 implica revocación efectiva.
4. Postura fail-closed coherente con `/auth/refresh` y `/auth/revoke`: si el store Redis
   no está disponible, login y change-password responden 503 en lugar de degradar en
   silencio la garantía de revocación.

**Prueba (RED → GREEN):** `test_change_password_revokes_previous_refresh_tokens` —
login → change-password → refresh con token previo ⇒ **401** (antes del fix: 200).
Control: `test_new_login_after_password_change_still_refreshes` — login posterior al
cambio ⇒ refresh **200** (la revocación no mata sesiones nuevas).

**Limitación documentada:** las familias emitidas ANTES de desplegar este fix no están
en el índice y no se revocan con un cambio de contraseña posterior (ventana de un
despliegue); caducan solas en ≤7 días. La rotación reutiliza la familia del login, así
que un solo registro por sesión cubre toda la cadena.

## L-1 — validación de BYTES en schemas — RESUELTO

**Hallazgo:** pydantic cuenta caracteres, bcrypt cuenta bytes. `"🔐" * 20` (20 chars,
80 bytes UTF-8) pasaba `max_length=72` y reventaba como **500** en change-password
(`PasswordTooLongError` sin capturar); en register devolvía 400 desde la capa de
servicio.

**Fix:** `_validate_password_max_bytes` (validator pydantic compartido) aplicado a
`ChangePasswordRequest.new_password` y `UserCreate.password` ⇒ **422** limpio en la
frontera de confianza. La defensa de 400 en `create_user_service` se mantiene como
defense-in-depth (sigue cubierta por su test en `tests/services/test_user_service.py`).

**Prueba:** `test_change_password_multibyte_over_72_bytes_rejected_422` y
`test_register_multibyte_over_72_bytes_rejected_422` (multibyte 80 bytes ⇒ 422, sin
efecto en DB).

## Riesgo residual — ACEPTADO (a trasladar al PR cuando exista)

> **Access tokens JWT ≤30 min sin denylist.** `access_token_expire_minutes = 30`
> (`dashboard/backend/config.py:41`). Un access token emitido antes del cambio de
> contraseña sigue válido como máximo 30 minutos; no hay denylist de access tokens.
> Decisión estándar para JWT de vida corta: aceptado. La exposición se acota a ≤30 min
> y requiere posesión del token. No se considera parte del alcance de este fix.

## Verificación

```bash
cd dashboard/backend
.venv/bin/python -m pytest tests/unit/test_auth_change_password.py --no-cov -q
# => 12 passed (8 iteración 1 + 4 nuevos)

.venv/bin/python -m pytest tests/unit -q --no-cov
# => 8 failed, 251 passed, 18 skipped
#    (los mismos 8 fallos PREEXISTENTES de la línea base: browser_use 0.1.8 pin ×6,
#     config env hardening ×2 — ajenos a auth; línea base: 247 passed / 8 failed)

.venv/bin/python -m pytest tests/unit/test_auth_change_password.py \
  tests/unit/test_auth_service_token_guards.py tests/unit/test_refresh_rotation.py \
  tests/services/test_user_service.py --no-cov -q
# => 45 passed, 18 skipped (refresh_rotation: skip por no haber Redis local)
```

## Defecto de infra detectado (escalar, fuera del alcance del fix)

- **Hook pre-commit `bandit` es config muerta desde 2026-06-09** (`d8b171d`):
  `args: ['-r','src','-f','json']` + filenames que pre-commit añade ⇒ bandit rechaza
  los argumentos con CUALQUIER fichero Python staged; además `src/` no existe en la
  raíz del repo (el backend está en `dashboard/backend/src`). Han aterrizado 8+ commits
  con Python desde entonces (incluidas iteración 1 y esta) con el hook imposibilitado
  de pasar. En este commit se usó `SKIP=bandit` (mecanismo oficial de pre-commit; el
  resto de hooks corrió y pasó) + escaneo manual documentado.
- **Semgrep:** falso positivo preexistente en `TokenResponse.token_type = "bearer"`
  anulado con `# nosemgrep: no-hardcoded-passwords` (anotación estándar, el gate sigue
  vivo para el resto del código).
- **Escaneo bandit manual (1.9.4) sobre los ficheros cambiados:** 0 Medium/High,
  4 Low de patrón preexistente (literales `'bearer'`/`'refresh'` B105/B106, `assert`
  B101 en store).

## Artefactos

- Código: `dashboard/backend/api/v1/auth_routes.py`,
  `dashboard/backend/services/auth_service.py`,
  `dashboard/backend/src/infrastructure/refresh_tokens/store.py`,
  `dashboard/backend/schemas/__init__.py`
- Tests: `dashboard/backend/tests/unit/test_auth_change_password.py`
- Estado: **en review** — pendiente re-gate de security + firma de Alfred. Sin
  self-proof.
