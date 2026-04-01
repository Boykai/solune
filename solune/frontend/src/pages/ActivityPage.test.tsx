import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, userEvent } from '@/test/test-utils';

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

import { ActivityPage, groupEventsByTimeBucket, getTimeBucketLabel } from './ActivityPage';

const mockEvents = [
  {
    id: 'evt-today',
    event_type: 'pipeline_run',
    entity_type: 'pipeline',
    entity_id: 'pipe-1',
    project_id: 'PVT_1',
    actor: 'octocat',
    action: 'launched',
    summary: 'Pipeline launched',
    detail: { issue_number: 42 },
    created_at: '2026-04-01T08:00:00Z',
  },
  {
    id: 'evt-yesterday',
    event_type: 'settings',
    entity_type: 'settings',
    entity_id: 'PVT_1',
    project_id: 'PVT_1',
    actor: 'octocat',
    action: 'updated',
    summary: 'Settings updated',
    created_at: '2026-03-31T10:00:00Z',
  },
];

describe('ActivityPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.useActivityFeed.mockReturnValue({
      allItems: mockEvents,
      hasNextPage: false,
      isFetchingNextPage: false,
      fetchNextPage: vi.fn(),
      isLoading: false,
      isError: false,
    });
    mocks.useActivityStats.mockReturnValue({
      stats: {
        total_count: 8,
        today_count: 3,
        by_type: { pipeline_run: 5, settings: 2, webhook: 1 },
        last_event_at: null,
      },
      isLoading: false,
      error: null,
    });
  });

  it('renders stats cards, grouped sections, and event metadata badges', () => {
    render(<ActivityPage />);

    expect(screen.getByText('Total Events')).toBeInTheDocument();
    expect(screen.getByText('8')).toBeInTheDocument();
    expect(screen.getAllByText('Today')).toHaveLength(2);
    expect(screen.getByText('3')).toBeInTheDocument();
    expect(screen.getByText('Most Common')).toBeInTheDocument();
    expect(screen.getByText('Pipeline Run')).toBeInTheDocument();
    expect(screen.getByText('Last Activity')).toBeInTheDocument();
    expect(screen.getByText('No activity')).toBeInTheDocument();

    expect(screen.getAllByText('Today')).toHaveLength(2);
    expect(screen.getByText('Yesterday')).toBeInTheDocument();
    expect(screen.getByText('Pipeline launched')).toBeInTheDocument();
    expect(screen.getByText('Launched')).toBeInTheDocument();
    expect(screen.getAllByText('Pipeline').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Settings').length).toBeGreaterThan(0);
  });

  it('uses the new project and execution filter categories', async () => {
    render(<ActivityPage />);

    await userEvent.click(screen.getByRole('button', { name: /project/i }));
    expect(mocks.useActivityFeed).toHaveBeenLastCalledWith('PVT_1', ['project', 'settings']);

    await userEvent.click(screen.getByRole('button', { name: /execution/i }));
    expect(mocks.useActivityFeed).toHaveBeenLastCalledWith('PVT_1', [
      'agent_execution',
      'project',
      'settings',
    ]);
  });
});

describe('ActivityPage time bucketing helpers', () => {
  const now = new Date('2026-04-01T12:00:00Z');

  it('categorizes timestamps into the expected time buckets', () => {
    expect(getTimeBucketLabel('2026-04-01T08:00:00Z', now)).toBe('Today');
    expect(getTimeBucketLabel('2026-03-31T08:00:00Z', now)).toBe('Yesterday');
    expect(getTimeBucketLabel('2026-03-28T08:00:00Z', now)).toBe('This Week');
    expect(getTimeBucketLabel('2026-03-20T08:00:00Z', now)).toBe('Earlier');
  });

  it('groups events by time bucket in display order', () => {
    const groups = groupEventsByTimeBucket(
      [
        mockEvents[1],
        mockEvents[0],
        {
          ...mockEvents[0],
          id: 'evt-earlier',
          created_at: '2026-03-20T08:00:00Z',
        },
      ],
      now
    );

    expect(groups.map((group) => group.label)).toEqual(['Today', 'Yesterday', 'Earlier']);
    expect(groups[0]?.events).toHaveLength(1);
  });
});
