import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@/test/test-utils';

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

import { ActivityPage } from './ActivityPage';

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
    created_at: new Date().toISOString(),
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
    created_at: new Date(Date.now() - 86_400_000 - 1000).toISOString(),
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
      data: {
        total: 8,
        today: 3,
        by_type: { pipeline_run: 5, settings: 2, webhook: 1 },
        last_event_at: null,
      },
      isLoading: false,
      error: null,
    });
  });

  it('renders stat cards from the stats hook', () => {
    render(<ActivityPage />);
    expect(screen.getByText('Total Events')).toBeTruthy();
    expect(screen.getByText('8')).toBeTruthy();
    // "Today" appears as both stat label and time-bucket header
    expect(screen.getAllByText('Today').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('3')).toBeTruthy();
  });

  it('renders event summaries', () => {
    render(<ActivityPage />);
    expect(screen.getByText('Pipeline launched')).toBeTruthy();
    expect(screen.getByText('Settings updated')).toBeTruthy();
  });

  it('renders Project and Status filter chips', () => {
    render(<ActivityPage />);
    expect(screen.getByText('Project')).toBeTruthy();
    expect(screen.getByText('Status')).toBeTruthy();
  });

  it('shows loading state while stats are loading', () => {
    mocks.useActivityStats.mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    });
    render(<ActivityPage />);
    // Stat labels should still be present; values show skeleton/placeholder
    expect(screen.getByText('Total Events')).toBeTruthy();
  });

  it('renders empty state when no events', () => {
    mocks.useActivityFeed.mockReturnValue({
      allItems: [],
      hasNextPage: false,
      isFetchingNextPage: false,
      fetchNextPage: vi.fn(),
      isLoading: false,
      isError: false,
    });
    render(<ActivityPage />);
    expect(screen.getByText(/no activity/i)).toBeTruthy();
  });
});
