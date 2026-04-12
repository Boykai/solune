# Project Structure

This guide maps the current Solune repository layout so you can find the right frontend page, backend router, service, hook, or migration quickly.

## Top-Level Layout

```text
solune/
├── .devcontainer/                # GitHub Codespaces / Dev Container config
│   ├── devcontainer.json         #   Python 3.13, Node 25, Docker-in-Docker
│   ├── docker-compose.devcontainer.yml
│   ├── post-create.sh            #   Installs deps, creates venv, Playwright
│   └── post-start.sh             #   Prints Codespaces callback URL
├── .env.example                  # Environment template (documented)
├── .github/
│   ├── agents/                   # Custom Copilot agent definitions + MCP config
│   │   ├── archivist.agent.md
│   │   ├── designer.agent.md
│   │   ├── judge.agent.md
│   │   ├── linter.agent.md
│   │   ├── quality-assurance.agent.md
│   │   ├── tester.agent.md
│   │   ├── speckit.analyze.agent.md
│   │   ├── speckit.checklist.agent.md
│   │   ├── speckit.clarify.agent.md
│   │   ├── speckit.constitution.agent.md
│   │   ├── speckit.implement.agent.md
│   │   ├── speckit.plan.agent.md
│   │   ├── speckit.specify.agent.md
│   │   ├── speckit.tasks.agent.md
│   │   ├── speckit.taskstoissues.agent.md
│   │   ├── mcp.json              #   Built-in MCP server definitions (Context7, Azure, Bicep)
│   │   └── copilot-instructions.md
│   ├── prompts/                  # GitHub Copilot prompt files
│   └── workflows/                # GitHub Actions workflows
├── .pre-commit-config.yaml       # Pre-commit framework config
├── docker-compose.yml            # 3 services: backend, frontend, signal-api
├── README.md
├── docs/                         # Documentation (this directory)
│
├── backend/
│   ├── Dockerfile                # Python 3.14-slim, non-root user, health check
│   ├── pyproject.toml            # Dependencies + dev tools (ruff, pyright, pytest)
│   ├── src/
│   │   ├── main.py               # FastAPI app factory, lifespan, CORS, exception handlers
│   │   ├── config.py             # pydantic-settings from .env
│   │   ├── constants.py          # Status names, agent mappings, labels, cache keys
│   │   ├── dependencies.py       # FastAPI DI helpers (app.state singletons)
│   │   ├── exceptions.py         # AppException hierarchy
│   │   ├── utils.py              # BoundedSet, CIDict, utcnow, resolve_repository
│   │   ├── api/                  # Route handlers
│   │   │   ├── auth.py           #   OAuth flow, sessions, dev-login
│   │   │   ├── board.py          #   Project board (Kanban columns + items)
│   │   │   ├── chat.py           #   Chat messages, proposals, #agent command
│   │   │   ├── chores.py        #   Chore CRUD, triggering, chat, evaluation
│   │   │   ├── cleanup.py        #   Stale resource cleanup
│   │   │   ├── health.py         #   Health check endpoint
│   │   │   ├── mcp.py            #   MCP configuration endpoints
│   │   │   ├── pipelines.py      #   Pipeline CRUD + launch from imported issue
│   │   │   ├── projects.py       #   Project selection, tasks, WebSocket, SSE
│   │   │   ├── settings.py       #   User, global, project settings
│   │   │   ├── signal.py         #   Signal connection, preferences, banners
│   │   │   ├── tasks.py          #   Task CRUD
│   │   │   ├── agents.py         #   Agent CRUD and configuration
│   │   │   ├── metadata.py       #   Repository metadata (labels, branches, milestones)
│   │   │   ├── tools.py          #   MCP tool CRUD and configuration
│   │   │   ├── webhooks.py       #   GitHub webhook handler
│   │   │   └── workflow.py       #   Workflow config, pipeline, polling control
│   │   ├── middleware/
│   │   │   ├── admin_guard.py    #   AdminGuardMiddleware for @admin/@adminlock file protection
│   │   │   ├── csp.py            #   CSPMiddleware — Content Security Policy + HTTP security headers
│   │   │   ├── csrf.py           #   CSRFMiddleware — double-submit cookie CSRF protection
│   │   │   ├── rate_limit.py     #   RateLimitMiddleware — per-user request rate limiting
│   │   │   └── request_id.py     #   RequestIDMiddleware for request tracing
│   │   ├── migrations/           # SQL schema migrations (27 SQL files, 001–022, auto-run)
│   │   ├── models/               # Pydantic v2 data models
│   │   │   ├── agent.py          #   AgentSource, AgentAssignment, AvailableAgent
│   │   │   ├── agent_creator.py  #   CreationStep, AgentPreview, AgentCreationState
│   │   │   ├── board.py          #   Board columns, items, custom fields
│   │   │   ├── chat.py           #   ChatMessage, SenderType, ActionType
│   │   │   ├── chores.py         #   Chore models
│   │   │   ├── cleanup.py        #   Cleanup models
│   │   │   ├── mcp.py            #   MCP configuration models
│   │   │   ├── pipeline.py       #   PipelineConfig, ExecutionGroup, PipelineIssueLaunchRequest, assignments
│   │   │   ├── project.py        #   GitHubProject, StatusColumn
│   │   │   ├── agents.py         #   AgentConfig list/CRUD models
│   │   │   ├── recommendation.py #   AITaskProposal, IssueRecommendation, labels
│   │   │   ├── settings.py       #   User preferences, global/project settings
│   │   │   ├── signal.py         #   Signal connection, message, banner models
│   │   │   ├── task.py           #   Task / project item
│   │   │   ├── tools.py          #   MCP tool models
│   │   │   ├── user.py           #   UserSession
│   │   │   └── workflow.py       #   WorkflowConfiguration, WorkflowTransition
│   │   ├── prompts/              # AI prompt templates
│   │   │   ├── issue_generation.py  # System/user prompts for issue creation
│   │   │   └── task_generation.py   # Task generation prompts
│   │   └── services/             # Business logic layer
│   │       ├── github_projects/
│   │       │   ├── __init__.py    #   GitHubClientFactory (pooled githubkit SDK clients)
│   │       │   ├── service.py    #   GitHubProjectsService (REST + GraphQL via githubkit)
│   │       │   └── graphql.py    #   GraphQL queries and mutations
│   │       ├── copilot_polling/
│   │       │   ├── state.py      #   Module-level mutable state
│   │       │   ├── helpers.py    #   Sub-issue lookup, tracking helpers
│   │       │   ├── polling_loop.py  # Start/stop/tick scheduling
│   │       │   ├── agent_output.py  # Agent output extraction and posting
│   │       │   ├── pipeline.py   #   Pipeline advancement and transitions
│   │       │   ├── recovery.py   #   Stalled issue recovery, cooldowns
│   │       │   └── completion.py #   PR completion detection
│   │       ├── workflow_orchestrator/
│   │       │   ├── models.py     #   WorkflowContext, PipelineState, WorkflowState
│   │       │   ├── config.py     #   Async config load/persist/defaults/dedup
│   │       │   ├── transitions.py  # Status transitions, branch tracking
│   │       │   └── orchestrator.py  # WorkflowOrchestrator class
│   │       ├── chores/
│   │       │   ├── chat.py       #   Chore chat flow
│   │       │   ├── counter.py    #   Counter tracking
│   │       │   ├── scheduler.py  #   Schedule management
│   │       │   ├── service.py    #   ChoresService
│   │       │   └── template_builder.py  # Template generation
│   │       ├── agents/
│   │       │   ├── service.py    #   Agent configuration CRUD (SQLite + GitHub repo merge)
│   │       │   └── agent_mcp_sync.py  # MCP sync: enforces tools: ["*"] + mcp-servers on all agent files
│   │       ├── pipelines/
│   │       │   └── service.py    #   PipelineService CRUD and normalization
│   │       ├── tools/
│   │       │   ├── presets.py    #   Built-in MCP tool presets
│   │       │   └── service.py    #   ToolsService CRUD
│   │       ├── agent_creator.py  #   #agent command: guided agent creation flow
│   │       ├── agent_tracking.py #   Agent pipeline tracking (issue body markdown)
│   │       ├── agent_provider.py #   Agent provider factory (creates Agent Framework agents)
│   │       ├── agent_tools.py    #   Agent tool definitions (task proposals, status changes, recommendations)
│   │       ├── ai_agent.py       #   AI issue generation (via CompletionProvider)
│   │       ├── cache.py          #   In-memory TTL cache
│   │       ├── chat_agent.py     #   ChatAgentService (Microsoft Agent Framework wrapper)
│   │       ├── chat_store.py     #   Chat message persistence (async SQLite)
│   │       ├── cleanup_service.py  # Stale resource cleanup service
│   │       ├── completion_providers.py  # Pluggable LLM: Copilot SDK / Azure OpenAI
│   │       ├── database.py       #   aiosqlite connection, WAL mode, migrations
│   │       ├── encryption.py     #   Fernet encryption for tokens at rest
│   │       ├── github_auth.py    #   OAuth token exchange
│   │       ├── github_commit_workflow.py  # Git commit workflow helpers
│   │       ├── mcp_store.py      #   MCP configuration persistence
│   │       ├── metadata_service.py  # Repository metadata caching service
│   │       ├── model_fetcher.py  #   AI model metadata fetching
│   │       ├── pipeline_state_store.py  # Pipeline execution state persistence
│   │       ├── session_store.py  #   Session CRUD (async SQLite)
│   │       ├── settings_store.py #   Settings persistence (async SQLite)
│   │       ├── signal_bridge.py  #   Signal HTTP client, DB helpers, WS listener
│   │       ├── signal_chat.py    #   Inbound Signal message processing
│   │       ├── signal_delivery.py  # Outbound Signal formatting & retry
│   │       └── websocket.py      #   WebSocket connection manager
│   └── tests/
│       ├── conftest.py           # Shared test fixtures
│       ├── helpers/              # Test helper utilities
│       ├── unit/                 # 59 unit test files
│       ├── integration/          # Integration tests
│       └── test_api_e2e.py       # API end-to-end tests
│
├── frontend/
│   ├── Dockerfile                # Multi-stage: Node 25 build → nginx:1.29-alpine
│   ├── nginx.conf                # SPA + /api/ reverse proxy + security headers
│   ├── package.json              # Dependencies + scripts
│   ├── vite.config.ts            # Vite configuration
│   ├── vitest.config.ts          # Vitest configuration
│   ├── playwright.config.ts      # Playwright E2E configuration
│   ├── tsconfig.json             # TypeScript config
│   ├── eslint.config.js          # ESLint flat config
│   ├── src/
│   │   ├── App.tsx               # Root component (auth, routing, providers)
│   │   ├── main.tsx              # React entry point
│   │   ├── constants.ts          # Named timing/polling/cache constants
│   │   ├── types/index.ts        # TypeScript type definitions
│   │   ├── context/               # React context providers
│   │   │   └── RateLimitContext.tsx  # Rate limit status context
│   │   ├── data/                  # Static data and presets
│   │   │   └── preset-pipelines.ts  # Built-in pipeline preset definitions
│   │   ├── components/
│   │   │   ├── ThemeProvider.tsx  # Dark/light/system theme + cosmic transition overlay
│   │   │   ├── auth/             # LoginButton
│   │   │   ├── board/            # ProjectBoard, BoardColumn, IssueCard,
│   │   │   │                     # IssueDetailModal, ProjectIssueLaunchPanel,
│   │   │   │                     # agent config UI, cleanup UI
│   │   │   ├── chat/             # ChatInterface, ChatPopup, MessageBubble,
│   │   │   │                     # TaskPreview, StatusChangePreview,
│   │   │   │                     # IssueRecommendationPreview, CommandAutocomplete,
│   │   │   │                     # ChatToolbar, VoiceInputButton,
│   │   │   │                     # MentionInput, MentionAutocomplete,
│   │   │   │                     # FilePreviewChips, MarkdownRenderer,
│   │   │   │                     # ChatMessageSkeleton, PipelineWarningBanner,
│   │   │   │                     # PipelineIndicator
│   │   │   ├── common/           # ErrorBoundary, CompactPageHeader,
│   │   │   │                     # CelestialLoader, ThemedAgentIcon, agentIcons
│   │   │   ├── agents/           # AgentsPanel, AgentCard, AgentAvatar,
│   │   │   │                     # AgentChatFlow, AddAgentModal, AgentInlineEditor
│   │   │   ├── chores/           # ChoresPanel, ChoresToolbar, ChoresGrid,
│   │   │   │                     # ChoresSaveAllBar, ChoresSpotlight,
│   │   │   │                     # AddChoreModal, ChoreCard,
│   │   │   │                     # ChoreScheduleConfig, ChoreChatFlow,
│   │   │   │                     # ChoreInlineEditor, ConfirmChoreModal,
│   │   │   │                     # FeaturedRitualsPanel, PipelineSelector
│   │   │   ├── pipeline/         # PipelineBoard, PipelineFlowGraph, AgentNode,
│   │   │   │                     # StageCard, ExecutionGroupCard, ModelSelector,
│   │   │   │                     # PipelineToolbar
│   │   │   ├── tools/            # ToolsPanel, ToolSelectorModal, ToolCard,
│   │   │   │                     # McpPresetsGallery, EditRepoMcpModal,
│   │   │   │                     # UploadMcpModal, RepoConfigPanel,
│   │   │   │                     # GitHubMcpConfigGenerator
│   │   │   ├── settings/         # AIPreferences, PrimarySettings, SettingsSection,
│   │   │   │                     # ProjectSettings, SignalConnection, McpSettings,
│   │   │   │                     # DynamicDropdown
│   │   │   └── ui/               # Shared UI primitives (button, input, card, tooltip)
│   │   ├── hooks/                # React hooks (see Architecture doc)
│   │   │                         # useAuth, useChat, useChatHistory,
│   │   │                         # useChatProposals, useFileUpload,
│   │   │                         # useMentionAutocomplete, useVoiceInput,
│   │   │                         # useProjects, useWorkflow, and more
│   │   ├── lib/                 # Shared utilities and helpers
│   │   │   ├── utils.ts         #   cn() class-name helper
│   │   │   ├── buildGitHubMcpConfig.ts  # GitHub.com MCP config generator
│   │   │   ├── pipelineMigration.ts  # Legacy-to-group pipeline format migration
│   │   │   └── commands/        #   Chat command registry + handlers
│   │   ├── pages/                # AgentsPage, AgentsPipelinePage, AppPage,
│   │   │                         # ChoresPage, LoginPage, NotFoundPage,
│   │   │                         # ProjectsPage, SettingsPage, ToolsPage
│   │   ├── layout/               # App shell layout components
│   │   │                         # AppLayout, AuthGate, TopBar, Sidebar,
│   │   │                         # Breadcrumb, ProjectSelector, NotificationBell,
│   │   │                         # RateLimitBar
│   │   ├── services/api.ts       # Centralized HTTP/WS client
│   │   ├── test/                  # Shared test utilities, factories, and setup
│   │   └── utils/                # generateId, formatTime
│   └── e2e/                      # Playwright E2E test specs
│
├── scripts/
│   ├── pre-commit                # Git hook: ruff, pyright, eslint, tsc, vitest, build
│   └── setup-hooks.sh            # Install git hooks
│
└── specs/                        # Feature specifications (Spec Kit output)
```

