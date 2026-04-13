# Quickstart: Remove Fleet Dispatch & Copilot CLI Code

**Feature**: 006-remove-fleet-dispatch-cli
**Date**: 2026-04-13

## Prerequisites

- Python 3.12+ with `uv` package manager
- Node.js 18+ with `npm`
- Git

## Setup

```bash
cd solune/backend && uv sync --locked --extra dev
cd solune/frontend && npm ci
```

## Execution Order

This is a **deletion-heavy refactor** organized into 6 phases. Phases 1 and 2 must be sequential; Phases 3–6 can run in parallel after Phase 2 completes.

### Phase 1: Delete Standalone Artifacts

Delete files that have no dependents:

```bash
# Shell scripts
rm solune/scripts/fleet-dispatch.sh
rm solune/scripts/lib/fleet_dispatch_common.sh

# Pipeline config and templates
rm solune/scripts/pipelines/fleet-dispatch.json
rm solune/scripts/pipelines/pipeline-config.schema.json
rm -rf solune/scripts/pipelines/templates/

# CLI plugin
rm -rf solune/cli-plugin/

# Fleet backend service
rm solune/backend/src/services/fleet_dispatch.py

# Clean up empty directories
rmdir solune/scripts/pipelines/ 2>/dev/null || true
```

### Phase 2: Remove Fleet Models & Config

Edit `solune/backend/src/models/pipeline.py`:
- Delete 9 `FleetDispatch*` classes (lines 141–228)

Edit `solune/backend/src/services/workflow_orchestrator/config.py`:
- Delete `_DEFAULT_FLEET_DISPATCH_CONFIG`, `get_default_fleet_dispatch_config_path()`, `load_fleet_dispatch_config()`, `build_pipeline_stages_from_fleet_config()`
- Remove `FleetDispatchConfig` import

### Phase 3: Modify Core Orchestration

Edit files in parallel:

1. **`orchestrator.py`**: Remove `FleetDispatchService` import, `self.fleet_dispatch` instantiation, 3 `is_fleet_eligible()` branch sites, `_find_reusable_fleet_sub_issue()`, fleet logging, `agent_task_ids` from state writes
2. **`pipeline_orchestrator.py`**: Replace `_default_pipeline_stages()` with hardcoded legacy stages
3. **`copilot.py`**: Delete `list_agent_tasks()`, `get_agent_task()`, `_discover_agent_task_endpoint()`
4. **`copilot_polling/helpers.py`**: Remove `_get_agent_task_id()`, `_check_agent_task_status()`
5. **`api/workflow.py`**: Remove `_infer_dispatch_backend()`, fleet imports, fleet fields from response
6. **`pipeline_state_store.py`**: Remove `agent_task_ids` from serialization
7. **`workflow_orchestrator/models.py`**: Remove `agent_task_ids` field from `PipelineState`

### Phase 4: Frontend Cleanup

Edit files in parallel:

1. **`types/index.ts`**: Remove `agent_task_ids` and `dispatch_backend` from `PipelineStateInfo`
2. **`schemas/pipeline.ts`**: Remove same 2 fields from Zod schema

### Phase 5: Delete Fleet Tests

```bash
# Delete fleet-specific test files
rm solune/backend/tests/fleet_dispatch_harness.py
rm solune/backend/tests/unit/test_fleet_dispatch_cli.py
rm solune/backend/tests/unit/test_fleet_dispatch_service.py
rm solune/backend/tests/unit/test_fleet_dispatch_templates.py
rm solune/backend/tests/unit/test_fleet_parity.py
rm solune/backend/tests/integration/test_fleet_dispatch_smoke.py
rm solune/backend/tests/integration/test_fleet_app_dispatch.py
```

Modify test files to remove fleet assertions:
- `test_pipeline_config_schema.py`
- `test_workflow_orchestrator.py`
- `test_api_workflow.py`
- `test_issues.py`
- `test_helpers_polling.py`
- `test_pipeline_state_store.py`
- `frontend/src/services/schemas/pipeline.test.ts`

### Phase 6: Documentation

1. Edit `solune/docs/architectures/backend-components.mmd`: Remove `SVC_23["Fleet Dispatch"]` and renumber
2. Run `./solune/scripts/generate-diagrams.sh` to regenerate diagrams

## Verification

```bash
# Backend unit tests
cd solune/backend && uv run pytest tests/unit/ -x -q

# Backend integration tests
cd solune/backend && uv run pytest tests/integration/ -x -q

# Backend linting
cd solune/backend && uv run ruff check src/ tests/
cd solune/backend && uv run ruff format --check src/ tests/

# Backend type checking
cd solune/backend && uv run pyright src/

# Frontend type checking
cd solune/frontend && npx tsc --noEmit

# Frontend tests
cd solune/frontend && npx vitest run

# Zero fleet references (excluding CHANGELOG.md)
grep -rn "fleet\|FleetDispatch\|fleet_dispatch\|fleet-dispatch\|agent_task_ids\|dispatch_backend" solune/ \
  --exclude-dir=node_modules --exclude=CHANGELOG.md

# Verify preserved callers
grep -n "assign_copilot_to_issue" solune/backend/src/ -r
```

## Key Decisions

| Decision | Rationale |
|----------|-----------|
| `assign_copilot_to_issue()` preserved | Shared by `app_plan_orchestrator.py` and `auto_merge.py` |
| Legacy fallback stages become primary | Identical to fleet-derived stages; no regression |
| `dispatch_backend`/`agent_task_ids` removed from API | Frontend never renders them (zero UI references) |
| `.github/agents/*.agent.md` preserved | Fleet eligibility was runtime, not encoded in agent definitions |
| `guard-config.yml` unchanged | No fleet-specific entries |
| No database migration | Removed fields safely ignored on deserialization |
