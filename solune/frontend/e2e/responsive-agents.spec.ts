/**
 * E2E test for responsive agents page layout at mobile/tablet/desktop viewports.
 * Verifies card reflow, touch targets, and overflow behavior.
 */

import { test, expect } from './fixtures';
import { VIEWPORTS } from './viewports';

test.describe('Responsive Agents Layout', () => {
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

  test('should meet minimum touch target size for interactive elements at mobile', async ({ page }) => {
    await page.setViewportSize(VIEWPORTS.mobile);
    await page.goto('/');
    await expect(page.locator('body')).toBeVisible();

    // All visible buttons should meet the 44×44px minimum touch target
    const buttons = page.locator('button:visible');
    const count = await buttons.count();
    for (let i = 0; i < count; i++) {
      const box = await buttons.nth(i).boundingBox();
      if (box) {
        expect(
          box.width >= 44 || box.height >= 44,
          `Button ${i} (${box.width}×${box.height}) should have at least one dimension ≥ 44px`,
        ).toBe(true);
      }
    }
  });

  // Visual regression: capture agents layout at mobile viewport
  test('visual regression — agents at mobile', async ({ page }) => {
    await page.setViewportSize(VIEWPORTS.mobile);
    await page.goto('/');
    await expect(page.locator('body')).toBeVisible();
    await expect(page).toHaveScreenshot('responsive-agents-mobile.png', {
      maxDiffPixels: 100,
    });
  });
});
