# Implementation Plan: Fix App Building Project Recovery

**Branch**: `001-fix-app-building-recovery` | **Date**: 2026-04-15 | **Spec**: [GitHub Issue #1950](https://github.com/Boykai/solune/issues/1950)
**Input**: Parent issue Boykai/solune#1950 — Fix App Building Project Recovery (PR #1961)

## Summary

Restore cross-repo app-building recovery by carrying the target repository all the way from plan-driven app orchestration into `execute_pipeline_launch()`, reusing the existing restart-time app-pipeline restoration logic for project selection, and preserving repository metadata when `_reconstruct_pipeline_state()` rebuilds in-memory pipeline state. The implementation should stay surgical: four backend source files, focused unit tests in the existing suites, and no schema migration or same-repo polling behavior changes.

## Technical Context

**Language/Version**: Python 3.12 backend service  
**Primary Dependencies**: FastAPI route handlers, Pydantic models, `src.api.pipelines.execute_pipeline_launch`, `src.services.copilot_polling.ensure_app_pipeline_polling`, `src.services.task_registry.task_registry`, existing GitHub/project/session services  
**Storage**: Existing SQLite-backed session / project-settings / orchestration tables plus the in-memory pipeline state store  
**Testing**: `pytest` via `uv run`, focused unit suites in `solune/backend/tests/unit/test_app_plan_orchestrator.py`, `solune/backend/tests/unit/test_api_projects.py`, `solune/backend/tests/unit/test_copilot_polling.py`, and `solune/backend/tests/unit/test_main.py`, plus regression `pytest solune/backend/tests/`  
**Target Platform**: Solune backend API / background worker runtime  
**Project Type**: Backend workflow-recovery enhancement  
**Performance Goals**: Preserve non-blocking project selection, restore scoped polling within the existing background-task window, and keep restart recovery within one normal polling cycle  
**Constraints**: No DB migration in this issue; same-repo pipelines must remain on the main polling loop; project-selection restoration must run fire-and-forget; reuse existing recovery helpers and logging patterns instead of introducing a parallel recovery path  
**Scale/Scope**: Small backend-only change spanning `solune/backend/src/services/app_plan_orchestrator.py`, `solune/backend/src/api/projects.py`, `solune/backend/src/services/copilot_polling/pipeline.py`, and `solune/backend/src/main.py` as reference, plus existing unit tests

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Specification-First Development**: PASS — `spec.md` defines three prioritized user stories, explicit acceptance scenarios, edge cases, and measurable success criteria for the recovery failure.
- **II. Template-Driven Workflow**: PASS — The planning artifacts for this feature live at the repository root (`spec.md`, `plan.md`, `research.md`, `contracts/`, `tasks.md`) using the standard Speckit artifact set.
- **III. Agent-Orchestrated Execution**: PASS — The work decomposes cleanly into orchestration forwarding, project-selection polling restoration, pipeline reconstruction, and verification, each with a clear dependency chain.
- **IV. Test Optionality with Clarity**: PASS — Tests are explicitly required by the issue, so the plan reuses existing unit suites and the backend regression command instead of inventing new harnesses.
- **V. Simplicity and DRY**: PASS — The design reuses `execute_pipeline_launch(target_repo=...)`, mirrors `main._restore_app_pipeline_polling()`, and keeps same-repo behavior untouched rather than adding a second recovery model.

**Post-Phase-1 Re-check**: PASS — The research and design keep the feature inside existing seams: one forwarded tuple, one scoped helper for project selection, one constructor-field fix, and focused tests. No constitution violations or complexity justifications are required.

## Project Structure

### Documentation (this feature)

```text
.
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
└── tasks.md
```

### Source Code (repository root)

```text
solune/backend/
├── src/
│   ├── api/
│   │   ├── apps.py                               # Existing plan-driven app creation entrypoint
│   │   ├── pipelines.py                          # Existing target_repo-aware launch contract
│   │   └── projects.py                           # select_project + new scoped restoration helper
│   ├── services/
│   │   ├── app_plan_orchestrator.py              # Forward owner/repo into phase pipeline launches
│   │   └── copilot_polling/
│   │       └── pipeline.py                       # Preserve repository fields during reconstruction
│   └── main.py                                   # Reference-only restart restoration logic
└── tests/
    └── unit/
        ├── test_app_plan_orchestrator.py         # Assert target_repo forwarding into execute_pipeline_launch
        ├── test_api_projects.py                  # Assert select_project schedules scoped restoration correctly
        ├── test_copilot_polling.py               # Assert reconstructed PipelineState retains owner/repo
        └── test_main.py                          # Existing restart-restore behavior reference/regression surface
```

**Structure Decision**: The fix is entirely backend-scoped. It should extend the existing app-creation, project-selection, and pipeline-reconstruction paths in place, while using `solune/backend/src/main.py` only as the authoritative reference for restart-time polling restoration behavior.

## Phase Execution Plan

### Phase 1 — Forward Target Repository Through Orchestration

**Goal**: Ensure every phase pipeline launch for a new-repo app carries the resolved `(owner, repo)` pair into `execute_pipeline_launch()`.

| Step | Action | Details |
|------|--------|---------|
| 1.1 | Extend `_launch_phase_pipelines()` signature | Add `owner` and `repo` parameters in `/home/runner/work/solune/solune/solune/backend/src/services/app_plan_orchestrator.py` so the launch helper has the same repository context already held by `orchestrate_app_creation()` |
| 1.2 | Pass repository context from orchestration | Update the `orchestrate_app_creation()` call site to forward `owner=owner` and `repo=repo` into `_launch_phase_pipelines()` |
| 1.3 | Forward `target_repo` to the pipeline launcher | Pass `target_repo=(owner, repo)` into `execute_pipeline_launch()` so parent issues, `use_app_scoped_polling`, and persisted pipeline state all use the app repo |
| 1.4 | Add focused orchestrator test coverage | Extend `/home/runner/work/solune/solune/solune/backend/tests/unit/test_app_plan_orchestrator.py` to assert each launch call includes the expected `target_repo` tuple |

**Dependencies**: None — this is the root-cause fix that unlocks the rest of the recovery behavior.

**Output**: Cross-repo app phase launches create issues and pipeline state against the correct repository from the start.

### Phase 2 — Restore Scoped App-Pipeline Polling on Project Selection

**Goal**: Recreate the restart-time scoped polling behavior when a user manually re-selects a project.

| Step | Action | Details |
|------|--------|---------|
| 2.1 | Add a project-scoped restoration helper | In `/home/runner/work/solune/solune/solune/backend/src/api/projects.py`, add `_restore_app_pipelines_for_project()` immediately after `_start_copilot_polling()`, mirroring `/home/runner/work/solune/solune/solune/backend/src/main.py:_restore_app_pipeline_polling()` but filtering to the selected `project_id` |
| 2.2 | Reuse existing filtering rules | Scan `get_all_pipeline_states()` for matching, non-complete pipeline states; skip same-repo pipelines by comparing against default repo settings; call `ensure_app_pipeline_polling()` only for cross-repo states |
| 2.3 | Preserve non-blocking selection | After `_start_copilot_polling()` in `select_project()`, enqueue the new helper via `task_registry.create_task(...)` so the HTTP response is not delayed |
| 2.4 | Reuse existing logging semantics | Log each restored scoped polling task in the same informational style as restart recovery so runtime behavior stays observable |
| 2.5 | Add focused project-selection tests | Extend `/home/runner/work/solune/solune/solune/backend/tests/unit/test_api_projects.py` to verify cross-repo states trigger the helper/task scheduling, while same-repo or empty-state cases do not create extra scoped polling |

**Dependencies**: Phase 1 should land first so newly launched pipelines already contain correct repository metadata for this helper to consume.

**Output**: Selecting a project resumes monitoring for active cross-repo app pipelines without changing same-repo behavior.

### Phase 3 — Preserve Repository Info During Reconstruction

**Goal**: Make reconstructed pipeline state carry the original repository owner/name instead of dropping back to empty strings.

| Step | Action | Details |
|------|--------|---------|
| 3.1 | Update `_reconstruct_pipeline_state()` construction | In `/home/runner/work/solune/solune/solune/backend/src/services/copilot_polling/pipeline.py`, pass the existing `owner` and `repo` arguments into the `PipelineState` constructor |
| 3.2 | Preserve behavior for deleted/missing issues | Keep the current graceful error handling and empty-agent fallback; only the repository fields change |
| 3.3 | Add reconstruction regression coverage | Extend `/home/runner/work/solune/solune/solune/backend/tests/unit/test_copilot_polling.py` to assert `repository_owner` and `repository_name` are populated on reconstructed state |
| 3.4 | Cross-check restart logic assumptions | Confirm `/home/runner/work/solune/solune/solune/backend/tests/unit/test_main.py` still reflects the legacy backfill path for old blank states, ensuring forward fixes and restart self-healing coexist |

**Dependencies**: Phases 1 and 2 can proceed independently, but this phase is required for restart recovery to stay correct after process restarts.

**Output**: Reconstructed pipeline states reliably identify their backing repository and no longer depend on API lookups for newly created states.

### Phase 4 — Verification and Regression Review

**Goal**: Prove the recovery fix works across normal launch, project selection, and restart reconstruction scenarios.

| Step | Action | Details |
|------|--------|---------|
| 4.1 | Run focused unit tests | Execute the targeted orchestrator, projects, copilot-polling, and main recovery test suites |
| 4.2 | Run backend regression suite | Execute `pytest` across `/home/runner/work/solune/solune/solune/backend/tests/` to confirm no same-repo or unrelated pipeline regressions |
| 4.3 | Manual recovery walkthrough | Create a new-repo app, stall the agent/poller, then verify recovery paths (normal operation, project selection, restart) all target the app repo and resume scoped polling |
| 4.4 | Verify out-of-scope boundaries hold | Confirm same-repo pipelines still stay on the main loop and no repository-qualified pipeline-state key migration is introduced |

**Dependencies**: Phases 1–3 complete.

**Output**: Verified recovery behavior across the three failure scenarios called out in the issue.

## Verification Matrix

| Check | Command / Method | After Phase |
|-------|------------------|-------------|
| Orchestrator + project-selection tests | `cd /home/runner/work/solune/solune/solune/backend && uv run --with pytest --with pytest-asyncio pytest tests/unit/test_app_plan_orchestrator.py tests/unit/test_api_projects.py -q` | 1, 2 |
| Reconstruction + restart recovery tests | `cd /home/runner/work/solune/solune/solune/backend && uv run --with pytest --with pytest-asyncio pytest tests/unit/test_copilot_polling.py tests/unit/test_main.py -q` | 3 |
| Focused end-to-end recovery slice | `cd /home/runner/work/solune/solune/solune/backend && uv run --with pytest --with pytest-asyncio pytest tests/unit/test_app_plan_orchestrator.py tests/unit/test_api_projects.py tests/unit/test_copilot_polling.py tests/unit/test_main.py -q` | 4 |
| Backend regression | `cd /home/runner/work/solune/solune/solune/backend && uv run --with pytest --with pytest-asyncio pytest tests/ -q` | 4 |
| Manual verification | Create app → confirm phase launches target the app repo → select project → restart service → confirm scoped polling resumes only for cross-repo pipelines | 4 |

## Decisions

| Decision | Rationale |
|----------|-----------|
| **Use `target_repo` instead of adding a new repo lookup** | `/home/runner/work/solune/solune/solune/backend/src/api/pipelines.py` already exposes the correct extension point for cross-repo launches and toggles scoped polling when the tuple is present. |
| **Mirror restart recovery for project selection** | `/home/runner/work/solune/solune/solune/backend/src/main.py:_restore_app_pipeline_polling()` already codifies the right filters, fallback order, and logging semantics, so project selection should reuse that behavior rather than invent a new polling policy. |
| **Keep same-repo pipelines on the main polling loop** | This is explicit in the issue and avoids unnecessary extra polling tasks or behavior drift for the default-repo path. |
| **Do not address pipeline-state key collisions in this issue** | The issue explicitly scopes that to a follow-up DB migration, so the plan avoids mixing data-model changes into a targeted recovery fix. |

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Project-selection restoration accidentally blocks the HTTP response | UX slowdown when switching projects | Enqueue the helper with `task_registry.create_task(...)` and keep `_start_copilot_polling()` as the only awaited recovery step |
| Same-repo pipelines start duplicate scoped polling | Extra polling load and behavior drift | Compare state repo vs default repo before calling `ensure_app_pipeline_polling()` and cover the skip path in tests |
| Legacy blank repository fields still exist in old state rows | Restart recovery may still need fallback resolution | Preserve the existing `resolve_repository()` self-healing path in `/home/runner/work/solune/solune/solune/backend/src/main.py` and treat this fix as forward-correctness for new states |
| Cross-repo repo access is lost or the repo is deleted | Recovery can fail noisily | Keep current error logging/propagation behavior so failures surface instead of silently creating work in the default repo |

## Complexity Tracking

> No constitution violations found. No complexity justifications required.
