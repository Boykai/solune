import { describe, it, expect, vi, beforeEach } from 'vitest';
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

  it('passes the expected query config to useQuery', () => {
    const fakeReturn = { data: { total_count: 4 }, isLoading: false };
    mockUseQuery.mockReturnValue(fakeReturn);

    const { result } = renderHook(() => useActivityStats('proj-1'));

    expect(mockUseQuery).toHaveBeenCalledWith(
      expect.objectContaining({
        queryKey: ['activity', 'stats', 'proj-1'],
        enabled: true,
        staleTime: 30_000,
      }),
    );
    expect(result.current).toBe(fakeReturn);

    const options = mockUseQuery.mock.calls[0][0];
    options.queryFn();
    expect(mockActivityApi.stats).toHaveBeenCalledWith('proj-1');
  });

  it('is disabled when projectId is empty', () => {
    mockUseQuery.mockReturnValue({ data: undefined, isLoading: false });

    renderHook(() => useActivityStats(''));

    expect(mockUseQuery).toHaveBeenCalledWith(expect.objectContaining({ enabled: false }));
  });
});
