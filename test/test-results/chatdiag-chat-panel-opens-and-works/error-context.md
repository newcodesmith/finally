# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: chatdiag.spec.ts >> chat panel opens and works
- Location: e2e/chatdiag.spec.ts:3:5

# Error details

```
Test timeout of 60000ms exceeded.
```

```
Error: page.goto: net::ERR_ABORTED; maybe frame was detached?
Call log:
  - navigating to "http://localhost:8000/", waiting until "domcontentloaded"

```

# Test source

```ts
  1  | import { test, expect } from '@playwright/test';
  2  | 
  3  | test('chat panel opens and works', async ({ page }) => {
> 4  |   await page.goto('http://localhost:8000/', { waitUntil: 'domcontentloaded' });
     |              ^ Error: page.goto: net::ERR_ABORTED; maybe frame was detached?
  5  |   await page.waitForTimeout(2000);
  6  | 
  7  |   // Screenshot before opening chat
  8  |   await page.screenshot({ path: '/tmp/claude/before-chat.png', fullPage: true });
  9  | 
  10 |   // Look for the chat toggle button
  11 |   const chatButton = page.getByTitle('Open AI Assistant');
  12 |   const isVisible = await chatButton.isVisible();
  13 |   console.log('Chat button visible:', isVisible);
  14 | 
  15 |   if (isVisible) {
  16 |     await chatButton.click();
  17 |     await page.waitForTimeout(500);
  18 |     await page.screenshot({ path: '/tmp/claude/after-chat.png', fullPage: true });
  19 | 
  20 |     // Check if AI Assistant header appears
  21 |     const assistantHeader = page.getByText('AI Assistant');
  22 |     console.log('AI Assistant header visible:', await assistantHeader.isVisible());
  23 |   }
  24 | });
  25 | 
```