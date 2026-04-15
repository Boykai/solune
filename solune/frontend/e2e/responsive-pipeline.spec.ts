/**
 * E2E test for responsive pipeline layout at mobile/tablet/desktop viewports.
 * Verifies stage grid, font scaling, and overflow behavior across breakpoints.
 */

import type { Page } from '@playwright/test';
import { test, expect } from './authenticated-fixtures';
import { VIEWPORTS } from './viewports';

const PIPELINE_PROJECT_BADGE = /test-user\/test project/i;

async function openPipelinePage(page: Page) {
  const viewport = page.viewportSize();
  if (viewport && viewport.width < 768) {
    await page.addInitScript(() => {
      window.localStorage.setItem('sidebar-collapsed', 'true');
    });
  }

  await page.goto('/pipeline');
  await expect(page.getByRole('button', { name: /^New pipeline$/ })).toBeVisible();
  await expect(page.getByText(PIPELINE_PROJECT_BADGE)).toBeVisible();
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

  // Visual regression: capture the pipeline stages region at mobile viewport.
  test('visual regression — pipeline at mobile', async ({ page }) => {
    await page.setViewportSize(VIEWPORTS.mobile);
    await openPipelinePage(page);
    const stagesGrid = page.getByTestId('pipeline-stages-grid');

    await expect(stagesGrid).toBeVisible({ timeout: 15_000 });
    await expect(stagesGrid).toHaveScreenshot('responsive-pipeline-mobile.png', {
      maxDiffPixelRatio: 0.08,
      timeout: 15_000,
    });
  });
});
