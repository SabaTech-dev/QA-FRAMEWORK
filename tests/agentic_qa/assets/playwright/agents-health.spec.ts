/**
 * Playwright Test Agents spec — QA-FRAMEWORK endpoints (PoC Fase 1).
 *
 * Usa API requests de Playwright (no requiere navegador/UI pesada) contra
 * los endpoints objetivo del backend FastAPI:
 *   - GET /health/live   (smoke, siempre disponible)
 *   - GET /api/v1/suites (CRUD real; admite 200 autenticado o 401 sin auth)
 *
 * Ejecución:
 *   npx playwright test tests/agentic_qa/assets/playwright/agents-health.spec.ts \
 *     --base-url=http://localhost:8000 --reporter=list
 *
 * Este spec es generado/manual pero debe ser auto-reparable por el
 * Playwright Healer Agent ante cambios del DOM/API.
 */
import { test, expect } from '@playwright/test';

test.describe('QA-FRAMEWORK endpoints (PoC agéntico)', () => {
  test('GET /health/live responde status "alive"', async ({ request }) => {
    const res = await request.get('/health/live');
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body.status).toBe('alive');
  });

  test('GET /api/v1/suites responde 200 (auth) o 401 (sin auth)', async ({ request }) => {
    const res = await request.get('/api/v1/suites?skip=0&limit=5');
    expect([200, 401]).toContain(res.status());
  });

  test('GET /health/live responde en menos de 2s', async ({ request }) => {
    const start = Date.now();
    const res = await request.get('/health/live');
    const elapsed = Date.now() - start;
    expect(res.status()).toBe(200);
    expect(elapsed).toBeLessThan(2000);
  });
});
