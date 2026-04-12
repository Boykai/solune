import type {
  App,
  AppAssetInventory,
  AppCreate,
  AppUpdate,
  AppStatusResponse,
  AppStatus,
  DeleteAppResult,
  Owner,
  AppCreateWithPlanRequest,
  AppCreateWithPlanResponse,
  AppPlanStatusResponse,
} from '@/types/apps';
import type { PaginatedResponse } from '@/types';
import { request } from './client';

export const appsApi = {
  list(status?: AppStatus): Promise<App[]> {
    const qs = status ? `?status=${status}` : '';
    return request<App[]>(`/apps${qs}`);
  },

  listPaginated(
    params: { limit: number; cursor?: string },
    status?: AppStatus,
  ): Promise<PaginatedResponse<App>> {
    const qs = new URLSearchParams({ limit: String(params.limit) });
    if (params.cursor) qs.set('cursor', params.cursor);
    if (status) qs.set('status', status);
    return request<PaginatedResponse<App>>(`/apps?${qs}`);
  },

  create(data: AppCreate): Promise<App> {
    return request<App>('/apps', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  get(appName: string): Promise<App> {
    return request<App>(`/apps/${appName}`);
  },

  update(appName: string, data: AppUpdate): Promise<App> {
    return request<App>(`/apps/${appName}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },

  delete(appName: string, force?: boolean): Promise<DeleteAppResult | void> {
    const qs = force ? '?force=true' : '';
    return request<DeleteAppResult | void>(`/apps/${appName}${qs}`, { method: 'DELETE' });
  },

  assets(appName: string): Promise<AppAssetInventory> {
    return request<AppAssetInventory>(`/apps/${appName}/assets`);
  },

  start(appName: string): Promise<AppStatusResponse> {
    return request<AppStatusResponse>(`/apps/${appName}/start`, { method: 'POST' });
  },

  stop(appName: string): Promise<AppStatusResponse> {
    return request<AppStatusResponse>(`/apps/${appName}/stop`, { method: 'POST' });
  },

  status(appName: string): Promise<AppStatusResponse> {
    return request<AppStatusResponse>(`/apps/${appName}/status`);
  },

  owners(): Promise<Owner[]> {
    return request<Owner[]>('/apps/owners');
  },

  createWithPlan(data: AppCreateWithPlanRequest): Promise<AppCreateWithPlanResponse> {
    return request<AppCreateWithPlanResponse>('/apps/create-with-plan', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  planStatus(appName: string): Promise<AppPlanStatusResponse> {
    return request<AppPlanStatusResponse>(`/apps/${appName}/plan-status`);
  },
};
