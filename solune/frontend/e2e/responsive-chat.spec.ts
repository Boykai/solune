/**
 * E2E test for responsive chat layout at mobile/tablet/desktop viewports.
 * Verifies mobile full-screen behaviour, touch targets, and overflow.
 */

import type { Page } from '@playwright/test';
import { test, expect } from './authenticated-fixtures';
import { VIEWPORTS } from './viewports';

async function openChat(page: Page) {
  await page.goto('/projects');
  const toggle = page.getByRole('button', { name: 'Open chat' });
  await expect(toggle).toBeVisible();
  await toggle.click();
  await expect(page.getByRole('button', { name: 'Close chat' })).toBeVisible();
}

function getChatSendButton(page: Page) {
  return page.locator('button[type="submit"]').last();
}

test.describe('Responsive Chat Layout', () => {
  for (const [name, viewport] of Object.entries(VIEWPORTS)) {
    test(`should render without overflow at ${name} (${viewport.width}x${viewport.height})`, async ({ page }) => {
      await page.setViewportSize(viewport);
      await openChat(page);

      // Verify no horizontal overflow
      const overflows = await page.evaluate(() => document.body.scrollWidth > window.innerWidth);
      expect(overflows).toBe(false);
    });

    test(`should open the chat panel at ${name} viewport`, async ({ page }) => {
      await page.setViewportSize(viewport);
      await openChat(page);
    });
  }

  test('should meet minimum touch target size for buttons at mobile', async ({ page }) => {
    await page.setViewportSize(VIEWPORTS.mobile);
    await openChat(page);

    const buttons = [
      page.getByRole('button', { name: 'Close chat' }),
      getChatSendButton(page),
    ];

    for (const [index, button] of buttons.entries()) {
      const box = await button.boundingBox();
      if (box) {
        expect(
          box.width >= 44 || box.height >= 44,
          `Chat control ${index} (${box.width}×${box.height}) should have at least one dimension ≥ 44px`,
        ).toBe(true);
      }
    }
  });

  test('should keep the chat panel within the mobile viewport', async ({ page }) => {
    await page.setViewportSize(VIEWPORTS.mobile);
    await openChat(page);

    const panel = getChatSendButton(page).locator('xpath=ancestor::div[contains(@class, "fixed")][1]');
    const panelBounds = await panel.boundingBox();

    expect(panelBounds).not.toBeNull();
    expect(panelBounds!.x).toBeGreaterThanOrEqual(0);
    expect(panelBounds!.y).toBeGreaterThanOrEqual(0);
    expect(panelBounds!.x + panelBounds!.width).toBeLessThanOrEqual(VIEWPORTS.mobile.width + 1);
    expect(panelBounds!.y + panelBounds!.height).toBeLessThanOrEqual(VIEWPORTS.mobile.height + 1);
  });

  // Visual regression: capture chat layout at mobile viewport
  test('visual regression — chat at mobile', async ({ page }) => {
    await page.setViewportSize(VIEWPORTS.mobile);
    await openChat(page);
    await expect(page).toHaveScreenshot('responsive-chat-mobile.png', {
      maxDiffPixelRatio: 0.02,
    });
  });
});
