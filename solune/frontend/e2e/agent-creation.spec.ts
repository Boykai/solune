import { test, expect } from './authenticated-fixtures';

test.describe('Agent Creation', () => {
  test('creates an agent and exposes the pending PR state', async ({ page }) => {
    await page.goto('/agents');

    await page.getByRole('button', { name: /\+ Add Agent/i }).click();

    const dialog = page.getByRole('dialog', { name: /Add Agent/i });
    await dialog.getByLabel('Name').fill('Security Reviewer');
    await dialog.getByLabel('System Prompt').fill(
      'Review security-sensitive changes and highlight risky implementation details.',
    );

    await dialog.getByRole('button', { name: 'Create Agent' }).click();

    const createdDialog = page.getByRole('dialog', { name: /Agent created/i });
    await expect(createdDialog).toBeVisible();
    await expect(createdDialog.getByText(/pull request has been opened/i)).toBeVisible();
    await expect(createdDialog.getByRole('link', { name: /View Pull Request/i })).toBeVisible();

    await createdDialog.getByRole('button', { name: 'Close' }).click();

    await expect(page.getByText('Agent PRs waiting on main')).toBeVisible();
    await expect(page.getByText('Security Reviewer')).toBeVisible();
  });
});
