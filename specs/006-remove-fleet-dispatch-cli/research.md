# Research: Remove Fleet Dispatch & Copilot CLI Code

**Feature**: 006-remove-fleet-dispatch-cli
**Date**: 2026-04-13
**Status**: Complete

## R1: Fleet Dispatch Service Dependency Map

**Task**: Identify all consumers and dependents of `FleetDispatchService` to safely remove the module.

**Decision**: Delete `fleet_dispatch.py` and update all 4 consuming modules to remove fleet imports and calls.

**Rationale**: The `FleetDispatchService` class (356 lines) is consumed by exactly 4 modules:
1. `orchestrator.py` — imports `FleetDispatchService`, instantiates `self.fleet_dispatch`, calls `is_fleet_eligible()`, `build_dispatch_payload()`, `build_fleet_sub_issue_labels()`, `resolve_task_id()`
2. `workflow.py` (API) — imports `FleetDispatchService`, calls `FleetDispatchService.is_fleet_eligible()` in `_infer_dispatch_backend()`
3. `copilot_polling/helpers.py` — lazily imports `FleetDispatchService.normalize_task_state()`
4. `pipeline_orchestrator.py` — indirectly consumes fleet config via `load_fleet_dispatch_config()` and `build_pipeline_stages_from_fleet_config()`

No external callers exist. All paths either branch on `is_fleet_eligible()` (with a fallback "classic" path already present) or use fleet-only utilities with no non-fleet consumers.

**Alternatives considered**: Keeping `FleetDispatchService` as a stub — rejected because it would leave dead code and confuse future maintainers.

---

## R2: Pipeline Orchestrator Stage Fallback Verification

**Task**: Confirm that the hardcoded legacy fallback in `_default_pipeline_stages()` is production-equivalent to the fleet-config-derived stages.

**Decision**: Replace `_default_pipeline_stages()` with the hardcoded legacy stages directly.

**Rationale**: `pipeline_orchestrator.py` already defines a complete fallback stage list (11 stages across 4 groups) inside the `except` branch of `_default_pipeline_stages()`. This fallback is identical in structure to what `build_pipeline_stages_from_fleet_config()` produces from `fleet-dispatch.json`. The function currently:
1. Tries to load from `fleet-dispatch.json`
2. Falls back to hardcoded stages on any exception

After removal, the hardcoded stages become the sole definition. No behavioral regression — the fallback was designed as the legacy path.

**Alternatives considered**: Keeping a separate config file (YAML/TOML) for stages — rejected per YAGNI; the 11-stage list is static and rarely changes.

---

## R3: `assign_copilot_to_issue()` Caller Analysis

**Task**: Verify that `assign_copilot_to_issue()` in `copilot.py` has non-fleet callers and must be preserved.

**Decision**: Preserve `assign_copilot_to_issue()` — it is shared by both fleet and non-fleet callers.

**Rationale**: Two independent callers exist:
1. `app_plan_orchestrator.py` — uses it for standard Copilot assignment in app planning flows
2. `auto_merge.py` — uses it for Copilot assignment during auto-merge flows

Neither caller depends on fleet dispatch. The function itself has no fleet-specific logic — it's a general-purpose GitHub Copilot assignment helper.

**Alternatives considered**: None — clear shared utility, no fleet coupling.

---

## R4: Frontend Field Impact Assessment

**Task**: Determine whether `agent_task_ids` and `dispatch_backend` fields in frontend types are rendered by any UI component.

**Decision**: Remove both fields from frontend types and schemas with zero UI impact.

**Rationale**: Comprehensive grep across `solune/frontend/src/` shows:
- `agent_task_ids` appears only in `types/index.ts` (type definition), `schemas/pipeline.ts` (Zod schema), and `schemas/pipeline.test.ts` (test)
- `dispatch_backend` appears only in the same 3 files
- Zero references in any React component, hook, or page file
- The fields were added for observability but never wired to UI elements

**Alternatives considered**: Keeping fields as optional/deprecated — rejected because unused fields add confusion and maintenance cost.

---

## R5: `agent_task_ids` in Pipeline State Store

**Task**: Assess the impact of removing `agent_task_ids` from `PipelineState` and `pipeline_state_store`.

**Decision**: Remove `agent_task_ids` from `PipelineState` dataclass and `pipeline_state_store.py` serialization/deserialization.

