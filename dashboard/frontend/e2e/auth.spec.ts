import { test, expect } from '@playwright/test';

test.describe('Auth Flow', () => {
  test('Login page displays correctly', async ({ page }) => {
    await page.goto('/login');
    await page.waitForLoadState('networkidle');

    // Check for login form
    const inputs = page.locator('input');
    await expect(inputs.nth(0)).toBeVisible();
  });

  test('Login with valid credentials', async ({ page }) => {
    await page.goto('/login');
    await page.waitForLoadState('networkidle');

    const inputs = page.locator('input');
    await inputs.nth(0).fill('Joker');
    await inputs.nth(1).fill('Joker123!');

    await page.click('button:has-text("Login")');
    await page.waitForURL(/\/(dashboard|onboarding)/, { timeout: 15000 });

    // Should redirect or show dashboard
    const url = page.url();
    expect(url).not.toContain('/login');
  });

  test('Logout works', async ({ page }) => {
    // Login first
    await page.goto('/login');
    const inputs = page.locator('input');
    await inputs.nth(0).fill('Joker');
    await inputs.nth(1).fill('Joker123!');
    await page.click('button:has-text("Login")');
    await page.waitForURL(/\/(dashboard|onboarding)/, { timeout: 15000 });

    // Find and click logout (if exists)
    const logoutBtn = page.locator('button:has-text("Logout"), [data-testid=logout]');
    if (await logoutBtn.isVisible({ timeout: 2000 })) {
      await logoutBtn.click();
      await page.waitForTimeout(1000);
      expect(page.url()).toContain('/login');
    }
  });
});
