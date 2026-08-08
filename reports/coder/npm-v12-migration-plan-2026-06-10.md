# Plan de Migración npm v12 — SabaTech Pipelines CI/CD

**Fecha:** 2026-06-10
**Autor:** Coder (agente)
**Estado:** BORRADOR — Pendiente revisión Security + QA
**Prioridad:** P2

---

## 1. Contexto

npm v12.0.0-pre.0 fue publicado el **2026-05-20** (actualmente en pre-release).
La versión estable actual en el sistema es **npm 11.16.0** (con Node 26.3.0).

npm v12 se incluye con Node.js v24+ como bundling por defecto. Actualmente usamos
**Node 18 y Node 20** en los pipelines, por lo que la migración NO es inmediata pero
debe planificarse para cuando adoptemos Node 22+ o npm v12 como requisito.

### Estado de adopción
- npm v12 sigue en **pre-release** (`12.0.0-pre.0.0`)
- No hay fecha de GA anunciada aún
- Node 26 (nuestro runtime local) bundlea npm 11.x, no 12.x

---

## 2. Breaking Changes de npm v12 Relevantes

### 2.1 Cambios que AFECTAN nuestros pipelines

| # | Breaking Change | Impacto | Severidad | Archivos afectados |
|---|---|---|---|---|
| BC-1 | `npm view --json` siempre devuelve array | Scripts que parseen JSON y esperen un objeto raíz | 🟡 Media | Ninguno detectado actualmente |
| BC-2 | `npm pack` / `npm publish` output JSON cambiado | Si parseamos output para CI reporting | 🟢 Baja | No usamos `npm pack`/`npm publish` en CI |
| BC-3 | `npm pkg` no fuerza output JSON | Scripts que esperen JSON de `npm pkg` | 🟢 Baja | No usamos `npm pkg` |
| BC-4 | `npm shrinkwrap` eliminado | Si existiera `npm-shrinkwrap.json` | 🟢 Baja | No tenemos shrinkwrap files |
| BC-5 | `npm adduser` eliminado | CI con `npm login` | 🟢 Baja | No usamos `adduser` en CI |
| BC-6 | Man pages no registrados globalmente | Docs en containers | 🟢 Baja | Usamos `npm help` internamente |
| BC-7 | `whichnode` eliminado | Scripts que lean `process.execPath` | 🟢 Baja | No afecta CI/CD |

### 2.2 Cambios que NO nos afectan

- **`star`/`stars`/`unstar` eliminados:** No los usamos
- **Twitter/Freenode profile fields eliminados:** No aplica
- **`npm sbom` name field cambia:** Usamos Trivy para SBOM, no `npm sbom`

### 2.3 Nuevas features para considerar post-migración

| Feature | Utilidad | Prioridad |
|---|---|---|
| `npm stage` (nuevo comando) | Staging interactivo de cambios | P3 |
| `allowScripts` opt-in policy | Seguridad: controlar lifecycle scripts | **P1** — Reduce riesgo de supply chain |
| `allow-git/allow-file/allow-directory/allow-remote` configs | Seguridad: restringir fuentes de deps | **P1** — Ideal para CI hardened |
| `publish --access=private` alias | Si publicamos packages privados | P3 |

---

## 3. Inventario de Pipelines Afectados

### 3.1 Repos con pipelines npm

| Repo | Workflow | Node Version | Package Manager | Usa npm directamente? |
|---|---|---|---|---|
| **Alfred-Mission-Control** | `ci-cd.yml` | 20 | **pnpm** 9 | ❌ (solo pnpm) |
| **QA-FRAMEWORK** (main) | `ci-cd.yml` | 20 | Poetry | ⚠️ Solo para frontend Playwright tests |
| **QA-FRAMEWORK** (main) | `e2e.yml` | 20 | npm | ✅ `npm ci` en dashboard/frontend |
| **QA-FRAMEWORK** (main) | `pr-deploy-coolify.yml` | N/A (env) | npm | ✅ |
| **QA-FRAMEWORK** (dashboard) | `ci.yml` | 18.x, 20.x | npm | ✅ `npm ci`, `npm run lint/test/build` |
| **QA-FRAMEWORK** (dashboard) | `code-quality.yml` | 20.x | npm | ✅ |
| **saba-osint** | `ci.yml` / `cd.yml` | — | pip | ❌ |
| **Saba-AgenticFlow** | `ci.yml` | — | pip | ❌ |

