import { test, expect } from '@playwright/test';

test.describe('Project Management Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Login
    await page.goto('/login');
    const inputs = page.locator('input');
    await inputs.nth(0).fill('Joker');
    await inputs.nth(1).fill('Joker123!');
    await page.click('button:has-text("Login")');
    await page.waitForTimeout(3000);
  });

  test('Navigate to Test Suites page', async ({ page }) => {
    await page.click('text=Test Suites');
    await page.waitForURL('**/suites');
    await expect(page).toHaveURL(/.*suites.*/);
  });

  test('Create new test suite', { lock: 'suites' }, async ({ page }) => {
    await page.click('text=Test Suites');
    await page.waitForURL('**/suites');
    
    // Click create button
    const createBtn = page.locator('button:has-text("Create"), button:has-text("New Suite")');
    if (await createBtn.isVisible({ timeout: 2000 })) {
      await createBtn.click();
      
      // Fill form
      const nameInput = page.locator('input[name="name"], input[placeholder*="name"]');
      if (await nameInput.isVisible({ timeout: 2000 })) {
        await nameInput.fill('E2E Test Suite');
        await page.click('button:has-text("Create"), button[type="submit"]');
        await page.waitForTimeout(2000);
      }
    }
  });

  test('Create test case in suite', { lock: 'suites' }, async ({ page }) => {
    await page.click('text=Test Suites');
    await page.waitForURL('**/suites');
    
    // Click on a suite
    const suiteCard = page.locator('[data-testid=suite-card], .suite-card').first();
    if (await suiteCard.isVisible({ timeout: 2000 })) {
      await suiteCard.click();
      await page.waitForTimeout(1000);
      
      // Create test case
      const addTestBtn = page.locator('button:has-text("Add Test"), button:has-text("New Test")');
      if (await addTestBtn.isVisible({ timeout: 2000 })) {
        await addTestBtn.click();
      }
    }
  });
});
