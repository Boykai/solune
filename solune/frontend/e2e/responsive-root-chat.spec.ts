import { test, expect, type MockApiState } from './authenticated-fixtures';
import { VIEWPORTS } from './viewports';

function seedRecentInteractions(mockApi: MockApiState) {
  const board = mockApi.boardDataByProject.PVT_test123;
  const baseItem = board.columns[0].items[0];

  board.columns[0].items = Array.from({ length: 12 }, (_, index) => ({
    ...baseItem,
    item_id: `PVTI_recent_${index + 1}`,
    title: `Recent interaction ${index + 1}`,
    number: index + 1,
  }));
  board.columns[0].item_count = board.columns[0].items.length;
}

test.describe('Responsive Root Chat Route', () => {
  test('bootstraps an empty authenticated session into a usable chat panel', async ({ page, mockApi }) => {
    mockApi.conversations = [];
    mockApi.chatMessagesByConversation = {};

    await page.goto('/');

    await expect(page.getByText('Start a conversation')).toBeVisible();
    await expect(
      page.getByLabel('Chat input — ask questions, describe tasks, use slash commands, or mention pipelines'),
    ).toBeVisible();
    await expect(page.getByText('Starting your chat...')).toHaveCount(0);
  });

  test('keeps the full desktop sidebar reachable at short viewport heights', async ({ page, mockApi }) => {
    mockApi.conversations = [];
    mockApi.chatMessagesByConversation = {};
    seedRecentInteractions(mockApi);

    await page.setViewportSize({ width: VIEWPORTS.desktop.width, height: 420 });
    await page.goto('/');
    await expect(page.getByText('Start a conversation')).toBeVisible();

    const scrollSurface = page.getByTestId('sidebar-scroll-surface');
    const sidebarMetrics = await scrollSurface.evaluate((surface) => {
      const element = surface as HTMLElement;

      const scrollHeight = element.scrollHeight;
      const clientHeight = element.clientHeight;
      element.scrollTop = Math.max(0, scrollHeight - clientHeight);
      const bottomScrollTop = element.scrollTop;
      element.scrollTop = 0;

      return {
        scrollHeight,
        clientHeight,
        bottomScrollTop,
        returnedToTop: element.scrollTop === 0,
      };
    });

    expect(sidebarMetrics).not.toBeNull();
    expect(sidebarMetrics?.scrollHeight ?? 0).toBeGreaterThan(sidebarMetrics?.clientHeight ?? 0);
    expect(sidebarMetrics?.bottomScrollTop ?? 0).toBeGreaterThan(0);
    expect(sidebarMetrics?.returnedToTop).toBe(true);
    await expect(page.getByText('Solune')).toBeVisible();
    await expect(page.getByText('Test Project')).toBeVisible();
  });

  test('keeps the root route usable on mobile without horizontal overflow', async ({ page, mockApi }) => {
    mockApi.conversations = [];
    mockApi.chatMessagesByConversation = {};
    seedRecentInteractions(mockApi);

    await page.setViewportSize(VIEWPORTS.mobile);
    await page.goto('/');

    await expect(page.getByText('Start a conversation')).toBeVisible();

    const hasHorizontalOverflow = await page.evaluate(() => document.body.scrollWidth > window.innerWidth);
    expect(hasHorizontalOverflow).toBe(false);

    await page.getByRole('button', { name: /expand sidebar/i }).click();
    const sidebar = page.getByLabel('Sidebar navigation');
    await expect(sidebar).toBeVisible();

    const sidebarCanScroll = await page.getByTestId('sidebar-scroll-surface').evaluate((surface) => {
      return getComputedStyle(surface as HTMLElement).overflowY === 'auto';
    });

    expect(sidebarCanScroll).toBe(true);
  });
});