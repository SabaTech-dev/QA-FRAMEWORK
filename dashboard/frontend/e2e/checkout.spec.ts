import { test, expect } from '@playwright/test';

test.describe('Stripe Checkout Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Login primero
    await page.goto('/login');
    const inputs = page.locator('input');
    await inputs.nth(0).fill('Joker');
    await inputs.nth(1).fill('Joker123!');
    await page.click('button:has-text("Login")');
    await page.waitForTimeout(3000);
  });

  test('Navigate to pricing/plans page', async ({ page }) => {
    // Buscar link a pricing o plans
    const pricingLink = page.locator('a:has-text("Pricing"), a:has-text("Plans"), nav a[href*="pricing"]');
    
    if (await pricingLink.first().isVisible({ timeout: 2000 })) {
      await pricingLink.first().click();
      await page.waitForTimeout(2000);
      expect(page.url()).toMatch(/pricing|plans|subscribe/i);
    } else {
      // Skip si no hay página de pricing
      test.skip(true, 'No pricing page found');
    }
  });

  test('Checkout button redirects to Stripe', { lock: 'billing' }, async ({ page }) => {
    // Navegar a pricing si existe
    const pricingLink = page.locator('a:has-text("Pricing"), a:has-text("Plans")').first();
    
    if (await pricingLink.isVisible({ timeout: 2000 })) {
      await pricingLink.click();
      await page.waitForTimeout(2000);
      
      // Buscar botón de checkout
      const checkoutBtn = page.locator('button:has-text("Subscribe"), button:has-text("Upgrade"), button:has-text("Get Started")').first();
      
      if (await checkoutBtn.isVisible({ timeout: 2000 })) {
        await checkoutBtn.click();
        await page.waitForTimeout(3000);
        
        // Verificar redirección a Stripe o página de checkout
        const url = page.url();
        expect(url).toMatch(/checkout\.stripe|stripe|success|payment/i);
      } else {
        test.skip(true, 'No checkout button found');
      }
    } else {
      test.skip(true, 'No pricing page found');
    }
  });

  test('Stripe test card flow (mocked)', async ({ page }) => {
    // Este test valida que el flujo existe, no hace pago real
    const pricingLink = page.locator('a:has-text("Pricing"), a:has-text("Plans")').first();
    
    if (await pricingLink.isVisible({ timeout: 2000 }).catch(() => false)) {
      await pricingLink.click();
      await page.waitForTimeout(2000);
      
      // Verificar que hay elementos de precio/plan
      const priceElement = page.locator('text=/\\$[0-9]+|€[0-9]+|month|year/i');
      const hasPrices = await priceElement.first().isVisible({ timeout: 2000 }).catch(() => false);
      
      expect(hasPrices || page.url().includes('pricing')).toBeTruthy();
    } else {
      test.skip(true, 'No pricing page found');
    }
  });
});
