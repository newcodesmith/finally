import { test, expect } from '@playwright/test';

test.describe('AI Chat (Mock Mode)', () => {
  test('can open chat panel and send a message', async ({ page }) => {
    await page.goto('/');
    // Wait for page to load
    await expect(page.getByText('AAPL')).toBeVisible({ timeout: 15000 });

    // The chat panel is collapsed by default. The toggle button is a floating
    // button with title "Open AI Assistant" (from AppShell.tsx)
    const chatToggle = page.getByTitle('Open AI Assistant');
    await chatToggle.click();

    // Chat panel should now be visible with "AI Assistant" header
    await expect(page.getByText('AI Assistant')).toBeVisible({ timeout: 5000 });

    // Type a message in the chat input (placeholder: "Ask FinAlly...")
    const chatInput = page.getByPlaceholder('Ask FinAlly...');
    await chatInput.fill('What is my portfolio worth?');

    // Click the Send button
    const sendButton = page.getByRole('button', { name: 'Send' });
    await sendButton.click();

    // Wait for the mock LLM response to appear
    // In mock mode, the response is: "I'm running in mock mode..."
    await expect(page.getByText(/mock mode/i)).toBeVisible({ timeout: 15000 });
  });

  test('chat shows user message in conversation', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByText('AAPL')).toBeVisible({ timeout: 15000 });

    // Open chat
    await page.getByTitle('Open AI Assistant').click();
    await expect(page.getByText('AI Assistant')).toBeVisible();

    // Send a message
    const chatInput = page.getByPlaceholder('Ask FinAlly...');
    await chatInput.fill('Hello FinAlly');
    await page.getByRole('button', { name: 'Send' }).click();

    // The user message should appear in the chat
    await expect(page.getByText('Hello FinAlly')).toBeVisible({ timeout: 10000 });

    // The assistant response should also appear (mock mode response)
    await expect(page.getByText(/mock mode/i)).toBeVisible({ timeout: 15000 });
  });

  test('chat API returns mock response with correct structure', async ({ page }) => {
    // Test the chat API endpoint directly
    const response = await page.request.post('/api/chat', {
      data: { message: 'What stocks should I buy?' },
    });
    expect(response.ok()).toBeTruthy();

    const data = await response.json();
    // Mock mode returns a message about running in mock mode
    expect(data.message).toBeTruthy();
    expect(data.message).toContain('mock mode');
    // trades and watchlist_changes should be empty arrays in mock mode
    expect(Array.isArray(data.trades)).toBe(true);
    expect(Array.isArray(data.watchlist_changes)).toBe(true);
  });

  test('can close the chat panel', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByText('AAPL')).toBeVisible({ timeout: 15000 });

    // Open chat
    await page.getByTitle('Open AI Assistant').click();
    await expect(page.getByText('AI Assistant')).toBeVisible();

    // Close chat via the X button (title="Close chat")
    await page.getByTitle('Close chat').click();

    // Chat panel should be hidden; the toggle button should reappear
    await expect(page.getByTitle('Open AI Assistant')).toBeVisible({ timeout: 5000 });
  });
});
