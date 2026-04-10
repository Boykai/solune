# Testing

Solune is built test-first. The backend alone has 1,450+ tests spanning unit, integration, property, fuzz, and mutation testing. The frontend adds component tests (Vitest), end-to-end tests (Playwright), and its own mutation suite (Stryker). This guide covers how to run everything.

## Quick Commands

| What | Command |
|------|----------|
| Backend tests | `cd backend && pytest tests/ -v` |
| Frontend unit | `cd frontend && npm test` |
| Frontend E2E | `cd frontend && npm run test:e2e` |
| Backend coverage | `cd backend && pytest tests/ --cov=src` |
| Frontend coverage | `cd frontend && npm run test:coverage` |
| Backend mutation | `cd backend && mutmut run` |
| Frontend mutation | `cd frontend && npx stryker run` |

## Overview

| Tool | Scope | Count / Notes |
|------|-------|---------------|
| pytest + pytest-asyncio | Backend unit / integration / e2e | Extensive suite (hundreds of tests, auto-discovered) |
| Vitest + React Testing Library | Frontend unit | Growing suite of frontend unit tests (auto-discovered) |
| fast-check / Hypothesis | Property + fuzz testing | Input invariants, schema drift, and malformed payload coverage |
| Playwright | Frontend E2E | Multiple E2E spec files (auto-discovered) |
| mutmut / Stryker | Mutation testing | Scheduled CI plus local focused baselines |

## Mutation Testing

### Backend Mutation (mutmut)

```bash
cd backend
PATH="$PWD/.venv/bin:$PATH" .venv/bin/python -m mutmut run

# Review the latest result summary
PATH="$PWD/.venv/bin:$PATH" .venv/bin/python -m mutmut results

# Run a specific shard locally
PATH="$PWD/.venv/bin:$PATH" .venv/bin/python scripts/run_mutmut_shard.py --shard app-and-data --max-children 1
```

Backend mutation shards (5 total):

| Shard | Scope |
|-------|-------|
| `auth-and-projects` | `github_auth`, `completion_providers`, `model_fetcher`, `github_projects/` |
| `orchestration` | `workflow_orchestrator/`, `pipelines/`, `copilot_polling/`, `task_registry`, `pipeline_state_store`, `agent_tracking` |
| `app-and-data` | `app_service`, `guard_service`, `metadata_service`, `cache`, `database`, stores, `cleanup_service`, `encryption`, `websocket` |
| `agents-and-integrations` | `ai_agent`, `agent_creator`, `github_commit_workflow`, signals, `tools/`, `agents/`, `chores/` |
| `api-and-middleware` | `src/api/`, `src/middleware/`, `src/utils.py` |

Notes:

- Run `mutmut` from `backend/` so the generated `mutants/` tree uses the backend `pyproject.toml` configuration.
- The backend config mutates `src/services/` but also copies the rest of the `src/` modules and the `templates/` directory required by the test suite into `mutants/`.
- Backend tests seed `MUTANT_UNDER_TEST=stats` during stats collection so import-time service wiring does not crash the initial mutmut analysis pass.
- The shard runner temporarily narrows `paths_to_mutate` and restores `pyproject.toml` after each run, which keeps local and CI shard invocations aligned.

### Frontend Mutation (Stryker)

```bash
cd frontend

# Full mutation run (all shards combined)
npx stryker run

# Run a specific shard via STRYKER_SHARD env var
STRYKER_SHARD=hooks-board npx stryker run
STRYKER_SHARD=hooks-data npx stryker run
STRYKER_SHARD=hooks-general npx stryker run
STRYKER_SHARD=lib npx stryker run

# Or use npm scripts
npm run test:mutate:hooks-board
npm run test:mutate:hooks-data
npm run test:mutate:hooks-general
npm run test:mutate:lib

# Focused baseline on a single file
npx stryker run --mutate src/utils/formatTime.ts --testFiles src/utils/formatTime.property.test.ts --reporters clear-text
```

