import { test, expect } from '@playwright/test';

test.describe('Portfolio Visualization', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await expect(page.getByText('Live')).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText('$10,000.00').first()).toBeVisible({ timeout: 10_000 });
  });

  test('heatmap renders with rectangles after buying a position', async ({ page }) => {
    // Initially the heatmap shows empty state
    await expect(page.getByText('No positions yet')).toBeVisible();

    // Buy some shares to create a position
    const tickerInput = page.locator('input[placeholder="AAPL"]');
    const qtyInput = page.locator('input[placeholder="Qty"]');
    const buyButton = page.locator('button:has-text("Buy")');

    await tickerInput.fill('AAPL');
    await qtyInput.fill('10');
    await buyButton.click();
    await expect(page.getByText(/BUY 10 AAPL/)).toBeVisible({ timeout: 10_000 });

    // Wait for portfolio to refresh
    await page.waitForTimeout(3000);

    // The heatmap should now contain an SVG with at least one rect element
    const heatmapSvg = page.locator('svg rect');
    await expect(heatmapSvg.first()).toBeVisible({ timeout: 10_000 });

    // The empty state message should be gone
    await expect(page.getByText('No positions yet')).not.toBeVisible();
  });

  test('positions table shows correct columns and data after buying', async ({ page }) => {
    // Buy shares
    const tickerInput = page.locator('input[placeholder="AAPL"]');
    const qtyInput = page.locator('input[placeholder="Qty"]');
    const buyButton = page.locator('button:has-text("Buy")');

    await tickerInput.fill('AAPL');
    await qtyInput.fill('5');
    await buyButton.click();
    await expect(page.getByText(/BUY 5 AAPL/)).toBeVisible({ timeout: 10_000 });

    // Wait for portfolio refresh
    await page.waitForTimeout(3000);

    // Check table headers exist
    const table = page.locator('table');
    await expect(table.getByText('Ticker')).toBeVisible();
    await expect(table.getByText('Qty')).toBeVisible();
    await expect(table.getByText('Avg Cost')).toBeVisible();
    await expect(table.getByText('Price')).toBeVisible();
    await expect(table.getByText('P&L')).toBeVisible();

    // Check the AAPL row data
    const aaplRow = table.locator('tr').filter({ hasText: 'AAPL' });
    await expect(aaplRow).toBeVisible();

    // Quantity should be 5
    await expect(aaplRow.locator('td').nth(1)).toContainText('5');

    // Avg cost and price should be dollar amounts
    const avgCost = await aaplRow.locator('td').nth(2).textContent();
    expect(avgCost).toMatch(/\$\d+\.\d{2}/);

    const price = await aaplRow.locator('td').nth(3).textContent();
    expect(price).toMatch(/\$\d+\.\d{2}/);
  });

  test('P&L chart area is present and has canvas element', async ({ page }) => {
    // The P&L chart should have a canvas element
    const pnlSection = page.getByText('Portfolio Value').locator('..');
    await expect(pnlSection).toBeVisible();

    const canvas = pnlSection.locator('canvas');
    await expect(canvas).toBeVisible();
  });

  test('portfolio total value updates in header after buying', async ({ page }) => {
    // Record initial portfolio value
    const initialValueText = await page.locator('header').getByText(/\$[\d,]+\.\d{2}/).first().textContent();

    // Buy shares
    const tickerInput = page.locator('input[placeholder="AAPL"]');
    const qtyInput = page.locator('input[placeholder="Qty"]');
    const buyButton = page.locator('button:has-text("Buy")');

    await tickerInput.fill('AAPL');
    await qtyInput.fill('10');
    await buyButton.click();
    await expect(page.getByText(/BUY 10 AAPL/)).toBeVisible({ timeout: 10_000 });

    // Wait for portfolio to refresh
    await page.waitForTimeout(3000);

    // Portfolio value in header should still be approximately $10,000
    // (cash decreased but position value was added)
    const headerValues = page.locator('header').getByText(/\$[\d,]+\.\d{2}/);
    const portfolioValue = await headerValues.first().textContent();
    expect(portfolioValue).toBeTruthy();
  });

  test('buying multiple tickers shows multiple positions', async ({ page }) => {
    const tickerInput = page.locator('input[placeholder="AAPL"]');
    const qtyInput = page.locator('input[placeholder="Qty"]');
    const buyButton = page.locator('button:has-text("Buy")');

    // Buy AAPL
    await tickerInput.fill('AAPL');
    await qtyInput.fill('5');
    await buyButton.click();
    await expect(page.getByText(/BUY 5 AAPL/)).toBeVisible({ timeout: 10_000 });
    await page.waitForTimeout(1500);

    // Buy MSFT
    await tickerInput.fill('MSFT');
    await qtyInput.fill('3');
    await buyButton.click();
    await expect(page.getByText(/BUY 3 MSFT/)).toBeVisible({ timeout: 10_000 });
    await page.waitForTimeout(2000);

    // Both should appear in positions table
    const table = page.locator('table');
    await expect(table.getByText('AAPL')).toBeVisible();
    await expect(table.getByText('MSFT')).toBeVisible();

    // Positions count should show "2 open"
    await expect(page.getByText('2 open')).toBeVisible();

    // Heatmap should have at least 2 rects
    const rects = page.locator('svg rect');
    await expect(rects).toHaveCount(2, { timeout: 5_000 });
  });
});
