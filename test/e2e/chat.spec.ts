import { test, expect } from '@playwright/test';

test.describe('AI Chat (Mock Mode)', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await expect(page.getByText('AI Assistant')).toBeVisible({ timeout: 10_000 });
  });

  test('send a message and receive a mock response', async ({ page }) => {
    // Type a message in the chat input
    const chatInput = page.getByPlaceholder('Ask FinAlly...');
    await chatInput.fill('How is my portfolio doing?');

    // Click send
    const sendButton = page.locator('button:has-text("Send")');
    await sendButton.click();

    // The user message should appear in the chat
    await expect(page.getByText('How is my portfolio doing?')).toBeVisible();

    // Loading indicator should appear (bouncing dots with "Thinking...")
    await expect(page.getByText('Thinking...')).toBeVisible({ timeout: 5_000 });

    // Wait for the mock response to appear
    // The mock response contains "mock mode"
    await expect(page.getByText(/mock mode/i)).toBeVisible({ timeout: 15_000 });
  });

  test('chat history persists across multiple messages', async ({ page }) => {
    const chatInput = page.getByPlaceholder('Ask FinAlly...');
    const sendButton = page.locator('button:has-text("Send")');

    // Send first message
    await chatInput.fill('Hello');
    await sendButton.click();
    await expect(page.getByText(/mock mode/i)).toBeVisible({ timeout: 15_000 });

    // Send second message
    await chatInput.fill('What should I buy?');
    await sendButton.click();

    // Wait for second response
    // There should be two instances of the mock response text
    await page.waitForTimeout(5000);
    const mockResponses = page.getByText(/mock mode/i);
    await expect(mockResponses).toHaveCount(2, { timeout: 15_000 });

    // Both user messages should still be visible
    await expect(page.getByText('Hello')).toBeVisible();
    await expect(page.getByText('What should I buy?')).toBeVisible();
  });

  test('send message using Enter key', async ({ page }) => {
    const chatInput = page.getByPlaceholder('Ask FinAlly...');

    await chatInput.fill('Test message');
    await chatInput.press('Enter');

    // User message should appear
    await expect(page.getByText('Test message')).toBeVisible();

    // Wait for response
    await expect(page.getByText(/mock mode/i)).toBeVisible({ timeout: 15_000 });
  });

  test('send button is disabled while loading', async ({ page }) => {
    const chatInput = page.getByPlaceholder('Ask FinAlly...');
    const sendButton = page.locator('button:has-text("Send")');

    await chatInput.fill('Hello');
    await sendButton.click();

    // While loading, the input and send button should be disabled
    await expect(chatInput).toBeDisabled({ timeout: 2_000 });
  });

  test('empty state shows welcome message', async ({ page }) => {
    // Before any messages are sent, the chat panel shows a welcome prompt
    await expect(page.getByText('FinAlly AI Assistant')).toBeVisible();
    await expect(page.getByText(/analyze your portfolio/i)).toBeVisible();
  });

  test('chat panel can be closed and reopened', async ({ page }) => {
    // Close the chat panel
    const closeButton = page.locator('button:has-text("x")').first();
    // The close button is in the chat header
    const chatHeader = page.getByText('AI Assistant').locator('..');
    const chatCloseBtn = chatHeader.locator('button');
    await chatCloseBtn.click();

    // Chat panel should be hidden
    await expect(page.getByText('AI Assistant')).not.toBeVisible();

    // The "AI Chat" toggle button should appear
    const toggleButton = page.locator('button:has-text("AI Chat")');
    await expect(toggleButton).toBeVisible();

    // Click it to reopen
    await toggleButton.click();
    await expect(page.getByText('AI Assistant')).toBeVisible();
  });
});
