# Implementation Plan: Remove Fleet Dispatch & Copilot CLI Code

**Branch**: `006-remove-fleet-dispatch-cli` | **Date**: 2026-04-13 | **Spec**: GitHub Issue #1753
**Input**: Parent issue Boykai/solune#1753 — Remove Fleet Dispatch & Copilot CLI Code

## Summary

Remove all fleet dispatch orchestration and GitHub Copilot CLI plugin code from Solune. Fleet enrichment (custom templates, agent-task tracking, fleet-specific labels) is deleted; the existing "classic" dispatch path — which uses `format_issue_context_as_prompt()` and standard Copilot assignment — becomes the sole execution path. ~30 files deleted, ~15 files modified. Zero behavioral regressions for users — the classic path is already the active default.

## Technical Context

**Language/Version**: Python 3.12+ (backend); TypeScript/React (frontend)
**Primary Dependencies**: FastAPI, Pydantic, Vite, Zod
**Storage**: SQLite via aiosqlite — no schema migration needed (removed fields are safely ignored on deserialization)
**Testing**: `pytest` (backend: `uv run pytest tests/`); Vitest (frontend: `npx vitest run`); `pyright` type checking; `ruff` linting
**Target Platform**: Linux server (backend); browser SPA (frontend)
**Project Type**: Web application (backend + frontend monorepo under `solune/`)
**Performance Goals**: N/A — deletion-only; no new runtime paths introduced
**Constraints**: Zero behavioral regressions; all existing tests must pass after fleet test removal; no new type errors; `assign_copilot_to_issue()` must remain functional for non-fleet callers
**Scale/Scope**: ~30 files deleted, ~15 files modified, 9 model classes removed, 4 config functions removed, 3 shell scripts deleted, 12 templates deleted, 1 CLI plugin directory deleted

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Specification-First Development**: PASS — The parent issue (#1753) provides a structured specification with phased requirements (6 phases), explicit scope boundaries (preserved functions listed), verification criteria (5 check commands), and clear decisions. This plan follows the issue as the authoritative spec.
- **II. Template-Driven Workflow**: PASS — This plan and all Phase 0/1 artifacts reside in `specs/006-remove-fleet-dispatch-cli/` using the canonical Speckit artifact set (plan.md, research.md, data-model.md, quickstart.md, contracts/).
- **III. Agent-Orchestrated Execution**: PASS — The plan decomposes into 6 phases with clear dependency ordering. Phases 1–2 are sequential; Phases 3–6 are parallelizable. Each phase has defined inputs, outputs, and verification criteria.
- **IV. Test Optionality with Clarity**: PASS — No new tests are mandated. 7 fleet-specific test files are deleted alongside their subjects. 5+ test files are modified to remove fleet-specific assertions. Existing non-fleet tests serve as regression gates.
- **V. Simplicity and DRY**: PASS — The plan exclusively removes complexity (fleet abstractions, dead code, unused models). The hardcoded legacy pipeline stages replace the dynamic fleet-config-derived stages with zero behavioral change. No new abstractions introduced.

**Post-Phase-1 Re-check**: PASS — No constitution violations introduced by the design. The phased approach removes complexity without introducing new abstractions. All decisions favor simplicity (hardcoded stages over config files, field removal over deprecation).

## Project Structure

### Documentation (this feature)

```text
specs/006-remove-fleet-dispatch-cli/
├── plan.md              # This file
├── research.md          # Phase 0 output — dependency analysis and removal safety research
├── data-model.md        # Phase 1 output — entities removed and preserved
├── quickstart.md        # Phase 1 output — execution guide for each phase
├── contracts/
│   └── removal-contract.yaml  # Phase 1 output — API surface changes
└── tasks.md             # Phase 2 output (NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
solune/
├── backend/
│   ├── src/
│   │   ├── models/
│   │   │   └── pipeline.py                    # MODIFY: remove 9 FleetDispatch* classes
│   │   ├── services/
│   │   │   ├── fleet_dispatch.py              # DELETE: entire file (356 lines)
│   │   │   ├── pipeline_orchestrator.py       # MODIFY: hardcode legacy stages
│   │   │   ├── pipeline_state_store.py        # MODIFY: remove agent_task_ids
│   │   │   ├── workflow_orchestrator/
│   │   │   │   ├── config.py                  # MODIFY: remove 4 fleet functions
│   │   │   │   ├── models.py                  # MODIFY: remove agent_task_ids field
│   │   │   │   └── orchestrator.py            # MODIFY: remove 29 fleet references
│   │   │   ├── copilot_polling/
│   │   │   │   └── helpers.py                 # MODIFY: remove fleet task helpers
│   │   │   └── github_projects/
│   │   │       └── copilot.py                 # MODIFY: remove 3 fleet-only methods
│   │   └── api/
│   │       └── workflow.py                    # MODIFY: remove fleet inference + fields
│   └── tests/
│       ├── fleet_dispatch_harness.py          # DELETE
│       ├── unit/
│       │   ├── test_fleet_dispatch_cli.py     # DELETE
│       │   ├── test_fleet_dispatch_service.py # DELETE
│       │   ├── test_fleet_dispatch_templates.py # DELETE
│       │   ├── test_fleet_parity.py           # DELETE
│       │   ├── test_pipeline_config_schema.py # MODIFY: remove fleet schema tests
│       │   ├── test_workflow_orchestrator.py   # MODIFY: remove fleet assertions
│       │   ├── test_api_workflow.py            # MODIFY: remove fleet fields
│       │   ├── test_issues.py                 # MODIFY: remove fleet assertions
│       │   ├── test_helpers_polling.py        # MODIFY: remove fleet polling tests
│       │   └── test_pipeline_state_store.py   # MODIFY: remove agent_task_ids tests
│       └── integration/
│           ├── test_fleet_dispatch_smoke.py    # DELETE
│           └── test_fleet_app_dispatch.py      # DELETE
├── frontend/
│   └── src/
│       ├── types/
│       │   └── index.ts                       # MODIFY: remove 2 fleet fields
│       └── services/
│           └── schemas/
│               ├── pipeline.ts                # MODIFY: remove 2 fleet fields
│               └── pipeline.test.ts           # MODIFY: remove fleet test
├── scripts/
│   ├── fleet-dispatch.sh                      # DELETE
│   ├── lib/
│   │   └── fleet_dispatch_common.sh           # DELETE
│   └── pipelines/
│       ├── fleet-dispatch.json                # DELETE
│       ├── pipeline-config.schema.json        # DELETE
│       └── templates/ (12 files)              # DELETE entire directory
├── cli-plugin/ (5 files)                      # DELETE entire directory
└── docs/
    └── architectures/
        └── backend-components.mmd             # MODIFY: remove Fleet Dispatch entry
```

**Structure Decision**: Web application monorepo (`solune/backend` + `solune/frontend`). This is a deletion-focused refactor — no new directories or files are created. The existing project structure is preserved.

## Implementation Phases

### Phase 1: Delete Standalone Fleet & CLI Artifacts

**Dependencies**: None (all parallel)
**Estimated impact**: ~30 files deleted

| Step | Action | Files | Notes |
|------|--------|-------|-------|
| 1.1 | Delete shell scripts | `scripts/fleet-dispatch.sh`, `scripts/lib/fleet_dispatch_common.sh` | No dependents |
| 1.2 | Delete pipeline config & templates | `scripts/pipelines/fleet-dispatch.json`, `scripts/pipelines/pipeline-config.schema.json`, `scripts/pipelines/templates/` (12 files) | Config read by `load_fleet_dispatch_config()` (removed in Phase 2) |
| 1.3 | Delete CLI plugin directory | `cli-plugin/` (5 files: `plugin.json`, `.mcp.json`, `agents/`, `hooks/`, `skills/`) | Self-contained, no imports from backend/frontend |
| 1.4 | Delete fleet backend service | `backend/src/services/fleet_dispatch.py` (356 lines) | Consumers updated in Phase 2–3 |
| 1.5 | Clean up empty directories | `scripts/pipelines/` (if empty after template removal) | Conditional |

### Phase 2: Remove Fleet Models & Config Functions

**Dependencies**: Phase 1 complete (deleted files no longer importable)

| Step | Action | File | Details |
|------|--------|------|---------|
| 2.1 | Remove FleetDispatch* models | `backend/src/models/pipeline.py` | Delete 9 classes: `FleetDispatchModel`, `FleetDispatchRepository`, `FleetDispatchDefaults`, `FleetDispatchSubIssue`, `FleetDispatchAgent`, `FleetDispatchExecutionGroup`, `FleetDispatchConfig`, `FleetDispatchStatus`, `FleetDispatchRecord`. Preserve all non-fleet models. |
| 2.2 | Remove fleet config functions | `backend/src/services/workflow_orchestrator/config.py` | Delete: `_DEFAULT_FLEET_DISPATCH_CONFIG`, `get_default_fleet_dispatch_config_path()`, `load_fleet_dispatch_config()`, `build_pipeline_stages_from_fleet_config()`. Remove `FleetDispatchConfig` import. Preserve: `get_workflow_config()`, `set_workflow_config()`, `resolve_project_pipeline_mappings()`, `load_user_agent_mappings()`, etc. |

### Phase 3: Modify Core Orchestration

**Dependencies**: Phase 2 complete (models and config functions removed)

| Step | Action | File | Details |
|------|--------|------|---------|
| 3.1 | Clean orchestrator | `backend/src/services/workflow_orchestrator/orchestrator.py` | Remove `FleetDispatchService` import + `self.fleet_dispatch` instantiation. At 3 `is_fleet_eligible()` branch sites: remove fleet branches, keep "classic" path as sole code path. Remove `_find_reusable_fleet_sub_issue()`, `build_fleet_sub_issue_labels()` calls, fleet logging. Remove `agent_task_ids` from state writes. |
| 3.2 | Simplify pipeline orchestrator | `backend/src/services/pipeline_orchestrator.py` | Remove fleet imports (`load_fleet_dispatch_config`, `build_pipeline_stages_from_fleet_config`). Replace `_default_pipeline_stages()` with hardcoded legacy stages (the existing fallback becomes primary). |
| 3.3 | Clean copilot service | `backend/src/services/github_projects/copilot.py` | Delete `list_agent_tasks()`, `get_agent_task()`, `_discover_agent_task_endpoint()`. Preserve `assign_copilot_to_issue()` — used by `app_plan_orchestrator.py` and `auto_merge.py`. |
| 3.4 | Clean copilot polling | `backend/src/services/copilot_polling/helpers.py` | Remove `_get_agent_task_id()`, `_check_agent_task_status()`, `FleetDispatchService.normalize_task_state()` import. |
| 3.5 | Clean API layer | `backend/src/api/workflow.py` | Remove `_infer_dispatch_backend()`, `FleetDispatchService` import. Remove `dispatch_backend` and `agent_task_ids` from response dict. |
| 3.6 | Clean pipeline state | `backend/src/services/pipeline_state_store.py` | Remove `agent_task_ids` from serialization/deserialization. |
| 3.7 | Clean state model | `backend/src/services/workflow_orchestrator/models.py` | Remove `agent_task_ids: dict[str, str]` field from `PipelineState` dataclass. |

### Phase 4: Frontend Cleanup

**Dependencies**: None (parallel with Phase 3)

| Step | Action | File | Details |
|------|--------|------|---------|
| 4.1 | Remove fleet type fields | `frontend/src/types/index.ts` | Remove `agent_task_ids: Record<string, string>` and `dispatch_backend: 'fleet' \| 'classic'` from `PipelineStateInfo` |
| 4.2 | Remove fleet schema fields | `frontend/src/services/schemas/pipeline.ts` | Remove `agent_task_ids` and `dispatch_backend` from Zod schema |

### Phase 5: Delete Fleet Tests

**Dependencies**: None (parallel with Phase 3)

| Step | Action | Files | Details |
|------|--------|-------|---------|
| 5.1 | Delete fleet test files | 7 files (see Project Structure) | All fleet-specific test files |
| 5.2 | Modify test files | `test_pipeline_config_schema.py`, `test_workflow_orchestrator.py`, `test_api_workflow.py`, `test_issues.py`, `test_helpers_polling.py`, `test_pipeline_state_store.py`, `frontend/…/pipeline.test.ts` | Remove fleet-specific assertions and fixtures |

### Phase 6: Documentation

**Dependencies**: None (parallel with Phase 3)

| Step | Action | File | Details |
|------|--------|------|---------|
| 6.1 | Update architecture diagram | `docs/architectures/backend-components.mmd` | Remove `SVC_23["Fleet Dispatch"]` entry and renumber subsequent entries |
| 6.2 | Regenerate diagrams | Run `./solune/scripts/generate-diagrams.sh` | CI checks diagrams with `--check` flag |
| 6.3 | Update root plan.md | `plan.md` | Remove `specs/001-fleet-dispatch-pipelines/` reference (line 176) |

## Verification Checklist

| # | Command | Expected Result |
|---|---------|----------------|
| V1 | `cd solune/backend && uv run pytest tests/unit/ -x -q` | All pass, no import errors |
| V2 | `cd solune/backend && uv run pytest tests/integration/ -x -q` | No broken imports |
| V3 | `cd solune/frontend && npx tsc --noEmit` | No type errors |
| V4 | `cd solune/frontend && npx vitest run` | Schema tests pass |
| V5 | `grep -rn "fleet\|FleetDispatch\|fleet_dispatch\|fleet-dispatch\|agent_task_ids\|dispatch_backend" solune/ --exclude-dir=node_modules --exclude=CHANGELOG.md` | Zero matches |
| V6 | Verify `assign_copilot_to_issue()` callers (`app_plan_orchestrator.py`, `auto_merge.py`) are unaffected | No fleet dependencies |
| V7 | Verify `_default_pipeline_stages()` returns hardcoded stages | No fleet dependency |
| V8 | `cd solune/backend && uv run ruff check src/ tests/` | No lint errors |
| V9 | `cd solune/backend && uv run pyright src/` | No type errors |

## Key Decisions

| Decision | Rationale |
|----------|-----------|
| `assign_copilot_to_issue()` preserved | Shared by fleet AND non-fleet callers (`app_plan_orchestrator.py`, `auto_merge.py`) |
| Legacy fallback stages become primary in `pipeline_orchestrator.py` | Identical to fleet-derived stages; the fallback was designed as the legacy path |
| `dispatch_backend`/`agent_task_ids` removed from API | Frontend never renders them (zero UI references verified) |
| `.github/agents/*.agent.md` files preserved | Fleet eligibility was runtime, not encoded in agent definitions |
| `guard-config.yml` unchanged | No fleet-specific entries |
| No database migration | `agent_task_ids` field safely ignored on deserialization of existing SQLite rows |
| `scripts/pipelines/` directory deleted if empty | Only contained fleet config, schema, and templates |

## Complexity Tracking

> No constitution violations identified. This plan exclusively removes complexity.