Frontend mutation shards (4 total, configured in `stryker.config.mjs` via `STRYKER_SHARD`):

| Shard | `STRYKER_SHARD` | Scope |
|-------|-----------------|-------|
| `hooks-board` | `hooks-board` | `useAdaptivePolling`, `useBoardProjection`, `useBoardRefresh`, `useProjectBoard`, `useRealTimeSync` |
| `hooks-data` | `hooks-data` | `useProjects`, `useChat`, `useChatHistory`, `useCommands`, `useWorkflow`, `useSettingsForm`, `useAuth` |
| `hooks-general` | `hooks-general` | All remaining hooks not in board or data shards |
| `lib` | `lib` | `src/lib/**/*.ts` (utilities, config builders, migrations) |

## Backend Tests

```bash
cd backend
source .venv/bin/activate

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run a focused fuzz suite
pytest tests/fuzz/test_api_input_fuzz.py -q

# Run specific test file
pytest tests/unit/test_copilot_polling.py -v

# Run specific test by name
pytest tests/ -k "test_pipeline_advancement" -v
```

### Test Structure

```text
backend/tests/
├── conftest.py              # Shared fixtures (db, sessions, mocks)
├── helpers/                 # Test helper utilities
├── unit/                    # 144 unit test files
│   ├── test_admin_authorization.py
│   ├── test_admin_guard.py
│   ├── test_agent_creator.py
│   ├── test_agent_mcp_sync.py
│   ├── test_agent_output.py
│   ├── test_agent_tracking.py
│   ├── test_agents_service.py
│   ├── test_ai_agent.py
│   ├── test_alert_dispatcher.py
│   ├── test_api_agents.py
│   ├── test_api_apps.py
│   ├── test_api_auth.py
│   ├── test_api_board.py
│   ├── test_api_chat.py
│   ├── test_api_cleanup.py
│   ├── test_api_health.py
│   ├── test_api_mcp.py
│   ├── test_api_metadata.py
│   ├── test_api_onboarding.py
│   ├── test_api_pipelines.py
│   ├── test_api_projects.py
│   ├── test_api_settings.py
│   ├── test_api_signal.py
│   ├── test_api_tasks.py
│   ├── test_api_tools.py
│   ├── test_api_webhook_models.py
│   ├── test_api_workflow.py
│   ├── test_app_service.py
│   ├── test_app_service_new_repo.py
│   ├── test_attachment_formatter.py
│   ├── test_auth_security.py
│   ├── test_auto_merge.py
│   ├── test_blocking_removal.py
│   ├── test_board.py
│   ├── test_branches.py
│   ├── test_cache.py
│   ├── test_cache_keys.py
│   ├── test_chat_store.py
│   ├── test_chat_transcript.py
│   ├── test_chores_api.py
│   ├── test_chores_chat.py
│   ├── test_chores_counter.py
│   ├── test_chores_scheduler.py
│   ├── test_chores_service.py
│   ├── test_chores_template_builder.py
│   ├── test_cleanup_service.py
│   ├── test_completion_child_pr.py
│   ├── test_completion_false_positive.py
│   ├── test_completion_merge.py
│   ├── test_completion_providers.py
│   ├── test_completion_signals.py
│   ├── test_config.py
│   ├── test_config_validation.py
│   ├── test_copilot.py
│   ├── test_copilot_polling.py
│   ├── test_csp.py
│   ├── test_csrf.py
│   ├── test_cursor_pagination.py
│   ├── test_database.py
│   ├── test_dependencies.py
│   ├── test_done_items_store.py
│   ├── test_error_responses.py
│   ├── test_exceptions.py
│   ├── test_filter_events_after.py
│   ├── test_github_agents.py
│   ├── test_github_auth.py
│   ├── test_github_commit_workflow.py
│   ├── test_github_projects.py
│   ├── test_github_projects_create.py
│   ├── test_github_repository.py
│   ├── test_graphql.py
│   ├── test_guard_service.py
│   ├── test_guard_signal_edge_cases.py
│   ├── test_helpers_polling.py
│   ├── test_identities.py
│   ├── test_issue_creation_retry.py
│   ├── test_issues.py
│   ├── test_label_constants.py
│   ├── test_label_fast_path.py
│   ├── test_label_manager.py
│   ├── test_label_manager_crud.py
│   ├── test_label_validation.py
│   ├── test_label_write_path.py
│   ├── test_lint_async.py
│   ├── test_logging_utils.py
│   ├── test_main.py
│   ├── test_mcp_store.py
│   ├── test_metadata_service.py
│   ├── test_middleware.py
│   ├── test_model_fetcher.py
│   ├── test_models.py
│   ├── test_module_boundaries.py
│   ├── test_oauth_state.py
│   ├── test_orchestrator.py
│   ├── test_otel_config.py
│   ├── test_pagination.py
│   ├── test_pipeline_events.py
│   ├── test_pipeline_run_models.py
│   ├── test_pipeline_state_service.py
│   ├── test_pipeline_state_store.py
│   ├── test_polling_helpers.py
│   ├── test_polling_loop.py
│   ├── test_polling_pipeline.py
│   ├── test_polling_state.py
│   ├── test_project_ownership.py
│   ├── test_projects.py
│   ├── test_prompts.py
│   ├── test_protocols.py
│   ├── test_pull_requests.py
│   ├── test_queue_mode.py
│   ├── test_rate_limiting.py
│   ├── test_readiness_endpoint.py
│   ├── test_recommendation_models.py
│   ├── test_recovery.py
│   ├── test_recovery_edge_cases.py
│   ├── test_recovery_selfheal.py
│   ├── test_regression_bugfixes.py
│   ├── test_repository.py
│   ├── test_request_id_middleware.py
│   ├── test_service.py
│   ├── test_session_store.py
│   ├── test_settings_auto_merge.py
│   ├── test_settings_store.py
│   ├── test_signal_bridge.py
│   ├── test_signal_bridge_edge_cases.py
│   ├── test_signal_chat.py
│   ├── test_signal_delivery.py
│   ├── test_state_validation.py
│   ├── test_state_validation_edge_cases.py
│   ├── test_state_validation_edges.py
│   ├── test_task_registry.py
│   ├── test_template_files.py
│   ├── test_time_dependent.py
│   ├── test_token_encryption.py
│   ├── test_tools_service.py
│   ├── test_transcript_analysis_prompt.py
│   ├── test_transcript_detector.py
│   ├── test_utils.py
│   ├── test_webhook_ci.py
│   ├── test_webhooks.py
│   ├── test_websocket.py
│   ├── test_workflow_orchestrator.py
│   ├── test_workflow_orchestrator_config.py
│   └── test_workflow_transitions.py
├── integration/             # Integration tests
└── test_api_e2e.py          # API end-to-end tests
```

