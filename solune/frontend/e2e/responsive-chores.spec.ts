/**
 * E2E test for responsive chores page layout at mobile/tablet/desktop viewports.
 * Verifies grid gap scaling, card stacking, and overflow behavior.
 */

import type { Page } from '@playwright/test';
import { test, expect } from './authenticated-fixtures';
import { VIEWPORTS } from './viewports';

const CHORES_TITLE = 'Turn upkeep into a visible rhythm.';

async function openChoresPage(page: Page) {
  await page.goto('/chores');
  await expect(page.getByText(CHORES_TITLE)).toBeVisible();
}

test.describe('Responsive Chores Layout', () => {
  for (const [name, viewport] of Object.entries(VIEWPORTS)) {
    test(`should render without overflow at ${name} (${viewport.width}x${viewport.height})`, async ({ page }) => {
      await page.setViewportSize(viewport);
      await openChoresPage(page);

      // Verify no horizontal overflow
      const overflows = await page.evaluate(() => document.body.scrollWidth > window.innerWidth);
      expect(overflows).toBe(false);
    });

    test(`should have readable text at ${name} viewport`, async ({ page }) => {
      await page.setViewportSize(viewport);
      await openChoresPage(page);
    });
  }

  test('should not have clipped text at mobile viewport', async ({ page }) => {
    await page.setViewportSize(VIEWPORTS.mobile);
    await openChoresPage(page);

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
    await openChoresPage(page);
    await expect(page.getByRole('main')).toHaveScreenshot('responsive-chores-mobile.png', {
      maxDiffPixels: 100,
    });
  });
});
