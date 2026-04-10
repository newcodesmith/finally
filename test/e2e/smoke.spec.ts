import { test, expect } from '@playwright/test';

test.describe('Smoke Test', () => {
  test('page loads with correct title', async ({ page }) => {
    await page.goto('/');
    await expect(page).toHaveTitle(/FinAlly/i);
  });

  test('header displays app name and cash balance', async ({ page }) => {
    await page.goto('/');
    // Header shows "FinAlly" branding
    await expect(page.locator('header').getByText('FinAlly')).toBeVisible({ timeout: 15000 });
    // Header shows "Cash" label with default $10,000 balance
    await expect(page.locator('header').getByText('Cash')).toBeVisible();
    await expect(page.locator('header').getByText(/10,000/).first()).toBeVisible({ timeout: 15000 });
  });

  test('default watchlist tickers are visible', async ({ page }) => {
    await page.goto('/');
    // Wait for SSE to deliver prices and tickers to appear in the watchlist sidebar
    const watchlist = page.locator('[data-testid="watchlist"]');
    await expect(watchlist.getByText('AAPL')).toBeVisible({ timeout: 15000 });
    await expect(watchlist.getByText('MSFT')).toBeVisible();
    await expect(watchlist.getByText('GOOGL')).toBeVisible();
  });

  test('prices are streaming with numeric values', async ({ page }) => {
    await page.goto('/');
    // Wait for at least one ticker to appear
    const watchlist = page.locator('[data-testid="watchlist"]');
    await expect(watchlist.getByText('AAPL')).toBeVisible({ timeout: 15000 });
    // Prices should display as dollar amounts (e.g., $190.45)
    // The formatPrice function outputs "$X,XXX.XX" or "$XXX.XX" format
    await expect(page.locator('text=/\\$\\d+\\.\\d{2}/').first()).toBeVisible({ timeout: 15000 });
  });

  test('watchlist panel header is visible', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByText('Watchlist')).toBeVisible({ timeout: 15000 });
  });
});
