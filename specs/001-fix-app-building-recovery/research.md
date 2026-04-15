# Research: Fix App Building Project Recovery

## Decision 1: Reuse `target_repo` as the orchestration handoff contract

- **Decision**: Thread `owner` and `repo` from `orchestrate_app_creation()` into `_launch_phase_pipelines()` and pass `target_repo=(owner, repo)` to `execute_pipeline_launch()`.
- **Rationale**: `/home/runner/work/solune/solune/solune/backend/src/api/pipelines.py` already supports explicit target repositories and uses that tuple to skip fallback resolution, create issues on the right repo, and enable app-scoped polling. Reusing the existing parameter is the smallest fix with the least risk.
- **Alternatives considered**:
  - Re-resolve the repository inside `_launch_phase_pipelines()` — rejected because the orchestrator already has authoritative `owner`/`repo` values.
  - Add a second repo override path inside `execute_pipeline_launch()` — rejected because `target_repo` already exists and covers the needed behavior.

## Decision 2: Mirror restart recovery for project selection

- **Decision**: Add `_restore_app_pipelines_for_project()` in `/home/runner/work/solune/solune/solune/backend/src/api/projects.py` using the same filtering and `ensure_app_pipeline_polling()` logic as `/home/runner/work/solune/solune/solune/backend/src/main.py:_restore_app_pipeline_polling()`, but scoped to the selected project.
- **Rationale**: Restart recovery already defines the correct fallback order (pipeline state → project settings → GitHub resolve), same-repo skip rule, and logging semantics. Reusing that pattern avoids divergence between restart recovery and project-selection recovery.
- **Alternatives considered**:
  - Call the global restart helper directly from `select_project()` — rejected because it scans every project, not just the selected one.
  - Fold scoped restoration into `_start_copilot_polling()` — rejected because `_start_copilot_polling()` should remain focused on the main polling loop and the app-pipeline restoration must stay fire-and-forget.

## Decision 3: Preserve repository fields during reconstruction instead of backfilling later

- **Decision**: Pass `owner` and `repo` directly into the `PipelineState` built by `_reconstruct_pipeline_state()`.
- **Rationale**: `_reconstruct_pipeline_state()` already receives the repository context from the recovery caller. Writing those fields at construction time makes newly reconstructed states immediately usable by recovery logic and reduces dependence on later self-healing lookups.
- **Alternatives considered**:
  - Leave fields blank and rely on `/home/runner/work/solune/solune/solune/backend/src/main.py` to backfill via GitHub API — rejected because it preserves the failure mode the issue describes.
  - Add a second persistence/update pass after reconstruction — rejected as unnecessary once the constructor receives the existing values.

## Decision 4: Validate with existing unit suites plus backend regression

- **Decision**: Keep verification inside the existing test surfaces: orchestrator, projects API, copilot polling, and main recovery tests, followed by the backend regression suite.
- **Rationale**: The repository already has focused tests around each touched seam, so the implementation can stay surgical and avoid introducing new test infrastructure just for this issue.
- **Alternatives considered**:
  - Add a brand-new integration harness for app recovery — rejected for this issue because the existing unit surfaces already map cleanly to the three failure scenarios.
