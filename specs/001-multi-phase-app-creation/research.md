# Research: Multi-Phase App Creation with Auto-Merge Pipeline Orchestration

**Branch**: `copilot/create-implementation-plan-for-app` | **Date**: 2026-04-06

## R1: Two-Stage Planning (Chat Plan Agent → speckit.plan)

**Decision**: Use `chat_agent_svc.run_plan()` (existing, fast ~seconds) to generate a structured plan summary, then feed that into `speckit.plan` (detailed, 5–15 min) via `assign_copilot_to_issue(custom_agent="speckit.plan")`.

**Rationale**: The chat plan agent produces a quick high-level outline suitable for structuring the speckit.plan prompt. speckit.plan then generates a full `plan.md` with phases, dependencies, and contracts. Separating the two stages avoids blocking the user for 15 minutes while still producing a rich plan.

**Alternatives considered**:
- *Single-stage speckit.plan only*: Would require the user's raw description to be detailed enough; loses the structured seed from the chat agent.
- *Chat agent only (no speckit.plan)*: Produces plans too shallow for multi-phase orchestration — no phases, no dependency graph, no contracts.
- *LLM-generated plan outside agent framework*: Would bypass existing Copilot SDK patterns and require custom integration.

## R2: Plan Parser Strategy

**Decision**: Regex-based Markdown parser targeting `## Implementation Phases` → `### Phase N — Title` blocks, extracting `PlanPhase(index, title, description, steps, depends_on_phases, execution_mode)`.

**Rationale**: The plan.md template is well-structured with predictable heading patterns. A regex parser is simpler and more maintainable than a full AST parser. Dependency markers ("depends on Phase N", "parallel with Phase N") appear in the phase description/steps and can be detected with straightforward patterns.

**Alternatives considered**:
- *YAML/JSON structured plan*: Would require modifying the plan template format (out of scope).
- *LLM-based parsing*: Adds latency, cost, and non-determinism for a structurally predictable format.
- *markdown-it or mistune library*: Full Markdown AST is overkill; heading extraction and line-level regex suffice.

## R3: Wave-Based Execution vs DAG Scheduler

**Decision**: Group phases into "waves" by dependency depth. Wave 1 = no dependencies; Wave 2 = depends only on Wave 1 phases; etc. Reuse existing queue mode infrastructure with a new `prerequisite_issues` field on `PipelineState`.

**Rationale**: The existing queue mode already serializes pipeline execution per-project with FIFO dequeue. Adding `prerequisite_issues: list[int]` is a lightweight extension — the dequeue function checks that all prerequisite PRs are merged before starting a pipeline. No separate DAG scheduler is needed.

**Alternatives considered**:
- *Full DAG scheduler (e.g., networkx)*: Over-engineered for sequential phase execution; adds a new dependency for graph traversal that wave grouping solves trivially.
- *Project-level auto-merge toggle*: Less granular than per-pipeline `auto_merge=True`; would affect unrelated pipelines in the project.
- *External orchestrator (Temporal, Airflow)*: Heavy infrastructure dependency for what is fundamentally a sequential pipeline with merge gates.

## R4: Background Orchestration and Status Tracking

**Decision**: `POST /apps/create-with-plan` returns immediately with `plan_status: "planning"`. The orchestration runs as a `BackgroundTask`. Status is tracked in a new `app_plan_orchestrations` SQLite table with states: `planning → speckit_running → parsing_phases → creating_issues → launching_pipelines → active`. WebSocket broadcasts on each state transition.

**Rationale**: speckit.plan takes 5–15 minutes. Returning immediately with a tracking ID lets the frontend show live progress without long HTTP timeouts. The existing `ConnectionManager.broadcast_to_project()` WebSocket pattern handles real-time updates.

**Alternatives considered**:
- *Long-polling HTTP*: Simpler but wasteful; requires repeated requests and risks timeouts.
- *SSE (Server-Sent Events)*: Already used for chat, but WebSocket is the established pattern for pipeline/build progress in Solune.
- *Celery/task queue*: Adds operational complexity; `BackgroundTask` from Starlette is sufficient for single-instance deployment.

## R5: PipelineState Serialization for prerequisite_issues

**Decision**: Add `prerequisite_issues: list[int] = field(default_factory=list)` to `PipelineState` (in `workflow_orchestrator/models.py`). Serialize as part of the existing `metadata` JSON blob in `pipeline_state_store.py`.

**Rationale**: The pipeline state store already serializes all non-core fields as a JSON `metadata` dict. Adding `prerequisite_issues` to this dict requires only updating `_row_to_pipeline_state()` and `_pipeline_state_to_row()` — no schema migration needed since metadata is an opaque JSON column.

**Alternatives considered**:
- *Separate `prerequisite_issues` SQL column*: Requires a migration and schema change for a field that's only relevant during orchestration.
- *External state (Redis, etc.)*: Adds infrastructure; SQLite metadata JSON is sufficient.

## R6: Auto-Merge Per Pipeline

**Decision**: `PipelineState.auto_merge` already exists as a boolean field. Currently set based on project-level settings. For app creation phases, each pipeline gets `auto_merge=True` explicitly via `execute_pipeline_launch()`.

**Rationale**: The auto-merge field already exists on PipelineState (confirmed in codebase). The `_attempt_auto_merge()` function in `auto_merge.py` already checks this field and triggers dequeue after successful merge. We only need to pass `auto_merge=True` when creating PipelineState for app creation phases.

**Alternatives considered**:
- *Project-level auto-merge toggle*: Would affect all pipelines, not just app creation phases. Less precise.
- *Post-merge webhook*: Already handled — `_dequeue_next_pipeline()` is called after auto-merge in `pipeline.py`.

## R7: Frontend Progress View

**Decision**: Extend `CreateAppDialog.tsx` to show a post-submission progress view. After form submission, display a stepper/progress component with live updates via the existing WebSocket connection. Each state transition (`planning → speckit_running → ...`) maps to a step in the UI.

**Rationale**: The frontend already has WebSocket infrastructure (`ConnectionManager`) for build progress. The `CreateAppDialog` already handles the submission flow. Adding a progress view within the same dialog keeps the UX cohesive.

**Alternatives considered**:
- *Separate progress page*: Would break the dialog flow and require navigation.
- *Toast notifications only*: Insufficient for a 5–15 minute process; users need persistent progress indication.
- *Polling-based progress*: WebSocket is already established for real-time updates.

## R8: Database Migration Strategy

**Decision**: Create migration `042_app_plan_orchestrations.sql` with a single new table for tracking orchestration state. No changes to existing tables (prerequisite_issues goes in metadata JSON).

**Rationale**: The only new persistent state is the orchestration tracking table. All pipeline state extensions (prerequisite_issues) fit within the existing metadata JSON column, avoiding schema changes to `pipeline_states`.

**Alternatives considered**:
- *Extend `apps` table with plan columns*: Violates single-responsibility; orchestration state is transient and separate from app lifecycle.
- *In-memory only tracking*: Would lose state on restart during a 15-minute operation.
