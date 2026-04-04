# Research: Full-Stack Plan Pipeline Enhancement

**Feature**: 016-plan-pipeline-enhancement | **Date**: 2026-04-04

## 1. Plan Versioning Strategy (SQLite)

**Decision**: Snapshot-based versioning with a separate `chat_plan_versions` table

**Rationale**: SQLite's single-writer model and the existing `BEGIN IMMEDIATE` transaction pattern make copy-on-write snapshots the natural fit. Before each `save_plan()` overwrite, the current plan state is copied into `chat_plan_versions` with the current version number, then the `chat_plans.version` column is incremented. This avoids event-sourcing complexity while providing full history for diff computation.

**Alternatives considered**:
- **Event sourcing (append-only log)**: Rejected — adds reconstruction complexity for a feature with ≤50 versions per plan; snapshot reads are O(1) vs O(n) replay
- **JSON column on `chat_plans`**: Rejected — growing JSON blob in a single row degrades SQLite page utilization; separate table enables indexed queries by version number
- **Soft-delete with version column only**: Rejected — cannot reconstruct historical step snapshots without storing `steps_snapshot`

**Key implementation detail**: `steps_snapshot` is stored as a JSON TEXT column containing the serialized array of steps at that version. This avoids a join-heavy schema for historical step data.

## 2. Step-Level Feedback Persistence

**Decision**: Transient feedback injected into agent session context (not persisted to database)

**Rationale**: Step feedback is ephemeral by nature — it guides the next refinement cycle and becomes obsolete once the agent addresses it. Persisting feedback would require a new table, additional CRUD endpoints, and cleanup logic for stale comments, all for data that loses relevance after one refinement pass.

**Alternatives considered**:
- **`chat_plan_step_feedback` table**: Rejected — adds schema complexity, requires cleanup triggers, and the data is only consumed by the agent's next run
- **JSON column on `chat_plan_steps`**: Rejected — conflates transient feedback with the canonical step definition; would require clearing after each refinement

**Implementation approach**: The `POST /plans/{plan_id}/steps/{step_id}/feedback` endpoint stores comments in the agent session state dictionary (`state["step_feedback"]`). The `run_plan_stream()` method injects these comments into the system prompt for the next refinement pass, then clears them from state.

## 3. Dependency Graph Visualization

**Decision**: Custom lightweight SVG component (`PlanDependencyGraph.tsx`) with topological layer layout

**Rationale**: With a hard constraint of ≤15 steps, the graph is small enough for a simple layered layout computed via topological sort. Each "layer" contains steps whose dependencies are all in previous layers. Steps are rendered as clickable rectangles connected by SVG path elements. This avoids adding a heavy graphing library for a bounded, simple use case.

**Alternatives considered**:
- **D3.js + dagre**: Rejected — adds ~200KB bundle weight for a graph that never exceeds 15 nodes; D3's imperative API conflicts with React's declarative model
- **react-flow**: Rejected — powerful but heavyweight; designed for interactive node editors, not read-mostly plan visualization
- **Mermaid.js rendering**: Rejected — runtime parsing overhead; limited click interaction; server-side rendering complications

**Layout algorithm**: Kahn's algorithm (BFS topological sort) assigns each step to a layer. Within each layer, steps are arranged left-to-right. Edges are drawn as SVG `<path>` elements with simple bezier curves. Clicking a node scrolls the step list to the corresponding step.

## 4. Drag-and-Drop Reordering Pattern

**Decision**: Reuse existing `@dnd-kit` setup from `ExecutionGroupCard.tsx`

**Rationale**: `@dnd-kit/core` (^6.3.1), `@dnd-kit/sortable` (^10.0.0), and `@dnd-kit/utilities` (^3.2.2) are already installed and proven. The `ExecutionGroupCard.tsx` pattern provides a working reference for `DndContext`, `SortableContext`, `useSortable`, `useSensors`, `PointerSensor`, `KeyboardSensor`, `closestCenter` collision detection, and `arrayMove`. Reusing this pattern ensures consistency and avoids new dependencies.

**Implementation approach**:
- Wrap the step list in `DndContext` + `SortableContext` with `verticalListSortingStrategy`
- Each step wrapped in a `useSortable` hook providing drag handle listeners
- `onDragEnd` calls `reorderPlanSteps()` API with the new position array
- 5px `PointerSensor` activation distance prevents accidental drags (matching existing pattern)

## 5. Board Sync Strategy

**Decision**: Client-side polling (not webhooks) for issue status synchronization

**Rationale**: SQLite's single-writer model makes webhook-driven concurrent writes risky. Polling from the frontend at a reasonable interval (30s when plan view is active) is simpler to implement, requires no GitHub App webhook configuration, and naturally rate-limits API calls.

