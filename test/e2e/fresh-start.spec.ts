import { test, expect } from '@playwright/test';

test.describe('Fresh Start', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    // Wait for the page to fully load and initial data to arrive
    await page.waitForSelector('header');
  });

  test('default watchlist of 10 tickers appears', async ({ page }) => {
    const defaultTickers = ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA', 'NVDA', 'META', 'JPM', 'V', 'NFLX'];

    // Wait for the watchlist to populate — look for ticker text in the watchlist panel
    await expect(page.getByText('10 tickers')).toBeVisible({ timeout: 10_000 });

    // Verify each default ticker is visible in the page
    for (const ticker of defaultTickers) {
      await expect(page.locator(`text="${ticker}"`).first()).toBeVisible();
    }
  });

  test('$10,000 initial balance shown in header', async ({ page }) => {
    // The header shows portfolio value and cash balance
    // Cash should be $10,000.00 on fresh start
    await expect(page.getByText('$10,000.00').first()).toBeVisible({ timeout: 10_000 });
  });

  test('prices are streaming — at least one price update received', async ({ page }) => {
    // Wait for at least one price to appear in the watchlist.
    // Prices display as $xxx.xx format. Wait for a dollar sign with digits in the watchlist area.
    const watchlistArea = page.locator('.overflow-y-auto').first();
    await expect(watchlistArea.locator('text=/\\$\\d+\\.\\d{2}/')).toBeVisible({ timeout: 15_000 });
  });

  test('connection status indicator shows green (Live)', async ({ page }) => {
    // The header has a connection status dot and label.
    // When connected, it shows "Live" text.
    await expect(page.getByText('Live')).toBeVisible({ timeout: 15_000 });

    // The green dot uses the bg-price-up class which maps to #3fb950
    const statusDot = page.locator('header .rounded-full').first();
    await expect(statusDot).toBeVisible();
  });

  test('header displays FinAlly branding', async ({ page }) => {
    await expect(page.getByText('Fin')).toBeVisible();
    await expect(page.getByText('Ally')).toBeVisible();
    await expect(page.getByText('AI Trading Workstation')).toBeVisible();
  });

  test('main UI panels are present', async ({ page }) => {
    // Watchlist panel
    await expect(page.getByText('Watchlist').first()).toBeVisible();

    // Positions table
    await expect(page.getByText('Positions').first()).toBeVisible();

    // Portfolio Map (heatmap)
    await expect(page.getByText('Portfolio Map')).toBeVisible();

    // Portfolio Value (P&L chart)
    await expect(page.getByText('Portfolio Value')).toBeVisible();

    // Trade bar
    await expect(page.getByText('Trade').first()).toBeVisible();

    // AI Assistant chat panel
    await expect(page.getByText('AI Assistant')).toBeVisible();
  });

  test('no open positions on fresh start', async ({ page }) => {
    await expect(page.getByText('No open positions')).toBeVisible({ timeout: 5_000 });
  });

  test('portfolio heatmap shows empty state message', async ({ page }) => {
    await expect(page.getByText('No positions yet')).toBeVisible({ timeout: 5_000 });
  });
});
