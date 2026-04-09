import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright configuration for FinAlly E2E tests.
 *
 * The app is expected to be running on http://localhost:8000 before tests start.
 * When run via docker-compose.test.yml, the app container starts first and
 * Playwright waits for it to be healthy before executing tests.
 */
export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: [['list'], ['html', { open: 'never' }]],

  use: {
    baseURL: process.env.BASE_URL || 'http://localhost:8000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],

  /* Wait for the app to be available before running tests */
  webServer: process.env.SKIP_WEB_SERVER
    ? undefined
    : {
        command: 'echo "Waiting for app..." && curl --retry 30 --retry-delay 2 --retry-connrefused -s http://localhost:8000/api/health > /dev/null',
        url: 'http://localhost:8000/api/health',
        reuseExistingServer: true,
        timeout: 120_000,
      },
});
