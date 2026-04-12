/**
 * API client service for Solune — barrel re-export.
 * All existing imports continue to work via this barrel.
 */

// Shared client infrastructure
export { ApiError, onAuthExpired, request, API_BASE_URL, getCsrfToken } from './client';

// Domain API namespaces
export { authApi } from './auth';
export { chatApi, conversationApi } from './chat';
export { boardApi } from './board';
export { tasksApi } from './tasks';
export { projectsApi } from './projects';
export { settingsApi } from './settings';
export { workflowApi } from './workflow';
export { metadataApi, signalApi } from './metadata';
export { agentsApi } from './agents';
export { pipelinesApi } from './pipelines';
export { choresApi } from './chores';
export { toolsApi, agentToolsApi } from './tools';
export { appsApi } from './apps';
export { activityApi } from './activity';
export { cleanupApi } from './cleanup';
export { modelsApi } from './models';
export { mcpApi } from './mcp';

// Agent types (previously defined in api.ts, re-exported for backward compatibility)
export type {
  AgentStatus,
  AgentSource,
  AgentConfig,
  AgentCreate,
  AgentUpdate,
  AgentCreateResult,
  AgentDeleteResult,
  AgentPendingCleanupResult,
  AgentChatMessage,
  AgentPreviewResponse,
  AgentChatResponse,
  BulkModelUpdateResult,
  AgentMcpSyncResult,
  CatalogAgent,
  ImportAgentRequest,
  ImportAgentResult,
  InstallAgentResult,
} from './agents';
