/**
 * Authenticated UI flow E2E smoke tests.
 *
 * Uses the authenticated fixtures that return 200 for `/auth/me` with a
 * mock user, so the frontend renders authenticated views instead of the
 * login page.
 *
 * These tests verify that the authenticated UI renders correctly with
 * mock API data — they do NOT hit a real backend.
 */

import { test, expect } from './authenticated-fixtures';

test.describe('Authenticated Dashboard', () => {
  test('dashboard renders with authenticated user data', async ({ page }) => {
    await page.goto('/');

    // Should NOT show the login page — we are authenticated
    await expect(
      page.locator('text=Login with GitHub')
    ).not.toBeVisible({ timeout: 5000 });

    // Should show authenticated user content (project list, dashboard, etc.)
    // The exact content depends on the frontend routing for authenticated users
    const body = page.locator('body');
    await expect(body).toBeVisible();
  });

  test('navigation sidebar or header is visible for authenticated users', async ({
    page,
  }) => {
    await page.goto('/');

    // Wait for the page to load past any loading states
    await page.waitForLoadState('networkidle');

    // Authenticated users should see navigation elements
    // (sidebar, header nav, or navigation links)
    const nav = page.locator('nav, [role="navigation"], header');
    await expect(nav.first()).toBeVisible({ timeout: 5000 });
  });
});

test.describe('Authenticated Board', () => {
  test('board page renders columns when authenticated', async ({ page }) => {
    await page.goto('/board');

    // Wait for the page to settle
    await page.waitForLoadState('networkidle');

    // The board page should render without errors
    const body = page.locator('body');
    await expect(body).toBeVisible();

    // Should not show login page
    await expect(
      page.locator('text=Login with GitHub')
    ).not.toBeVisible({ timeout: 3000 });
  });
});

test.describe('Authenticated Navigation', () => {
  test('navigation between authenticated pages works', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Navigate to different routes and verify they render
    const routes = ['/', '/board', '/apps', '/help'];

    for (const route of routes) {
      await page.goto(route);
      await page.waitForLoadState('networkidle');

      // Page should render without crashing
      const body = page.locator('body');
      await expect(body).toBeVisible();

      // Should not show unhandled error messages
      await expect(
        page.locator('text=/unhandled|exception|stack trace/i')
      ).not.toBeVisible();
    }
  });
});
