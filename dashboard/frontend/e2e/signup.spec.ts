import { test, expect } from '@playwright/test';

test.describe('Signup Flow', () => {
  test('Signup page displays correctly', async ({ page }) => {
    await page.goto('/signup');
    await page.waitForLoadState('networkidle');
    
    // Verificar formulario de registro
    const inputs = page.locator('input');
    await expect(inputs.first()).toBeVisible();
  });

  test('Signup with valid data creates user', { lock: 'signup' }, async ({ page }) => {
    await page.goto('/signup');
    await page.waitForLoadState('networkidle');
    
    const inputs = page.locator('input');
    const timestamp = Date.now();
    
    // Llenar formulario (ajustar selectores según UI real)
    await inputs.nth(0).fill(`testuser_${timestamp}`);
    await inputs.nth(1).fill(`test_${timestamp}@example.com`);
    await inputs.nth(2).fill('TestPassword123!');
    
    await page.click('button:has-text("Sign up"), button:has-text("Register"), button[type="submit"]');
    await page.waitForTimeout(3000);
    
    // Verificar redirección o mensaje de éxito
    const url = page.url();
    expect(url).not.toContain('/signup');
  });

  test('Signup with existing email shows error', { lock: 'signup' }, async ({ page }) => {
    await page.goto('/signup');
    await page.waitForLoadState('networkidle');
    
    const inputs = page.locator('input');
    
    // Usar credenciales ya existentes
    await inputs.nth(0).fill('Joker');
    await inputs.nth(1).fill('joker@example.com');
    await inputs.nth(2).fill('TestPassword123!');
    
    await page.click('button:has-text("Sign up"), button:has-text("Register"), button[type="submit"]');
    await page.waitForTimeout(2000);
    
    // Verificar mensaje de error o permanencia en página
    const errorVisible = await page.locator('text=/already exists|duplicate|error/i').isVisible({ timeout: 2000 }).catch(() => false);
    expect(errorVisible || page.url().includes('/signup')).toBeTruthy();
  });

  test('Link to login page works', async ({ page }) => {
    await page.goto('/signup');
    await page.waitForLoadState('networkidle');
    
    const loginLink = page.locator('a:has-text("Login"), a:has-text("Sign in")');
    if (await loginLink.isVisible({ timeout: 2000 })) {
      await loginLink.click();
      await page.waitForTimeout(1000);
      expect(page.url()).toContain('/login');
    }
  });
});
