# Data Model: Fix App Building Project Recovery

## Entity: Orchestration Launch Context

| Field | Type | Source | Notes |
|-------|------|--------|-------|
| `project_id` | `str` | `create_with_plan` / orchestration request | Target GitHub Project V2 used for routing and polling |
| `pipeline_id` | `str` | orchestration request | Saved pipeline definition to launch for each phase |
| `owner` | `str` | resolved before orchestration starts | Must be forwarded unchanged into `_launch_phase_pipelines()` |
| `repo` | `str` | resolved before orchestration starts | Combined with `owner` as `target_repo=(owner, repo)` |
| `phases` | `list[PlanPhase]` | parsed `plan.md` | Drives issue creation and launch ordering |
| `phase_issue_numbers` | `list[int]` | GitHub issue creation step | Mapped back to phase dependencies when launching pipelines |

**Relationships**
- One orchestration launch context produces many phase issues.
- Each phase issue launch must inherit the same `(owner, repo)` pair for cross-repo correctness.

**Validation Rules**
- `owner` and `repo` must be non-empty before passing `target_repo`.
- `phase_issue_numbers` must remain aligned with `phases` by position/index.

## Entity: PipelineState

| Field | Type | Existing? | Recovery requirement |
|-------|------|-----------|----------------------|
| `issue_number` | `int` | Yes | Primary key in the in-memory state store |
| `project_id` | `str` | Yes | Used to scope project-selection restoration |
| `status` | `str` | Yes | Determines active vs complete recovery behavior |
| `agents` | `list[str]` | Yes | Reconstructed from workflow config/comments |
| `completed_agents` | `list[str]` | Yes | Rebuilt from `Done!` comment markers |
| `repository_owner` | `str` | Yes | Must be populated during launch and reconstruction |
| `repository_name` | `str` | Yes | Must be populated during launch and reconstruction |
| `is_complete` | `bool` | Derived/existing | Completed states are ignored by scoped restoration |

**State Transitions**
1. **Launch-time creation** → `execute_pipeline_launch()` persists state with the explicit target repo.
2. **Normal active polling** → cross-repo states run under `ensure_app_pipeline_polling()`.
3. **Restart reconstruction** → `_reconstruct_pipeline_state()` rebuilds the state and must preserve `repository_owner` / `repository_name`.
4. **Project selection restoration** → active, non-complete states for the selected project may restart scoped polling if their repo differs from the default repo.
5. **Completion** → complete states are skipped by both restart and project-selection restoration.

## Entity: Project-Scoped App-Pipeline Restoration Task

| Field | Type | Notes |
|-------|------|-------|
| `selected_project_id` | `str` | The project the user just selected |
| `access_token` | `str` | Reused from the current session |
| `default_repo_owner` | `str` | Used to detect same-repo pipelines |
| `default_repo_name` | `str` | Used to detect same-repo pipelines |
| `active_pipeline_states` | `dict[int, PipelineState]` | Filtered to `project_id == selected_project_id` and `is_complete == False` |

**Rules**
- Create the task asynchronously via `task_registry.create_task(...)`.
- Only call `ensure_app_pipeline_polling()` for cross-repo states.
- Multiple active cross-repo pipelines for the same project are allowed, but deduplication remains owned by `ensure_app_pipeline_polling()`.
