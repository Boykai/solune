import type {
  McpToolConfig,
  McpToolConfigCreate,
  McpToolConfigUpdate,
  McpToolConfigListResponse,
  McpToolSyncResult,
  RepoMcpConfigResponse,
  RepoMcpServerConfig,
  RepoMcpServerUpdate,
  McpPresetListResponse,
  ToolChip,
  ToolDeleteResult,
} from '@/types';
import { request } from './client';

export const toolsApi = {
  getRepoConfig(projectId: string): Promise<RepoMcpConfigResponse> {
    return request<RepoMcpConfigResponse>(`/tools/${projectId}/repo-config`);
  },

  updateRepoServer(
    projectId: string,
    serverName: string,
    data: RepoMcpServerUpdate
  ): Promise<RepoMcpServerConfig> {
    return request<RepoMcpServerConfig>(
      `/tools/${projectId}/repo-config/${encodeURIComponent(serverName)}`,
      {
        method: 'PUT',
        body: JSON.stringify(data),
      }
    );
  },

  deleteRepoServer(projectId: string, serverName: string): Promise<RepoMcpServerConfig> {
    return request<RepoMcpServerConfig>(
      `/tools/${projectId}/repo-config/${encodeURIComponent(serverName)}`,
      {
        method: 'DELETE',
      }
    );
  },

  listPresets(): Promise<McpPresetListResponse> {
    return request<McpPresetListResponse>('/tools/presets');
  },

  list(projectId: string): Promise<McpToolConfigListResponse> {
    return request<McpToolConfigListResponse>(`/tools/${projectId}`);
  },

  listPaginated(
    projectId: string,
    params: { limit: number; cursor?: string },
  ): Promise<McpToolConfigListResponse & { next_cursor: string | null; has_more: boolean; total_count: number | null }> {
    const qs = new URLSearchParams({ limit: String(params.limit) });
    if (params.cursor) qs.set('cursor', params.cursor);
    return request<McpToolConfigListResponse & { next_cursor: string | null; has_more: boolean; total_count: number | null }>(`/tools/${projectId}?${qs}`);
  },

  get(projectId: string, toolId: string): Promise<McpToolConfig> {
    return request<McpToolConfig>(`/tools/${projectId}/${toolId}`);
  },

  create(projectId: string, data: McpToolConfigCreate): Promise<McpToolConfig> {
    return request<McpToolConfig>(`/tools/${projectId}`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  update(projectId: string, toolId: string, data: McpToolConfigUpdate): Promise<McpToolConfig> {
    return request<McpToolConfig>(`/tools/${projectId}/${toolId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },

  sync(projectId: string, toolId: string): Promise<McpToolSyncResult> {
    return request<McpToolSyncResult>(`/tools/${projectId}/${toolId}/sync`, {
      method: 'POST',
    });
  },

  delete(projectId: string, toolId: string, confirm = false): Promise<ToolDeleteResult> {
    const qs = confirm ? '?confirm=true' : '';
    return request<ToolDeleteResult>(`/tools/${projectId}/${toolId}${qs}`, {
      method: 'DELETE',
    });
  },
};

export const agentToolsApi = {
  getTools(projectId: string, agentId: string): Promise<{ tools: ToolChip[] }> {
    return request<{ tools: ToolChip[] }>(`/agents/${projectId}/${agentId}/tools`);
  },

  updateTools(
    projectId: string,
    agentId: string,
    toolIds: string[]
  ): Promise<{ tools: ToolChip[] }> {
    return request<{ tools: ToolChip[] }>(`/agents/${projectId}/${agentId}/tools`, {
      method: 'PUT',
      body: JSON.stringify({ tool_ids: toolIds }),
    });
  },
};
