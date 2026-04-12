/**
 * Settings domain types.
 */

// ============ Settings Types (006-sqlite-settings-storage) ============

export type AIProviderType = 'copilot' | 'azure_openai';

export type ThemeModeType = 'dark' | 'light';

export type DefaultViewType = 'chat' | 'board' | 'settings';

export interface AIPreferences {
  provider: AIProviderType;
  model: string;
  temperature: number;
  agent_model: string;
  reasoning_effort?: string;
  agent_reasoning_effort?: string;
}

export interface DisplayPreferences {
  theme: ThemeModeType;
  default_view: DefaultViewType;
  sidebar_collapsed: boolean;
}

export interface WorkflowDefaults {
  default_repository: string | null;
  default_assignee: string;
  copilot_polling_interval: number;
}

export interface NotificationPreferences {
  task_status_change: boolean;
  agent_completion: boolean;
  new_recommendation: boolean;
  chat_mention: boolean;
}

export interface EffectiveUserSettings {
  ai: AIPreferences;
  display: DisplayPreferences;
  workflow: WorkflowDefaults;
  notifications: NotificationPreferences;
}

export interface GlobalSettings {
  ai: AIPreferences;
  display: DisplayPreferences;
  workflow: WorkflowDefaults;
  notifications: NotificationPreferences;
  allowed_models: string[];
}

export interface ProjectBoardConfig {
  column_order: string[];
  collapsed_columns: string[];
  show_estimates: boolean;
  queue_mode: boolean;
  auto_merge: boolean;
}

export interface ProjectAgentMapping {
  slug: string;
  display_name?: string | null;
}

export interface ProjectSpecificSettings {
  project_id: string;
  board_display_config?: ProjectBoardConfig | null;
  agent_pipeline_mappings?: Record<string, ProjectAgentMapping[]> | null;
}

export interface EffectiveProjectSettings {
  ai: AIPreferences;
  display: DisplayPreferences;
  workflow: WorkflowDefaults;
  notifications: NotificationPreferences;
  project: ProjectSpecificSettings;
}

// ── Update (PUT) request types ──

export interface AIPreferencesUpdate {
  provider?: AIProviderType | null;
  model?: string | null;
  temperature?: number | null;
  agent_model?: string | null;
  reasoning_effort?: string | null;
  agent_reasoning_effort?: string | null;
}

export interface DisplayPreferencesUpdate {
  theme?: ThemeModeType | null;
  default_view?: DefaultViewType | null;
  sidebar_collapsed?: boolean | null;
}

export interface WorkflowDefaultsUpdate {
  default_repository?: string | null;
  default_assignee?: string | null;
  copilot_polling_interval?: number | null;
}

export interface NotificationPreferencesUpdate {
  task_status_change?: boolean | null;
  agent_completion?: boolean | null;
  new_recommendation?: boolean | null;
  chat_mention?: boolean | null;
}

export interface UserPreferencesUpdate {
  ai?: AIPreferencesUpdate;
  display?: DisplayPreferencesUpdate;
  workflow?: WorkflowDefaultsUpdate;
  notifications?: NotificationPreferencesUpdate;
}

export interface GlobalSettingsUpdate {
  ai?: AIPreferencesUpdate;
  display?: DisplayPreferencesUpdate;
  workflow?: WorkflowDefaultsUpdate;
  notifications?: NotificationPreferencesUpdate;
  allowed_models?: string[];
}

export interface ProjectSettingsUpdate {
  board_display_config?: ProjectBoardConfig | null;
  agent_pipeline_mappings?: Record<string, ProjectAgentMapping[]> | null;
  queue_mode?: boolean | null;
  auto_merge?: boolean | null;
}

// ============ Dynamic Model Fetching Types (012-settings-dynamic-ux) ============

export interface ModelOption {
  id: string;
  name: string;
  provider: string;
  supported_reasoning_efforts?: string[];
  default_reasoning_effort?: string | null;
}

export interface ModelsResponse {
  status: 'success' | 'auth_required' | 'rate_limited' | 'error';
  models: ModelOption[];
  fetched_at: string | null;
  cache_hit: boolean;
  rate_limit_warning: boolean;
  message: string | null;
}

// ============ Signal Messaging Types (011-signal-chat-integration) ============

export type SignalConnectionStatus = 'pending' | 'connected' | 'error' | 'disconnected';

export type SignalNotificationMode = 'all' | 'actions_only' | 'confirmations_only' | 'none';

export type SignalLinkStatus = 'pending' | 'connected' | 'failed' | 'expired';

export interface SignalConnection {
  connection_id: string | null;
  status: SignalConnectionStatus | null;
  signal_identifier: string | null;
  notification_mode: SignalNotificationMode | null;
  linked_at: string | null;
  last_active_project_id: string | null;
}

export interface SignalLinkResponse {
  qr_code_base64: string;
  expires_in_seconds: number;
}

export interface SignalLinkStatusResponse {
  status: SignalLinkStatus;
  signal_identifier: string | null;
  error_message: string | null;
}

export interface SignalPreferences {
  notification_mode: SignalNotificationMode;
}

export interface SignalPreferencesUpdate {
  notification_mode: SignalNotificationMode;
}

export interface SignalBanner {
  id: string;
  message: string;
  created_at: string;
}

export interface SignalBannersResponse {
  banners: SignalBanner[];
}

// ============ MCP Configuration Types (012-mcp-settings-config) ============

export interface McpConfiguration {
  id: string;
  name: string;
  endpoint_url: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface McpConfigurationListResponse {
  mcps: McpConfiguration[];
  count: number;
}

export interface McpConfigurationCreate {
  name: string;
  endpoint_url: string;
}
