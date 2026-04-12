import type {
  Chore,
  ChoreCreate,
  ChoreTemplate,
  ChoreUpdate,
  ChoreStatus,
  ChoreTriggerResult,
  ChoreChatMessage,
  ChoreChatResponse,
  ChoreInlineUpdate,
  ChoreInlineUpdateResponse,
  ChoreCreateWithConfirmation,
  ChoreCreateResponse,
  EvaluateChoreTriggersResponse,
  ScheduleType,
  PaginatedResponse,
} from '@/types';
import { request } from './client';

export const choresApi = {
  /**
   * Idempotently seed built-in chore presets for a project.
   */
  seedPresets(projectId: string): Promise<{ created: number }> {
    return request<{ created: number }>(`/chores/${projectId}/seed-presets`, {
      method: 'POST',
    });
  },

  /**
   * List all chores for a project.
   */
  list(projectId: string): Promise<Chore[]> {
    return request<Chore[]>(`/chores/${projectId}`);
  },

  /**
   * List chores with cursor-based pagination and optional server-side filters.
   */
  listPaginated(
    projectId: string,
    params: { limit: number; cursor?: string; status?: ChoreStatus; scheduleType?: ScheduleType | 'unscheduled'; search?: string; sort?: 'name' | 'updated_at' | 'created_at' | 'attention'; order?: 'asc' | 'desc' },
  ): Promise<PaginatedResponse<Chore>> {
    const qs = new URLSearchParams({ limit: String(params.limit) });
    if (params.cursor) qs.set('cursor', params.cursor);
    if (params.status) qs.set('status', params.status);
    if (params.scheduleType) qs.set('schedule_type', params.scheduleType);
    if (params.search) qs.set('search', params.search);
    if (params.sort) qs.set('sort', params.sort);
    if (params.order) qs.set('order', params.order);
    return request<PaginatedResponse<Chore>>(`/chores/${projectId}?${qs}`);
  },

  /**
   * List available chore templates from the repo's .github/ISSUE_TEMPLATE/.
   */
  listTemplates(projectId: string): Promise<ChoreTemplate[]> {
    return request<ChoreTemplate[]>(`/chores/${projectId}/templates`);
  },

  /**
   * List ALL chore names for a project — unpaginated, unfiltered.
   * Used for accurate template membership checks.
   */
  listChoreNames(projectId: string): Promise<string[]> {
    return request<string[]>(`/chores/${projectId}/chore-names`);
  },

  /**
   * Create a new chore.
   */
  create(projectId: string, data: ChoreCreate): Promise<Chore> {
    return request<Chore>(`/chores/${projectId}`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  /**
   * Update a chore (schedule, status).
   */
  update(projectId: string, choreId: string, data: ChoreUpdate): Promise<Chore> {
    return request<Chore>(`/chores/${projectId}/${choreId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  },

  /**
   * Delete a chore.
   */
  delete(
    projectId: string,
    choreId: string
  ): Promise<{ deleted: boolean; closed_issue_number: number | null }> {
    return request<{ deleted: boolean; closed_issue_number: number | null }>(
      `/chores/${projectId}/${choreId}`,
      { method: 'DELETE' }
    );
  },

  /**
   * Manually trigger a chore.
   */
  trigger(
    projectId: string,
    choreId: string,
    parentIssueCount?: number
  ): Promise<ChoreTriggerResult> {
    return request<ChoreTriggerResult>(`/chores/${projectId}/${choreId}/trigger`, {
      method: 'POST',
      ...(parentIssueCount !== undefined
        ? { body: JSON.stringify({ parent_issue_count: parentIssueCount }) }
        : {}),
    });
  },

  /**
   * Send a chat message for sparse-input template refinement.
   */
  chat(projectId: string, data: ChoreChatMessage): Promise<ChoreChatResponse> {
    return request<ChoreChatResponse>(`/chores/${projectId}/chat`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  /**
   * Inline update a chore definition (creates a PR on save).
   */
  inlineUpdate(
    projectId: string,
    choreId: string,
    data: ChoreInlineUpdate
  ): Promise<ChoreInlineUpdateResponse> {
    return request<ChoreInlineUpdateResponse>(`/chores/${projectId}/${choreId}/inline-update`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },

  /**
   * Create a new chore with auto-merge flow.
   */
  createWithAutoMerge(
    projectId: string,
    data: ChoreCreateWithConfirmation
  ): Promise<ChoreCreateResponse> {
    return request<ChoreCreateResponse>(`/chores/${projectId}/create-with-merge`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  /**
   * Evaluate all active chore triggers.
   */
  evaluateTriggers(
    projectId?: string,
    parentIssueCount?: number
  ): Promise<EvaluateChoreTriggersResponse> {
    return request<EvaluateChoreTriggersResponse>('/chores/evaluate-triggers', {
      method: 'POST',
      body: JSON.stringify(
        projectId
          ? {
              project_id: projectId,
              ...(parentIssueCount !== undefined ? { parent_issue_count: parentIssueCount } : {}),
            }
          : {}
      ),
    });
  },
};
