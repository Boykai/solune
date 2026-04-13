# Research: Remove Fleet Dispatch & Copilot CLI Code

**Branch**: `002-remove-fleet-dispatch` | **Date**: 2026-04-13

## Research Tasks

### R1: Fleet Dispatch Dependency Graph

**Task**: Map all imports and usages of fleet dispatch code to determine safe deletion order.

**Decision**: Six-phase dependency-ordered removal (matching spec).

**Rationale**: Files have clear layering — service → config/models → orchestrators → API/frontend → tests. Deleting leaf nodes first (standalone scripts, CLI plugin, service module, test files) breaks no imports. Model/config removal second. Orchestrator cleanup third since it imports from both service and models. API/frontend in parallel. Tests last.

**Alternatives considered**:
- Single atomic commit removing everything — rejected because import errors during development would block incremental verification.
- Bottom-up removal (models first) — rejected because it would break the service module before it's deleted.

### R2: Pipeline Orchestrator Legacy Fallback Stages

**Task**: Verify the hardcoded legacy pipeline stages that will replace the fleet-aware `_default_pipeline_stages()`.

**Decision**: The current fallback path in `_default_pipeline_stages()` already returns a fixed list of 11 stages (speckit.specify → speckit.plan → speckit.tasks → speckit.analyze → speckit.implement → quality-assurance/tester/copilot-review parallel → judge/linter parallel → devops). This becomes the sole return value as a module-level constant.

**Rationale**: The fallback has been the actual production default; the fleet config path was layered on top and gated behind `is_fleet_eligible()`. Promoting it to a constant simplifies the module and removes all fleet imports.

**Alternatives considered**:
- Keep the function but just remove fleet branches — rejected; the function becomes trivial (returns a constant) so a module-level `PIPELINE_STAGES` list is cleaner.
- Read stages from a non-fleet config file — rejected; YAGNI; no non-fleet config existed.

### R3: assign_copilot_to_issue() Caller Analysis

**Task**: Confirm all callers of `assign_copilot_to_issue()` are non-fleet and will be unaffected.

**Decision**: Preserve `assign_copilot_to_issue()` unchanged. Three callers verified:
1. `orchestrator.py` — used by the classic dispatch path (the path being preserved).
2. `app_plan_orchestrator.py` (line ~266) — independent planner, no fleet awareness.
3. `auto_merge.py` (line ~397) — merge automation, no fleet awareness.

**Rationale**: The function itself has no fleet logic; it simply calls the GitHub API to assign Copilot. Fleet dispatch called it too, but that's the caller being deleted, not the callee.

**Alternatives considered**: None — clearly a shared utility.

### R4: API Field Removal Impact

**Task**: Verify no external consumers depend on `dispatch_backend` and `agent_task_ids` in API responses.

**Decision**: Remove both fields from API responses, TypeScript types, and Zod schemas.

**Rationale**: 
- Zero UI component references to either field (verified by grep across `solune/frontend/src/`).
- The frontend schema test includes them but only as schema validation — the UI never reads them.
- No external API consumers documented; Solune's API is internal.

**Alternatives considered**:
- Mark as deprecated and return null — rejected; no consumers exist, so deprecation is unnecessary ceremony.

### R5: scripts/pipelines/ Directory Cleanup

**Task**: Determine if `scripts/pipelines/` will be empty after fleet file removal.

**Decision**: Delete the entire `scripts/pipelines/` directory. After removing `fleet-dispatch.json`, `pipeline-config.schema.json`, and the `templates/` subdirectory, the directory is empty.

**Rationale**: No non-fleet files exist in this directory. Verified by listing: only fleet-dispatch.json, pipeline-config.schema.json, and templates/ (all fleet).

**Alternatives considered**: Keep empty directory with .gitkeep — rejected; empty directories add noise.

### R6: Guard Config and Agent Definition Files

**Task**: Verify guard-config.yml and .github/agents/*.agent.md have no fleet-specific content.

**Decision**: No changes needed to either.

**Rationale**:
- `guard-config.yml` was checked; no fleet-specific entries exist.
- `.github/agents/*.agent.md` files define agent identities — fleet eligibility was a runtime check in `FleetDispatchService.is_fleet_eligible()`, not encoded in agent definitions.

**Alternatives considered**: None — confirmed no action needed.

### R7: Test Files Requiring Modification (Not Deletion)

**Task**: Identify all non-fleet test files that reference fleet identifiers and plan their cleanup.

**Decision**: 7 test files need modification (not deletion):

| File | References to Remove |
|------|---------------------|
| `test_pipeline_config_schema.py` | Fleet config schema validation tests |
| `test_workflow_orchestrator.py` | Fleet dispatch mocks, is_fleet_eligible assertions |
| `test_api_workflow.py` | dispatch_backend/agent_task_ids in response assertions |
| `test_issues.py` | Fleet label assertions |
| `test_helpers_polling.py` | _get_agent_task_id, _check_agent_task_status tests |
| `test_pipeline_state_store.py` | agent_task_ids in state fixtures |
| `pipeline.test.ts` | Fleet metadata Zod parsing test, agent_task_ids/dispatch_backend in fixtures |

**Rationale**: These files contain both fleet and non-fleet tests. The fleet-specific test cases and fixtures are removed; all non-fleet test cases are preserved.

**Alternatives considered**: None — straightforward surgical removal from mixed-concern test files.

### R8: Copilot Polling Cleanup Scope

**Task**: Map fleet references in the copilot_polling package.

**Decision**: Three files in `src/services/copilot_polling/` need modification:
1. `helpers.py` — delete `_get_agent_task_id()` and `_check_agent_task_status()`
2. `pipeline.py` — remove "Fleet task failed" log messages
3. `__init__.py` — remove `_check_agent_task_status` from imports/exports

**Rationale**: These functions exclusively served fleet task polling. The non-fleet polling path (PR status checks) is unaffected and preserved.

**Alternatives considered**: None — clean scoping, fleet-only functions.
