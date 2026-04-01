import { useQuery } from '@tanstack/react-query';
import { activityApi } from '@/services/api';
import type { ActivityStats } from '@/types';

export function useActivityStats(projectId: string) {
  return useQuery<ActivityStats>({
    queryKey: ['activity', 'stats', projectId],
    queryFn: () => activityApi.stats(projectId),
    enabled: !!projectId,
    staleTime: 30_000,
  });
}
