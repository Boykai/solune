# Research: Human Agent — Delay Until Auto-Merge

**Feature**: 001-human-agent-delay-until-auto-merge | **Date**: 2026-04-04

## R1: Where to store `delay_seconds` — PipelineAgentNode.config vs new field

**Decision**: Store `delay_seconds` in `PipelineAgentNode.config` dict (existing field).

**Rationale**: `PipelineAgentNode` already has a `config: dict = Field(default_factory=dict)` field at `solune/backend/src/models/pipeline.py:18`. This dict is an open extension point. Storing `delay_seconds` here requires zero schema migration, zero model changes, and the value flows naturally through the existing `AgentAssignment.config` path. The frontend `PipelineAgentNode` type already declares `config: Record<string, unknown>` (`solune/frontend/src/types/index.ts:1195`), so no TypeScript type changes are needed either.

**Alternatives considered**:
- **New `delay_seconds` field on `PipelineAgentNode` model**: Would require backend model change + frontend type change + serialization updates. Rejected because `config` dict already exists for this purpose.
- **Project-level delay setting**: Would lose per-agent granularity. Different human agents in the same pipeline might need different delays. Rejected.
- **New `HumanAgentConfig` Pydantic model**: Over-engineering for a single integer field. Violates Principle V (Simplicity). Rejected.

## R2: Config flow — How `delay_seconds` reaches the execution loop

**Decision**: Merge full `node.config` into `AgentAssignment.config` at `config.py:367-378`. Add `agent_configs` dict to `PipelineState` at `models.py:140`. Populate at pipeline launch.

**Rationale**: Currently, `config.py:371-376` builds `AgentAssignment.config` with only `{"model_id": ..., "model_name": ...}` when `node.model_id` is truthy, else `None`. The fix is to always start with the full `node.config` dict (which may contain `delay_seconds`) and merge `model_id`/`model_name` into it. This preserves backward compatibility while enabling any future config keys.

At runtime, the execution loop in `pipeline.py` needs to read `delay_seconds` for the current agent. Adding `agent_configs: dict[str, dict]` to `PipelineState` (mapping agent_slug → config dict) gives the polling loop direct access. This field is populated from `WorkflowConfiguration`'s `AgentAssignment.config` dicts when constructing `PipelineState` at `pipelines.py:467-489`.

**Alternatives considered**:
- **Re-query WorkflowConfiguration at execution time**: Would add an extra DB/config lookup on every poll cycle. Inefficient and introduces timing issues if config changes mid-execution. Rejected.
- **Pass config through function parameters**: Would require changing signatures of `_advance_pipeline`, `_handle_human_agent`, and multiple helper functions. Too invasive. Rejected.

## R3: Delay execution strategy — asyncio.sleep with polling vs background task

**Decision**: Loop `asyncio.sleep(15)` in increments within the `_advance_pipeline` function, checking sub-issue status after each sleep.

**Rationale**: The existing polling loop already operates on ~15-second intervals. Using a simple sleep loop with the same cadence:
1. Keeps implementation within the existing `_advance_pipeline` flow (no new background task infrastructure)
2. Enables early cancellation by checking if the sub-issue was closed between sleep intervals
3. Does not block the main event loop (`asyncio.sleep` yields control)
4. Aligns with the existing `_attempt_auto_merge` retry patterns

The total delay is divided into `ceil(delay_seconds / 15)` intervals. After each 15-second sleep, the code checks if the human sub-issue has been closed (via GitHub API). If closed early, the delay loop breaks immediately and proceeds to auto-merge.

**Alternatives considered**:
- **Single `asyncio.sleep(delay_seconds)`**: No early cancellation possible. User would have to wait the full delay even after closing the sub-issue. Rejected.
- **`asyncio.create_task` with cancellation token**: More complex, requires task lifecycle management, potential for orphaned tasks. Over-engineering for a simple delay. Rejected.
- **Celery/background worker**: Adds external dependency. The in-process sleep approach is sufficient for delays up to 24 hours. Rejected.

## R4: Auto-merge trigger — When and how to invoke `_attempt_auto_merge`

**Decision**: After delay expires (or early cancel), call the existing `_attempt_auto_merge()` from `auto_merge.py`. This replaces the current "skip human entirely" behavior.

**Rationale**: `_attempt_auto_merge` (`solune/backend/src/services/copilot_polling/auto_merge.py:31`) already handles all the auto-merge complexity:
1. Discovers main PR via multi-strategy logic
2. Marks draft PRs as ready-for-review
3. Checks CI status
4. Checks mergeability
5. Performs squash merge

The delay feature only needs to call this function after the grace period expires. The existing "skip human if auto_merge" block at `pipeline.py:1951-2039` already demonstrates the pattern — close sub-issue, mark as completed, then transition. The delay feature wraps this with a sleep loop.

**Alternatives considered**:
- **Trigger auto-merge from a webhook**: Would require new webhook handler and event routing. Rejected — the polling loop already has all the context.
- **Schedule a GitHub Actions workflow**: External dependency, latency, and complexity. Rejected.

## R5: Validation boundaries — Where to validate `delay_seconds`

**Decision**: Validate at two points: (1) frontend input component, (2) backend execution in `pipeline.py` before entering the delay loop.

**Rationale**:
- **Frontend**: Numeric input with min=1, max=86400 prevents invalid values at entry time
- **Backend**: Guard in `pipeline.py` before the delay loop ensures safety even if frontend validation is bypassed (API calls, stale clients)
- **No API endpoint validation**: The pipeline config is saved as a JSON blob. Adding validation at the save endpoint would require understanding agent-slug-specific config schemas, which is premature. Runtime validation is sufficient.

**Alternatives considered**:
- **Pydantic validator on PipelineAgentNode**: Would couple pipeline model to human-agent-specific validation. Violates single responsibility. Rejected.
- **API middleware validation**: Too broad — would need to inspect all config dicts for all agent types. Rejected.

## R6: Frontend UX — Toggle vs always-visible input

**Decision**: Toggle "Delay until auto-merge" (off by default), when on: numeric input for seconds with human-readable badge.

**Rationale**: Most human agents won't use delay (it's an opt-in power feature). A toggle keeps the UI clean by default while making the feature discoverable. The badge (`⏱️ Auto-merge: 5m` or `Manual review`) provides at-a-glance status without expanding the node.

**Alternatives considered**:
- **Always-visible input with 0 = disabled**: Confusing — 0 seconds is ambiguous (disabled or immediate?). Rejected.
- **Dropdown with preset values (30s, 1m, 5m, 30m, 1h)**: Limits flexibility. Users may want specific values. Rejected in favor of free-form numeric input.
- **Duration picker (hours:minutes:seconds)**: Over-engineering for a feature that primarily uses round numbers. The badge already formats seconds into human-readable duration. Rejected.

## R7: Backward compatibility — Existing auto-merge skip behavior

**Decision**: Preserve current "skip human entirely" behavior when `delay_seconds` is NOT set AND auto_merge is active AND human is last step. The delay feature is additive — it only changes behavior when `delay_seconds` is explicitly configured.

**Rationale**: The current skip behavior (`pipeline.py:1951-2039`) is a valid optimization for pipelines that don't need a human review window at all. Removing it would be a breaking change for existing users. The new delay feature provides a middle ground: users who want a review window set `delay_seconds`; users who want instant auto-merge leave it unset (current behavior preserved).

**Alternatives considered**:
- **Always require delay for human+auto_merge**: Breaking change. Existing pipelines would stop auto-merging. Rejected.
- **Default delay of 300s (5 min)**: Would change behavior for existing users without explicit opt-in. Rejected.