## Backend

```text
backend/
├── Dockerfile
├── pyproject.toml
├── openapi.json            # Generated when contracts are exported
├── src/
│   ├── api/                # FastAPI routers
│   ├── middleware/         # Request ID, CSP, CSRF, rate-limit, admin-guard
│   ├── migrations/         # SQL migrations 023–044
│   ├── models/             # Pydantic request/response/domain models
│   ├── prompts/            # AI prompt templates
│   ├── services/           # Business logic and integrations
│   ├── config.py           # Environment settings schema
│   ├── constants.py        # Shared constants and labels
│   ├── dependencies.py     # FastAPI dependency helpers
│   ├── exceptions.py       # AppException hierarchy
│   ├── logging_utils.py    # Structured logging helpers
│   ├── main.py             # App factory and startup lifecycle
│   └── utils.py            # Shared utility functions
└── tests/
    ├── architecture/
    ├── chaos/
    ├── concurrency/
    ├── e2e/
    ├── fuzz/
    ├── helpers/
    ├── integration/
    ├── performance/
    ├── property/
    └── unit/
```

### Backend routers

`backend/src/api/` currently contains:

- `activity.py`, `agents.py`, `apps.py`, `auth.py`, `board.py`, `chat.py`, `chores.py`, `cleanup.py`
- `health.py`, `mcp.py`, `metadata.py`, `onboarding.py`, `pipelines.py`, `projects.py`, `settings.py`
- `signal.py`, `tasks.py`, `templates.py`, `tools.py`, `webhooks.py`, `workflow.py`

