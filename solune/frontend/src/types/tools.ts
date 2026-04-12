/**
 * MCP Tools domain types (027-mcp-tools-page).
 */

export type McpToolSyncStatus = 'synced' | 'pending' | 'error';

export interface McpToolConfig {
  id: string;
  name: string;
  description: string;
  endpoint_url: string;
  config_content: string;
  sync_status: McpToolSyncStatus;
  sync_error: string;
  synced_at: string | null;
  github_repo_target: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface McpToolConfigCreate {
  name: string;
  description: string;
  config_content: string;
  github_repo_target: string;
}

export interface McpToolConfigUpdate {
  name?: string;
  description?: string;
  config_content?: string;
  github_repo_target?: string;
}

export interface McpToolConfigListResponse {
  tools: McpToolConfig[];
  count: number;
}

export interface McpToolSyncResult {
  id: string;
  sync_status: McpToolSyncStatus;
  sync_error: string;
  synced_at: string | null;
  synced_paths: string[];
}

export interface RepoMcpServerConfig {
  name: string;
  config: Record<string, unknown>;
  source_paths: string[];
}

export interface RepoMcpServerUpdate {
  name: string;
  config_content: string;
}

export interface RepoMcpConfigResponse {
  paths_checked: string[];
  available_paths: string[];
  primary_path: string | null;
  servers: RepoMcpServerConfig[];
}

export interface McpPreset {
  id: string;
  name: string;
  description: string;
  category: string;
  icon: string;
  config_content: string;
}

export interface McpPresetListResponse {
  presets: McpPreset[];
  count: number;
}

export interface ToolChip {
  id: string;
  name: string;
  description: string;
}

export interface ToolDeleteResult {
  success: boolean;
  deleted_id: string | null;
  affected_agents: ToolChip[];
}
