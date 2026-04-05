# Research: Full-Stack Plan Pipeline Enhancement (v2 — Copilot SDK + MAF)

**Branch**: `001-full-stack-plan-pipeline` | **Date**: 2026-04-04

## Research Tasks

### R1: Copilot SDK v1.0.17 Custom Agent API

**Decision**: Use `copilot-sdk>=1.0.17` `create_session(custom_agents=[...])` to define a dedicated `solune-plan` agent with tool whitelist and system prompt, replacing the current `is_plan_mode` flag-based switching in `chat_agent.py`.

**Rationale**: The current implementation uses a boolean flag (`is_plan_mode`) in `AgentSession.state` to switch between regular chat tools and plan-only tools. The SDK's custom agent primitive provides:
- Native tool whitelisting per agent (no manual tool filtering)
- Per-agent system prompts (no conditional prompt building)
- CLI/IDE interoperability via agent profiles
- Permission isolation (read-only agents vs. full-tool agents)

**Alternatives Considered**:
- **Keep `is_plan_mode` flag**: Simpler short-term but no CLI interop, manual tool filtering error-prone, doesn't scale to multi-agent pipeline stages
- **Custom agent framework wrapper**: Extra abstraction layer with no SDK benefits; the project already uses `agent-framework-github-copilot` which wraps the SDK
- **Separate FastAPI service per agent**: Over-engineered; SDK handles agent isolation natively

**Current Codebase Impact**:
- `agent_provider.py`: Add factory method for plan agent sessions using SDK custom agents
- `chat_agent.py`: Route plan mode through new factory instead of flag-based delegation
- `agent_tools.py`: No change — existing `register_plan_tools()` already isolates tools

### R2: Session Hooks for Automatic Plan Versioning

**Decision**: Register `on_pre_tool_use` and `on_post_tool_use` session hooks to automatically snapshot plan versions before `save_plan` overwrites and emit diff events after completion.

**Rationale**: The current `save_plan()` tool in `agent_tools.py` (lines 636-807) overwrites the plan in-place with no version history. Adding versioning logic directly to the tool would violate separation of concerns. SDK session hooks provide:
- Transparent interception before/after tool execution
- No modification to existing `save_plan()` tool logic
- Composable with other hooks (logging, metrics)

**Alternatives Considered**:
- **Database triggers**: SQLite supports triggers but async Python can't easily react to them for SSE events
- **Modify `save_plan()` directly**: Violates single-responsibility; mixes versioning with plan persistence
- **Store-level middleware**: Would require custom abstraction over `chat_store.py`; SDK hooks are simpler

**Current Codebase Impact**:
- New `plan_agent_provider.py`: Hook registration and snapshot logic
- `chat_store.py`: Add `snapshot_plan_version()` function and `get_plan_versions()` query
- New migration `040_plan_versioning.sql`: `chat_plan_versions` table + `version` column on `chat_plans`

### R3: Sub-Agent Pipeline Orchestrator

**Decision**: Create `pipeline_orchestrator.py` that sequences speckit agents via SDK sessions, listening for `subagent.completed/failed` events to drive stage transitions, with `asyncio.gather()` for parallel groups.

**Rationale**: The current pipeline in `services/pipelines/service.py` defines preset configurations but doesn't leverage SDK sub-agent events. The SDK provides:
- Native `subagent.started/completed/failed` events mapped to pipeline stages
- Built-in error propagation and retry via event handlers
- Parallel execution support via SDK session management

**Alternatives Considered**:
- **Extend existing `pipelines/service.py`**: Current service is configuration-focused (presets/stages); runtime orchestration is a different concern
- **Celery/task queue**: Over-engineered for in-process agent coordination; adds deployment complexity
- **Custom event bus**: Reinventing what SDK provides natively

**Current Codebase Impact**:
- New `pipeline_orchestrator.py`: Stage sequencing, parallel groups, event emission
- `chat_agent.py`: Wire orchestrator for pipeline-mode execution
- Frontend: New `stage_started/completed/failed` SSE events

### R4: SDK Streaming Event Mapping

**Decision**: Map SDK native events to enhanced SSE events:
- `assistant.reasoning_delta` → `reasoning` event
- `tool.execution_start` → `tool_start` event
- `tool.execution_completion` → `tool_result` event (existing)
- `assistant.intent` → enhanced `thinking` event
- `subagent.*` → `stage_*` events

**Rationale**: The current streaming implementation in `chat_agent.py` uses custom `thinking` events with three phases (`researching`, `planning`, `refining`). The SDK provides richer event granularity:
- Reasoning deltas show agent thought process in real-time
- Tool execution events provide precise timing
- Sub-agent events drive pipeline progress visualization