### Configuration

Backend tests use `pyproject.toml`:

- `pytest-asyncio` for async test support
- `pytest-cov` for coverage reporting
- Test fixtures in `conftest.py` provide mock databases, sessions, and services

## Frontend Tests

### Unit Tests (Vitest)

```bash
cd frontend

# Run all unit tests
npm test

# Watch mode
npm run test:watch

# With coverage
npm run test:coverage

# Run a focused property-based suite
npm test -- src/utils/formatTime.property.test.ts
```

Test files are co-located with components:

- `components/auth/LoginButton.test.tsx`
- `components/board/AgentSaveBar.test.tsx`
- `components/board/BoardColumn.test.tsx`
- `components/board/IssueCard.test.tsx`
- `components/board/IssueDetailModal.test.tsx`
- `components/chat/CommandAutocomplete.test.tsx`
- `components/chat/IssueRecommendationPreview.test.tsx`
- `components/chat/MessageBubble.test.tsx`
- `components/chat/StatusChangePreview.test.tsx`
- `components/chat/TaskPreview.test.tsx`
- `components/chores/__tests__/AddChoreModal.test.tsx`
- `components/chores/__tests__/ChoreScheduleConfig.test.tsx`
- `components/chores/__tests__/ChoresPanel.test.tsx`
- `components/chores/__tests__/FeaturedRitualsPanel.test.tsx`
- `components/common/ErrorBoundary.test.tsx`
- `components/settings/DynamicDropdown.test.tsx`
- `components/settings/SettingsSection.test.tsx`
- `components/ThemeProvider.test.tsx`
- `components/ui/button.test.tsx`
- `components/ui/card.test.tsx`
- `components/ui/input.test.tsx`
- `hooks/useAuth.test.tsx`
- `hooks/useBoardRefresh.test.tsx`
- `hooks/useChat.test.tsx`
- `hooks/useChatHistory.test.ts`
- `hooks/useCommands.test.tsx`
- `hooks/useProjectBoard.test.tsx`
- `hooks/useProjects.test.tsx`
- `hooks/useRealTimeSync.test.tsx`
- `hooks/useSettingsForm.test.tsx`
- `hooks/useWorkflow.test.tsx`
- `lib/commands/registry.test.ts`
- `lib/commands/handlers/help.test.ts`
- `lib/commands/handlers/settings.test.ts`
- `lib/buildGitHubMcpConfig.test.ts`
- `components/tools/ToolsEnhancements.test.tsx`

