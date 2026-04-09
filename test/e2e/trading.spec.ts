import { test, expect } from '@playwright/test';

test.describe('Trading', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    // Wait for prices to be streaming so trades can execute
    await expect(page.getByText('Live')).toBeVisible({ timeout: 15_000 });
    // Wait for initial data to load
    await expect(page.getByText('$10,000.00').first()).toBeVisible({ timeout: 10_000 });
  });

  test('buy shares — cash decreases and position appears', async ({ page }) => {
    // Fill in the trade bar
    const tickerInput = page.locator('input[placeholder="AAPL"]');
    const qtyInput = page.locator('input[placeholder="Qty"]');
    const buyButton = page.locator('button:has-text("Buy")');

    await tickerInput.fill('AAPL');
    await qtyInput.fill('5');
    await buyButton.click();

    // Wait for success message
    await expect(page.getByText(/BUY 5 AAPL/)).toBeVisible({ timeout: 10_000 });

    // Cash should decrease from $10,000
    // Wait for portfolio to refresh — cash should no longer be $10,000.00
    await page.waitForTimeout(2000);
    const cashText = await page.locator('header').getByText(/\$[\d,]+\.\d{2}/).nth(1).textContent();
    expect(cashText).not.toBe('$10,000.00');

    // Position should appear in the positions table
    await expect(page.locator('table').getByText('AAPL')).toBeVisible({ timeout: 10_000 });

    // "No open positions" should be gone
    await expect(page.getByText('No open positions')).not.toBeVisible();
  });

  test('sell shares — cash increases and position quantity decreases', async ({ page }) => {
    // First buy some shares
    const tickerInput = page.locator('input[placeholder="AAPL"]');
    const qtyInput = page.locator('input[placeholder="Qty"]');
    const buyButton = page.locator('button:has-text("Buy")');
    const sellButton = page.locator('button:has-text("Sell")');

    await tickerInput.fill('AAPL');
    await qtyInput.fill('10');
    await buyButton.click();
    await expect(page.getByText(/BUY 10 AAPL/)).toBeVisible({ timeout: 10_000 });

    // Wait for portfolio refresh
    await page.waitForTimeout(2000);

    // Now sell 3 shares
    await tickerInput.fill('AAPL');
    await qtyInput.fill('3');
    await sellButton.click();
    await expect(page.getByText(/SELL 3 AAPL/)).toBeVisible({ timeout: 10_000 });

    // Wait for refresh and check position still exists with reduced quantity
    await page.waitForTimeout(2000);
    const positionsTable = page.locator('table');
    await expect(positionsTable.getByText('AAPL')).toBeVisible();

    // The quantity cell should show 7 (10 bought - 3 sold)
    const aaplRow = positionsTable.locator('tr').filter({ hasText: 'AAPL' });
    await expect(aaplRow.locator('td').nth(1)).toContainText('7');
  });

  test('sell all shares — position disappears', async ({ page }) => {
    const tickerInput = page.locator('input[placeholder="AAPL"]');
    const qtyInput = page.locator('input[placeholder="Qty"]');
    const buyButton = page.locator('button:has-text("Buy")');
    const sellButton = page.locator('button:has-text("Sell")');

    // Buy 5 shares
    await tickerInput.fill('AAPL');
    await qtyInput.fill('5');
    await buyButton.click();
    await expect(page.getByText(/BUY 5 AAPL/)).toBeVisible({ timeout: 10_000 });
    await page.waitForTimeout(2000);

    // Sell all 5 shares
    await tickerInput.fill('AAPL');
    await qtyInput.fill('5');
    await sellButton.click();
    await expect(page.getByText(/SELL 5 AAPL/)).toBeVisible({ timeout: 10_000 });
    await page.waitForTimeout(2000);

    // Position should be gone, back to "No open positions"
    await expect(page.getByText('No open positions')).toBeVisible({ timeout: 10_000 });
  });

  test('insufficient cash — error shown', async ({ page }) => {
    // Try to buy a huge quantity that would exceed $10,000 cash
    const tickerInput = page.locator('input[placeholder="AAPL"]');
    const qtyInput = page.locator('input[placeholder="Qty"]');
    const buyButton = page.locator('button:has-text("Buy")');

    await tickerInput.fill('AAPL');
    await qtyInput.fill('10000');
    await buyButton.click();

    // Should see an error message about insufficient cash/funds
    await expect(page.getByText(/insufficient|not enough|cannot afford/i)).toBeVisible({ timeout: 10_000 });
  });

  test('insufficient shares — error shown when selling more than owned', async ({ page }) => {
    // Try to sell AAPL without owning any
    const tickerInput = page.locator('input[placeholder="AAPL"]');
    const qtyInput = page.locator('input[placeholder="Qty"]');
    const sellButton = page.locator('button:has-text("Sell")');

    await tickerInput.fill('AAPL');
    await qtyInput.fill('1');
    await sellButton.click();

    // Should see an error about insufficient shares or no position
    await expect(page.getByText(/insufficient|not enough|no position|don't own/i)).toBeVisible({ timeout: 10_000 });
  });

  test('ticker not in watchlist — error shown', async ({ page }) => {
    const tickerInput = page.locator('input[placeholder="AAPL"]');
    const qtyInput = page.locator('input[placeholder="Qty"]');
    const buyButton = page.locator('button:has-text("Buy")');

    await tickerInput.fill('ZZZZZ');
    await qtyInput.fill('1');
    await buyButton.click();

    // Frontend validates ticker is in watchlist before submitting
    await expect(page.getByText(/not in watchlist/i)).toBeVisible({ timeout: 5_000 });
  });

  test('empty ticker or quantity shows validation error', async ({ page }) => {
    const buyButton = page.locator('button:has-text("Buy")');

    // Click buy with empty fields
    await buyButton.click();

    // Should show validation message
    await expect(page.getByText(/enter a ticker/i)).toBeVisible({ timeout: 5_000 });
  });
});
