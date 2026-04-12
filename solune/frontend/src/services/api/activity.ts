import type { PaginatedResponse, ActivityEvent, ActivityStats } from '@/types';
import { request } from './client';

export const activityApi = {
  feed(
    projectId: string,
    params?: { limit?: number; cursor?: string; event_type?: string },
  ): Promise<PaginatedResponse<ActivityEvent>> {
    const qs = new URLSearchParams({ project_id: projectId });
    if (params?.limit) qs.set('limit', String(params.limit));
    if (params?.cursor) qs.set('cursor', params.cursor);
    if (params?.event_type) qs.set('event_type', params.event_type);
    return request<PaginatedResponse<ActivityEvent>>(`/activity?${qs}`);
  },

  stats(projectId: string): Promise<ActivityStats> {
    const qs = new URLSearchParams({ project_id: projectId });
    return request<ActivityStats>(`/activity/stats?${qs}`);
  },

  entityHistory(
    projectId: string,
    entityType: string,
    entityId: string,
    params?: { limit?: number; cursor?: string },
  ): Promise<PaginatedResponse<ActivityEvent>> {
    const qs = new URLSearchParams({ project_id: projectId });
    if (params?.limit) qs.set('limit', String(params.limit));
    if (params?.cursor) qs.set('cursor', params.cursor);
    const qsStr = qs.toString();
    return request<PaginatedResponse<ActivityEvent>>(
      `/activity/${entityType}/${entityId}${qsStr ? `?${qsStr}` : ''}`,
    );
  },
};