### E2E Tests (Playwright)

```bash
cd frontend

# Run E2E tests
npm run test:e2e

# With browser visible
npm run test:e2e:headed

# Interactive UI mode
npm run test:e2e:ui

# View test report
npm run test:e2e:report
```

E2E specs:

- `e2e/auth.spec.ts`
- `e2e/board-navigation.spec.ts`
- `e2e/chat-interaction.spec.ts`
- `e2e/integration.spec.ts`
- `e2e/protected-routes.spec.ts`
- `e2e/responsive-board.spec.ts`
- `e2e/responsive-home.spec.ts`
- `e2e/responsive-settings.spec.ts`
- `e2e/settings-flow.spec.ts`
- `e2e/ui.spec.ts`

## CI Gates

- Backend CI enforces coverage and uploads `coverage.xml` plus `htmlcov/` artifacts.
- Frontend CI enforces Vitest coverage thresholds and uploads the `coverage/` artifact.
- Frontend E2E runs Playwright in Chromium on every push and pull request and uploads `e2e-report/` and `test-results/`.
- Contract validation exports backend OpenAPI, regenerates frontend types, and type-checks the generated contract.
- Flaky detection and mutation testing run in dedicated workflows on schedule or manual dispatch.
- Backend mutation CI runs five shard jobs (`auth-and-projects`, `orchestration`, `app-and-data`, `agents-and-integrations`, `api-and-middleware`) to keep reports smaller and faster to finish.
- Frontend mutation CI runs four shard jobs (`hooks-board`, `hooks-data`, `hooks-general`, `lib`) via `STRYKER_SHARD` env var, each finishing well under the 3-hour timeout.

## Code Quality

### Backend

```bash
cd backend
source .venv/bin/activate

# Linting
ruff check src/ tests/

# Formatting
ruff format src/ tests/

# Type checking
pyright src/
pyright -p pyrightconfig.tests.json
```

### Frontend

```bash
cd frontend

# Linting
npm run lint
npm run lint:fix

# Formatting
npm run format

# Type checking
npm run type-check
npm run type-check:test
```

### Pre-Commit Hook

Install the git pre-commit hook that runs ruff, backend/frontend source type checks, backend/frontend test type checks, vitest, and build:

```bash
./scripts/setup-hooks.sh
```

## Contributing Tests

When adding a new feature or fixing a bug, include tests that cover the change. Place backend tests in the appropriate `tests/unit/` or `tests/integration/` directory. Frontend component tests live alongside their source files. End-to-end tests go in `frontend/e2e/`.

---

## What's Next?

- [Explore the architecture](architecture.md) — understand how the components connect
- [Browse the project structure](project-structure.md) — find the right file to edit
- [Troubleshoot common issues](troubleshooting.md) — when tests fail unexpectedly
