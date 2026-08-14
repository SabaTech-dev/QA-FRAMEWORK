# E2E Testing with Playwright - Design Doc

**Fecha:** 2026-03-25
**Autor:** coder agent
**Task ID:** 057be126-d398-4131-aa81-d52b9668c12f
**Estado:** DRAFT

---

## 1. Goal

Completar la suite E2E con Playwright para los 5 flujos críticos del QA-FRAMEWORK, integrando con CI/CD existente.

---

## 2. Contexto Actual

### 2.1 Estado de Tests E2E
- **Playwright:** v1.58.2 (ya instalado)
- **Tests existentes:** 16/18 pasando (88.9%)
- **CI/CD:** GitHub Actions con E2E stage
- **Paralelización:** Habilitada (fullyParallel: true)
- **Reportes:** HTML configurados

### 2.2 Tests Existentes Cubren
- ✅ Backend health/API docs
- ✅ Login/auth
- ✅ User info
- ✅ Frontend rendering
- ✅ Billing plans (API level)

### 2.3 Tests Faltantes (Scope de Esta Tarea)
1. ❌ Registro/Login completo (mejorar existente)
2. ❌ Crear proyecto → crear suite → crear test case
3. ❌ Ejecutar test → ver resultados
4. ❌ Checkout/pago (Stripe)
5. ❌ Exportar resultados

---

## 3. Arquitectura Propuesta

### 3.1 Estructura de Tests
```
dashboard/tests/e2e/
├── auth.spec.ts          # Registro + Login (mejorar)
├── projects.spec.ts      # Crear proyecto → suite → test case
├── execution.spec.ts     # Ejecutar test → ver resultados
├── billing.spec.ts       # Checkout/pago Stripe
├── export.spec.ts        # Exportar resultados
└── fixtures/
    └── test-data.ts      # Datos de prueba compartidos
```

### 3.2 Flujo de Tests
```
┌─────────────────────────────────────────────────────────────┐
│                    Playwright E2E Tests                      │
├─────────────────────────────────────────────────────────────┤
│  1. Auth Flow                                                │
│     - Registro nuevo usuario                                 │
│     - Login con credenciales                                 │
│     - Logout                                                 │
├─────────────────────────────────────────────────────────────┤
│  2. Project Management Flow                                  │
│     - Crear proyecto                                         │
│     - Crear suite dentro del proyecto                        │
│     - Crear test case dentro de la suite                     │
│     - Verificar que aparece en la lista                      │
├─────────────────────────────────────────────────────────────┤
│  3. Test Execution Flow                                      │
│     - Seleccionar suite                                      │
│     - Ejecutar tests                                         │
│     - Ver resultados en tiempo real                          │
│     - Verificar métricas (passed/failed)                     │
├─────────────────────────────────────────────────────────────┤
│  4. Billing/Checkout Flow                                    │
│     - Navegar a planes                                       │
│     - Seleccionar plan Pro                                   │
│     - Completar checkout (Stripe test mode)                  │
│     - Verificar upgrade                                      │
├─────────────────────────────────────────────────────────────┤
│  5. Export Results Flow                                      │
│     - Ejecutar tests                                         │
│     - Exportar a JSON/CSV                                    │
│     - Verificar archivo descargado                           │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. Tech Stack

- **Playwright:** v1.58.2 (ya instalado)
- **pytest-playwright:** Para tests Python backend
- **@playwright/test:** Para tests TypeScript frontend
- **Stripe test mode:** Tarjetas de prueba Stripe
- **GitHub Actions:** CI/CD existente

---

## 5. Tests Detallados

### 5.1 Auth Flow (auth.spec.ts)
```typescript
test('complete auth flow', async ({ page }) => {
  // Registro
  await page.goto('/register');
  await page.fill('[name=email]', 'test@example.com');
  await page.fill('[name=password]', 'Test123!@#');
  await page.click('button[type=submit]');
  
  // Verificar redirect a dashboard
  await expect(page).toHaveURL('/dashboard');
  
  // Logout
  await page.click('[data-testid=logout]');
  await expect(page).toHaveURL('/login');
  
  // Login
  await page.fill('[name=email]', 'test@example.com');
  await page.fill('[name=password]', 'Test123!@#');
  await page.click('button[type=submit]');
  await expect(page).toHaveURL('/dashboard');
});
```

### 5.2 Project Management Flow (projects.spec.ts)
```typescript
test('create project → suite → test case', async ({ page }) => {
  // Login
  await login(page);
  
  // Crear proyecto
  await page.click('[data-testid=new-project]');
  await page.fill('[name=name]', 'Test Project');
  await page.click('button[type=submit]');
  await expect(page.locator('text=Test Project')).toBeVisible();
  
  // Crear suite
  await page.click('[data-testid=new-suite]');
  await page.fill('[name=name]', 'Test Suite');
  await page.click('button[type=submit]');
  await expect(page.locator('text=Test Suite')).toBeVisible();
  
  // Crear test case
  await page.click('[data-testid=new-test]');
  await page.fill('[name=name]', 'Test Case 1');
  await page.fill('[name=code]', 'assert True');
  await page.click('button[type=submit]');
  await expect(page.locator('text=Test Case 1')).toBeVisible();
});
```

### 5.3 Execution Flow (execution.spec.ts)
```typescript
test('execute test and view results', async ({ page }) => {
  await login(page);
  await createTestSuite(page);
  
  // Ejecutar
  await page.click('[data-testid=run-suite]');
  
  // Esperar resultados
  await expect(page.locator('[data-testid=execution-status]')).toHaveText('completed', { timeout: 30000 });
  
  // Verificar métricas
  const passed = await page.locator('[data-testid=passed-count]').textContent();
  expect(parseInt(passed!)).toBeGreaterThan(0);
});
```

### 5.4 Billing Flow (billing.spec.ts)
```typescript
test('checkout flow with Stripe test card', async ({ page }) => {
  await login(page);
  
  // Navegar a planes
  await page.click('[data-testid=billing]');
  
  // Seleccionar plan
  await page.click('[data-testid=plan-pro]');
  
  // Completar checkout (Stripe test card)
  await page.fill('[name=cardNumber]', '4242424242424242');
  await page.fill('[name=exp]', '12/28');
  await page.fill('[name=cvc]', '123');
  await page.click('button[type=submit]');
  
  // Verificar upgrade
  await expect(page.locator('[data-testid=plan-badge]')).toHaveText('Pro');
});
```

### 5.5 Export Flow (export.spec.ts)
```typescript
test('export results to JSON', async ({ page }) => {
  await login(page);
  await executeTests(page);
  
  // Exportar
  const [download] = await Promise.all([
    page.waitForEvent('download'),
    page.click('[data-testid=export-json]')
  ]);
  
  // Verificar archivo
  expect(download.suggestedFilename()).toContain('results');
});
```

---

## 6. Configuración Adicional

### 6.1 Screenshot/Video en Fallos
```typescript
// playwright.config.ts
export default defineConfig({
  use: {
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    trace: 'retain-on-failure',
  },
});
```

### 6.2 CI/CD Mejoras
```yaml
# .github/workflows/ci-cd.yml
- name: Run E2E tests
  run: npx playwright test
  
