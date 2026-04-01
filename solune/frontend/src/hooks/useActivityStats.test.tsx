import { beforeEach, describe, expect, it, vi } from 'vitest';
import { renderHook } from '@testing-library/react';

const mockUseQuery = vi.fn();

vi.mock('@tanstack/react-query', () => ({
  useQuery: (...args: unknown[]) => mockUseQuery(...args),
}));

vi.mock('@/services/api', () => ({
  activityApi: {
    stats: vi.fn(),
  },
}));

import { useActivityStats } from './useActivityStats';
import { activityApi } from '@/services/api';

const mockActivityApi = activityApi as unknown as {
  stats: ReturnType<typeof vi.fn>;
};

describe('useActivityStats', () => {
  beforeEach(() => vi.clearAllMocks());

  it('requests stats for the selected project', () => {
    mockUseQuery.mockReturnValue({
      data: { total: 5, today: 1, by_type: {}, last_event_at: null },
      isLoading: false,
      error: null,
    });

    const { result } = renderHook(() => useActivityStats('proj-1'));

    expect(mockUseQuery).toHaveBeenCalledWith(
      expect.objectContaining({
        queryKey: ['activity-stats', 'proj-1'],
        enabled: true,
        staleTime: 60_000,
      }),
    );

    const opts = mockUseQuery.mock.calls[0][0];
    opts.queryFn();
    expect(mockActivityApi.stats).toHaveBeenCalledWith('proj-1');
    expect(result.current.data?.total).toBe(5);
  });

  it('is disabled without a project id', () => {
    mockUseQuery.mockReturnValue({ data: undefined, isLoading: false, error: null });

    renderHook(() => useActivityStats(''));

    expect(mockUseQuery).toHaveBeenCalledWith(expect.objectContaining({ enabled: false }));
  });
});
