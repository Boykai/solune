import type { PaginatedResponse } from '@/types';
import { request } from './client';

// ── Agent Types ─────────────────────────────────────────────────────────

export type AgentStatus = 'active' | 'pending_pr' | 'pending_deletion' | 'imported' | 'installed';
export type AgentSource = 'local' | 'repo' | 'both';

export interface AgentConfig {
  id: string;
  name: string;
  slug: string;
  description: string;
  icon_name: string | null;
  system_prompt: string;
  default_model_id: string;
  default_model_name: string;
  status: AgentStatus;
  tools: string[];
  status_column: string | null;
  github_issue_number: number | null;
  github_pr_number: number | null;
  branch_name: string | null;
  source: AgentSource;
  created_at: string | null;
  agent_type?: 'custom' | 'imported';
  catalog_source_url?: string | null;
  catalog_agent_id?: string | null;
  imported_at?: string | null;
}

export interface AgentCreate {
  name: string;
  description?: string;
  icon_name?: string | null;
  system_prompt: string;
  tools?: string[];
  status_column?: string;
  default_model_id?: string;
  default_model_name?: string;
  raw?: boolean;
}

export interface AgentUpdate {
  name?: string;
  description?: string;
  icon_name?: string | null;
  system_prompt?: string;
  tools?: string[];
  default_model_id?: string;
  default_model_name?: string;
}

export interface AgentCreateResult {
  agent: AgentConfig;
  pr_url: string;
  pr_number: number;
  issue_number: number | null;
  branch_name: string;
}

export interface AgentDeleteResult {
  success: boolean;
  pr_url: string;
  pr_number: number;
  issue_number: number | null;
}

export interface AgentPendingCleanupResult {
  success: boolean;
  deleted_count: number;
}

export interface AgentChatMessage {
  message: string;
  session_id?: string | null;
}

export interface AgentPreviewResponse {
  name: string;
  slug: string;
  description: string;
  system_prompt: string;
  status_column: string;
  tools: string[];
}

export interface AgentChatResponse {
  reply: string;
  session_id: string;
  is_complete: boolean;
  preview: AgentPreviewResponse | null;
}

export interface BulkModelUpdateResult {
  success: boolean;
  updated_count: number;
  failed_count: number;
  updated_agents: string[];
  failed_agents: string[];
  target_model_id: string;
  target_model_name: string;
}

export interface AgentMcpSyncResult {
  success: boolean;
  files_updated: number;
  files_skipped: number;
  files_unchanged: number;
  warnings: string[];
  errors: string[];
  synced_mcps: string[];
}

export interface CatalogAgent {
  id: string;
  name: string;
  description: string;
  source_url: string;
  already_imported: boolean;
}

export interface ImportAgentRequest {
  catalog_agent_id: string;
  name: string;
  description: string;
  source_url: string;
}

export interface ImportAgentResult {
  agent: AgentConfig;
  message: string;
}

export interface InstallAgentResult {
  agent: AgentConfig;
  pr_url: string;
  pr_number: number;
  issue_number: number | null;
  branch_name: string;
}

export const agentsApi = {
  list(projectId: string): Promise<AgentConfig[]> {
    return request<AgentConfig[]>(`/agents/${projectId}`);
  },

  listPaginated(
    projectId: string,
    params: { limit: number; cursor?: string },
  ): Promise<PaginatedResponse<AgentConfig>> {
    const qs = new URLSearchParams({ limit: String(params.limit) });
    if (params.cursor) qs.set('cursor', params.cursor);
    return request<PaginatedResponse<AgentConfig>>(`/agents/${projectId}?${qs}`);
  },

  pending(projectId: string): Promise<AgentConfig[]> {
    return request<AgentConfig[]>(`/agents/${projectId}/pending`);
  },

  clearPending(projectId: string): Promise<AgentPendingCleanupResult> {
    return request<AgentPendingCleanupResult>(`/agents/${projectId}/pending`, {
      method: 'DELETE',
    });
  },

  create(projectId: string, data: AgentCreate): Promise<AgentCreateResult> {
    return request<AgentCreateResult>(`/agents/${projectId}`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  update(projectId: string, agentId: string, data: AgentUpdate): Promise<AgentCreateResult> {
    return request<AgentCreateResult>(`/agents/${projectId}/${agentId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  },

  delete(projectId: string, agentId: string): Promise<AgentDeleteResult> {
    return request<AgentDeleteResult>(`/agents/${projectId}/${agentId}`, {
      method: 'DELETE',
    });
  },

  chat(projectId: string, data: AgentChatMessage): Promise<AgentChatResponse> {
    return request<AgentChatResponse>(`/agents/${projectId}/chat`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  bulkUpdateModels(
    projectId: string,
    targetModelId: string,
    targetModelName: string
  ): Promise<BulkModelUpdateResult> {
    return request<BulkModelUpdateResult>(`/agents/${projectId}/bulk-model`, {
      method: 'PATCH',
      body: JSON.stringify({ target_model_id: targetModelId, target_model_name: targetModelName }),
    });
  },

  syncMcps(projectId: string): Promise<AgentMcpSyncResult> {
    return request<AgentMcpSyncResult>(`/agents/${projectId}/sync-mcps`, {
      method: 'POST',
    });
  },

  browseCatalog(projectId: string): Promise<CatalogAgent[]> {
    return request<CatalogAgent[]>(`/agents/${projectId}/catalog`);
  },

  importAgent(projectId: string, data: ImportAgentRequest): Promise<ImportAgentResult> {
    return request<ImportAgentResult>(`/agents/${projectId}/import`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  installAgent(projectId: string, agentId: string): Promise<InstallAgentResult> {
    return request<InstallAgentResult>(`/agents/${projectId}/${agentId}/install`, {
      method: 'POST',
    });
  },
};
