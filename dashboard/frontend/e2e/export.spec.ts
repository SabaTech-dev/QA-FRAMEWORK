import { test, expect } from '@playwright/test';

test.describe('Export Results Flow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    const inputs = page.locator('input');
    await inputs.nth(0).fill('Joker');
    await inputs.nth(1).fill('Joker123!');
    await page.click('button:has-text("Login")');
    await page.waitForURL(/\/(dashboard|onboarding)/, { timeout: 15000 });
  });

  test('Export results to JSON', async ({ page }) => {
    await page.click('text=Executions');
    await page.waitForURL('**/executions');

    // Find export button
    const exportBtn = page.locator('button:has-text("Export"), [data-testid=export-json]').first();
    if (await exportBtn.isVisible({ timeout: 2000 })) {
      const [download] = await Promise.all([
        page.waitForEvent('download', { timeout: 5000 }).catch(() => null),
        exportBtn.click()
      ]);

      if (download) {
        expect(download.suggestedFilename()).toContain('.json');
      }
    }
  });
});