### 3.2 Dockerfiles con npm

| Archivo | Base Image | Usa npm? | Comandos |
|---|---|---|---|
| `Alfred-Mission-Control/Dockerfile` | `node:26-slim` | ✅ | `npm install`, `npm run build` |
| `saba-osint/dashboard/frontend/Dockerfile` | `node:18-alpine` | ✅ | `npm install` |
| `QA-FRAMEWORK/dashboard/frontend/Dockerfile` | `node:18-alpine` | ✅ | `npm install` |
| `QA-FRAMEWORK/dashboard/frontend/Dockerfile.prod` | `node:18-alpine` | ✅ | `npm ci`, `npm run build`, `npm install -g serve` |
| `QA-FRAMEWORK/dashboard/backend/Dockerfile` | `python:3.x` | ❌ | pip |

---

## 4. Plan de Migración

### Fase 0: Pre-requisitos (AHORA — sin esperar npm v12 GA)
**Duración estimada:** 1 día

- [x] Auditar todos los pipelines y Dockerfiles (este documento)
- [ ] Crear branch `chore/npm-v12-prep` en cada repo afectado
- [ ] Añadir `engines` field en `package.json` de cada proyecto npm:
  ```json
  "engines": {
    "node": ">=18.0.0",
    "npm": ">=9.0.0"
  }
  ```

### Fase 1: Node 18 → Node 20 (ACTUALIZACIÓN INDEPENDIENTE)
**Duración estimada:** 2-3 días
**Riesgo:** 🟢 Bajo

Los Dockerfiles que aún usan `node:18-alpine` deben actualizarse:

| Archivo | Cambio |
|---|---|
| `QA-FRAMEWORK/dashboard/frontend/Dockerfile` | `node:18-alpine` → `node:20-alpine` |
| `QA-FRAMEWORK/dashboard/frontend/Dockerfile.prod` | `node:18-alpine` → `node:20-alpine` |
| `saba-osint/dashboard/frontend/Dockerfile` | `node:18-alpine` → `node:20-alpine` |
| `QA-FRAMEWORK/dashboard/.github/workflows/ci.yml` | Matrix: eliminar `18.x`, mantener `20.x` |

**Validación:**
- `docker compose build` en cada repo
- Tests de CI pasando con Node 20

### Fase 2: Testing con npm v12 pre-release (OPCIONAL)
**Duración estimada:** 1-2 días
**Riesgo:** 🟡 Medio

Solo si queremos validar anticipadamente:

```yaml
# Test matrix upgrade temporal
strategy:
  matrix:
    npm-version: ['11', '12.0.0-pre.0.0']
```

**Pasos:**
1. Añadir `npm install -g npm@12.0.0-pre.0.0` después de `setup-node` en un workflow de test
2. Ejecutar tests completos
3. Documentar cualquier fallo

### Fase 3: Migración definitiva (cuando npm v12 sea GA)
**Duración estimada:** 3-5 días
**Riesgo:** 🟡 Medio

#### Paso 3.1: Actualizar `engines` en package.json
```json
"engines": {
  "node": ">=20.0.0",
  "npm": ">=12.0.0"
}
```

#### Paso 3.2: Actualizar Dockerfiles

**Antes:**
```dockerfile
FROM node:20-alpine AS builder
RUN npm ci
```

**Después:**
```dockerfile
FROM node:22-alpine AS builder
# npm 12 viene con Node 22+
RUN npm ci
```

#### Paso 3.3: Actualizar GitHub Actions workflows

**Antes:**
```yaml
- uses: actions/setup-node@v4
  with:
    node-version: '20'
```

