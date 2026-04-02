# Data Model: Fix Mutation Testing Infrastructure

**Feature**: 005-fix-mutation-tests
**Date**: 2026-04-02

## Overview

This feature is infrastructure/configuration-focused. There are no new database entities, API models, or runtime data structures. The "data model" here describes the configuration entities and their relationships.

## Configuration Entities

### 1. mutmut Configuration (`pyproject.toml` `[tool.mutmut]`)

| Field | Type | Current Value | Change |
|-------|------|---------------|--------|
| `paths_to_mutate` | `list[str]` | `["src/services/"]` | No change (overridden per shard by `run_mutmut_shard.py`) |
| `tests_dir` | `list[str]` | `["tests/"]` | No change |
| `debug` | `bool` | `true` | No change |
| `also_copy` | `list[str]` | 15 entries (src modules) | **Add `"templates/"`** |

**Validation**: After adding `templates/`, the mutant workspace must contain `templates/app-templates/` with all 4 template subdirectories (`api-fastapi`, `cli-python`, `dashboard-react`, `saas-react-fastapi`).

### 2. Backend Shard Definition (`run_mutmut_shard.py` `SHARDS`)

| Shard Name | Paths | CI Status |
|------------|-------|-----------|
| `auth-and-projects` | `github_auth.py`, `completion_providers.py`, `model_fetcher.py`, `github_projects/` | ✅ In CI |
| `orchestration` | `workflow_orchestrator/`, `pipelines/`, `copilot_polling/`, `task_registry.py`, `pipeline_state_store.py`, `agent_tracking.py` | ✅ In CI |
| `app-and-data` | `app_service.py`, `guard_service.py`, `metadata_service.py`, `cache.py`, `database.py`, + 8 more stores/services | ✅ In CI |
| `agents-and-integrations` | `ai_agent.py`, `agent_creator.py`, `github_commit_workflow.py`, `signal_*`, `tools/`, `agents/`, `chores/` | ✅ In CI |
| `api-and-middleware` | `src/api/`, `src/middleware/`, `src/utils.py` | **❌ Missing from CI → Add** |

**Validation**: `mutation-testing.yml` matrix entries must exactly match `SHARDS.keys()` in `run_mutmut_shard.py`.

### 3. Frontend Stryker Shard Definition

| Shard Name | Config File | Mutate Globs | Description |
|------------|-------------|--------------|-------------|
| `hooks-board` | `stryker-hooks-board.config.mjs` | `src/hooks/useAdaptivePolling.ts`, `src/hooks/useBoardProjection.ts`, `src/hooks/useBoardRefresh.ts`, `src/hooks/useProjectBoard.ts`, `src/hooks/useRealTimeSync.ts` | Board, polling, and projection hooks |
| `hooks-data` | `stryker-hooks-data.config.mjs` | `src/hooks/useProjects.ts`, `src/hooks/useChat.ts`, `src/hooks/useChatHistory.ts`, `src/hooks/useCommands.ts`, `src/hooks/useWorkflow.ts`, `src/hooks/useSettingsForm.ts`, `src/hooks/useAuth.ts` | Data-fetching and state management hooks |
| `hooks-general` | `stryker-hooks-general.config.mjs` | `src/hooks/**/*.ts` minus board and data hooks, `!src/**/*.test.ts` | Remaining hooks |
| `lib` | `stryker-lib.config.mjs` | `src/lib/**/*.ts`, `!src/**/*.test.ts`, `!src/**/*.property.test.ts` | Utility functions, command registry, config builders |

**Validation**: Union of all shard globs must equal the original `stryker.config.mjs` `mutate` scope.

### 4. test-utils.tsx Provider Tree

**Current (broken)**:
```
QueryClientProvider
├── ConfirmationDialogProvider → children
└── TooltipProvider → children  (duplicate render!)
```

**Fixed**:
```
QueryClientProvider
└── ConfirmationDialogProvider
    └── TooltipProvider → children  (single render)
```

## State Transitions

N/A — no runtime state machines. All changes are static configuration.

## Relationships

```text
pyproject.toml [tool.mutmut].also_copy
    └── templates/  ──→  registry.py reads templates/app-templates/
                          └── test_agent_tools.py exercises list_app_templates()

run_mutmut_shard.py SHARDS
    └── mutation-testing.yml backend matrix (must match 1:1)

stryker-*.config.mjs (4 files)
    └── mutation-testing.yml frontend matrix
    └── package.json scripts (1 per shard)

test-utils.tsx renderWithProviders()
    └── used by ~30+ frontend test files
```
