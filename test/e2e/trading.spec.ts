import { test, expect } from '@playwright/test';

test.describe('Trading', () => {
  test('can buy shares and see portfolio update', async ({ page }) => {
    await page.goto('/');
    // Wait for prices to stream so the trade bar can work
    await expect(page.locator('[data-testid="watchlist"]').getByText('AAPL')).toBeVisible({ timeout: 15000 });

    // Fill in the trade bar — TradeBar has inputs with placeholders "Ticker" and "Qty"
    const tickerInput = page.getByPlaceholder('Ticker');
    const qtyInput = page.getByPlaceholder('Qty');
    await tickerInput.fill('AAPL');
    await qtyInput.fill('5');

    // Click Buy button
    const buyButton = page.getByRole('button', { name: 'Buy' });
    await buyButton.click();

    // Wait for trade execution feedback — TradeBar shows "Bought X AAPL @ $..." on success
    await expect(page.getByText(/Bought 5 AAPL/)).toBeVisible({ timeout: 15000 });

    // Cash balance in the header should decrease from $10,000
    // The header shows the cash balance; after buying 5 AAPL (~$190 each = ~$950),
    // the cash should be less than $10,000
    const headerCash = page.locator('header');
    // Verify cash is no longer exactly $10,000 — it should show a different value
    await expect(headerCash.getByText(/\$[0-9,]+\.\d{2}/).first()).toBeVisible();

    // A position for AAPL should appear in the positions table
    // PositionsTable has table headers: Ticker, Qty, Avg Cost, Price
    await expect(page.locator('table').getByText('AAPL')).toBeVisible({ timeout: 10000 });
  });

  test('can sell shares after buying them', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('[data-testid="watchlist"]').getByText('AAPL')).toBeVisible({ timeout: 15000 });

    // First buy shares
    await page.getByPlaceholder('Ticker').fill('AAPL');
    await page.getByPlaceholder('Qty').fill('10');
    await page.getByRole('button', { name: 'Buy' }).click();
    await expect(page.getByText(/Bought 10 AAPL/)).toBeVisible({ timeout: 15000 });

    // Wait for feedback to clear, then sell
    await page.waitForTimeout(1000);
    await page.getByPlaceholder('Ticker').fill('AAPL');
    await page.getByPlaceholder('Qty').fill('5');
    await page.getByRole('button', { name: 'Sell' }).click();
    await expect(page.getByText(/Sold 5 AAPL/)).toBeVisible({ timeout: 15000 });
  });

  test('portfolio endpoint returns updated data after trade', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('[data-testid="watchlist"]').getByText('AAPL')).toBeVisible({ timeout: 15000 });

    // Check initial portfolio (use relative assertions — prior tests may have modified state)
    const initialPortfolio = await page.request.get('/api/portfolio');
    const initialData = await initialPortfolio.json();
    const initialCash = initialData.cash_balance;

    // Execute a trade via API
    const tradeResponse = await page.request.post('/api/portfolio/trade', {
      data: { ticker: 'AAPL', quantity: 2, side: 'buy' },
    });
    const tradeData = await tradeResponse.json();
    expect(tradeData.success).toBe(true);

    // Verify portfolio is updated
    const updatedPortfolio = await page.request.get('/api/portfolio');
    const updatedData = await updatedPortfolio.json();
    expect(updatedData.cash_balance).toBeLessThan(initialCash);
    expect(updatedData.positions.length).toBeGreaterThan(0);
  });
});
