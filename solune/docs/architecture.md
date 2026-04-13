# Architecture

Solune is a three-service application — a React frontend, a FastAPI backend, and a Signal sidecar — orchestrated by Docker Compose. The frontend hosts the authenticated workspace, the backend owns GitHub/API/state orchestration, and the sidecar handles Signal delivery.

## Overview

Solune runs as a full-stack web application with a shared bridge network and a single persistent SQLite database.

```text
┌───────────────────────────┐     ┌──────────────────────────────────┐     ┌──────────────────┐
│        Frontend           │────▶│            Backend               │────▶│    GitHub API     │
│  React 19 + Vite 8        │◀────│            FastAPI               │◀────│  GraphQL + REST   │
│  React Router 7           │ WS  │                                  │     │                  │
│  TanStack Query v5        │     │  ┌──────────────────────────┐    │     └──────────────────┘
│  Tailwind CSS 4           │     │  │ Workflow + Pipeline      │    │
└───────────────────────────┘     │  │ orchestration services    │    │     ┌──────────────────┐
                                  │  └──────────────────────────┘    │     │ signal-cli-rest- │
                                  │  ┌──────────────────────────┐    │ HTTP │ api (sidecar)    │
                                  │  │ Chat agent + plan mode   │────│────▶│ Signal relay      │
                                  │  │ + conversation storage   │◀───│─WS──│                  │
                                  │  └──────────────────────────┘    │     └──────────────────┘
                                  │  ┌──────────────────────────┐    │
                                  │  │ Apps, agents, tools,     │    │
                                  │  │ chores, metadata         │    │
                                  │  └──────────────────────────┘    │
                                  │  ┌──────────────────────────┐    │
                                  │  │ SQLite (WAL mode)        │    │
                                  │  │ migrations 023–044       │    │
                                  │  └──────────────────────────┘    │
                                  └──────────────────────────────────┘
```

## Docker Compose Services

| Service | Container | Port | Purpose |
|---------|-----------|------|---------|
| `backend` | `solune-backend` | 8000 | FastAPI API server |
| `frontend` | `solune-frontend` | 5173 → 80 | nginx serving the SPA and proxying `/api/` |
| `signal-api` | `solune-signal-api` | 8080 (internal) | `bbernhard/signal-cli-rest-api` sidecar |

Volumes: `solune-data` for SQLite persistence and `signal-cli-config` for Signal protocol state.

## Frontend Architecture

The frontend is a browser-routed SPA. `App.tsx` wires React Router, TanStack Query, the shared layout shell, and the lazy-loaded page surfaces.

- **Framework**: React 19 + TypeScript 6, built with Vite 8
- **Routing**: React Router 7 with page routes such as `/`, `/projects`, `/pipeline`, `/apps`, `/activity`, and `/help`
- **State management**: TanStack Query v5 for server state plus local React state for UI-only behavior
- **Real-time updates**: WebSocket + SSE fallbacks for project/pipeline updates; chat streaming over SSE
- **Styling**: Tailwind CSS 4 with reusable primitives and themed motion utilities
- **Error handling**: Shared `ErrorBoundary`, route-level retry/reload fallback, and query retry policies

### Frontend Module Map

| Area | Current modules |
|------|-----------------|
| `components/` | `activity`, `agents`, `apps`, `auth`, `board`, `chat`, `chores`, `command-palette`, `common`, `help`, `onboarding`, `pipeline`, `settings`, `tools`, `ui` |
| `pages/` | `ActivityPage`, `AgentsPage`, `AgentsPipelinePage`, `AppPage`, `AppsPage`, `ChoresPage`, `HelpPage`, `LoginPage`, `NotFoundPage`, `ProjectsPage`, `SettingsPage`, `ToolsPage` |
| `layout/` | `AppLayout`, `AuthGate`, `Sidebar`, `TopBar`, `Breadcrumb`, `ProjectSelector`, `NotificationBell`, `RateLimitBar`, `PageTransition` |
| `services/` | `api.ts` plus schema adapters and generated contract helpers |

### Frontend Hooks (grouped by domain)

Solune currently ships **63 production hooks** in `frontend/src/hooks/`.

| Domain | Hooks |
|--------|-------|
| **Activity & analytics** | `useActivityFeed`, `useActivityStats`, `useEntityHistory` |
| **Agents, tools, metadata, and settings** | `useAgentConfig`, `useAgentTools`, `useAgents`, `useMcpPresets`, `useMcpSettings`, `useMetadata`, `useModels`, `useRepoMcpConfig`, `useSettings`, `useSettingsForm`, `useTools` |
| **Apps & planning** | `useApps`, `useBuildProgress`, `usePlan` |
| **Board & project data** | `useAdaptivePolling`, `useBoardControls`, `useBoardDragDrop`, `useBoardProjection`, `useBoardRefresh`, `useProjectBoard`, `useProjects`, `useRealTimeSync`, `useRecentParentIssues` |
| **Chat & conversation UX** | `useChat`, `useChatHistory`, `useChatPanels`, `useChatProposals`, `useConversations`, `useFileUpload`, `useMentionAutocomplete`, `useSelectedPipeline`, `useVoiceInput` |
| **Chores, cleanup, and workflow editing** | `useChores`, `useCleanup`, `useCommands`, `usePipelineBoardMutations`, `usePipelineConfig`, `usePipelineModelOverride`, `usePipelineReducer`, `usePipelineValidation`, `useUndoRedo`, `useUndoableDelete`, `useUnsavedChanges`, `useUnsavedPipelineGuard`, `useWorkflow` |
| **Shared UI utilities** | `useAppTheme`, `useAuth`, `useBreadcrumb`, `useCommandPalette`, `useConfirmation`, `useCountdown`, `useCyclingPlaceholder`, `useFirstErrorFocus`, `useGlobalShortcuts`, `useInfiniteList`, `useMediaQuery`, `useNotifications`, `useOnboarding`, `useScrollLock`, `useSidebarState` |

