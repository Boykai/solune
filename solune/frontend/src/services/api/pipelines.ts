import type {
  PipelineConfig,
  PipelineConfigCreate,
  PipelineConfigUpdate,
  PipelineConfigListResponse,
  PipelineIssueLaunchRequest,
  PresetSeedResult,
  ProjectPipelineAssignment,
  WorkflowResult,
} from '@/types';
import { request } from './client';

export const pipelinesApi = {
  list(projectId: string, sort?: string, order?: string): Promise<PipelineConfigListResponse> {
    const params = new URLSearchParams();
    if (sort) params.set('sort', sort);
    if (order) params.set('order', order);
    const qs = params.toString();
    return request<PipelineConfigListResponse>(`/pipelines/${projectId}${qs ? `?${qs}` : ''}`);
  },

  listPaginated(
    projectId: string,
    params: { limit: number; cursor?: string },
    sort?: string,
    order?: string,
  ): Promise<PipelineConfigListResponse & { next_cursor: string | null; has_more: boolean; total_count: number | null }> {
    const qs = new URLSearchParams({ limit: String(params.limit) });
    if (params.cursor) qs.set('cursor', params.cursor);
    if (sort) qs.set('sort', sort);
    if (order) qs.set('order', order);
    return request<PipelineConfigListResponse & { next_cursor: string | null; has_more: boolean; total_count: number | null }>(`/pipelines/${projectId}?${qs}`);
  },

  get(projectId: string, pipelineId: string): Promise<PipelineConfig> {
    return request<PipelineConfig>(`/pipelines/${projectId}/${pipelineId}`);
  },

  create(projectId: string, data: PipelineConfigCreate): Promise<PipelineConfig> {
    return request<PipelineConfig>(`/pipelines/${projectId}`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  update(
    projectId: string,
    pipelineId: string,
    data: PipelineConfigUpdate
  ): Promise<PipelineConfig> {
    return request<PipelineConfig>(`/pipelines/${projectId}/${pipelineId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },

  delete(projectId: string, pipelineId: string): Promise<{ success: boolean; deleted_id: string }> {
    return request<{ success: boolean; deleted_id: string }>(
      `/pipelines/${projectId}/${pipelineId}`,
      {
        method: 'DELETE',
      }
    );
  },

  seedPresets(projectId: string): Promise<PresetSeedResult> {
    return request<PresetSeedResult>(`/pipelines/${projectId}/seed-presets`, {
      method: 'POST',
    });
  },

  getAssignment(projectId: string): Promise<ProjectPipelineAssignment> {
    return request<ProjectPipelineAssignment>(`/pipelines/${projectId}/assignment`);
  },

  setAssignment(projectId: string, pipelineId: string): Promise<ProjectPipelineAssignment> {
    return request<ProjectPipelineAssignment>(`/pipelines/${projectId}/assignment`, {
      method: 'PUT',
      body: JSON.stringify({ pipeline_id: pipelineId }),
    });
  },

  launch(projectId: string, data: PipelineIssueLaunchRequest): Promise<WorkflowResult> {
    return request<WorkflowResult>(`/pipelines/${projectId}/launch`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  listRuns(
    pipelineId: string,
    params?: { limit?: number; offset?: number; status?: string },
  ): Promise<{
    runs: Array<Record<string, unknown>>;
    total: number;
    limit: number;
    offset: number;
  }> {
    const qs = new URLSearchParams();
    if (params?.limit) qs.set('limit', String(params.limit));
    if (params?.offset) qs.set('offset', String(params.offset));
    if (params?.status) qs.set('status', params.status);
    const qsStr = qs.toString();
    return request<{
      runs: Array<Record<string, unknown>>;
      total: number;
      limit: number;
      offset: number;
    }>(
      `/pipelines/${pipelineId}/runs${qsStr ? `?${qsStr}` : ''}`,
    );
  },

  getRun(
    pipelineId: string,
    runId: string,
  ): Promise<Record<string, unknown>> {
    return request<Record<string, unknown>>(`/pipelines/${pipelineId}/runs/${runId}`);
  },
};
