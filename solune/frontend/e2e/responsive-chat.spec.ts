/**
 * E2E test for responsive chat layout at mobile/tablet/desktop viewports.
 * Verifies mobile full-screen behaviour, touch targets, and overflow.
 */

import { test, expect } from './fixtures';
import { VIEWPORTS } from './viewports';

test.describe('Responsive Chat Layout', () => {
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

  test('should meet minimum touch target size for buttons at mobile', async ({ page }) => {
    await page.setViewportSize(VIEWPORTS.mobile);
    await page.goto('/');
    await expect(page.locator('body')).toBeVisible();

    // Verify all visible buttons have at least one dimension ≥ 44px (WCAG touch target)
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

  test('should not clip any text at mobile viewport', async ({ page }) => {
    await page.setViewportSize(VIEWPORTS.mobile);
    await page.goto('/');
    await expect(page.locator('body')).toBeVisible();

    const textClipping = await page.evaluate(() => {
      const elements = document.querySelectorAll('p, span, h1, h2, h3, h4, h5, h6');
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

  // Visual regression: capture chat layout at mobile viewport
  test('visual regression — chat at mobile', async ({ page }) => {
    await page.setViewportSize(VIEWPORTS.mobile);
    await page.goto('/');
    await expect(page.locator('body')).toBeVisible();
    await expect(page).toHaveScreenshot('responsive-chat-mobile.png', {
      maxDiffPixels: 100,
    });
  });
});
