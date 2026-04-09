import { test, expect } from '@playwright/test';

test.describe('Watchlist Management', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    // Wait for watchlist to load
    await expect(page.getByText('10 tickers')).toBeVisible({ timeout: 10_000 });
  });

  test('add a new ticker to the watchlist', async ({ page }) => {
    // Type a new ticker into the add input
    const addInput = page.getByPlaceholder('Add ticker...');
    await addInput.fill('PYPL');
    await addInput.press('Enter');

    // Wait for the ticker count to update to 11
    await expect(page.getByText('11 tickers')).toBeVisible({ timeout: 10_000 });

    // The new ticker should appear in the watchlist
    await expect(page.locator('text="PYPL"').first()).toBeVisible();
  });

  test('remove a ticker from the watchlist', async ({ page }) => {
    // Find a ticker row and click its remove button.
    // NFLX is the last default ticker, let's remove it.
    // Each ticker row has a small "x" button for removal.
    const nflxRow = page.locator('text="NFLX"').first().locator('..');

    // The remove button is a sibling "x" button within the row
    // We need to find the row containing NFLX and then find the remove button
    const tickerRows = page.locator('.overflow-y-auto > div');
    const nflxRowLocator = tickerRows.filter({ hasText: 'NFLX' });

    // Hover to make the remove button visible, then click
    await nflxRowLocator.hover();
    const removeButton = nflxRowLocator.locator('button');
    await removeButton.click();

    // Wait for ticker count to decrease
    await expect(page.getByText('9 tickers')).toBeVisible({ timeout: 10_000 });

    // NFLX should no longer be in the watchlist
    // Use a more specific selector to avoid matching partial text elsewhere
    const watchlistPanel = page.locator('.overflow-y-auto').first();
    await expect(watchlistPanel.locator('text="NFLX"')).not.toBeVisible({ timeout: 5_000 });
  });

  test('duplicate ticker add is handled gracefully', async ({ page }) => {
    // Try to add AAPL which is already in the watchlist
    const addInput = page.getByPlaceholder('Add ticker...');
    await addInput.fill('AAPL');
    await addInput.press('Enter');

    // The ticker count should still be 10 (not 11)
    // Wait a moment for any network request to complete
    await page.waitForTimeout(2000);
    await expect(page.getByText('10 tickers')).toBeVisible();
  });

  test('add ticker using the + button', async ({ page }) => {
    const addInput = page.getByPlaceholder('Add ticker...');
    await addInput.fill('BABA');

    // Click the "+" add button
    const addButton = page.locator('button:has-text("+")');
    await addButton.click();

    await expect(page.getByText('11 tickers')).toBeVisible({ timeout: 10_000 });
    await expect(page.locator('text="BABA"').first()).toBeVisible();
  });

  test('ticker input converts to uppercase', async ({ page }) => {
    const addInput = page.getByPlaceholder('Add ticker...');
    await addInput.fill('pypl');

    // The input should auto-convert to uppercase
    await expect(addInput).toHaveValue('PYPL');
  });
});
