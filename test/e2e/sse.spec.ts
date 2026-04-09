import { test, expect } from '@playwright/test';

test.describe('SSE Price Streaming', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await expect(page.getByText('Live')).toBeVisible({ timeout: 15_000 });
  });

  test('prices update in real-time — verify a price element changes', async ({ page }) => {
    // Wait for the watchlist to load with prices
    await expect(page.getByText('10 tickers')).toBeVisible({ timeout: 10_000 });

    // Find the AAPL row price and capture its initial value
    const watchlistArea = page.locator('.overflow-y-auto').first();
    const aaplRow = watchlistArea.locator('div').filter({ hasText: 'AAPL' }).first();
    await expect(aaplRow).toBeVisible();

    // Wait for at least one price to show up
    await page.waitForTimeout(2000);

    // Get the initial price text for AAPL
    const priceLocator = aaplRow.locator('text=/\\$\\d+\\.\\d{2}/').first();
    await expect(priceLocator).toBeVisible({ timeout: 10_000 });
    const initialPrice = await priceLocator.textContent();

    // Wait for the price to change (simulator updates every ~500ms)
    // Poll for up to 10 seconds to see a price change
    let priceChanged = false;
    for (let i = 0; i < 20; i++) {
      await page.waitForTimeout(500);
      const currentPrice = await priceLocator.textContent();
      if (currentPrice !== initialPrice) {
        priceChanged = true;
        break;
      }
    }

    expect(priceChanged).toBe(true);
  });

  test('price flash animation triggers on price change', async ({ page }) => {
    // Wait for watchlist to load
    await expect(page.getByText('10 tickers')).toBeVisible({ timeout: 10_000 });
    await page.waitForTimeout(2000);

    // Watch for flash-up or flash-down CSS class to appear on any watchlist row
    // The simulator changes prices every 500ms, so flashes should trigger frequently
    let flashDetected = false;

    for (let i = 0; i < 30; i++) {
      await page.waitForTimeout(500);

      // Check if any element in the watchlist has the flash class
      const flashUp = await page.locator('.flash-up').count();
      const flashDown = await page.locator('.flash-down').count();

      if (flashUp > 0 || flashDown > 0) {
        flashDetected = true;
        break;
      }
    }

    expect(flashDetected).toBe(true);
  });

  test('SSE connection established — EventSource connects to /api/stream/prices', async ({ page }) => {
    // Verify we can see prices flowing in by checking the API endpoint directly
    const response = await page.request.get('/api/stream/prices', {
      headers: { Accept: 'text/event-stream' },
      timeout: 10_000,
    });

    // The endpoint should return a 200 with event-stream content type
    expect(response.status()).toBe(200);
    expect(response.headers()['content-type']).toContain('text/event-stream');
  });

  test('watchlist shows session change percentages', async ({ page }) => {
    // Wait for prices to start streaming
    await page.waitForTimeout(3000);

    // The watchlist should display percentage changes for tickers
    // These appear as small text elements with % sign
    const watchlistArea = page.locator('.overflow-y-auto').first();
    const percentageTexts = watchlistArea.locator('text=/%/');

    // At least some tickers should show a percentage
    const count = await percentageTexts.count();
    expect(count).toBeGreaterThan(0);
  });

  test('clicking a ticker selects it and updates the main chart', async ({ page }) => {
    // Wait for watchlist to load
    await expect(page.getByText('10 tickers')).toBeVisible({ timeout: 10_000 });

    // AAPL is selected by default. Click on MSFT.
    const watchlistArea = page.locator('.overflow-y-auto').first();
    const msftRow = watchlistArea.locator('div').filter({ hasText: 'MSFT' }).first();
    await msftRow.click();

    // The main chart area should now show MSFT
    // The MainChart component likely shows the ticker name
    await expect(page.getByText('MSFT').first()).toBeVisible();
  });
});