### Chat surfaces

- **`AppPage`** renders `ChatPanelManager`, a multi-conversation workspace with resizable side-by-side panels on desktop and tabs on mobile.
- **`ChatPopup`** remains available from every authenticated page as the floating global chat assistant.
- **`useConversations`** + **`useChatPanels`** separate persisted conversation records from the locally persisted panel layout.

## Backend Architecture

The backend is the operational core of Solune. It handles authentication, GitHub API access, chat execution, pipeline orchestration, app creation flows, and all durable state.

- **Framework**: FastAPI with async endpoints and Pydantic v2 models
- **Database**: SQLite via `aiosqlite`, WAL mode, migrations `023` through `044`
- **Dependency injection**: `app.state` singletons accessed through `dependencies.py`
- **Middleware**: request IDs, CSP/security headers, CSRF, rate limiting, and admin-guard protections
- **Background execution**: `asyncio.TaskGroup` plus `TaskRegistry` for managed startup/shutdown work
- **Observability**: structured logging, optional OpenTelemetry, optional Sentry, and alert dispatch hooks

### Backend Module Layout

| Area | Current modules |
|------|-----------------|
| `api/` | `activity`, `agents`, `apps`, `auth`, `board`, `chat`, `chores`, `cleanup`, `health`, `mcp`, `metadata`, `onboarding`, `pipelines`, `projects`, `settings`, `signal`, `tasks`, `templates`, `tools`, `webhooks`, `workflow` |
| `models/` | Activity, agent, app, board, chat, chore, cleanup, guard, MCP, pagination, pipeline, plan, project, recommendation, settings, signal, task, tool, user, workflow models |
| `middleware/` | `admin_guard`, `csp`, `csrf`, `rate_limit`, `request_id` |
| `migrations/` | SQL migrations `023_consolidated_schema.sql` through `044_conversations.sql` |

### Backend services (grouped by responsibility)

| Responsibility | Services |
|----------------|----------|
| **Activity, observability, and alerts** | `activity_logger`, `activity_service`, `alert_dispatcher`, `logging_utils`, `otel_setup`, `rate_limit_tracker` |
| **Agents, plans, and chat execution** | `agent_creator`, `agent_middleware`, `agent_provider`, `agent_tools`, `agent_tracking`, `ai_utilities`, `chat_agent`, `chat_store`, `guard_service`, `label_classifier`, `plan_agent_provider`, `plan_issue_service`, `plan_parser`, `template_files`, `transcript_detector` |
| **Apps and templates** | `app_plan_orchestrator`, `app_service`, `app_templates/loader`, `app_templates/registry`, `app_templates/renderer` |
| **Pipeline lifecycle** | `collision_resolver`, `copilot_polling/*`, `fleet_dispatch`, `pipeline_estimate`, `pipeline_launcher`, `pipeline_orchestrator`, `pipeline_state_store`, `pipelines/pipeline_config`, `pipelines/service`, `task_registry`, `workflow_orchestrator/*` |
| **GitHub, metadata, and persistence** | `cache`, `database`, `done_items_store`, `encryption`, `github_auth`, `github_commit_workflow`, `github_projects/*`, `metadata_service`, `mcp_store`, `model_fetcher`, `pagination`, `session_store`, `settings_store`, `websocket` |
| **Feature-specific services** | `agents/service`, `agents/catalog`, `agents/agent_mcp_sync`, `chores/chat`, `chores/counter`, `chores/scheduler`, `chores/service`, `chores/template_builder`, `mcp_server/*`, `signal_bridge`, `signal_chat`, `signal_delivery`, `tools/presets`, `tools/service` |

### ChatAgentService

`ChatAgentService` wraps the Microsoft Agent Framework and powers Solune's chat experiences.

- Maintains an in-memory pool of agent sessions with configurable TTL and LRU eviction
- Registers project-scoped MCP tools when a project context is available
- Supports both standard JSON chat responses and streaming SSE responses
- Uses `session_id:conversation_id` keys for multi-conversation dashboard chat while leaving the floating popup conversation-unaware

### Startup lifecycle (`main.py`)

1. Configure logging and the global asyncio exception handler
2. Open SQLite, run pending migrations, and seed default rows
3. Register shared services on `app.state`
4. Resume polling / Signal background loops
5. Start session cleanup, watchdog, and MCP sync background tasks
6. On shutdown, drain task registries, stop listeners, and close the database

### nginx reverse proxy

The frontend `nginx.conf`:

- Proxies `/api/` to `backend:8000` with WebSocket upgrade support
- Serves built assets and SPA fallbacks for browser routes
- Sets basic browser security headers
- Exposes `/health` for container health checks

---

For architecture decisions and rationale, see the [Architecture Decision Records](decisions/README.md).

## What's next?

- [Agent Pipeline](agent-pipeline.md) — How execution stages, groups, and recovery work
- [Configuration](configuration.md) — Every environment variable and deployment switch
- [Project Structure](project-structure.md) — The up-to-date directory layout
