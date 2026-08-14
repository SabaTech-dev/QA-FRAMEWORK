# E2E Testing con Playwright - Design Doc

**Fecha:** 2026-03-26
**Autor:** coder agent
**Task ID:** 057be126-d398-4131-aa81-d52b9668c12f

---

## Goal

Completar la suite E2E existente con los 2 flujos faltantes (Registro + Stripe Checkout) y añadir CI/CD pipeline en GitHub Actions.

**DoD:** Suite E2E funcional con los 5 flujos principales. Commit + CI pipeline.

---

## Current State

### Tests existentes (792 líneas)
| Archivo | Líneas | Flujo |
|---------|--------|-------|
| auth.spec.ts | 46 | Login/Logout |
| projects.spec.ts | 56 | Crear proyecto/suite/case |
| execution.spec.ts | 42 | Ejecutar test → ver resultados |
| export.spec.ts | 30 | Exportar resultados |
| app.spec.ts | 91 | Smoke tests |
| debug-*.spec.ts | 158 | Debug helpers |
| quick-wins.spec.ts | 369 | Quick wins validation |

### Config actual (playwright.config.ts)
- ✅ `fullyParallel: true`
- ✅ `screenshot: 'only-on-failure'`
- ✅ `video: 'retain-on-failure'`
- ✅ `trace: 'on-first-retry'`
- ✅ `reporter: 'html'`
- ❌ CI/CD workflow → **FALTA**

---

## Architecture

### Nuevos archivos a crear

```
dashboard/frontend/e2e/
├── signup.spec.ts          # NUEVO: Flujo de registro
└── checkout.spec.ts        # NUEVO: Flujo de pago Stripe

.github/workflows/
└── e2e.yml                 # NUEVO: CI/CD pipeline
```

---

## Tech Stack

- **Playwright** (ya instalado): Framework E2E
- **GitHub Actions**: CI/CD runner
- **Vercel**: Deployment (baseURL ya configurado)
- **Stripe (test mode)**: Pasarela de pago

---

## Tasks Breakdown

### Task 1: signup.spec.ts (Flujo de Registro)
**Estimación:** 30 min

```typescript
// Test cases:
1. Página de registro muestra formulario correcto
2. Registro con datos válidos crea usuario
3. Registro con email duplicado muestra error
4. Link a login funciona
```

**Dependencias:** Backend endpoint `/api/auth/register` debe existir

### Task 2: checkout.spec.ts (Flujo de Pago Stripe)
**Estimación:** 45 min

```typescript
// Test cases:
1. Usuario puede navegar a página de pricing/plans
2. Botón de checkout redirige a Stripe
3. (Opcional) Webhook de éxito actualiza suscripción
```

**Consideraciones:**
- Usar Stripe test cards: `4242 4242 4242 4242`
- NO probar webhook real (requiere backend setup)
- Validar que el flujo inicia correctamente

### Task 3: e2e.yml (GitHub Actions CI/CD)
**Estimación:** 30 min

```yaml
# Workflow:
- Trigger: push to main, PRs
- Jobs: 
  - install dependencies
  - run playwright tests
  - upload test artifacts (on failure)
```

**Secretos necesarios:**
- Ninguno (usa baseURL pública de Vercel)

---

## Data Flow

### Flujo de Registro
```
Usuario → /signup → Form → POST /api/auth/register → Redirect /dashboard
```

### Flujo de Checkout
```
Usuario → /pricing → "Subscribe" → Stripe Checkout → Success Page
```

### CI/CD Flow
```
Push/PR → GitHub Actions → npm ci → npx playwright test → Upload artifacts
```

---

## Error Handling Strategy

- **Tests flaky:** Usar `retries: 2` en CI (ya configurado)
- **Selectors dinámicos:** Preferir `data-testid` sobre texto
- **Timeouts:** Usar `expect().toBeVisible({ timeout: 5000 })` en vez de `waitForTimeout()`
- **Artifacts:** Subir screenshots/videos solo en fallo

---

## Risks

| Riesgo | Probabilidad | Mitigación |
|--------|--------------|------------|
| Backend de registro no existe | Media | Verificar endpoint antes de escribir test |
| Stripe checkout requiere auth real | Alta | Usar cuenta de test, mockear si es necesario |
| CI timeout en GitHub Actions | Baja | Limitar a chromium, paralelizar |
| Tests existentes usan anti-patrones | Baja | No modificar (scope limitado) |

---

## Out of Scope

- ❌ Refactor de tests existentes
- ❌ Tests en Firefox/Safari (solo Chromium)
- ❌ Visual regression testing
- ❌ Performance testing

---

## Approval

- [ ] Design aprobado por Alfred/user
- [ ] Proceder a `coder-writing-plans`
