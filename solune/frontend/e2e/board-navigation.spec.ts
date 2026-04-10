import AxeBuilder from '@axe-core/playwright';
import { test, expect } from './authenticated-fixtures';

test.describe('Board Navigation', () => {
  test('lets the user select a project and inspect an issue from the board', async ({ page, mockApi }) => {
    mockApi.user.selected_project_id = undefined;

    await page.goto('/projects');

    await expect(page.getByRole('heading', { name: 'Select a project' })).toBeVisible();

    await page.getByRole('button', { name: /Browse GitHub Projects/i }).click();
    await page.getByRole('option', { name: /Test Project/i }).click();

    const projectBoard = page.getByRole('region', { name: 'Project board' });
    await expect(projectBoard.getByText('Backlog')).toBeVisible();
    await expect(projectBoard.getByText('In Progress')).toBeVisible();
    await expect(projectBoard.getByText('Done')).toBeVisible();

    const issueCard = projectBoard.getByRole('button', { name: /Set up CI\/CD pipeline/i });
    await issueCard.click();

    const dialog = page.getByRole('dialog', { name: /Set up CI\/CD pipeline/i });
    await expect(dialog).toBeVisible();
    await expect(dialog.getByText('Create a resilient CI pipeline for pull requests and releases.')).toBeVisible();

    await page.keyboard.press('Escape');
    await expect(dialog).toBeHidden();
  });

  test('loads the selected project board immediately on return visits', async ({ page }) => {
    await page.goto('/projects');

    await expect(page.getByRole('button', { name: '#1 Set up CI/CD pipeline', exact: true })).toBeVisible();
    await expect(page.getByRole('button', { name: '#2 Implement auth flow', exact: true })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Select a project' })).toHaveCount(0);
  });

  test('board page passes WCAG 2.1 AA accessibility audit', async ({ page }) => {
    await page.goto('/projects');
    await expect(page.getByRole('button', { name: '#1 Set up CI/CD pipeline', exact: true })).toBeVisible();

    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze();

    expect(results.violations).toEqual([]);
  });
});
