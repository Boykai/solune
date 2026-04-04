import { test, expect } from './fixtures';

test.describe('Authentication', () => {
  test('redirects protected routes to login and preserves the intended path', async ({ page }) => {
    await page.goto('/agents');

    await expect(page).toHaveURL(/\/login$/);
    await expect(page.getByRole('heading', { name: 'Solune' })).toBeVisible();

    const redirectPath = await page.evaluate(() =>
      sessionStorage.getItem('solune-redirect-after-login'),
    );

    expect(redirectPath).toBe('/agents');
  });

  test('starts the GitHub OAuth flow from the login button', async ({ page }) => {
    await page.route('**/api/v1/auth/github', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'text/html',
        body: '<html><body>OAuth flow started</body></html>',
      }),
    );

    await page.goto('/login');

    await page.getByRole('button', { name: /Login with GitHub/i }).click();

    await expect(page).toHaveURL(/\/api\/v1\/auth\/github$/);
  });
});
