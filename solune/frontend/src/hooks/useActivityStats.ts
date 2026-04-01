/**
 * useActivityStats — query wrapper for activity summary statistics.
 */

import { useQuery } from '@tanstack/react-query';
import { activityApi } from '@/services/api';
import type { ActivityStats } from '@/types';

export function useActivityStats(projectId: string) {
  const { data, isLoading, error } = useQuery<ActivityStats>({
    queryKey: ['activity', 'stats', projectId],
    queryFn: () => activityApi.stats(projectId),
    enabled: !!projectId,
    staleTime: 30_000,
  });

  return {
    stats: data ?? null,
    isLoading,
    error,
  };
}