### Backend services

`backend/src/services/` is organized by domain plus focused support modules.

| Group | Current services |
|-------|------------------|
| **Activity / ops** | `activity_logger.py`, `activity_service.py`, `alert_dispatcher.py`, `otel_setup.py`, `rate_limit_tracker.py` |
| **Agent + chat flows** | `agent_creator.py`, `agent_middleware.py`, `agent_provider.py`, `agent_tools.py`, `agent_tracking.py`, `chat_agent.py`, `chat_store.py`, `guard_service.py`, `label_classifier.py`, `plan_agent_provider.py`, `plan_issue_service.py`, `plan_parser.py`, `template_files.py`, `transcript_detector.py` |
| **Apps** | `app_plan_orchestrator.py`, `app_service.py`, `app_templates/` |
| **Pipelines** | `collision_resolver.py`, `copilot_polling/`, `pipeline_estimate.py`, `pipeline_orchestrator.py`, `pipeline_state_store.py`, `pipelines/`, `task_registry.py`, `workflow_orchestrator/` |
| **Persistence / integrations** | `cache.py`, `database.py`, `done_items_store.py`, `encryption.py`, `github_auth.py`, `github_commit_workflow.py`, `github_projects/`, `mcp_store.py`, `metadata_service.py`, `model_fetcher.py`, `pagination.py`, `session_store.py`, `settings_store.py`, `signal_bridge.py`, `signal_chat.py`, `signal_delivery.py`, `websocket.py` |
| **Feature packages** | `agents/`, `chores/`, `mcp_server/`, `tools/` |

