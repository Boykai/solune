import type {
  CleanupPreflightResponse,
  CleanupExecuteRequest,
  CleanupExecuteResponse,
  CleanupHistoryResponse,
} from '@/types';
import { request } from './client';

export const cleanupApi = {
  /**
   * Perform a preflight check: fetch branches, PRs, and project board issues.
   */
  preflight(owner: string, repo: string, projectId: string): Promise<CleanupPreflightResponse> {
    return request<CleanupPreflightResponse>('/cleanup/preflight', {
      method: 'POST',
      body: JSON.stringify({ owner, repo, project_id: projectId }),
    });
  },

  /**
   * Execute the cleanup operation: delete branches, close PRs, and delete orphaned issues.
   */
  execute(data: CleanupExecuteRequest): Promise<CleanupExecuteResponse> {
    return request<CleanupExecuteResponse>('/cleanup/execute', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  /**
   * Get audit trail of past cleanup operations.
   */
  history(owner: string, repo: string, limit = 10): Promise<CleanupHistoryResponse> {
    return request<CleanupHistoryResponse>(
      `/cleanup/history?owner=${encodeURIComponent(owner)}&repo=${encodeURIComponent(repo)}&limit=${limit}`
    );
  },
};
