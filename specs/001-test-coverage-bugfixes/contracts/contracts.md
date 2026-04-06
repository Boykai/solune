# Contracts: Full Coverage Push + Bug Fixes

**Feature**: 001-test-coverage-bugfixes | **Date**: 2026-04-06

## Overview

This feature introduces no new API endpoints or external contracts. All changes are internal (concurrency fixes, test additions). This document captures the internal contracts that tests will validate.

## Internal Contracts

### C1: Polling State Lock Contract

**Module**: `solune/backend/src/services/copilot_polling/state.py`

```python
# Pre-condition: Called within the event loop
# Post-condition: All _polling_state mutations are serialized
_polling_state_lock: asyncio.Lock

# Pre-condition: Called within the event loop
# Post-condition: At most one polling task exists at any time
_polling_startup_lock: asyncio.Lock
```

**Invariants**:
- `_polling_state.is_running == True` implies exactly one active polling task exists.
- Concurrent `ensure_polling_started()` calls produce exactly one task.
- `_polling_state.last_error` always reflects the most recent error, not a stale overwrite.

### C2: Agent Preview Extraction Contract

**Module**: `solune/backend/src/services/agents/service.py`

```python
@staticmethod
def _extract_agent_preview(text: str) -> AgentPreview | None:
    """
    Pre-condition: text is a string (may contain agent-config code block)
    Post-condition:
      - Returns AgentPreview if valid JSON with name (str) and tools (list)
      - Returns None for: no code block, invalid JSON, empty name,
        missing name, non-dict config, non-list tools
    """
```

### C3: MCP Tool Response Contract

**All MCP tools follow this response pattern**:

```python
# Success response
{"status": "ok", "data": {...}}  # or direct data dict

# Error response
{"error": str}  # human-readable error message
```

**Specific tool contracts**:

| Tool | Input | Success | Error |
|------|-------|---------|-------|
| `list_chores(project_id)` | valid project_id | `{"chores": [...]}` | `{"error": "..."}` |
| `trigger_chore(project_id, chore_id)` | valid IDs | `{"result": {...}}` | `{"error": "..."}` |
| `send_chat_message(project_id, message)` | valid project_id + message | `{"content": "..."}` | `{"error": "..."}` |
| `get_activity(project_id, limit)` | valid project_id, 1≤limit≤100 | `{"events": [...]}` | `{"error": "..."}` |
| `update_item_status(project_id, item_id, status)` | valid IDs + status | `{"success": true, "status": "..."}` | `{"error": "..."}` |

### C4: Test Mock Migration Contract

**Before** (deprecated):
```python
patch("src.services.copilot_polling.get_project_repository", ...)
patch("src.services.copilot_polling.poll_for_copilot_completion", ...)
```

**After** (current):
```python
patch("src.services.copilot_polling.resolve_repository", ...)
patch("src.services.copilot_polling.ensure_polling_started", ...)
```

### C5: Frontend Component Render Contracts

| Component | Required Props | Renders | Testable Behavior |
|-----------|---------------|---------|-------------------|
| `PageTransition` | (none — uses useLocation) | `<Outlet />` with key={pathname} | Animation class present, children rendered |
| `CleanUpSummary` | `result \| error`, `onDismiss` | Portal modal | `useScrollLock` called, dismiss on Escape/backdrop |
| `CleanUpButton` | (board context) | Workflow trigger | State transitions: idle→loading→confirming→executing→summary |
| `PipelineStagesSection` | `pipelines`, `agents` | Stage cards + dropdown | Pipeline selection, stage rendering |
| `AddAgentPopover` | `onSelect`, `assignedAgents` | Radix Popover | Search filter, duplicate detection, loading states |