**Rationale**: `agent_task_ids` is a `dict[str, str]` field in the `PipelineState` dataclass (`models.py` line 201). It is written to by `orchestrator.py` during fleet dispatch flows and read by:
1. `copilot_polling/helpers.py` via `_get_agent_task_id()` — fleet-only
2. `orchestrator.py` — fleet-only state writes
3. `workflow.py` (API) — returns field in response, but frontend never renders it
4. `pipeline_state_store.py` — serialization/deserialization

Existing SQLite rows with `agent_task_ids` in JSON metadata will harmlessly ignore the removed field on deserialization (Pydantic/dataclass defaults). No migration needed.

**Alternatives considered**: Database migration to strip existing rows — rejected because the field is safely ignored when absent from the deserialized model.

---

## R6: Copilot Polling Fleet Task Check Flow

**Task**: Understand the fleet-specific polling flow to safely remove `_get_agent_task_id()` and `_check_agent_task_status()`.

**Decision**: Remove both functions from `copilot_polling/helpers.py` and all fleet-related log messages from `copilot_polling/pipeline.py`.

**Rationale**: The polling flow has two paths:
1. **Fleet path**: `_get_agent_task_id()` → `_check_agent_task_status()` → `FleetDispatchService.normalize_task_state()` — resolves fleet task IDs and checks GitHub agent task API
2. **Classic path**: Standard Copilot polling via PR/commit status checks — already the active default

After fleet removal, only the classic polling path remains. The helper functions `_get_agent_task_id()` and `_check_agent_task_status()` have no non-fleet callers.

**Alternatives considered**: None — clean removal of dead code paths.

---

## R7: Shell Script and CLI Plugin Dependency Analysis

**Task**: Verify that `fleet-dispatch.sh`, `fleet_dispatch_common.sh`, and `cli-plugin/` have no non-fleet consumers.

**Decision**: Delete all 3 shell scripts and the entire `cli-plugin/` directory.

**Rationale**:
- `fleet-dispatch.sh` (409 lines): Standalone CLI for fleet dispatch. Not sourced by any other script.
- `fleet_dispatch_common.sh` (447 lines): Library sourced only by `fleet-dispatch.sh`.
- `cli-plugin/` (5 files): Self-contained GitHub Copilot CLI plugin. No imports from backend or frontend code.
- `scripts/pipelines/` directory: After removing `fleet-dispatch.json`, `pipeline-config.schema.json`, and `templates/`, the directory will be empty and can be deleted.

**Alternatives considered**: Archiving to a separate branch — rejected because git history preserves the code.

---

## R8: Test File Triage

**Task**: Classify fleet test files as delete vs. modify.

**Decision**: Delete 7 fleet-specific test files; modify 5 test files to remove fleet assertions.

**Rationale**:

**Delete entirely** (fleet-only test files):
1. `tests/fleet_dispatch_harness.py` — shared harness for fleet tests
2. `tests/unit/test_fleet_dispatch_cli.py` — tests for `fleet-dispatch.sh`
3. `tests/unit/test_fleet_dispatch_service.py` — tests for `FleetDispatchService`
4. `tests/unit/test_fleet_dispatch_templates.py` — tests for template rendering
5. `tests/unit/test_fleet_parity.py` — fleet parity validation
6. `tests/integration/test_fleet_dispatch_smoke.py` — fleet smoke tests
7. `tests/integration/test_fleet_app_dispatch.py` — fleet app dispatch integration

**Modify** (remove fleet-specific assertions/fixtures):
1. `tests/unit/test_pipeline_config_schema.py` — remove fleet config schema tests
2. `tests/unit/test_workflow_orchestrator.py` — remove fleet branch/assertion references
3. `tests/unit/test_api_workflow.py` — remove `dispatch_backend`/`agent_task_ids` assertions
4. `tests/unit/test_issues.py` — remove fleet label/issue assertions
5. `frontend/src/services/schemas/pipeline.test.ts` — remove fleet metadata field test

Additional files with fleet references that may need cleanup:
6. `tests/unit/test_helpers_polling.py` — remove fleet polling assertions
7. `tests/unit/test_pipeline_state_store.py` — remove `agent_task_ids` assertions

**Alternatives considered**: None — standard test cleanup for removed features.
