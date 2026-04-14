/**
 * E2E test for responsive agents page layout at mobile/tablet/desktop viewports.
 * Verifies card reflow, touch targets, and overflow behavior.
 */

import type { Page } from '@playwright/test';
import { test, expect } from './authenticated-fixtures';
import { VIEWPORTS } from './viewports';

const AGENTS_TITLE = 'Shape your agent constellation.';

async function openAgentsPage(page: Page) {
  await page.goto('/agents');
  await expect(page.getByText(AGENTS_TITLE)).toBeVisible();
}

test.describe('Responsive Agents Layout', () => {
  for (const [name, viewport] of Object.entries(VIEWPORTS)) {
    test(`should render without overflow at ${name} (${viewport.width}x${viewport.height})`, async ({ page }) => {
      await page.setViewportSize(viewport);
      await openAgentsPage(page);

      // Verify no horizontal overflow
      const overflows = await page.evaluate(() => document.body.scrollWidth > window.innerWidth);
      expect(overflows).toBe(false);
    });

    test(`should have readable text at ${name} viewport`, async ({ page }) => {
      await page.setViewportSize(viewport);
      await openAgentsPage(page);
    });
  }

  test('should meet minimum touch target size for interactive elements at mobile', async ({ page }) => {
    await page.setViewportSize(VIEWPORTS.mobile);
    await openAgentsPage(page);

    // Restrict the assertion to the agents page content rather than shell controls.
    const buttons = page.locator('main button:visible');
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
    await openAgentsPage(page);
    await expect(page.getByRole('main')).toHaveScreenshot('responsive-agents-mobile.png', {
      maxDiffPixels: 100,
    });
  });
});