### Backend migrations

The repository no longer documents legacy `001–022` migrations as live files. The active migration chain is:

`023_consolidated_schema.sql` → `024_apps.sql` → `025_performance_indexes.sql` → `026_done_items_cache.sql` → `027_pipeline_state_persistence.sql` → `028_queue_mode.sql` → `029_activity_events.sql` → `030_copilot_review_requests.sql` → `031_auto_merge_and_pipeline_states.sql` → `032_phase8_mcp_version.sql` → `033_phase8_collision_events.sql` → `034_phase8_recovery_log.sql` → `035_chat_plans.sql` → `036_app_template_fields.sql` → `037_agent_import.sql` → `038_reasoning_effort_columns.sql` → `039_user_scoped_configs.sql` → `040_plan_versioning.sql` → `041_plan_step_status.sql` → `042_app_plan_orchestrations.sql` → `043_plan_selected_pipeline.sql` → `044_conversations.sql`

## Frontend

```text
frontend/
├── Dockerfile
├── nginx.conf
├── package.json
├── vite.config.ts
├── vitest.config.ts
├── playwright.config.ts
├── src/
│   ├── components/         # Reusable UI grouped by domain
│   ├── context/            # Shared React contexts
│   ├── data/               # Static presets and seed data
│   ├── hooks/              # Production hooks and colocated tests
│   ├── layout/             # Authenticated app shell
│   ├── lib/                # Shared utilities and command registry
│   ├── pages/              # Route-level page entry points
│   ├── services/           # API client and schemas
│   ├── test/               # Shared test helpers/setup
│   ├── types/              # Domain type definitions
│   └── utils/              # Small reusable helpers
└── e2e/                    # Playwright specs and snapshots
```

