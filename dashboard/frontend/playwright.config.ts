import { defineConfig, devices } from "@playwright/test";

// Card 4eb58505: E2E targets are env-driven — zero hardcoded external stacks.
//   - CI (PR): pr-deploy-coolify.yml injects E2E_BASE_URL pointing at the
//     Coolify preview deployed from the PR itself.
//   - CI (push to main): e2e.yml `e2e-prod-smoke` injects the self-hosted
//     prod stack URLs.
//   - Local / GitHub-hosted smoke: no env -> build + serve `vite preview`
//     and test this working tree, self-contained.
const E2E_BASE_URL = process.env.E2E_BASE_URL;

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: "html",
  use: {
    baseURL: E2E_BASE_URL ?? "http://localhost:4173",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    // no `video`: requires the ffmpeg playwright binary — not worth the CI
    // dependency for this suite (screenshots + trace carry the evidence).
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: E2E_BASE_URL
    ? undefined
    : {
        command: "npm run build && npm run preview -- --port 4173 --strictPort",
        url: "http://localhost:4173",
        reuseExistingServer: !process.env.CI,
        timeout: 180_000,
      },
});
