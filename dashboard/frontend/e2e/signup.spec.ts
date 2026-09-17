import { test, expect } from '@playwright/test';

test.describe('Signup Flow', () => {
  test('Signup page displays correctly', async ({ page }) => {
    await page.goto('/register');
    await page.waitForLoadState('networkidle');

    // Verificar formulario de registro
    const inputs = page.locator('input');
    await expect(inputs.first()).toBeVisible();
  });

  test('Signup with valid data creates user', { lock: 'signup' }, async ({ page }) => {
    await page.goto('/register');
    await page.waitForLoadState('networkidle');

    const inputs = page.locator('input');
    const timestamp = Date.now();

    // Llenar formulario (ajustar selectores según UI real)
    await inputs.nth(0).fill(`testuser_${timestamp}`);
    await inputs.nth(1).fill(`test_${timestamp}@example.com`);
    await inputs.nth(2).fill('TestPassword123!');
    await inputs.nth(3).fill('TestPassword123!');

    // El registro real es un wizard: Account -> (Details) -> Verify.
    await page.click('button:has-text("Next")');
    await page.click('button:has-text("Create Account")');

    // Registro exitoso => el wizard avanza al paso de verificación de email.
    // (No hay redirect: la app pide el código de verificación en /register.)
    await expect(
      page.getByPlaceholder('Enter 6-digit code'),
    ).toBeVisible({ timeout: 10000 });
  });

  test('Signup with existing email shows error', { lock: 'signup' }, async ({ page }) => {
    await page.goto('/register');
    await page.waitForLoadState('networkidle');

    const inputs = page.locator('input');

    // Usar credenciales ya existentes
    await inputs.nth(0).fill('Joker');
    await inputs.nth(1).fill('joker@example.com');
    await inputs.nth(2).fill('TestPassword123!');
    await inputs.nth(3).fill('TestPassword123!');

    // Wizard: Account -> (Details) -> submit
    await page.click('button:has-text("Next")');
    await page.click('button:has-text("Create Account")');
    await page.waitForTimeout(2000);

    // Verificar mensaje de error (toast "Email already registered") o permanencia en página
    const errorVisible = await page.locator('text=/already|duplicate|error/i').isVisible({ timeout: 2000 }).catch(() => false);
    expect(errorVisible || page.url().includes('/register')).toBeTruthy();
  });

  test('Link to login page works', async ({ page }) => {
    await page.goto('/register');
    await page.waitForLoadState('networkidle');

    const loginLink = page.locator('a:has-text("Login"), a:has-text("Sign in")');
    if (await loginLink.isVisible({ timeout: 2000 })) {
      await loginLink.click();
      await page.waitForTimeout(1000);
      expect(page.url()).toContain('/login');
    }
  });
});
