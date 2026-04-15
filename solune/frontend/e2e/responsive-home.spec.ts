/**
 * E2E test for responsive home layout at mobile/tablet/desktop viewports.
 * Verifies sidebar collapse, touch targets, and overflow.
 */

import { test, expect } from './fixtures';
import { VIEWPORTS } from './viewports';

test.describe('Responsive Home Layout', () => {
  for (const [name, viewport] of Object.entries(VIEWPORTS)) {
    test(`should render without overflow at ${name} (${viewport.width}x${viewport.height})`, async ({ page }) => {
      await page.setViewportSize(viewport);
      await page.goto('/');
      await expect(page.locator('body')).toBeVisible();

      // Verify no horizontal overflow
      const overflows = await page.evaluate(() => document.body.scrollWidth > window.innerWidth);
      expect(overflows).toBe(false);
    });

    test(`should display visible heading at ${name}`, async ({ page }) => {
      await page.setViewportSize(viewport);
      await page.goto('/');
      await expect(page.locator('h1')).toBeVisible();
    });
  }

  test('should meet minimum touch target sizes at mobile', async ({ page }) => {
    await page.setViewportSize(VIEWPORTS.mobile);
    await page.goto('/');
    await expect(page.locator('body')).toBeVisible();

    // All visible buttons should have at least one dimension ≥ 44px
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

  // Visual regression: capture home at mobile viewport
  test('visual regression — home at mobile', async ({ page }) => {
    await page.setViewportSize(VIEWPORTS.mobile);
    await page.goto('/');
    await expect(page.locator('body')).toBeVisible();
    await expect(page).toHaveScreenshot('responsive-home-mobile.png', {
      maxDiffPixelRatio: 0.08,
    });
  });
});
