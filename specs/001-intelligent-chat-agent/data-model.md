# Data Model: Complete v0.2.0 — Intelligent Chat Agent

**Feature**: `001-intelligent-chat-agent` | **Date**: 2026-03-30

## Entity Overview

This feature extends the existing data model with minimal additions. No new database tables are required — all new state is either ephemeral (session state) or extends existing enums/configs.

## Entities

### 1. ActionType (Enum Extension)

**File**: `solune/backend/src/models/chat.py`
**Change**: Add `PIPELINE_LAUNCH` to existing `ActionType` StrEnum.

| Value | Description | Added By |
|-------|-------------|----------|
| `TASK_CREATE` | Create a new task | Existing |
| `STATUS_UPDATE` | Move task between statuses | Existing |
| `PROJECT_SELECT` | Select a project | Existing |
| `ISSUE_CREATE` | Create a GitHub issue | Existing |
| **`PIPELINE_LAUNCH`** | **Launch a pipeline for a project** | **New** |

**Relationships**: Referenced by `ChatMessage.action_type`. Consumed by `_convert_agent_response()` in `chat_agent.py` and frontend action handlers.

---

### 2. Session State Keys (Ephemeral — In-Memory Dict)

**Storage**: `AgentSession.state` (dict, in-memory, TTL-evicted)
**No database schema change** — session state is already a generic dict.

| Key | Type | Set By | Read By | Description |
|-----|------|--------|---------|-------------|
| `github_token` | `str` | `ChatAgentService.run()` | `create_project_issue` | User's GitHub OAuth token |
| `project_name` | `str` | `ChatAgentService.run()` | `create_project_issue`, `select_pipeline_preset` | Current project name |
| `project_id` | `str` | `ChatAgentService.run()` | `launch_pipeline`, `load_mcp_tools` | Current project ID |
| `available_tasks` | `list[dict]` | `ChatAgentService.run()` | `update_task_status` | Available tasks for matching |
| `available_statuses` | `list[str]` | `ChatAgentService.run()` | `get_pipeline_list` | Pipeline status columns |
| `pipeline_id` | `str \| None` | `ChatAgentService.run()` | `launch_pipeline` | Active pipeline config ID |
| **`assessed_difficulty`** | **`str`** | **`assess_difficulty`** | **`select_pipeline_preset`** | **XS/S/M/L/XL rating** |
| **`selected_preset_id`** | **`str`** | **`select_pipeline_preset`** | **`create_project_issue`, `launch_pipeline`** | **Chosen pipeline preset ID** |

**Bold** = new keys added by this feature.

---

### 3. Difficulty Assessment (Tool Result — Transient)

**Not persisted** — returned as `ToolResult` and recorded in session state.

```
ToolResult {
    content: str          # Human-readable reasoning (e.g., "This is a medium complexity project because...")
    action_type: None     # No frontend action triggered
    action_data: None     # No structured payload
}
```

**Side effect**: Sets `context.session.state["assessed_difficulty"]` to one of: `"XS"`, `"S"`, `"M"`, `"L"`, `"XL"`.

---

### 4. Pipeline Preset Selection (Tool Result — Transient)

**Not persisted** — returned as `ToolResult` and recorded in session state.

```
ToolResult {
    content: str          # Preset details (name, stages, agents)
    action_type: None     # No frontend action triggered
    action_data: None     # No structured payload
}
```

**Side effect**: Sets `context.session.state["selected_preset_id"]` to a preset ID (e.g., `"medium"`, `"hard"`).

**Difficulty → Preset Mapping**:

| Difficulty | Preset ID | Preset Name | Description |
|-----------|-----------|-------------|-------------|
| XS | `github-copilot` | GitHub Copilot | Single-stage, Copilot-only |
| S | `easy` | Easy | Lightweight: Copilot implements, review agents check |
| M | `medium` | Medium | Balanced: Spec Kit plans, Copilot implements, review verifies |
| L | `hard` | Hard | Thorough: Full Spec Kit specify & plan, implementation + review |
| XL | `expert` | Expert | Comprehensive: Full Spec Kit, Designer, QA, Tester, Archivist |
| Unknown | `medium` | Medium | Fallback (FR-013) |

---

### 5. Project Issue Creation (Tool Result — Triggers Action)

**Not persisted locally** — creates a GitHub issue via API, returns metadata.

