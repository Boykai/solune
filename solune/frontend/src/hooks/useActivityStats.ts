/**
 * useActivityStats — fetches activity summary stats for the stats dashboard header.
 */

import { useQuery } from '@tanstack/react-query';
import { activityApi } from '@/services/api';
import type { ActivityStats } from '@/types';

export function useActivityStats(projectId: string) {
  return useQuery<ActivityStats>({
    queryKey: ['activity-stats', projectId],
    queryFn: () => activityApi.stats(projectId),
    staleTime: 60_000,
    enabled: !!projectId,
  });
}
