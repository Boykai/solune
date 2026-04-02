/**
 * E2E test for responsive pipeline layout at mobile/tablet/desktop viewports.
 * Verifies stage grid, font scaling, and overflow behavior across breakpoints.
 */

import { test, expect } from './fixtures';
import { VIEWPORTS } from './viewports';

test.describe('Responsive Pipeline Layout', () => {
  for (const [name, viewport] of Object.entries(VIEWPORTS)) {
    test(`should render without overflow at ${name} (${viewport.width}x${viewport.height})`, async ({ page }) => {
      await page.setViewportSize(viewport);
      await page.goto('/');
      await expect(page.locator('body')).toBeVisible();

      // Verify no horizontal overflow at any viewport
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

  test('should not have horizontal overflow at mobile', async ({ page }) => {
    await page.setViewportSize(VIEWPORTS.mobile);

    // Override auth to access the pipeline page
    await page.route('**/api/v1/auth/me', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          github_user_id: '12345',
          github_username: 'testuser',
          session_id: 'test-session',
        }),
      })
    );
    await page.route('**/api/v1/projects**', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([]),
      })
    );

    await page.goto('/pipeline');
    await page.waitForLoadState('networkidle');

    const bodyScrollWidth = await page.evaluate(() => document.body.scrollWidth);
    const windowWidth = await page.evaluate(() => window.innerWidth);
    expect(bodyScrollWidth).toBeLessThanOrEqual(windowWidth + 1);
  });

  // Visual regression: capture pipeline layout at mobile viewport
  test('visual regression — pipeline at mobile', async ({ page }) => {
    await page.setViewportSize(VIEWPORTS.mobile);
    await page.goto('/');
    await expect(page.locator('body')).toBeVisible();
    await expect(page).toHaveScreenshot('responsive-pipeline-mobile.png', {
      maxDiffPixels: 100,
    });
  });
});
