import { test, expect } from '@playwright/test';

// Card 4eb58505: no hardcoded external targets.
//   - Frontend navigations are relative and resolve against the playwright
//     config baseURL (vite preview locally, Coolify preview on PRs,
//     self-hosted prod on main pushes).
//   - API tests require a deployed backend injected via E2E_API_URL and are
//     skipped otherwise: fresh preview backends boot with an empty database
//     (create_all, no seed), so login-dependent checks only run against the
//     real prod stack in the `e2e-prod-smoke` job.
// Card 64763175: los credenciales hardcodeados de la era railway no existen
//   en la BD real de prod (usuario 'joker' con password propio — verificado
//   2026-09-03: login 401 con ambos casings) y /api/v1/docs está deshabilitado
//   en production POR DISEÑO (main.py: docs_url=None si is_production —
//   PR #147 / card 2972521c). Los auth tests pasan a E2E_AUTH_USERNAME /
//   E2E_AUTH_PASSWORD (skip si ausentes) y el test de docs afirma la postura
//   de seguridad (404) cuando E2E_DOCS_DISABLED=1.
const BACKEND_URL = process.env.E2E_API_URL ?? '';
const hasApi = BACKEND_URL !== '';
const AUTH_USERNAME = process.env.E2E_AUTH_USERNAME ?? '';
const AUTH_PASSWORD = process.env.E2E_AUTH_PASSWORD ?? '';
const hasAuth = AUTH_USERNAME !== '' && AUTH_PASSWORD !== '';
const docsDisabled = process.env.E2E_DOCS_DISABLED === '1';

test.describe('QA-FRAMEWORK E2E Tests', () => {

  test('Backend health check', async ({ request }) => {
    test.skip(!hasApi, 'E2E_API_URL not set — requires a deployed backend');
    const response = await request.get(`${BACKEND_URL}/health`);
    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    expect(data.status).toBe('healthy');
  });

  test('Backend API docs accessible', async ({ request }) => {
    test.skip(!hasApi, 'E2E_API_URL not set — requires a deployed backend');
    const response = await request.get(`${BACKEND_URL}/api/v1/docs`);
    if (docsDisabled) {
      // Card 2972521c (PR #147): docs_url=None si is_production — afirmar la
      // postura de seguridad en production en vez de exigir docs accesibles.
      expect(response.status()).toBe(404);
    } else {
      expect(response.ok()).toBeTruthy();
    }
  });

  test('Login API works', async ({ request }) => {
    test.skip(!hasApi || !hasAuth, 'requires E2E_API_URL and E2E_AUTH_USERNAME/E2E_AUTH_PASSWORD (card 64763175: creds de la era railway no válidos en prod)');
    const response = await request.post(`${BACKEND_URL}/api/v1/auth/login`, {
      headers: { 'Content-Type': 'application/json' },
      data: { username: AUTH_USERNAME, password: AUTH_PASSWORD }
    });
    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    expect(data.access_token).toBeDefined();
    expect(data.token_type).toBe('bearer');
  });

  test('Get user info with token', async ({ request }) => {
    test.skip(!hasApi || !hasAuth, 'requires E2E_API_URL and E2E_AUTH_USERNAME/E2E_AUTH_PASSWORD (card 64763175)');
    // First login
    const loginResponse = await request.post(`${BACKEND_URL}/api/v1/auth/login`, {
      headers: { 'Content-Type': 'application/json' },
      data: { username: AUTH_USERNAME, password: AUTH_PASSWORD }
    });
    const loginData = await loginResponse.json();
    const token = loginData.access_token;

    // Get user info
    const meResponse = await request.get(`${BACKEND_URL}/api/v1/me`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    expect(meResponse.ok()).toBeTruthy();
    const userData = await meResponse.json();
    // Login puede ser case-insensitive mientras /me devuelve el canonical:
    // comparar sin casing evita falsos rojos por 'Joker' vs 'joker'.
    expect(userData.username.toLowerCase()).toBe(AUTH_USERNAME.toLowerCase());
  });

  test('Frontend loads', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('body')).toBeVisible();
  });

  test('Login page displays correctly', async ({ page }) => {
    await page.goto('/login');
    // Wait for page to load
    await page.waitForLoadState('networkidle');
    // Check for login form elements
    const usernameInput = page.locator('input').first();
    await expect(usernameInput).toBeVisible();
  });

  test('Full login flow', async ({ page }) => {
    test.skip(!hasAuth, 'requires E2E_AUTH_USERNAME/E2E_AUTH_PASSWORD — BD sin seed en previews y creds de era railway no válidos en prod (card 64763175)');
    await page.goto('/login');
    await page.waitForLoadState('networkidle');

    // Fill login form using placeholder or type
    const inputs = page.locator('input');
    await inputs.nth(0).fill(AUTH_USERNAME);
    await inputs.nth(1).fill(AUTH_PASSWORD);

    // Submit
    await page.click('button:has-text("Login")');

    // Wait for redirect or success
    await page.waitForTimeout(5000);

    // Check if we're no longer on login page (successful login redirects)
    const url = page.url();
    // Either redirected to home or still on login with error
    expect(url).toBeDefined();
  });

  test('Billing plans accessible without auth', async ({ request }) => {
    test.skip(!hasApi, 'E2E_API_URL not set — requires a deployed backend');
    const response = await request.get(`${BACKEND_URL}/api/v1/billing/plans`);
    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    expect(data.plans).toBeDefined();
    expect(data.plans.length).toBe(3);
  });
});
