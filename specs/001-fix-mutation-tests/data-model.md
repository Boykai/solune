# Data Model: Fix Mutation Tests

**Feature**: 001-fix-mutation-tests
**Date**: 2026-04-02
**Status**: Complete

## Overview

This feature is primarily an infrastructure and CI configuration change. There are no new database entities, API endpoints, or persistent data models. The "entities" below describe the configuration-level structures that the implementation modifies.

## Entity: Mutation Shard (Backend)

A named subdivision of the backend mutation testing scope, defined in `run_mutmut_shard.py`.

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Shard identifier (e.g., `auth-and-projects`) |
| `paths` | `list[str]` | Source file/directory paths relative to `src/services/` (or `src/` for api-and-middleware) |

### Current State (5 shards defined in `run_mutmut_shard.py`)

| Shard Name | Modules |
|------------|---------|
| `auth-and-projects` | `github_auth.py`, `completion_providers.py`, `model_fetcher.py`, `github_projects/` |
| `orchestration` | `workflow_orchestrator/`, `pipelines/`, `copilot_polling/`, `task_registry.py`, `pipeline_state_store.py`, `agent_tracking.py` |
| `app-and-data` | `app_service.py`, `guard_service.py`, `metadata_service.py`, `cache.py`, `database.py`, `done_items_store.py`, `chat_store.py`, `session_store.py`, `settings_store.py`, `mcp_store.py`, `cleanup_service.py`, `encryption.py`, `websocket.py` |
| `agents-and-integrations` | `ai_agent.py`, `agent_creator.py`, `github_commit_workflow.py`, `signal_bridge.py`, `signal_chat.py`, `signal_delivery.py`, `tools/`, `agents/`, `chores/` |
| `api-and-middleware` | `api/`, `middleware/`, `utils.py` |

### Validation Rules

- Shard names must be unique within the `SHARDS` dictionary.
- Each source path must be a valid file or directory under `src/`.
- The union of all shard paths should cover the full mutation scope without overlaps (enforced by convention, not runtime).
- The CI workflow matrix must list exactly the same shard names as the `SHARDS` dictionary keys.

---

## Entity: Mutation Shard (Frontend)

A named subdivision of the frontend mutation testing scope, defined via CI workflow matrix and `--mutate` CLI overrides.

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Shard identifier (e.g., `board-polling-hooks`) |
| `mutate_globs` | `str` | Comma-separated Stryker `--mutate` glob patterns |
| `artifact_name` | `str` | CI artifact name for the shard's report |

### Proposed State (4 shards)

| Shard Name | Mutate Globs | Artifact |
|------------|-------------|----------|
| `board-polling-hooks` | `src/hooks/useAdaptivePolling.ts`, `src/hooks/useBoardProjection.ts`, `src/hooks/useBoard*.ts`, `src/hooks/*Poll*.ts` | `stryker-report-board-polling-hooks` |
| `data-query-hooks` | `src/hooks/useQuery*.ts`, `src/hooks/useMutation*.ts`, `src/hooks/use*Data*.ts`, `src/hooks/use*Fetch*.ts` | `stryker-report-data-query-hooks` |
| `general-hooks` | `src/hooks/**/*.ts` (minus board-polling and data-query globs) | `stryker-report-general-hooks` |
| `lib-utils` | `src/lib/**/*.ts` | `stryker-report-lib-utils` |

### Validation Rules

- Each glob must exclude test files (`!src/**/*.test.ts`, `!src/**/*.property.test.ts`).
- The union of all shard globs must cover every file in the original `stryker.config.mjs` `mutate` array.
- No file should be covered by more than one shard's glob set.
- Each shard must produce a separate report artifact with a unique name.

---

## Entity: Mutmut Workspace Configuration

The `[tool.mutmut]` section in `solune/backend/pyproject.toml` that controls which files are copied into the mutant workspace.

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `paths_to_mutate` | `list[str]` | Directories containing source files to mutate |
| `tests_dir` | `list[str]` | Directories containing test files |
| `also_copy` | `list[str]` | Additional files/directories to copy into the mutant workspace |

### Required Changes

The `also_copy` list must be extended to include paths that tests depend on but that are outside `src/`:

| Path | Required By | Resolution Method |
|------|------------|-------------------|
| `../templates/` | `registry.py` via `Path(__file__).resolve().parents[3] / "templates"` | Add `"../templates/"` to `also_copy` |

### Validation Rules

- Every file path resolved by production code using `Path(__file__)` traversal must be reachable from the mutant workspace.
- The `also_copy` list must include all runtime dependencies outside the `src/` tree that are exercised by the test suite.

---

## Entity: Provider Wrapper (test-utils.tsx)

The `renderWithProviders` test utility that wraps components in required React context providers.

### Current State (broken)

```
QueryClientProvider
├── ConfirmationDialogProvider → {children}  (render 1)
└── TooltipProvider → {children}             (render 2)
```

### Target State (fixed)

```
QueryClientProvider
└── ConfirmationDialogProvider
    └── TooltipProvider
        └── {children}                       (render 1 only)
```

### Validation Rules

- `{children}` must appear exactly once in the provider tree.
- All providers must be properly nested (not siblings).
- Provider order: QueryClientProvider (outermost) → ConfirmationDialogProvider → TooltipProvider (innermost).

---

## Relationships

```text
mutation-testing.yml
├── backend-mutation job
│   ├── matrix.shard → SHARDS dict in run_mutmut_shard.py
│   └── pyproject.toml [tool.mutmut] → also_copy → ../templates/
└── frontend-mutation job
    ├── matrix.shard → Stryker --mutate CLI overrides
    └── stryker.config.mjs (base config, shared settings)

testing.md
├── documents backend shards ↔ mutation-testing.yml backend matrix
├── documents frontend shards ↔ mutation-testing.yml frontend matrix
└── documents focused commands ↔ package.json scripts

test-utils.tsx
└── renderWithProviders → used by all component tests
```

## State Transitions

No runtime state transitions. All entities are static configuration. The mutation workflow is triggered weekly or manually and runs to completion.
