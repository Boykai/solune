import { test, expect } from './authenticated-fixtures';

test.describe('Chat Interaction', () => {
  test('creates and confirms an issue recommendation from chat', async ({ page }) => {
    await page.goto('/projects');

    await page.getByRole('button', { name: 'Open chat' }).click();

    const input = page.getByLabel(
      'Chat input — ask questions, describe tasks, use slash commands, or mention pipelines',
    );
    await input.fill('Create an issue for saved search filters');
    await page.locator('form button[type="submit"]').click();

    await expect(page.getByRole('heading', { name: 'Issue Recommendation' })).toBeVisible();
    await expect(page.getByText('Ship saved search filters')).toBeVisible();

    await page.getByRole('button', { name: /Confirm & Create Issue/i }).click();

    await expect(page.getByText('Recommendation confirmed')).toBeVisible();
  });

  test('can clear the current conversation and return to the empty state', async ({ page }) => {
    await page.goto('/projects');

    await page.getByRole('button', { name: 'Open chat' }).click();

    const input = page.getByLabel(
      'Chat input — ask questions, describe tasks, use slash commands, or mention pipelines',
    );
    await input.fill('Create an issue for saved search filters');
    await page.locator('form button[type="submit"]').click();

    await expect(page.getByRole('button', { name: 'New Chat' })).toBeVisible();
    await page.getByRole('button', { name: 'New Chat' }).click();

    await expect(page.getByText('Start a conversation')).toBeVisible();
  });
});