```
ToolResult {
    content: str          # "Created issue #42: {title} — {url}"
    action_type: "issue_create"
    action_data: {
        "issue_number": int,      # GitHub issue number
        "issue_url": str,         # Full GitHub issue URL
        "preset_id": str,         # Selected pipeline preset
        "project_name": str       # Project name
    }
}
```

**Safety gate**: When `CHAT_AUTO_CREATE_ENABLED=False`, returns a proposal instead:
```
ToolResult {
    content: str          # "I recommend creating issue: {title}. Auto-creation is disabled..."
    action_type: None     # No action — proposal only
    action_data: None
}
```

---

### 6. Pipeline Launch (Tool Result — Triggers Action)

**Not persisted locally** — triggers pipeline execution via `PipelineService`, returns metadata.

```
ToolResult {
    content: str          # "Launched pipeline {id} with preset {preset}..."
    action_type: "pipeline_launch"
    action_data: {
        "pipeline_id": str,       # Pipeline configuration ID
        "preset": str,            # Preset name/ID used
        "stages": list[str]       # Stage names in execution order
    }
}
```

---

### 7. Settings Extension (Config — Environment Variable)

**File**: `solune/backend/src/config.py`

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| **`CHAT_AUTO_CREATE_ENABLED`** | `bool` | `False` | Enable autonomous issue/pipeline creation from chat |

**Validation**: Standard pydantic bool coercion from environment variable.

---

### 8. McpToolConfig (Existing — No Changes)

**File**: `solune/backend/src/models/tools.py`
**Change**: None — existing model is sufficient.

Used by `load_mcp_tools()` to query active MCP configurations for a project and convert them to agent-compatible `mcp_servers` dict format.

Relevant fields for MCP loading:
- `project_id` — Filter configs by project
- `endpoint_url` — MCP server endpoint
- `config_content` — JSON configuration to pass to the server
- `is_active` — Only load active configs
- `name` — Used as the dict key for `mcp_servers`

## Entity Relationship Diagram

```
┌─────────────────┐     sets state     ┌──────────────────────┐
│ assess_difficulty│ ──────────────────▶│ AgentSession.state   │
│ (tool)           │                    │  assessed_difficulty  │
└─────────────────┘                    │  selected_preset_id   │
                                       │  github_token         │
┌──────────────────────┐  reads state  │  project_name         │
│ select_pipeline_preset│◀─────────────│  project_id           │
│ (tool)                │──────────────▶│  pipeline_id          │
└──────────────────────┘  sets state   └──────────────────────┘
                                              │        │
┌──────────────────────┐  reads state         │        │
│ create_project_issue  │◀────────────────────┘        │
│ (tool)                │                               │
└──────────┬───────────┘                               │
           │ calls                                     │
           ▼                                           │
┌──────────────────────┐               ┌───────────────┴──────┐
│ GitHubProjectsService│               │ launch_pipeline      │
│   .create_issue()    │               │ (tool)               │
└──────────────────────┘               └──────────┬───────────┘
                                                  │ calls
                                                  ▼
                                       ┌──────────────────────┐
                                       │ PipelineService      │
                                       │   .seed_presets()    │
                                       │   .get_presets()     │
                                       │   .set_assignment()  │
                                       └──────────────────────┘

┌──────────────────────┐  queries      ┌──────────────────────┐
│ load_mcp_tools()     │──────────────▶│ McpToolConfig (DB)   │
│ (function)           │               │   .project_id        │
└──────────┬───────────┘               │   .endpoint_url      │
           │ returns dict              │   .config_content    │
           ▼                           │   .is_active         │
┌──────────────────────┐               └──────────────────────┘
│ create_agent()       │
│   mcp_servers param  │
└──────────────────────┘
```

## State Transitions

### Conversation Workflow State Machine

```
[Start] ──▶ CLARIFYING ──▶ ASSESSING ──▶ SELECTING ──▶ PROPOSING ──▶ CREATING ──▶ LAUNCHING ──▶ [Done]
   │              │              │              │             │             │             │
   │         ask_clarifying  assess_       select_      (auto=False)  create_       launch_
   │         _question      difficulty    pipeline_    → proposal    project_      pipeline
   │                                      preset       (auto=True)   issue
   │                                                   → confirm
   │
   └── Any step can loop back to CLARIFYING if user provides new information
```

**Notes**:
- Not all states are required — the agent decides based on user input
- PROPOSING vs CREATING depends on `CHAT_AUTO_CREATE_ENABLED`
- Each state transition produces a `ToolResult` visible to the user via SSE