**Alternatives Considered**:
- **Keep custom thinking events only**: Loses SDK event richness; harder to maintain as SDK evolves
- **Pass SDK events through raw**: Frontend would need SDK-specific parsing; breaks abstraction
- **Hybrid approach** (chosen): Map SDK events to enhanced SSE while preserving existing event shape for backward compatibility

**Current Codebase Impact**:
- `chat_agent.py`: Enhanced event generator mapping SDK events → SSE
- Frontend `types/index.ts`: Extend `ThinkingPhase` type with new event types
- Frontend `ThinkingIndicator.tsx`: Handle new event types

### R5: Plan Versioning Schema Design

**Decision**: Add `version` column to `chat_plans` and create `chat_plan_versions` table with full plan snapshot per version.

**Rationale**: The plan refinement workflow (`save_plan` called multiple times in a session) currently overwrites in-place. Version history enables:
- Diff visualization between plan iterations
- Rollback capability (future)
- Audit trail for plan evolution

**Schema Design**:
```sql
-- Migration 040_plan_versioning.sql
ALTER TABLE chat_plans ADD COLUMN version INTEGER NOT NULL DEFAULT 1;

CREATE TABLE chat_plan_versions (
    version_id    TEXT PRIMARY KEY,
    plan_id       TEXT NOT NULL,
    version       INTEGER NOT NULL,
    title         TEXT NOT NULL,
    summary       TEXT NOT NULL,
    steps_json    TEXT NOT NULL,  -- JSON snapshot of all steps
    created_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    FOREIGN KEY (plan_id) REFERENCES chat_plans(plan_id) ON DELETE CASCADE
);
```

**Alternatives Considered**:
- **Event sourcing**: Full event log per plan change; over-engineered for this use case
- **Git-based versioning**: Store plan as file in repo; adds latency and complexity
- **JSON diff storage**: Store only deltas; harder to reconstruct full versions for display

### R6: Step CRUD and DAG Validation

**Decision**: Add step mutation APIs (`POST/PATCH/DELETE /plans/{plan_id}/steps`) with topological sort validation and register matching `@define_tool` functions for agent-driven mutations.

**Rationale**: Current `save_plan()` replaces all steps atomically. Per-step CRUD enables:
- Inline editing of individual steps without full plan rewrite
- Drag-and-drop reordering with position updates
- Agent-driven step modifications via `@define_tool`
- DAG validation prevents circular dependencies

**Validation Algorithm**: Kahn's algorithm for topological sort — O(V+E) complexity, detects cycles by checking if all nodes are visited.

**Alternatives Considered**:
- **Keep atomic save only**: Simpler but no granular editing; agent must regenerate entire plan for single step change
- **Client-side validation only**: Security risk; server must enforce DAG constraints
- **Adjacency matrix**: Less efficient for sparse graphs; Kahn's with adjacency lists is standard

**Current Codebase Impact**:
- `chat_store.py`: Add `add_plan_step()`, `update_plan_step()`, `delete_plan_step()`, `reorder_plan_steps()`
- `api/chat.py`: New step CRUD endpoints
- `agent_tools.py`: New `@define_tool` for `add_step`, `edit_step`, `delete_step`
- New migration `041_plan_step_status.sql`: Per-step approval status column

### R7: SDK Elicitation for Step Feedback

**Decision**: Use SDK's `session.ui.elicitation()` / `ask_user` for structured per-step feedback dialogs instead of free-text chat messages.

**Rationale**: Current plan refinement uses regular chat messages. SDK elicitation provides:
- Structured input (confirm/select/input dialogs)
- Agent-controlled dialog flow
- UI framework integration (renders as inline widgets)

**Alternatives Considered**:
- **Free-text chat only**: Current approach; works but no structure or agent-guided flow
- **Custom modal UI**: Frontend-only; no agent integration for intelligent follow-up
- **Slash commands**: Limited to text; can't render rich input widgets

**Current Codebase Impact**:
- `chat_agent.py`: Handle `on_user_input_request` for elicitation events
- Frontend: Handle elicitation SSE events, render inline input widgets
- `plan_instructions.py`: Add elicitation usage instructions to system prompt

### R8: Copilot CLI Plugin Packaging (Stretch)

**Decision**: Package plan agents as a Copilot CLI plugin in `solune/cli-plugin/` with `plugin.json`, agent definitions, skills, and MCP configuration.

**Rationale**: Phase 4 stretch goal. CLI plugin enables:
- `copilot /plugin install` for CLI-native plan mode
- IDE integration via ACP server endpoint
- Developer workflow without web UI dependency

**Alternatives Considered**:
- **Standalone CLI tool**: No Copilot integration; separate maintenance burden
- **VS Code extension only**: Platform-specific; CLI plugin covers CLI + IDE
- **Skip entirely**: Valid for MVP; flagged as stretch goal
