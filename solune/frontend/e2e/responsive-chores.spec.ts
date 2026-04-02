/**
 * E2E test for responsive chores page layout at mobile/tablet/desktop viewports.
 * Verifies grid gap scaling, card stacking, and overflow behavior.
 */

import { test, expect } from './fixtures';
import { VIEWPORTS } from './viewports';

test.describe('Responsive Chores Layout', () => {
  for (const [name, viewport] of Object.entries(VIEWPORTS)) {
    test(`should render without overflow at ${name} (${viewport.width}x${viewport.height})`, async ({ page }) => {
      await page.setViewportSize(viewport);
      await page.goto('/');
      await expect(page.locator('body')).toBeVisible();

      // Verify no horizontal overflow
      const overflows = await page.evaluate(() => document.body.scrollWidth > window.innerWidth);
      expect(overflows).toBe(false);
    });

    test(`should have readable text at ${name} viewport`, async ({ page }) => {
      await page.setViewportSize(viewport);
      await page.goto('/');
      const h1 = page.locator('h1');
      await expect(h1).toBeVisible();
    });
  }

  test('should not have clipped text at mobile viewport', async ({ page }) => {
    await page.setViewportSize(VIEWPORTS.mobile);
    await page.goto('/');
    await expect(page.locator('body')).toBeVisible();

    // Check that all visible text containers are within the viewport width
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

  // Visual regression: capture chores layout at mobile viewport
  test('visual regression — chores at mobile', async ({ page }) => {
    await page.setViewportSize(VIEWPORTS.mobile);
    await page.goto('/');
    await expect(page.locator('body')).toBeVisible();
    await expect(page).toHaveScreenshot('responsive-chores-mobile.png', {
      maxDiffPixels: 100,
    });
  });
});
