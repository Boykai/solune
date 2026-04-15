# Quickstart: Fix App Building Project Recovery

## 1. Implement the backend changes

1. Update `/home/runner/work/solune/solune/solune/backend/src/services/app_plan_orchestrator.py` so `_launch_phase_pipelines()` accepts `owner` and `repo`, and forwards `target_repo=(owner, repo)` into `execute_pipeline_launch()`.
2. Update `/home/runner/work/solune/solune/solune/backend/src/api/projects.py` so `select_project()` schedules a new `_restore_app_pipelines_for_project()` helper after `_start_copilot_polling()`.
3. Update `/home/runner/work/solune/solune/solune/backend/src/services/copilot_polling/pipeline.py` so `_reconstruct_pipeline_state()` passes `repository_owner=owner` and `repository_name=repo` when building `PipelineState`.
4. Keep `/home/runner/work/solune/solune/solune/backend/src/main.py` unchanged except as the reference implementation for restart-time restoration behavior.

## 2. Add or extend focused tests

1. Extend `/home/runner/work/solune/solune/solune/backend/tests/unit/test_app_plan_orchestrator.py` to assert `execute_pipeline_launch()` receives `target_repo=(owner, repo)` for every launched phase.
2. Extend `/home/runner/work/solune/solune/solune/backend/tests/unit/test_api_projects.py` to assert `select_project()` schedules app-pipeline restoration and only starts scoped polling for cross-repo states.
3. Extend `/home/runner/work/solune/solune/solune/backend/tests/unit/test_copilot_polling.py` to assert reconstructed `PipelineState` objects retain repository owner/name.
4. Keep `/home/runner/work/solune/solune/solune/backend/tests/unit/test_main.py` as the restart-recovery regression reference.

## 3. Run focused validation

```bash
cd /home/runner/work/solune/solune/solune/backend && \
uv run --with pytest --with pytest-asyncio pytest \
  tests/unit/test_app_plan_orchestrator.py \
  tests/unit/test_api_projects.py \
  tests/unit/test_copilot_polling.py \
  tests/unit/test_main.py -q
```

## 4. Run backend regression

```bash
cd /home/runner/work/solune/solune/solune/backend && \
uv run --with pytest --with pytest-asyncio pytest tests/ -q
```

## 5. Manual recovery walkthrough

1. Create a new-repo app via `POST /api/v1/apps/create-with-plan`.
2. Confirm the launched phase pipeline creates issues in the app repository rather than the default repository.
3. While the pipeline is active, call `POST /api/v1/projects/{project_id}/select` and confirm scoped polling is re-created in the background for the cross-repo pipeline.
4. Restart the backend process and confirm the reconstructed pipeline state retains `repository_owner` / `repository_name`, allowing restart recovery to restore scoped polling without an extra self-healing lookup for newly created states.
