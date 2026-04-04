# Research: Auto-Generated Project Labels & Fields on Pipeline Launch

**Feature**: 730-auto-generated-labels-fields  
**Date**: 2026-04-04  
**Status**: Complete  

## Research Tasks

### R1: Pipeline Estimate Heuristic Design

**Question**: What is the best approach for deriving estimate/size from agent count?

**Decision**: Pure function with lookup table — `estimate_from_agent_count(count: int) -> IssueMetadata`

**Rationale**: The parent issue specifies a clear formula (`estimate_hours = max(0.5, min(8.0, agent_count * 0.25))`) with a well-defined agent-to-size mapping table. A pure function is testable, deterministic, and follows YAGNI. The `IssueMetadata` Pydantic model already exists in `src/models/recommendation.py` with all needed fields (priority, size, estimate_hours, start_date, target_date).

**Alternatives Considered**:
- **AI-based estimation**: Rejected — AI can't know agent count reliably; overkill for a simple heuristic.
- **Config-driven lookup**: Rejected — adds unnecessary config complexity; the formula is simple enough to be a constant.
- **Database-stored estimates**: Rejected — no historical data to leverage; premature optimization.

---

### R2: Non-Blocking Metadata Integration Pattern

**Question**: How to integrate metadata setting into pipeline launch without blocking or failure propagation?

**Decision**: `asyncio.create_task()` with exception logging, called after `add_to_project_with_backlog()` completes (which provides the `project_item_id` needed by `set_issue_metadata()`).

**Rationale**: The existing `_set_issue_metadata()` in `WorkflowOrchestrator` (line 745) already follows this pattern — it catches all exceptions and logs warnings. The pipeline launch should follow the same convention. Using `asyncio.create_task()` makes it truly non-blocking while still capturing errors. The `project_item_id` is populated by `add_to_project_with_backlog()` and stored in the `WorkflowContext`.

**Alternatives Considered**:
- **Inline await**: Simpler but could delay launch response if GraphQL is slow.
- **Background queue**: Rejected — no message queue infrastructure exists; overkill for a single metadata call.
- **Post-launch webhook**: Rejected — adds complexity and latency.

---

### R3: AI Priority Extension in Label Classifier

**Question**: How to extend `classify_labels()` to optionally return priority without breaking existing callers?

**Decision**: New companion function `classify_labels_with_priority()` returning a `ClassificationResult` dataclass with `labels: list[str]` and `priority: IssuePriority | None`. Existing `classify_labels()` remains unchanged for backward compatibility.

**Rationale**: The current `classify_labels()` has 3 callers (pipeline launch, task creation, agent tool). Adding a new function avoids modifying all callers. Only the pipeline launch path needs priority. The prompt extension adds an optional `"priority"` key to the JSON output, with a fallback to `None` if not present (backward compatible with existing AI responses).

**Alternatives Considered**:
- **Modify classify_labels() return type**: Rejected — breaks 3 callers; violates backward compatibility.
- **Separate priority classifier**: Rejected — duplicates the AI call; unnecessary cost.
- **Priority from labels only**: Rejected — labels don't carry urgency signals like "production down".

---

### R4: Size Derivation from Estimate Hours

**Question**: How to map estimate hours to IssueSize enum values?

**Decision**: Threshold-based lookup following the table from the parent issue:

| Estimate Range | Size |
|---------------|------|
| ≤ 0.5h       | XS   |
| 0.51-1.0h    | S    |
| 1.01-2.0h    | M    |
| 2.01-4.0h    | L    |
| > 4.0h       | XL   |

**Rationale**: Direct mapping from the issue specification. Aligns with the `IssueSize` enum values and their descriptions in `recommendation.py` (XS=<1hr, S=1-4hrs, M=1day, L=1-3days, XL=3-5days). The estimate-to-size mapping is coarser than the description suggests, but matches the agent-count heuristic exactly.

**Alternatives Considered**:
- **Fibonacci-based sizing**: Rejected — doesn't align with the linear agent-count formula.
- **T-shirt sizes without numeric mapping**: Rejected — need numeric thresholds for deterministic behavior.

---

### R5: Date Calculation Strategy

**Question**: How to compute start_date and target_date?

**Decision**: `start_date = today (UTC)`, `target_date = today + ceil(estimate_hours / 8) days` (minimum 1 day).

**Rationale**: Start date is always "now" since pipeline launch means work begins immediately. Target date converts hours to working days (8h/day). Using `ceil()` ensures at least 1 day buffer. ISO 8601 format (`YYYY-MM-DD`) matches `IssueMetadata.start_date` and `IssueMetadata.target_date` field types.

**Alternatives Considered**:
- **Calendar-aware dates (skip weekends)**: Rejected — no business calendar library; overkill for automated pipelines that run 24/7.
- **No target date**: Rejected — issue specification explicitly requires it.

---

### R6: Existing Label Lifecycle Verification

**Question**: Are agent:/stalled label lifecycles already covered by tests?

**Decision**: Existing test coverage is sufficient — verify, don't modify.

**Rationale**: 
- `_swap_agent_labels()` is called in `orchestrator.py:1903` and has integration test coverage in `test_pipeline.py`.
- Stalled label addition happens in `recovery.py` with stale-detection tests.
- Stalled label removal happens in `orchestrator.py:1908` during agent swap.
- The parent issue explicitly says "Existing agent/stalled/type labels already work — no changes needed."

**Alternatives Considered**:
- **Add dedicated label lifecycle tests**: Could be done but would be testing existing functionality, not new changes. Deferred to P3 verification story.

## Resolved Unknowns

All NEEDS CLARIFICATION items from Technical Context have been resolved:

| Item | Resolution |
|------|-----------|
| Heuristic formula | `max(0.5, min(8.0, agent_count * 0.25))` with threshold-based size mapping |
| Integration point | After `add_to_project_with_backlog()` in `pipelines.py:431` |
| Non-blocking pattern | `asyncio.create_task()` + exception logging |
| AI priority extension | New `classify_labels_with_priority()` function + prompt extension |
| Backward compatibility | Existing `classify_labels()` unchanged; new function for priority |
| Date calculation | UTC today + `ceil(hours/8)` days |
