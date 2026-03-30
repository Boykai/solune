# Research: Complete v0.2.0 — Intelligent Chat Agent

**Feature**: `001-intelligent-chat-agent` | **Date**: 2026-03-30

## Research Tasks

### R1: Agent Framework `@tool` Decorator — Return Value Handling

**Decision**: Tools return `ToolResult` TypedDict with `content` (str), `action_type` (str | None), `action_data` (dict | None). The agent framework serializes the return value as a tool response message. `ChatAgentService._convert_response()` and `run_stream()` extract action metadata from tool results.

**Rationale**: This is the established pattern used by all 7 existing tools. The `ToolResult` TypedDict provides structured data flow from tools → agent response → chat message → frontend. No framework-level changes needed.

**Alternatives considered**:
- Returning raw strings: Rejected — loses structured action metadata needed for frontend rendering.
- Custom return types: Rejected — `ToolResult` TypedDict is already the convention and is type-safe.

---

### R2: Difficulty-to-Preset Mapping Strategy

**Decision**: Use a deterministic Python dict mapping difficulty levels to preset IDs. The mapping is:
- `"XS"` → `"github-copilot"`
- `"S"` → `"github-copilot"` (primary), `"easy"` (overlap)
- `"M"` → `"medium"` (primary), `"easy"` (overlap)
- `"L"` → `"hard"` (primary), `"medium"` (overlap)
- `"XL"` → `"expert"`
- Unknown/ambiguous → `"medium"` (fallback per FR-013)

Simplified primary mapping used in the tool:
```python
DIFFICULTY_PRESET_MAP = {
    "XS": "github-copilot",
    "S": "easy",
    "M": "medium",
    "L": "hard",
    "XL": "expert",
}
```

**Rationale**: The parent issue specifies overlap ranges (e.g., S/M→easy) but the tool needs a single deterministic selection. Using the higher preset for each level ensures adequate tooling. The fallback to `"medium"` (FR-013) handles edge cases.

**Alternatives considered**:
- LLM-based preset selection: Rejected — adds latency and non-determinism. The mapping is simple enough to be deterministic.
- User-selectable preset: Rejected — contradicts the "automatic" requirement. Users can override by asking the agent to adjust.

---

### R3: Session State for Cross-Tool Communication

**Decision**: Use `context.session.state` (dict) to pass data between sequential tool calls. Keys:
- `"assessed_difficulty"` — str (XS/S/M/L/XL), set by `assess_difficulty`
- `"selected_preset_id"` — str, set by `select_pipeline_preset`
- `"github_token"` — str, injected by `ChatAgentService.run()` (already exists)
- `"project_name"` — str, injected by `ChatAgentService.run()` (already exists)
- `"project_id"` — str, injected by `ChatAgentService.run()` (already exists)

**Rationale**: `ChatAgentService.run()` already injects `github_token`, `project_name`, `project_id`, and `available_tasks` into `agent_session.state`. The new tools follow the same pattern — read from and write to session state.

**Alternatives considered**:
- Tool parameters only (no state): Rejected — the agent must pass difficulty from `assess_difficulty` to `select_pipeline_preset`, which requires either state or the agent re-passing the value. State is more reliable.
- Database persistence: Rejected — session state is ephemeral and appropriate for single-conversation workflows. No need for durability.

---

### R4: Autonomous Creation Safety Gate

**Decision**: Add `CHAT_AUTO_CREATE_ENABLED: bool = False` to `config.py` Settings class. When `False`, the `create_project_issue` tool returns a proposal instead of creating the issue. The agent instructions always include "Shall I proceed?" regardless of this setting (per Open Question 1 recommendation and FR-006).

**Rationale**: Opt-in by default prevents accidental resource creation. The confirmation prompt adds a second layer of safety even when auto-creation is enabled. This matches the parent issue's decision: "Autonomous creation is opt-in."

**Alternatives considered**:
- Per-user setting: Rejected — adds complexity. A system-wide setting is sufficient for v0.2.0. Per-user can be added later.
- Per-project setting: Rejected — same reasoning. System-wide is simpler and sufficient.

---

### R5: MCP Tool Loading Architecture

**Decision**: Create `load_mcp_tools(project_id: str, db: aiosqlite.Connection) -> dict[str, Any]` in `agent_tools.py`. This function:
1. Queries the `mcp_tool_configs` table for active configs matching `project_id`
2. Converts each `McpToolConfig` to a dict compatible with `GitHubCopilotOptions.mcp_servers`
3. Returns empty dict if no MCP tools configured (graceful fallback)

Wire into `ChatAgentService` by calling `load_mcp_tools()` during agent creation and passing `mcp_servers` to `create_agent()` → `GitHubCopilotOptions`.

**Rationale**: The `McpToolConfig` model already stores endpoint URLs and config content. The `GitHubCopilotAgent` already accepts `mcp_servers` in its options. This is a pure mapping layer.

**Alternatives considered**:
- Dynamic MCP discovery at runtime: Rejected — deferred to v0.4.0 (marketplace). Foundation layer only loads project-configured servers.
- MCP in agent instructions: Rejected — MCP servers need to be registered at agent creation time, not in the system prompt.

---

### R6: Pipeline Launch Scope

**Decision**: Full pipeline trigger with status message (per Open Question 2 recommendation). The `launch_pipeline` tool calls `PipelineService` to initiate pipeline execution and returns the pipeline ID, preset, and initial stage list.

**Rationale**: Configure-only would leave users needing to manually trigger — contradicts the "autonomous" goal. Full trigger with a status message gives the user immediate feedback.

**Alternatives considered**:
- Configure-only: Rejected — requires additional manual step, reducing the end-to-end automation value.
- Background trigger with webhook: Rejected — adds complexity. Synchronous trigger with status message is simpler and sufficient.

---

### R7: Multi-Tool Streaming (4+ Sequential Tool Calls)

**Decision**: The existing SSE streaming architecture supports sequential tool calls. `ChatAgentService.run_stream()` yields `tool_call` and `tool_result` events for each tool invocation. The frontend's SSE parser in `api.ts` handles frame-based event parsing with proper buffering. No architecture changes needed.

**Rationale**: The streaming implementation already handles the `tool_call` → `tool_result` event cycle per tool. Multiple sequential calls simply produce multiple cycles. The frontend accumulates state across events.

**Alternatives considered**:
- Batch tool results: Rejected — individual events give better UX (user sees progress at each step).
- WebSocket instead of SSE: Rejected — SSE is already implemented and working. No reason to change transport.

---

### R8: Agent Confirmation UX (Open Question 1)

**Decision**: The agent always asks "Shall I proceed?" before creating external resources, even when `CHAT_AUTO_CREATE_ENABLED=True`. This is enforced in agent instructions, not in tool code.

**Rationale**: More predictable user experience. Users always see what will be created before it happens. The config toggle controls whether the agent *can* create (tool behavior) vs. whether it *will* ask first (always yes).

**Alternatives considered**:
- Skip confirmation when auto=True: Rejected — too aggressive. Users may not expect the agent to create issues without any confirmation.
- Programmatic confirmation gate: Rejected — the agent instruction approach is simpler and more flexible. The agent can adapt the confirmation phrasing contextually.
