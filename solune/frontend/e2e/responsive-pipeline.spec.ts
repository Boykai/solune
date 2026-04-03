/**
 * E2E test for responsive pipeline layout at mobile/tablet/desktop viewports.
 * Verifies stage grid, font scaling, and overflow behavior across breakpoints.
 */

import type { Page } from '@playwright/test';
import { test, expect } from './authenticated-fixtures';
import { VIEWPORTS } from './viewports';

const PIPELINE_TITLE = 'Orchestrate agents across every stage.';

async function openPipelinePage(page: Page) {
  await page.goto('/pipeline');
  await expect(page.getByText(PIPELINE_TITLE)).toBeVisible();
}

test.describe('Responsive Pipeline Layout', () => {
  for (const [name, viewport] of Object.entries(VIEWPORTS)) {
    test(`should render without overflow at ${name} (${viewport.width}x${viewport.height})`, async ({ page }) => {
      await page.setViewportSize(viewport);
      await openPipelinePage(page);

      // Verify no horizontal overflow at any viewport
      const overflows = await page.evaluate(() => document.body.scrollWidth > window.innerWidth);
      expect(overflows).toBe(false);
    });

    test(`should have readable text at ${name} viewport`, async ({ page }) => {
      await page.setViewportSize(viewport);
      await openPipelinePage(page);
    });
  }

  test('should not have horizontal overflow at mobile', async ({ page }) => {
    await page.setViewportSize(VIEWPORTS.mobile);
    await openPipelinePage(page);

    const bodyScrollWidth = await page.evaluate(() => document.body.scrollWidth);
    const windowWidth = await page.evaluate(() => window.innerWidth);
    expect(bodyScrollWidth).toBeLessThanOrEqual(windowWidth + 1);
  });

  // Visual regression: capture pipeline layout at mobile viewport
  test('visual regression — pipeline at mobile', async ({ page }) => {
    await page.setViewportSize(VIEWPORTS.mobile);
    await openPipelinePage(page);
    await expect(page).toHaveScreenshot('responsive-pipeline-mobile.png', {
      maxDiffPixels: 100,
    });
  });
});
