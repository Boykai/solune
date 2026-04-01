import { beforeEach, afterEach, describe, expect, it, vi } from 'vitest';
import { render, screen, userEvent, waitFor } from '@/test/test-utils';

const mocks = vi.hoisted(() => ({
  useActivityFeed: vi.fn(),
  useActivityStats: vi.fn(),
}));

vi.mock('@/hooks/useAuth', () => ({
  useAuth: () => ({ user: { selected_project_id: 'PVT_1' } }),
}));

vi.mock('@/hooks/useActivityFeed', () => ({
  useActivityFeed: (...args: unknown[]) => mocks.useActivityFeed(...args),
}));

vi.mock('@/hooks/useActivityStats', () => ({
  useActivityStats: (...args: unknown[]) => mocks.useActivityStats(...args),
}));

vi.mock('@/components/common/InfiniteScrollContainer', () => ({
  InfiniteScrollContainer: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

import { ActivityPage, bucketActivityEvents } from './ActivityPage';

const baseFeed = {
  allItems: [
    {
      id: 'evt-1',
      event_type: 'pipeline_run',
      entity_type: 'pipeline',
      entity_id: 'pipe-1',
      project_id: 'PVT_1',
      actor: 'testuser',
      action: 'launched',
      summary: 'Pipeline launched: Main Flow',
      detail: { issue_number: 42 },
      created_at: '2026-03-31T10:00:00Z',
    },
    {
      id: 'evt-2',
      event_type: 'settings',
      entity_type: 'settings',
      entity_id: 'PVT_1',
      project_id: 'PVT_1',
      actor: 'testuser',
      action: 'updated',
      summary: 'Settings updated: project',
      detail: { changed_fields: ['queue_mode'] },
      created_at: '2026-03-30T08:00:00Z',
    },
  ],
  hasNextPage: false,
  isFetchingNextPage: false,
  fetchNextPage: vi.fn(),
  isLoading: false,
  isError: false,
};

describe('ActivityPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(Date, 'now').mockReturnValue(new Date('2026-03-31T12:00:00Z').getTime());
    mocks.useActivityFeed.mockReturnValue(baseFeed);
    mocks.useActivityStats.mockReturnValue({
      data: {
        total_count: 7,
        today_count: 2,
        by_type: { pipeline_run: 4, settings: 2, webhook: 1 },
        last_event_at: '2026-03-31T10:00:00Z',
      },
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders stats cards, grouped sections, badges, and entity pills', () => {
    render(<ActivityPage />);

    expect(screen.getByText('Total Events')).toBeInTheDocument();
    expect(screen.getByText('7')).toBeInTheDocument();
    expect(screen.getByText('Most Common')).toBeInTheDocument();
    expect(screen.getByText('Pipeline Run (4)')).toBeInTheDocument();
    expect(screen.getByText('Last Activity')).toBeInTheDocument();

    expect(screen.getByRole('region', { name: 'Today' })).toBeInTheDocument();
    expect(screen.getByRole('region', { name: 'Yesterday' })).toBeInTheDocument();
    expect(screen.getByText('Launched')).toBeInTheDocument();
    expect(screen.getByText('Pipeline launched: Main Flow')).toBeInTheDocument();
    expect(screen.getByText('Settings updated: project')).toBeInTheDocument();
  });

  it('exposes the new project and execution filters and updates the feed query', async () => {
    render(<ActivityPage />);

    expect(screen.getByRole('button', { name: /^Project$/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^Execution$/i })).toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: /^Project$/i }));

    await waitFor(() => {
      expect(mocks.useActivityFeed).toHaveBeenLastCalledWith('PVT_1', ['project', 'settings']);
    });

    await userEvent.click(screen.getByRole('button', { name: 'Clear all' }));

    await waitFor(() => {
      expect(mocks.useActivityFeed).toHaveBeenLastCalledWith('PVT_1', undefined);
    });
  });

  it('keeps the empty state meaningful when filtered results are empty', async () => {
    mocks.useActivityFeed.mockReturnValue({ ...baseFeed, allItems: [] });

    render(<ActivityPage />);
    await userEvent.click(screen.getByRole('button', { name: /^Project$/i }));

    expect(screen.getByText('No project events found')).toBeInTheDocument();
  });

  it('buckets events into today, yesterday, this week, and earlier', () => {
    const grouped = bucketActivityEvents(
      [
        ...baseFeed.allItems,
        {
          ...baseFeed.allItems[0],
          id: 'evt-3',
          created_at: '2026-03-28T08:00:00Z',
        },
        {
          ...baseFeed.allItems[0],
          id: 'evt-4',
          created_at: '2026-03-20T08:00:00Z',
        },
      ],
      new Date('2026-03-31T12:00:00Z'),
    );

    expect(grouped.map((group) => group.label)).toEqual([
      'Today',
      'Yesterday',
      'This Week',
      'Earlier',
    ]);
  });
});
