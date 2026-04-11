# Contract: Domain-Scoped Types Interface (Frontend)

**Feature**: Codebase Modularity Review | **Date**: 2026-04-11

> Defines the structure of domain-scoped type files after splitting `types/index.ts`.

## Package Entry Point — `types/index.ts` (Barrel)

```typescript
// Barrel re-export — all existing imports continue to work
export * from './common';
export * from './chat';
export * from './board';
export * from './pipeline';
export * from './agents';
export * from './tasks';
export * from './projects';
export * from './settings';
export * from './chores';
export * from './workflow';
```

**Backward Compatibility**: `import { ChatMessage, BoardItem, Agent } from '@/types'` continues to work.

## Module: `types/common.ts` — Shared Types

Types used across multiple domains. These MUST NOT import from any domain-specific file.

```typescript
// Generic API response types
export type UUID = string;
export type DateString = string;
export interface PaginatedResponse<T> { items: T[]; total: number; page: number; }
export interface ApiError { message: string; code: string; details?: unknown; }

// User/session types
export interface UserSession { session_id: string; user_id: string; /* ... */ }
```

## Domain Modules

Each domain module exports types relevant to its domain. Domain modules may import from `./common` but MUST NOT import from other domain modules.

### `types/chat.ts`

```typescript
export interface ChatMessage { /* ... */ }
export interface ChatMessageRequest { /* ... */ }
export interface AITaskProposal { /* ... */ }
export interface IssueRecommendation { /* ... */ }
export interface Conversation { /* ... */ }
export interface ProposalConfirmRequest { /* ... */ }
// ... other chat-related types
```

### `types/board.ts`

```typescript
export interface BoardItem { /* ... */ }
export interface BoardColumn { /* ... */ }
export interface BoardView { /* ... */ }
// ... other board-related types
```

### `types/pipeline.ts`

```typescript
export interface Pipeline { /* ... */ }
export interface PipelineStep { /* ... */ }
export interface PipelineRun { /* ... */ }
// ... other pipeline-related types
```

### `types/agents.ts`

```typescript
export interface Agent { /* ... */ }
export interface AgentConfig { /* ... */ }
export interface AgentPreview { /* ... */ }
export type LifecycleStatus = 'active' | 'pending_pr' | 'pending_deletion';
// ... other agent-related types
```

### `types/tasks.ts`

```typescript
export interface Task { /* ... */ }
export type TaskStatus = 'todo' | 'in_progress' | 'done';
export type TaskPriority = 'low' | 'medium' | 'high' | 'urgent';
// ... other task-related types
```

## Import Rules

1. `common.ts` imports from **nothing** — it is the base
2. Domain modules import **only** from `./common` — never from each other
3. The barrel `index.ts` re-exports from all modules — never contains type definitions
4. Consumer code imports from `@/types` (the barrel) — never from sub-modules directly
5. When a type is used by exactly one domain, it belongs in that domain's file
6. When a type is used by 2+ domains, it belongs in `common.ts`

## Migration Strategy

1. Identify which types belong to which domain by analyzing imports
2. Move types to domain files, keeping `index.ts` as re-export barrel
3. Run `npx tsc --noEmit` after each domain extraction to catch errors
4. Final state: `types/index.ts` contains only `export * from './...'` lines
