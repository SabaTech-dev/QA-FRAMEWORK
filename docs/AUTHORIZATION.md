# Authorization & Multi-Tenant Access Control — Design Doc

**Status:** DRAFT — insumo para decisión gated (Joker). NO implementar durante freeze MVP→BETA.
**Fecha:** 2026-09-05
**Owner:** opencode (via card `c9cd4fe2`) · Review: Alfred · Decisión final: Joker (post-beta)
**Alcance:** documento de diseño. Cero cambios de código.
**Fuente taxonómica:** IDPro — [Authorization Terminology is a Mess: Let's Fix It](https://idpro.org/authorization-terminology-is-a-mess-lets-fix-it/) (Andrea Chiarelli) + Brossard, [The State of the Union of Authorization](https://idpro.org/the-state-of-the-union-of-authorization/) (PAP/PIP/PDP/PEP).
**Docs relacionados:** [AUTH.md](AUTH.md) (autenticación), `architecture.md`.

---

## 1. Resumen ejecutivo

QA-FRAMEWORK SaaS es multi-tenant y está camino a BETA **sin especificación de autorización**. Este doc:

1. Inventario el estado real (as-is) de auth/authz en el repo — con sus brechas.
2. Fija la terminología con la taxonomía IDPro (los términos RBAC/ABAC/PBAC/MAC/DAC **no compiten entre sí**: responden preguntas distintas).
3. Toma una decisión explícita por cada eje de la taxonomía, con justificación.
4. Define la matriz roles × permisos × tenants y los invariantes de gobernanza.
5. Decide la estrategia de aislamiento por tenant (RLS como backstop, app-layer como frontera primaria).
6. Enumera las decisiones gated Joker para presentación 1-a-1.

**Tesis:** el dominio ya tiene un scaffold RBAC correcto (`Role`, `Permission`, middlewares) que nunca se cableó. El diseño propone terminar ese cableado + añadir defensa en profundidad (RLS), sin cambiar de modelo.

---

## 2. Estado actual (as-is) — verificado en repo

### 2.1 Lo que existe y funciona

| Componente | Ubicación | Estado |
|---|---|---|
| Login email/password + JWT (HS256, access 60min / refresh 7d) | `dashboard/backend/services/auth_service.py` | ✅ Operativo |
| `get_current_user` (decodifica JWT, valida `sub` + `type=access`, chequea `is_active`) | `dashboard/backend/services/auth_service.py:168` | ✅ Operativo |
| Entidad `Tenant` (plan FREE/PRO/ENTERPRISE, status ACTIVE/SUSPENDED/TRIAL) | `src/domain/entities/tenant.py` | ✅ Operativo (modelo) |
| Middleware `TenantContextMiddleware` (resuelve tenant por header `X-Tenant-ID` o subdominio) | `src/api/middleware/tenant_context.py` | ✅ Scaffold, aplicado por rutas parcialmente |
| Entidad `Role` tenant-scoped, permisos `recurso:acción`, wildcards (`tests:*`, `admin:*`) | `src/domain/entities/role.py` | ✅ Modelo completo, sin persistencia |
| Catálogo `PERMISSIONS` (tests, projects, users, settings, `admin:*`) | `src/domain/entities/permission.py` | ✅ Modelo |
| Middleware RBAC (`require_permission`, `require_any/all`, `is_admin_only`) | `src/api/middleware/rbac_middleware.py` | ⚠️ Scaffold — depende de `request.state.user_roles` que **nadie llena** |
| `ApiKey` con `scopes` JSON y expiry | `dashboard/backend/models/__init__.py` (modelo `ApiKey`) | ✅ Modelo operativo |
| `User.is_superuser` (booleano de facto para admin) + `User.tenant_id` (**nullable**) | `dashboard/backend/models/__init__.py` (modelo `User`) | ⚠️ Parcial |
| JWT emitido con claims: `sub`, `type` **únicamente** | `auth_service.create_access_token` | ⚠️ Sin `tenant_id` ni roles |

### 2.2 Lo que NO existe (brechas)

| # | Brecha | Consecuencia |
|---|---|---|
| B1 | **`RoleModel` no existe** — `role_repository.py` importa `dashboard.backend.models.RoleModel` lazy, y ninguna tabla `roles` está definida | La persistencia de roles es código muerto; los roles no sobreviven un reinicio |
| B2 | **Sin asignación usuario→rol** (no hay tabla `role_assignments` ni campo) | Imposible saber qué roles tiene un usuario; `request.state.user_roles` nunca se llena → todo `require_permission` devolvería 401 |
| B3 | **JWT sin tenant ni roles** (`sub` only) | El token no vincula identidad con tenant; cualquier binding debe venir de DB |
| B4 | **Sin verificación de binding usuario↔tenant**: `get_current_user` (DB) y `TenantContextMiddleware` (header/subdominio) viven en capas separadas y nadie cruza `user.tenant_id` contra el tenant resuelto | **Riesgo crítico**: un usuario de tenant A con header `X-Tenant-ID` de tenant B pasaría ambos checks por separado |
| B5 | **Aislamiento 100% app-layer, sin backstop**: Postgres 15 en un solo schema (`qa_dashboard`), sin RLS ni schema-per-tenant | Un `WHERE tenant_id` olvidado = leak cross-tenant silencioso |
| B6 | `users.tenant_id` nullable | Usuarios "huérfanos" de tenant posibles; invariante de aislamiento no expresable en DB |
| B7 | `is_superuser` como rol implícito cross-tenant | Rol de plataforma invisible para el modelo RBAC, sin auditoría diferenciada |

> **Lectura honesta:** el scaffold de dominio (Clean Architecture) se construyó por delante de la infraestructura. El diseño no empieza de cero: termina el wiring existente.

---

## 3. Taxonomía IDPro — poner cada término en su eje

El artículo IDPro descompone cualquier sistema de autorización en **seis ejes independientes** (el digest del 09-04 los resumió en tres preguntas: *qué datos deciden, dónde se evalúa, quién administra*). Elegir en un eje **no** obliga en los demás.

| Eje | Pregunta que responde | Respuestas típicas | Etiquetas que viven aquí |
|---|---|---|---|
| 1. Administration | ¿Quién escribe/cambia las reglas? | Centralizado / Descentralizado / Híbrido | **MAC** (=centralizado), **DAC** (=descentralizado) |
| 2. Model | ¿Qué tipo de dato maneja la decisión? | Identidad (lista), Rol, Atributos, Relación | **ACL**, **RBAC**, **ABAC**, **ReBAC** |
| 3. Policy | ¿Qué forma tiene el artefacto de la regla? | Código inline / doc estructurado (JSON/YAML) / lenguaje declarativo (Rego, Cedar, XACML) / fila en DB | — |
| 4. Information | ¿De dónde salen los datos de la decisión? | Wired-in / token (claims JWT) / lookup (DB a la hora de decidir) / ambiental | — |
| 5. Decision (PDP) | ¿Dónde se computa allow/deny? | Inline en app / librería-módulo in-process / motor de políticas centralizado | **PBAC** (motor centralizado) vive aquí |
| 6. Enforcement (PEP) | ¿Dónde se aplica la decisión? | Inline / middleware dedicado / gateway-sidecar en el edge | — |

### El error clásico, desactivado por diseño

> **"PBAC reemplaza RBAC" es un error de categoría.** RBAC/ABAC describen *qué datos* usa la regla; PBAC describe *dónde* se evalúa (PDP centralizado vs in-process). Un motor PBAC puede evaluar reglas RBAC. Compararlos es comparar una receta con una cocina (metáfora del propio artículo).
>
> El error simétrico — *“ABAC reemplaza RBAC”* — también se desactiva: ABAC cambia el tipo de dato de la decisión, no necesariamente elimina los roles.

Regla operativa para este doc: **nunca elegimos “un modelo de autorización” como paquete. Elegimos una respuesta por eje.**

---

## 4. Decisión por eje

### Eje 1 — Administration: **Híbrido en dos niveles**

**Decisión.**

- **Nivel plataforma (centralizado, patrón MAC):** operadores QA-FW definen el catálogo de permisos, los planes/entitlements, y pueden suspender tenants (`TenantStatus.SUSPENDED` ya modelado). Los operadores no crean contenido de negocio dentro de un tenant.
- **Nivel tenant (delegado, patrón DAC acotado al tenant):** el `owner`/`admin` de cada organización administra membresías y puede crear roles custom para su tenant (el modelo `Role` ya es tenant-scoped y soporta roles no-default).
- **DAC a nivel de recurso** (compartir un test suite concreto con otro usuario): **fuera de scope** para beta. Los recursos son del tenant, no del usuario.

**Justificación.** En B2B SaaS el admin del cliente debe autogestionar su org (coste de soporte ~0) mientras la plataforma retiene el control de billing y abuso. Es exactamente el patrón híbrido del artículo: reglas centrales + discreción del dueño, superpuestas.

### Eje 2 — Model: **RBAC como columna vertebral + entitlements separados**

**Decisión.**

- El modelo de decisión es **RBAC**: sujeto → roles (tenant-scoped) → permisos `recurso:acción`.
- Los atributos que hoy importan — **plan** (FREE/PRO/ENTERPRISE), **status del tenant**, cuotas de uso — **no entran al modelo de roles**: se evalúan en una capa de **entitlements** distinta, *después* del check RBAC, alimentada por billing (Stripe), no por membresías.
- **No ReBAC**: no hay propiedad user-level de recursos ni grafos de relación (equipo→documento). Si post-beta se introduce sharing granular, se re-abre este eje.
- **No ACL per-object**: mantener permisos razonables por rol, no listas por instancia.

**Justificación.** Los permisos por rol son auditables y consulibles (“¿qué puede un member?” tiene respuesta). Mezclar plan/attributos dentro de los roles convertiría cada cambio de plan en una reescritura de roles de cada tenant. Capas separadas = cambios desacoplados (membresías ≠ billing).

### Eje 3 — Policy: **Catálogo declarativo en código + asignaciones como filas en DB**

**Decisión.**

1. **Catálogo de permisos** (`PERMISSIONS` en `src/domain/entities/permission.py`): fuente de verdad de *qué puede existir*. Vive en código, versionado en git, cambia por PR. Es un contrato (migraciones, tests y la UI lo consumen).
2. **Asignaciones rol→permisos**: filas en DB, tenant-scoped (datos de negocio, editables por admins de tenant dentro del catálogo).
3. Las reglas puntuales en app code (p. ej. `require_permission("tests:read")`) son **consumo** del catálogo, no definición.
4. **Sin lenguajes de política** (Rego/Cedar/XACML) ni documentos de política externos en beta.

**Justificación.** Separar “qué existe” (código, con tests) de “quién tiene qué” (dato, con UI) es la frontera correcta para un equipo pequeño. Un lenguaje de políticas añade superficie operativa (motor, aprendizaje, depuración) que un monolito de un solo servicio no necesita.

### Eje 4 — Information: **Token para identidad, lookup para permisos**

**Decisión.**

- **JWT (identidad estable):** `sub`, `tenant_id` (binding explícito identidad↔tenant), `type`, y un `token_version` para revocación global. **Sin roles ni permisos en el token** en beta.
- **Roles/permisos:** lookup en DB en el momento de la decisión, con cache in-process de TTL corto (30–60 s) y invalidación por escritura de membresías.
- **API keys:** scopes guardados en el registro DB (la key es solo credencial, no contenedor de permisos). El lookup es idéntico al de un usuario.

**Justificación.** Con access tokens de 60 min, meter roles en claims implica una ventana de hasta 60 min con privilegios ya revocados (degradar un admin y que siga admin). El lookup con cache de 30–60 s acota esa ventana a ~1 min manteniendo el coste O(1) por request. Es la opción revocable primero; si el volumen lo exige, migrar a claims + revocation list es aditivo (gated post-beta).

### Eje 5 — Decision (PDP): **Módulo in-process; sin motor de políticas externo**

**Decisión.**

- El PDP es un **módulo dedicado dentro del proceso** de la app: evolución del `RBACContext` existente (`src/api/middleware/rbac_middleware.py`), invocado por dependencies de FastAPI. Evalúa RBAC y devuelve allow/deny + razón.
- **NO** se adopta motor de políticas centralizado (OPA/SpiceDB/OpenFGA) en beta. **PBAC-engine queda como decisión de arquitectura post-beta**, disparada por: (a) ≥2 servicios que necesiten la misma decisión, (b) requisitos de auditoría centralizada de decisiones, (c) integración de políticas escritas por terceros.
- Como el modelo (RBAC) es ortogonal al punto de evaluación, extraer el PDP más adelante **no reescribe reglas**: solo mueve el evaluador. (Esta es la aplicación práctica de la taxonomía: hoy elegimos eje 5 ≠ PBAC sin renunciar a nada del eje 2.)

**Justificación.** Un solo servicio FastAPI no justifica un segundo sistema distribuido para decidir allow/deny. Latencia, despliegue y debugging empeoran; el beneficio (compartir políticas entre servicios) no tiene consumidor aún.

### Eje 6 — Enforcement (PEP): **Middleware/dependencies como frontera primaria + RLS como backstop**

**Decisión.**

- **PEP primario:** el orden por request será
  `TenantContextMiddleware` (resuelve tenant) → `get_current_user` (JWT→usuario) → **binding check** usuario.tenant_id == tenant resuelto (nuevo; cierra B4) → `require_permission(...)` (RBAC) → entitlement check (plan/cuotas) → handler.
- **PEP secundario (backstop de aislamiento):** Postgres RLS por `tenant_id` en las tablas de negocio (sección 6). La app ejecuta cada transacción con `SET LOCAL app.current_tenant = :tenant` y la policy restringe filas a ese valor. Un bug de app-layer (query sin filtro de tenant) deja de ser un leak.
- **Sin enforcement en gateway** (un solo servicio; un PEP de edge añadiría pieza ops sin atacar riesgo real hoy).

**Justificación.** Defensa en profundidad: la frontera primaria da errores ricos (403 con permiso faltante); el backstop garantiza la invariante de aislamiento ante bugs. Ambos son baratos; el backstop es el único que protege contra errores de código futuro.

---

## 5. Matriz roles × permisos × tenants

### 5.1 Actores y roles

| Rol | Scope | Quién lo asigna | Notas |
|---|---|---|---|
| `viewer` | Tenant | owner/admin | Read-only de todo el contenido del tenant |
| `member` | Tenant | owner/admin | Crea y ejecuta; no gestiona org |
| `admin` | Tenant | owner | Gestiona miembros y roles custom; no puede tocar owners |
| `owner` | Tenant | owner (transferencia) / signup | ≥1 owner activo por tenant, siempre |
| `platform_admin` | Plataforma (cross-tenant) | Operador QA-FW (bootstrap/seeds) | Reemplaza `is_superuser` (ver GD-3). Solo ops: soporte, suspensión, métricas. Nunca crea contenido de negocio. Toda acción cross-tenant auditada (break-glass) |

### 5.2 Matriz sobre el catálogo actual (`src/domain/entities/permission.py`)

| Permiso | viewer | member | admin | owner |
|---|:-:|:-:|:-:|:-:|
| `tests:read` | ✓ | ✓ | ✓ | ✓ |
| `tests:write` | ✗ | ✓ | ✓ | ✓ |
| `tests:run` | ✗ | ✓ | ✓ | ✓ |
| `tests:delete` | ✗ | ✗ | ✓ | ✓ |
| `projects:read` | ✓ | ✓ | ✓ | ✓ |
| `projects:write` | ✗ | ✓ | ✓ | ✓ |
| `projects:delete` | ✗ | ✗ | ✓ | ✓ |
| `users:read` (ver membresías) | ✗ | ✗ | ✓ | ✓ |
| `users:write` (invitar, asignar rol) | ✗ | ✗ | ✓¹ | ✓ |
| `users:delete` (quitar miembro) | ✗ | ✗ | ✓¹ | ✓ |
| `settings:read` | ✗ | ✗ | ✓ | ✓ |
| `settings:write` (config tenant, roles custom) | ✗ | ✗ | ✗ | ✓ |
| `admin:*` (wildcard total) | ✗ | ✗ | ✗ | ✓² |

¹ **Invariante I2:** un `admin` no puede crear/modificar/eliminar a un `owner`, ni elevar a alguien por encima de su propio nivel.
² El rol `owner` materializa `admin:*` (el wildcard ya está implementado en `Permission.matches`).

**Catálogo congelado para beta.** Candidatos post-beta (aditivos, no breaking): `billing:read` (ver la propia suscripción sin ser admin), `api_keys:manage` granular, `webhooks:manage`. Ver GD-5.

### 5.3 Invariantes de gobernanza (normativos)

- **I1 — Owner existence:** todo tenant tiene ≥1 `owner` activo. El último owner no puede ser degradado, eliminado, ni auto-degradarse (ni siquiera por sí mismo o por `platform_admin` sin transferencia previa).
- **I2 — No privilege escalation:** `admin` no modifica owners ni asigna permisos que él no posee.
- **I3 — Tenant binding:** todo request autenticado satisface `user.tenant_id == tenant_context.tenant_id`. Fallo = 403 (no 404/redirect). Sin excepciones salvo `platform_admin` (auditado).
- **I4 — Tenant status overridea:** tenant `SUSPENDED` (o trial expirado) → 403 en todos los endpoints salvo health y el portal de billing (para poder reactivar/pagar). El status del tenant se evalúa **antes** que RBAC.
- **I5 — Roles por defecto por tenant:** al crear el tenant se siembran `owner/admin/member/viewer` (factory `Role.create_default_role` ya lo modela). Roles custom son aditivos y nunca pueden *reducir* la matriz del owner.
- **I6 — API keys:** heredan el techo del rol de su usuario y **nunca** portan `admin:*` ni `users:*` (ver GD-6). Scopes ⊆ catálogo, validado contra `validate_permission`.

### 5.4 Entitlements por plan (capa separada del RBAC)

Esqueleto — los números los define billing (otra card). Aquí solo la estructura de decisión:

| Capability | FREE | PRO | ENTERPRISE |
|---|:-:|:-:|:-:|
| Asientos (members) | 1–3 | 10 | Custom |
| Ejecuciones de tests/mes | Cuota | Cuota↑ | Custom |
| Roles custom por tenant | ✗ | ✓ | ✓ |
| Retención de resultados | 7d | 30d | Custom |
| SSO SAML / SCIM | ✗ | ✗ | Roadmap post-beta |

Evaluación: entitlement check después del RBAC, resultado `403` con razón de plan (upgrade path en el error). El plan vive en `tenants.plan` + estado Stripe del usuario owner — nunca en roles.

---

## 6. Aislamiento multi-tenant

### 6.1 Opciones consideradas

| Opción | Descripción | Pros | Contras |
|---|---|---|---|
| **A. App-layer only** *(hoy)* | Cada query filtra `WHERE tenant_id = ...` por convención | Cero cambios | **Sin red de seguridad**: B5/B6 activos; un olvido = leak |
| **B. Shared schema + RLS** *(recomendado)* | Un schema; policies por fila `tenant_id = current_setting('app.current_tenant')`; la app fija el setting por transacción | Aislamiento en DB sin cambios de modelo; una sola migración por tabla | Requiere disciplina transaccional (ver 6.3); backfill de `tenant_id` |
| **C. Schema-per-tenant** | Un schema Postgres por tenant (`tenant_<slug>`) | Aislamiento fuerte, dump/restore por tenant | Migraciones × N tenants; pooling y connection-string por tenant; tooling (backup/monitoring) complica |
| **D. DB-per-tenant** | Base de datos física por tenant | Máximo aislamiento | Coste ops alto; no justificado antes de contrato enterprise |

### 6.2 Decisión

**Opción B (shared schema + RLS) como target, con app-layer como frontera primaria.** La Opción A es el estado actual y se corrige al implementar B. La Opción C se reserva como respuesta **reactiva** a un requisito contractual ENTERPRISE de aislamiento físico (ver GD-8) — no por defecto.

### 6.3 Mecánica de diseño (sin código)

1. **Sesión/transacción:** al abrir la transacción de request, la app ejecuta `SET LOCAL app.current_tenant = '<uuid>'` (y `SET LOCAL app.role = 'app'`). `SET LOCAL` revierte al cerrar la transacción → sin contaminación entre requests del pool (compatible con asyncpg/SQLAlchemy async).
2. **Usuario de DB no-superuser:** la app conecta como role `app` con `BYPASSRLS` desactivado (los superusers y roles con `BYPASSRLS` ignoran las policies — el usuario actual `qa_user` debe revisarse; las migraciones sí corren como superuser).
3. **Policies:** `USING (tenant_id = current_setting('app.current_tenant')::uuid)` en tablas de negocio; `FORCE ROW LEVEL SECURITY` en tablas donde también se escriba. `platform_admin` no opera writes de negocio cross-tenant (I3), así que no necesita bypass.
4. **Backfill previo:** `users.tenant_id` → `NOT NULL` (excepción explícita: cuentas `platform_admin`, marcadas por columna `is_platform_admin` — ver GD-3/4) + backfill de `tenant_id` en `test_suites`, `test_cases`, `test_executions`, `test_execution_details`, `api_keys` y tablas del dashboard (`notifications`, `cron_jobs`) donde falte. Índices compuestos `(tenant_id, id)` / `(tenant_id, <fk>)`.
5. **Testing del aislamiento (cuando se implemente):** suite adversarial — JWT válido del tenant A + header `X-Tenant-ID: B` debe resultar 403 y **cero** filas de B en cualquier query; el B4 (binding) y el RLS deben fallar *independientemente* el uno sin el otro.

### 6.4 Por qué no app-layer only

El único argumento para A es el coste de migración — que es finito y se ejecuta post-beta. El riesgo que cubre B (leak cross-tenant por query olvidada) es del tipo que no se descubre en code review sistemáticamente y que en SaaS B2B es existential (pérdida de confianza contractual). El freeze MVP→BETA no se rompe: **nada de esto se implementa ahora**; el doc deja el target unívoco.

---

## 7. Decisiones gated Joker — presentación 1-a-1

> Formato por decisión: **pregunta → opciones → recomendación → reversibilidad → coste de no decidir.** No son un paquete: cada una se presenta y decide por separado. Ninguna bloquea BETA per se (el freeze se mantiene); todas bloquean la *fase de implementación* post-beta salvo indicación.

### GD-1 · ¿RLS como backstop de aislamiento (Opción B)?
- **Opciones:** (a) mantener app-layer only; (b) shared schema + RLS; (c) schema-per-tenant.
- **Recomendación:** (b). (c) solo reactiva a contrato enterprise.
- **Reversibilidad:** alta al alza (añadir C después es posible); media a la baja (quitar RLS es trivial, pero llegar a RLS exige backfill costoso si se posterga).
- **Coste de no decidir:** cada tabla nueva nace sin `tenant_id` pensado para RLS → el backfill crece con el tiempo.

### GD-2 · ¿Roles fuera del JWT (lookup + cache 30–60 s)?
- **Opciones:** (a) roles en claims; (b) lookup en DB + cache corto.
- **Recomendación:** (b). Ventana de privilegio revocado: ~1 min vs hasta 60 min.
- **Reversibilidad:** alta (migrar a claims después es aditivo).
- **Coste de no decidir:** decidir (a) ahora y descubrir el problema de revocación en beta = re-emitir tokens y tocar clientes.

### GD-3 · ¿Reemplazar `is_superuser` por rol explícito `platform_admin`?
- **Opciones:** (a) mantener booleano; (b) columna `is_platform_admin` + rol fuera del modelo tenant, con auditoría.
- **Recomendación:** (b). El rol de plataforma debe ser visible, auditable y ajeno al RBAC de tenants.
- **Reversibilidad:** media (migración de datos pequeña; el booleano puede mantenerse como vista derivada durante una transición).
- **Coste de no decidir:** dos fuentes de verdad de “admin” para siempre.

### GD-4 · ¿`users.tenant_id` NOT NULL (con excepción `platform_admin`)?
- **Recomendación:** sí, junto con GD-3. Pre-requisito de RLS (policies limpias).
- **Reversibilidad:** alta. **Coste de no decidir:** invariante I3 no expresable en DB.

### GD-5 · ¿Congelar catálogo de permisos para beta?
- **Recomendación:** congelar el catálogo actual tal cual; post-beta añadir `billing:read`, `api_keys:manage`, `webhooks:manage` (aditivo, no breaking).
- **Reversibilidad:** trivial. **Coste de no decidir:** catálogo moving target = permisos en UI/código desincronizados.

### GD-6 · ¿API keys sin `admin:*` ni `users:*`?
- **Recomendación:** sí (invariante I6). Keys = acceso programático de contenido, no gobernanza de org.
- **Reversibilidad:** media — breaking para quien ya use keys con scopes elevados: **verificar uso real de scopes en producción antes de implementar**.
- **Coste de no decidir:** una key filtrada = compromiso total de la org.

### GD-7 · ¿PDP in-process sin motor de políticas (OPA/SpiceDB)?
- **Recomendación:** sí para beta. Criterios de re-apertura post-beta: ≥2 servicios, auditoría central, políticas de terceros.
- **Reversibilidad:** alta (el modelo no cambia; se mueve el evaluador).
- **Coste de no decidir:** adoptar un motor ahora = sobrecarga ops sin consumidor; decidirlo post-beta con criterios es gratis.

### GD-8 · ¿Schema-per-tenant para ENTERPRISE on-demand?
- **Recomendación:** no por defecto; evaluar solo ante requisito contractual concreto (aislamiento físico, residencia de datos). Si llega: es decisión de arquitectura + pricing, no de este doc.
- **Reversibilidad:** baja una vez un tenant vive en su schema (migrar de vuelta es doloroso) — por eso es opt-in por contrato.

---

## 8. Fuera de scope (explícito)

- **Implementación de código** — freeze MVP→BETA (este doc es design-only).
- Sharing granular de recursos (ReBAC), ACL per-object.
- ABAC fino (IP, horario, device posture, velocidad).
- SSO SAML / SCIM provisioning (roadmap ENTERPRISE post-beta).
- Motores de políticas externos (OPA, SpiceDB, OpenFGA, Cedar).
- Enforcement en gateway/APIGW.
- Números de cuotas/precios por plan (dominio de billing).
- Federación de identidad multi-IdP para el login (el OAuth actual Google/GitHub se mantiene).

## 9. Orden de implementación sugerido (post-decisión, NO ahora)

1. **Migraciones de datos:** backfill `tenant_id` + `NOT NULL` + índices compuestos (GD-4).
2. **Tablas de RBAC:** `roles` (`RoleModel` real, cierra B1) + `role_assignments` (cierra B2) + seeds de roles default por tenant.
3. **Wiring del JWT:** claims `tenant_id` + `token_version` (cierra B3); binding check en dependency chain (cierra B4).
4. **PEP RBAC:** poblar `request.state.user_roles` desde `role_assignments`; activar `require_permission` endpoint a endpoint.
5. **RLS:** policies + `SET LOCAL` por transacción + usuario DB no-superuser (GD-1).
6. **Suite adversarial de aislamiento** (ver 6.3.5) en CI.
7. **UI de gestión de miembros** (invitar, roles, quitar) respetando I1/I2.

Cada paso es independiente y reversible salvo el 1 (backfill: una sola vez).

## 10. Open questions

- ¿Las cuentas signup-via-OAuth heredan tenant en el momento de creación (tenant por dominio de email / invitación)? → propuesta: **solo por invitación** en beta (sin auto-join por dominio).
- ¿`platform_admin` accede a contenido de negocio de un tenant en modo lectura para soporte? → propuesta: sí, con auditoría inmutable; definir retención del audit log.
- ¿Los roles custom del tenant pueden usar wildcards (`tests:*`) o solo permisos atómicos? → propuesta: solo atómicos para custom (wildcards reservados a defaults) — evita escalaciones accidentales.

## 11. Referencias

- IDPro — *Authorization Terminology is a Mess: Let's Fix It* — https://idpro.org/authorization-terminology-is-a-mess-lets-fix-it/
- Brossard — *The State of the Union of Authorization* (PAP/PIP/PDP/PEP) — https://idpro.org/the-state-of-the-union-of-authorization/
- Mohamed, Auer, Hofer, Küng — *Systematic literature review on authorization and access control* (2022) — estratificación strategy/model/policy/mechanism.
- `docs/AUTH.md` — autenticación (login, OAuth, JWT, API keys).
- Código verificado (05-sep-2026): `dashboard/backend/models/__init__.py`, `dashboard/backend/services/auth_service.py`, `src/domain/entities/{role,permission,tenant}.py`, `src/api/middleware/{tenant_context,rbac_middleware}.py`, `src/infrastructure/persistence/role_repository.py`, `docker-compose.unified.yml`.
