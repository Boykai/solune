# Project Structure

This guide maps the current Solune repository layout so you can find the right frontend page, backend router, service, hook, or migration quickly.

## Top-Level Layout

```text
solune/
├── .devcontainer/          # Codespaces / devcontainer setup
├── .github/                # Prompts, workflows, and custom agent definitions
├── backend/                # FastAPI application, tests, and migrations
├── docs/                   # Product, architecture, and operational documentation
├── frontend/               # React 19 + Vite 8 SPA
├── scripts/                # Repo maintenance, OpenAPI export, and hook helpers
└── specs/                  # Spec Kit-generated feature specs
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
- `signal.py`, `tasks.py`, `templates.py`, `tools.py`, `webhook_models.py`, `webhooks.py`, `workflow.py`

### Backend services

`backend/src/services/` is organized by domain plus focused support modules.

| Group | Current services |
|-------|------------------|
| **Activity / ops** | `activity_logger.py`, `activity_service.py`, `alert_dispatcher.py`, `otel_setup.py`, `rate_limit_tracker.py`, `resettable_state.py` |
| **Agent + chat flows** | `agent_creator.py`, `agent_middleware.py`, `agent_provider.py`, `agent_tools.py`, `agent_tracking.py`, `ai_utilities.py`, `chat_agent.py`, `chat_store.py`, `guard_service.py`, `label_classifier.py`, `plan_agent_provider.py`, `plan_issue_service.py`, `plan_parser.py`, `template_files.py`, `transcript_detector.py` |
| **Apps** | `app_plan_orchestrator.py`, `app_service.py`, `app_templates/` |
| **Pipelines** | `cleanup_service.py`, `collision_resolver.py`, `copilot_polling/`, `pipeline_estimate.py`, `pipeline_launcher.py`, `pipeline_orchestrator.py`, `pipeline_state_store.py`, `pipelines/`, `task_registry.py`, `workflow_orchestrator/` |
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
- `scripts/check-suppressions.sh` verifies that all lint/test suppressions carry a `reason:` justification (see [Suppression Policy](testing.md#suppression-policy)).

---

## What's next?

- [Architecture](architecture.md) — service interactions and system boundaries
- [API Reference](api-reference.md) — current HTTP, WebSocket, and SSE endpoints
- [Testing](testing.md) — how the repository validates frontend and backend changes