- name: Upload artifacts on failure
  if: failure()
  uses: actions/upload-artifact@v3
  with:
    name: playwright-failures
    path: |
      test-results/
      playwright-report/
```

---

## 7. Tasks Breakdown

### Fase 1: Setup (1h)
- [ ] Configurar screenshot/video en fallos
- [ ] Crear fixtures para datos de prueba
- [ ] Verificar entorno de test

### Fase 2: Auth Tests (1h)
- [ ] Mejorar test de registro
- [ ] Mejorar test de login
- [ ] Añadir test de logout

### Fase 3: Project Management Tests (2h)
- [ ] Test crear proyecto
- [ ] Test crear suite
- [ ] Test crear test case
- [ ] Test flujo completo

### Fase 4: Execution Tests (1h)
- [ ] Test ejecutar suite
- [ ] Test ver resultados
- [ ] Test métricas

### Fase 5: Billing Tests (1h)
- [ ] Test navegación planes
- [ ] Test checkout Stripe
- [ ] Test verificación upgrade

### Fase 6: Export Tests (30min)
- [ ] Test export JSON
- [ ] Test export CSV

### Fase 7: CI/CD (30min)
- [ ] Actualizar GitHub Actions
- [ ] Añadir artifact upload
- [ ] Verificar en CI

---

## 8. Riesgos

| Riesgo | Mitigación |
|--------|------------|
| Stripe requiere API key | Usar Stripe test mode con tarjetas mock |
| Tests flaky por timing | Timeouts generosos, waitForLoadState |
| Frontend no tiene todos los data-testid | Añadir selectores necesarios |
| DB state entre tests | Usar beforeEach para cleanup |

---

## 9. DoD

- [ ] 5 flujos E2E implementados
- [ ] Todos los tests pasando
- [ ] Screenshot/video en fallos configurado
- [ ] CI/CD actualizado con artifacts
- [ ] Coverage >90% de flujos críticos

---

## 10. Próximos Pasos

1. **Aprobar diseño** (Alfred/main)
2. Pasar a `coder-writing-plans` para plan detallado
3. Implementar siguiendo `coder-tdd`

---

**PENDIENTE:** Aprobación del diseño.
