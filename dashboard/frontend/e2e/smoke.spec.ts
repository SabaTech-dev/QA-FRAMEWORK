import { test, expect } from "@playwright/test";

/**
 * Regression smoke suite (card 4eb58505, from QA's PR #212 local smoke).
 * Runs against whatever target playwright.config resolves: the Coolify
 * preview of the PR in CI (E2E_BASE_URL), the self-hosted prod on main
 * pushes, or a local `vite preview` build otherwise. Relative URLs only.
 * Catches runtime breakage of the majors migration in a real browser:
 * uncaught exceptions, broken public routes, broken auth redirect.
 */
test.describe("Smoke regression (post-migration)", () => {
  test("Landing renders with content", async ({ page }) => {
    const errors: string[] = [];
    page.on("pageerror", (e) => errors.push(String(e)));
    await page.goto("/");
    await expect(page.locator("body")).toBeVisible();
    await expect(
      page.locator('main, [role="main"], h1, h2').first(),
    ).toBeVisible();
    expect(errors, `uncaught JS errors on /: ${errors.join(" | ")}`).toEqual(
      [],
    );
  });

  test("Login renders form (2 inputs + submit)", async ({ page }) => {
    const errors: string[] = [];
    page.on("pageerror", (e) => errors.push(String(e)));
    await page.goto("/login");
    await expect(page.locator("input").first()).toBeVisible();
    const inputs = page.locator("input");
    expect(await inputs.count()).toBeGreaterThanOrEqual(2);
    await expect(
      page
        .locator(
          'button[type="submit"], button:has-text("Login"), button:has-text("Sign")',
        )
        .first(),
    ).toBeVisible();
    expect(
      errors,
      `uncaught JS errors on /login: ${errors.join(" | ")}`,
    ).toEqual([]);
  });

  test("Register renders form", async ({ page }) => {
    const errors: string[] = [];
    page.on("pageerror", (e) => errors.push(String(e)));
    await page.goto("/register");
    await expect(page.locator("input").first()).toBeVisible();
    expect(await page.locator("input").count()).toBeGreaterThanOrEqual(2);
    expect(
      errors,
      `uncaught JS errors on /register: ${errors.join(" | ")}`,
    ).toEqual([]);
  });

  test("Unauthenticated /dashboard redirects to /login (RR7)", async ({
    page,
  }) => {
    await page.goto("/dashboard");
    await page.waitForURL(/\/login/, { timeout: 10_000 });
    expect(page.url()).toContain("/login");
  });

  test("No 404/500 on unknown route (NotFound page)", async ({ page }) => {
    const errors: string[] = [];
    page.on("pageerror", (e) => errors.push(String(e)));
    const resp = await page.goto("/definitely-not-a-route");
    expect(resp?.status()).toBeLessThan(500);
    expect(errors).toEqual([]);
  });

  // Visual evidence for the codemod that removed margin="normal" from
  // TextField (PR #212, reviewer 9a74c5b6): full-page screenshots are
  // uploaded as CI artifacts from every run.
  test("Visual spot-check: Login & Register screenshots", async ({ page }) => {
    await page.goto("/login");
    await expect(page.locator("input").first()).toBeVisible();
    await page.screenshot({
      path: "test-results/spotcheck-login.png",
      fullPage: true,
    });

    await page.goto("/register");
    await expect(page.locator("input").first()).toBeVisible();
    await page.screenshot({
      path: "test-results/spotcheck-register.png",
      fullPage: true,
    });
  });
});