**Alternatives considered**:
- **GitHub webhooks**: Rejected — requires GitHub App setup, webhook endpoint, signature verification, and concurrent write handling with SQLite
- **Server-side polling daemon**: Rejected — adds a background process to manage; the frontend already knows when to poll (when viewing an approved plan)
- **SSE push from backend**: Rejected — the backend would still need to poll GitHub; adding SSE for this creates unnecessary indirection

**Implementation approach**: After plan approval, `PlanPreview.tsx` starts a `setInterval` polling loop that calls `GET /plans/{plan_id}` (which queries `chat_plan_steps.issue_status`). The backend updates `issue_status` via a lightweight `GET /plans/{plan_id}/sync-status` endpoint that checks GitHub issue states in bulk.

## 6. Selective Step Approval

**Decision**: Extend existing `POST /plans/{plan_id}/approve` with an optional `step_ids` body parameter

**Rationale**: Backward-compatible extension — omitting `step_ids` approves all steps (existing behavior); providing `step_ids` approves only selected steps. This avoids a new endpoint and keeps the approval flow unified.

**Alternatives considered**:
- **New `POST /plans/{plan_id}/approve-selected` endpoint**: Rejected — unnecessary proliferation of endpoints; the semantics are identical with a filter
- **Per-step `POST /steps/{step_id}/approve`**: Rejected — creates N API calls for N steps; parent issue creation logic needs all selected steps at once

**Implementation approach**: The `approve_plan_endpoint()` handler reads an optional `step_ids: list[str] | None` from the request body. If provided, `plan_issue_service.create_plan_issues()` filters steps to only those with matching IDs. The plan status transitions to `"approved"` regardless (partial approval is still an approval).

## 7. DAG Validation Algorithm

**Decision**: Kahn's algorithm (BFS-based topological sort) for cycle detection

**Rationale**: Simple, well-understood, O(V+E) complexity. For ≤15 steps with sparse dependencies, performance is negligible. The algorithm naturally detects cycles — if the sorted output contains fewer nodes than the input, a cycle exists.

**Alternatives considered**:
- **DFS with coloring**: Equally valid but slightly more complex to implement; Kahn's provides the topological ordering as a byproduct (useful for layer assignment in the graph)
- **Union-Find**: Only detects cycles in undirected graphs; dependencies are directed

**Implementation approach**: New `dag_validator.py` utility with `validate_step_dag(steps: list[PlanStep]) -> list[str]` that returns the topological order or raises `ValueError` with the cycle details. Called from `chat_store.py` on every dependency-modifying mutation. Returns HTTP 422 on validation failure.

## 8. SSE Event Extensions

**Decision**: Add three new SSE event types: `tools_used`, `context_gathered`, `plan_diff`

**Rationale**: The existing SSE events (`thinking`, `token`, `tool_result`, `done`, `error`) provide phase-level granularity but lack visibility into tool execution and plan changes. The new events enable the `ThinkingIndicator v2` breadcrumb display without changing existing event semantics.

**Alternatives considered**:
- **Extending `thinking` event with additional fields**: Rejected — would break existing frontend parsing; `thinking` events have an established `{phase, detail}` contract
- **Single `progress` event with subtypes**: Rejected — less semantic clarity; harder to filter in the frontend

**Implementation approach**:
- `tools_used`: Emitted after each tool call completes, containing `{tool_name, duration_ms}`
- `context_gathered`: Emitted after research phase, containing `{sources: string[]}`
- `plan_diff`: Emitted after refinement, containing `{added: string[], removed: string[], changed: string[]}` (step IDs)

## 9. Export Format

**Decision**: Markdown export via `GET /plans/{plan_id}/export?format=markdown`

**Rationale**: Markdown is the most portable format for plan sharing. It renders natively in GitHub issues, PRs, and README files. The backend generates the Markdown server-side to ensure consistent formatting regardless of frontend state.

**Alternatives considered**:
- **JSON export**: Available implicitly via `GET /plans/{plan_id}`; explicit Markdown is the value-add
- **PDF export**: Requires a rendering library (weasyprint, puppeteer); disproportionate complexity for the use case
- **Client-side Markdown generation**: Rejected — duplicates plan rendering logic; server-side is single-source-of-truth

**Implementation approach**: A new `format_plan_as_markdown(plan: dict) -> str` utility generates a structured Markdown document with title, summary, step checklist (with dependency annotations), and metadata footer. The frontend offers "Export as Markdown" (downloads `.md` file) and "Copy to clipboard" (copies Markdown text).

## 10. Migration Numbering

**Decision**: 040 for plan versioning, 041 for step status

**Rationale**: Sequential numbering after the current latest (039). Separate migrations for separate concerns: versioning is a Phase 1 prerequisite; step status is a Phase 3 addition. This allows Phase 1 to deploy independently.

**Key schema changes**:
- **040**: `ALTER TABLE chat_plans ADD COLUMN version INTEGER NOT NULL DEFAULT 1`; `CREATE TABLE chat_plan_versions`
- **041**: `ALTER TABLE chat_plan_steps ADD COLUMN issue_status TEXT`
