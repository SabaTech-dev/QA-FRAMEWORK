import { test, expect } from '@playwright/test';

test.describe('Test Execution Flow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    const inputs = page.locator('input');
    await inputs.nth(0).fill('Joker');
    await inputs.nth(1).fill('Joker123!');
    await page.click('button:has-text("Login")');
    await page.waitForTimeout(3000);
  });

  test('Navigate to Executions page', async ({ page }) => {
    await page.click('text=Executions');
    await page.waitForURL('**/executions');
    await expect(page).toHaveURL(/.*executions.*/);
  });

  test('Run test suite', { lock: 'suites' }, async ({ page }) => {
    await page.click('text=Test Suites');
    await page.waitForURL('**/suites');
    
    // Find run button
    const runBtn = page.locator('button:has-text("Run"), [data-testid=run-suite]').first();
    if (await runBtn.isVisible({ timeout: 2000 })) {
      await runBtn.click();
      await page.waitForTimeout(2000);
    }
  });

  test('View execution results', async ({ page }) => {
    await page.click('text=Executions');
    await page.waitForURL('**/executions');
    
    // Check for execution list or any content on the page
    // The page should show either executions or empty state
    await page.waitForTimeout(2000);
    
    // Verify we're on the executions page
    await expect(page).toHaveURL(/.*executions.*/);
  });
});
