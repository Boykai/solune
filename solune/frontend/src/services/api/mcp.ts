import type { McpConfiguration, McpConfigurationListResponse, McpConfigurationCreate } from '@/types';
import { request } from './client';

export const mcpApi = {
  /**
   * List all MCP configurations for the authenticated user.
   */
  listMcps(): Promise<McpConfigurationListResponse> {
    return request<McpConfigurationListResponse>('/settings/mcps');
  },

  /**
   * Add a new MCP configuration.
   */
  createMcp(data: McpConfigurationCreate): Promise<McpConfiguration> {
    return request<McpConfiguration>('/settings/mcps', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  /**
   * Delete an MCP configuration by ID.
   */
  deleteMcp(mcpId: string): Promise<{ message: string }> {
    return request<{ message: string }>(`/settings/mcps/${mcpId}`, {
      method: 'DELETE',
    });
  },
};
