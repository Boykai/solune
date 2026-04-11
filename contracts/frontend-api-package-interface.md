# Contract: `services/api/` Package Interface (Frontend)

**Feature**: Codebase Modularity Review | **Date**: 2026-04-11

> Defines the public interface of the frontend `services/api/` package after splitting `services/api.ts`.

## Package Entry Point — `services/api/index.ts`

```typescript
// Barrel re-export — all existing imports continue to work
export { apiClient, handleApiError } from './client';
export { authApi } from './auth';
export { chatApi, conversationApi } from './chat';
export { boardApi } from './board';
export { tasksApi } from './tasks';
export { projectsApi } from './projects';
export { settingsApi } from './settings';
export { workflowApi } from './workflow';
export { metadataApi, signalApi } from './metadata';
export { agentsApi, agentToolsApi } from './agents';
export { pipelinesApi } from './pipelines';
export { choresApi } from './chores';
export { toolsApi } from './tools';
export { appsApi } from './apps';
export { activityApi } from './activity';
export { cleanupApi } from './cleanup';
export { modelsApi } from './models';
export { mcpApi } from './mcp';
```

**Backward Compatibility**: `import { chatApi } from '@/services/api'` continues to work via barrel.

## Module: `client.ts` — Shared API Client

```typescript
// Axios/fetch instance with interceptors
export const apiClient: AxiosInstance;

// Error handler used by all domain modules
export function handleApiError(error: unknown): never;

// Base URL configuration
export const API_BASE_URL: string;

// Request/response type helpers
export type ApiResponse<T> = { data: T; status: number };
```

**All domain modules import from `./client`** — this is the only shared dependency.

## Domain Module Pattern

Each domain module follows this pattern:

```typescript
// services/api/chat.ts (example)
import { apiClient, handleApiError } from './client';

export const chatApi = {
  sendMessage: async (params: SendMessageParams): Promise<ChatMessage> => { ... },
  getMessages: async (params: GetMessagesParams): Promise<ChatMessage[]> => { ... },
  // ... other methods
} as const;

export const conversationApi = {
  create: async (params: CreateConversationParams): Promise<Conversation> => { ... },
  list: async (): Promise<Conversation[]> => { ... },
  // ... other methods
} as const;
```

## Module Inventory

| Module | Exports | Approx. Lines |
|--------|---------|---------------|
| `client.ts` | `apiClient`, `handleApiError`, `API_BASE_URL` | ~200 |
| `auth.ts` | `authApi` | ~40 |
| `chat.ts` | `chatApi`, `conversationApi` | ~250 |
| `board.ts` | `boardApi` | ~80 |
| `tasks.ts` | `tasksApi` | ~50 |
| `projects.ts` | `projectsApi` | ~50 |
| `settings.ts` | `settingsApi` | ~80 |
| `workflow.ts` | `workflowApi` | ~60 |
| `metadata.ts` | `metadataApi`, `signalApi` | ~80 |
| `agents.ts` | `agentsApi`, `agentToolsApi` | ~200 |
| `pipelines.ts` | `pipelinesApi` | ~120 |
| `chores.ts` | `choresApi` | ~100 |
| `tools.ts` | `toolsApi` | ~80 |
| `apps.ts` | `appsApi` | ~80 |
| `activity.ts` | `activityApi` | ~50 |
| `cleanup.ts` | `cleanupApi` | ~40 |
| `models.ts` | `modelsApi` | ~30 |
| `mcp.ts` | `mcpApi` | ~40 |
| `index.ts` | Barrel re-export | ~30 |

## Import Rules

1. Domain modules import **only** from `./client` — never from each other
2. The barrel `index.ts` imports from all domain modules — never contains logic
3. Consumer code imports from `@/services/api` (the barrel) — never from sub-modules directly
4. Type imports come from `@/types` — API modules don't define their own types
