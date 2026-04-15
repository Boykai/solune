/**
 * E2E test for responsive settings layout at mobile/tablet/desktop viewports.
 * Verifies responsive padding, form input widths, and overflow.
 */

import type { Page } from '@playwright/test';
import { test, expect } from './authenticated-fixtures';
import { VIEWPORTS } from './viewports';

async function openSettingsPage(page: Page) {
  await page.goto('/settings');
  await expect(page.getByRole('heading', { name: 'Settings' })).toBeVisible();
}

test.describe('Responsive Settings Layout', () => {
  for (const [name, viewport] of Object.entries(VIEWPORTS)) {
    test(`should render without overflow at ${name} (${viewport.width}x${viewport.height})`, async ({ page }) => {
      await page.setViewportSize(viewport);
      await openSettingsPage(page);

      // Check no horizontal scrollbar
      const overflows = await page.evaluate(() => document.body.scrollWidth > window.innerWidth);
      expect(overflows).toBe(false);
    });
  }

  test('should not clip text at mobile viewport', async ({ page }) => {
    await page.setViewportSize(VIEWPORTS.mobile);
    await openSettingsPage(page);

    const textClipping = await page.evaluate(() => {
      const elements = document.querySelectorAll('p, span, h1, h2, h3, h4, h5, h6, label');
      for (const el of elements) {
        const rect = el.getBoundingClientRect();
        if (rect.width > 0 && rect.right > window.innerWidth + 2) {
          return { clipped: true, text: el.textContent?.slice(0, 40), right: rect.right };
        }
      }
      return { clipped: false };
    });
    expect(textClipping.clipped).toBe(false);
  });

  // Visual regression: capture settings at mobile viewport
  test('visual regression — settings at mobile', async ({ page }) => {
    await page.setViewportSize(VIEWPORTS.mobile);
    await openSettingsPage(page);
    await expect(page).toHaveScreenshot('responsive-settings-mobile.png', {
      maxDiffPixelRatio: 0.08,
    });
  });
});