**Después:**
```yaml
- uses: actions/setup-node@v4
  with:
    node-version: '22'
    # npm 12 es el default con Node 22+
```

#### Paso 3.4: Aprovechar nuevas features de seguridad

Añadir `.npmrc` en cada repo npm para habilitar `allowScripts` policy:

```ini
# .npmrc — Security hardening (npm v12+)
allow-scripts=false
allow-git=none
allow-file=none
allow-directory=none
allow-remote=registry
```

Esto previene ejecución de lifecycle scripts de dependencias (postinstall, etc.)
y restringe fuentes de packages a solo el registry configurado.

#### Paso 3.5: Verificar que no hay shrinkwrap files

```bash
find . -name "npm-shrinkwrap.json" -delete
# Asegurar que package-lock.json existe
```

#### Paso 3.6: Actualizar scripts CI que usen npm commands afectados

Si en algún momento usamos `npm view --json`, actualizar parsing:
```bash
# Antes (podía devolver object)
npm view react version --json

# Después (siempre array)
npm view react version --json | jq '.[0]'
```

### Fase 4: Validación post-migración
**Duración estimada:** 1 día

- [ ] Todos los pipelines CI pasan en verde
- [ ] Docker builds exitosos para todos los repos
- [ ] `npm ci` funciona sin warnings nuevos
- [ ] Dependabot/Renovate actualizados para nueva versión
- [ ] Coolify deployments verificados
- [ ] SBOM generation (Trivy) verificado

---

## 5. Riesgos y Mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|---|---|---|---|
| npm v12 cambia más breaking changes antes de GA | Alta | Media | Esperar GA antes de Fase 3 |
| Dependencias incompatibles con npm 12 | Baja | Alta | Testear en Fase 2 |
| `npm ci` behavior change rompe lockfiles | Baja | Alta | Regenerar lockfiles con npm 12 |
| `allowScripts` bloquea deps que necesitan postinstall | Media | Media | Whitelist explícito de scripts necesarios |
| Node 22 no soportado por algún dependency | Baja | Media | Matrix testing antes de migrar |

---

## 6. Timeline Propuesto

```
2026-06  ┃ Fase 0: Pre-requisitos (este plan)
         ┃ Fase 1: Node 18→20 (independiente de npm 12)
         ┃
2026-07  ┃ (esperar npm v12 GA o RC estable)
         ┃ Fase 2: Testing con pre-release (opcional)
         ┃
2026-08  ┃ Fase 3: Migración definitiva (post-GA)
         ┃ Fase 4: Validación
```

---

## 7. Checklist de Acción Inmediata

### Hacer ahora (P2)
- [ ] Actualizar Dockerfiles `node:18-alpine` → `node:20-alpine`
- [ ] Eliminar Node 18.x de matrices de test en `dashboard/.github/workflows/ci.yml`
- [ ] Añadir `engines` field en package.json

### Hacer cuando npm v12 sea GA
- [ ] Actualizar Node version en CI a 22+
- [ ] Habilitar `allowScripts` policy en `.npmrc`
- [ ] Regenerar `package-lock.json` con npm 12
- [ ] Testing completo de todos los pipelines

### NO hacer
- [ ] Migrar Alfred-Mission-Control a npm (usa pnpm, no afectado)
- [ ] Cambiar saba-osint o Saba-AgenticFlow (Python, no afectados)

---

## 8. Conclusión

**npm v12 NO representa un riesgo crítico para nuestros pipelines.** Los breaking changes
afectan comandos que no usamos (`shrinkwrap`, `adduser`, `star`, `view --json` parsing).
El impacto principal es la oportunidad de adoptar **features de seguridad nuevas**
(`allowScripts`, `allow-*` configs) que refuerzan nuestra supply chain security (SLSA L1).

La acción inmediata recomendada es **Fase 1 (Node 18→20)** que es independiente y
reduce deuda técnica. La migración npm v12 propiamente dicha puede esperar a GA.

---

*Plan generado por Coder agent — Card ID: 54446e4b-5dd9-4639-b05e-d6738159e8bf*