### Frontend component directories

`frontend/src/components/` currently contains these feature folders:

- `activity/`
- `agents/`
- `apps/`
- `auth/`
- `board/`
- `chat/`
- `chores/`
- `command-palette/`
- `common/`
- `help/`
- `layout/`
- `onboarding/`
- `pipeline/`
- `settings/`
- `tools/`
- `ui/`

### Frontend pages

`frontend/src/pages/` contains the current browser-routed surfaces:

- `ActivityPage.tsx`
- `AgentsPage.tsx`
- `AgentsPipelinePage.tsx`
- `AppPage.tsx`
- `AppsPage.tsx`
- `ChoresPage.tsx`
- `HelpPage.tsx`
- `LoginPage.tsx`
- `NotFoundPage.tsx`
- `ProjectsPage.tsx`
- `SettingsPage.tsx`
- `ToolsPage.tsx`

### Frontend hooks

Solune currently ships **63 production hooks** in `frontend/src/hooks/`.

| Group | Hooks |
|-------|-------|
| **Activity / analytics** | `useActivityFeed`, `useActivityStats`, `useEntityHistory` |
| **Agents / tools / settings** | `useAgentConfig`, `useAgentTools`, `useAgents`, `useMcpPresets`, `useMcpSettings`, `useMetadata`, `useModels`, `useRepoMcpConfig`, `useSettings`, `useSettingsForm`, `useTools` |
| **Apps / planning** | `useApps`, `useBuildProgress`, `usePlan` |
| **Board / projects** | `useAdaptivePolling`, `useBoardControls`, `useBoardDragDrop`, `useBoardProjection`, `useBoardRefresh`, `useProjectBoard`, `useProjects`, `useRealTimeSync`, `useRecentParentIssues` |
| **Chat / conversations** | `useChat`, `useChatHistory`, `useChatPanels`, `useChatProposals`, `useConversations`, `useFileUpload`, `useMentionAutocomplete`, `useSelectedPipeline`, `useVoiceInput` |
| **Pipeline / chores / workflow editing** | `useChores`, `useCleanup`, `useCommands`, `usePipelineBoardMutations`, `usePipelineConfig`, `usePipelineModelOverride`, `usePipelineReducer`, `usePipelineValidation`, `useUndoRedo`, `useUndoableDelete`, `useUnsavedChanges`, `useUnsavedPipelineGuard`, `useWorkflow` |
| **Shared UI helpers** | `useAppTheme`, `useAuth`, `useBreadcrumb`, `useCommandPalette`, `useConfirmation`, `useCountdown`, `useCyclingPlaceholder`, `useFirstErrorFocus`, `useGlobalShortcuts`, `useInfiniteList`, `useMediaQuery`, `useNotifications`, `useOnboarding`, `useScrollLock`, `useSidebarState` |

## Tests and tooling

- `backend/tests/` includes `architecture`, `chaos`, `concurrency`, `e2e`, `fuzz`, `integration`, `performance`, `property`, and `unit` coverage.
- `frontend/e2e/` includes route, responsive-layout, chat, agents, MCP, settings, and pipeline monitoring specs.
- `scripts/export-openapi.py` regenerates `backend/openapi.json` when backend dependencies are available.

---

## What's next?

- [Architecture](architecture.md) — service interactions and system boundaries
- [API Reference](api-reference.md) — current HTTP, WebSocket, and SSE endpoints
- [Testing](testing.md) — how the repository validates frontend and backend changes
