# Data Model: Human Agent — Delay Until Auto-Merge

**Feature**: 001-human-agent-delay-until-auto-merge | **Date**: 2026-04-04

## Entities

### 1. PipelineAgentNode (existing — no schema change)

**Location**: `solune/backend/src/models/pipeline.py:8-18`

```python
class PipelineAgentNode(BaseModel):
    id: str
    agent_slug: str
    agent_display_name: str = ""
    model_id: str = ""
    model_name: str = ""
    tool_ids: list[str] = Field(default_factory=list)
    tool_count: int = 0
    config: dict = Field(default_factory=dict)  # ← delay_seconds stored here
```

**config dict schema** (when `agent_slug == "human"` and delay is configured):

| Key | Type | Required | Constraints | Description |
|-----|------|----------|-------------|-------------|
| `delay_seconds` | `int` | No | `[1, 86400]` | Seconds to wait before auto-merge. When absent or `None`, current manual-wait behavior applies. |

**config dict schema** (existing, all agents):

| Key | Type | Required | Constraints | Description |
|-----|------|----------|-------------|-------------|
| `model_id` | `str` | No | — | Override model ID for this agent |
| `model_name` | `str` | No | — | Override model display name |

**Note**: `delay_seconds` is only semantically valid when `agent_slug == "human"`. The backend ignores it for non-human agents.

---

### 2. AgentAssignment (existing — no schema change)

**Location**: `solune/backend/src/models/agent.py:17-26`

```python
class AgentAssignment(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    slug: str = Field(...)
    display_name: str | None = Field(default=None)
    config: dict | None = Field(default=None)  # ← delay_seconds flows through here
```

**Change in config.py**: The `config` dict construction changes from:

```python
# BEFORE (config.py:371-376)
config={
    "model_id": node.model_id,
    "model_name": node.model_name,
}
if node.model_id
else None,
```

To:

```python
# AFTER — merge node.config into AgentAssignment.config
config={
    **node.config,
    "model_id": node.model_id,
    "model_name": node.model_name,
}
if node.model_id or node.config
else None,
```

This ensures `delay_seconds` (and any future config keys) flow from `PipelineAgentNode.config` through `AgentAssignment.config` to the execution layer.

---

### 3. PipelineState (modified — new field)

**Location**: `solune/backend/src/services/workflow_orchestrator/models.py:140-177`

**New field added**:

```python
@dataclass
class PipelineState:
    # ... existing fields ...
    auto_merge: bool = False
    # NEW: Maps agent_slug → config dict for runtime config access
    agent_configs: dict[str, dict] = field(default_factory=dict)
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `agent_configs` | `dict[str, dict]` | `{}` | Maps agent slug to its config dict. Populated at pipeline launch from `WorkflowConfiguration.AgentAssignment.config` dicts. Allows the execution loop to read `delay_seconds` for the human agent without re-querying the workflow configuration. |

**Serialization**: `PipelineState` is a Python `dataclass` stored in-memory (module-level dict). It is serialized to JSON for state persistence via `dataclasses.asdict()`. The new `agent_configs` field is a simple `dict[str, dict]` — no custom serialization needed.

---

### 4. PipelineAgentNode (frontend — no type change)

**Location**: `solune/frontend/src/types/index.ts:1187-1196`

```typescript
export interface PipelineAgentNode {
  id: string;
  agent_slug: string;
  agent_display_name: string;
  model_id: string;
  model_name: string;
  tool_ids: string[];
  tool_count: number;
  config: Record<string, unknown>;  // ← delay_seconds stored here, no type change needed
}
```

The existing `config: Record<string, unknown>` type already accommodates `delay_seconds: number`. No frontend type changes required.

---

## Relationships

```text
PipelineAgentNode.config["delay_seconds"]
  ↓ (saved to pipeline config JSON)
AgentAssignment.config["delay_seconds"]
  ↓ (populated at pipeline launch)
PipelineState.agent_configs["human"]["delay_seconds"]
  ↓ (read at execution time)
pipeline.py: _advance_pipeline() → delay loop → _attempt_auto_merge()
```

## State Transitions

### Human Agent with `delay_seconds` set:

```text
[Pipeline reaches human agent]
  → Create sub-issue (existing behavior)
  → Comment "⏱️ Auto-merge in {duration}"
  → State: "⏱️ Delay ({duration})"
  → Loop: asyncio.sleep(15) + check sub-issue status
    ├── Sub-issue closed early → break loop → proceed
    └── Delay expired → proceed
  → Call _attempt_auto_merge()
  → Close sub-issue with completion comment
  → Mark agent as completed
  → Advance pipeline
```

### Human Agent without `delay_seconds` (unchanged):

```text
[Pipeline reaches human agent]
  → Create sub-issue (existing behavior)
  → State: "active" (manual wait)
  → Poll for "Done!" comment or sub-issue close
  → Mark agent as completed
  → Advance pipeline
```

### Human Agent without `delay_seconds` + auto_merge active + last step (unchanged):

```text
[Pipeline reaches human agent]
  → Skip human (existing ⏭ SKIPPED behavior)
  → Close sub-issue with "Skipped — Auto Merge enabled"
  → Advance pipeline → transition → auto-merge
```

## Validation Rules

| Rule | Scope | Implementation |
|------|-------|----------------|
| `delay_seconds` must be `int` in `[1, 86400]` | Backend runtime | Guard check in `pipeline.py` before delay loop |
| `delay_seconds` only meaningful for `agent_slug == "human"` | Backend runtime | Ignored for non-human agents |
| `delay_seconds` must be positive integer | Frontend input | `<input type="number" min={1} max={86400}>` |
| `delay_seconds` absent = manual wait behavior | Backend runtime | Default path when key not in config |
