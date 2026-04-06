# Data Model: Full Coverage Push + Bug Fixes

**Feature**: 001-test-coverage-bugfixes | **Date**: 2026-04-06

## Overview

This feature is primarily a test-coverage and bug-fix effort. No new persistent data models are introduced. The changes affect runtime state management and test infrastructure only.

## Modified Entities

### PollingState (Runtime — Not Persisted)

**Location**: `solune/backend/src/services/copilot_polling/state.py`

```python
@dataclass
class PollingState:
    is_running: bool = False
    last_poll_time: datetime | None = None
    poll_count: int = 0
    errors_count: int = 0
    last_error: str | None = None
    processed_issues: BoundedDict[int, datetime] = field(...)
```

**Modification**: Add two module-level `asyncio.Lock` instances to guard mutations:

| Lock | Protects | Scope |
|------|----------|-------|
| `_polling_state_lock` | All `_polling_state` field writes | `polling_loop.py`, `pipeline.py` |
| `_polling_startup_lock` | `ensure_polling_started()` check-and-create | `__init__.py` |

**State Transitions**:

```
                ┌─────────────┐
                │   Idle      │  is_running=False
                │ poll_count=0│
                └──────┬──────┘
                       │ ensure_polling_started()
                       │ (guarded by _polling_startup_lock)
                       ▼
                ┌─────────────┐
                │  Running    │  is_running=True
                │ poll_count++│  (guarded by _polling_state_lock)
                └──────┬──────┘
                       │ error or shutdown
                       ▼
                ┌─────────────┐
                │  Stopped    │  is_running=False
                │ errors_count│  last_error set
                └─────────────┘
```

### AgentPreview (Validation Guard — No Schema Change)

**Location**: `solune/backend/src/services/agents/service.py`

No data model change. Existing guard at `_extract_agent_preview()` validates `tools` is a `list`. The regression test confirms this guard works for non-list inputs (e.g., `"read"` string).

## New Test Data Fixtures

No new database fixtures required. All tests use in-memory mocks:

| Test Area | Mock Pattern |
|-----------|-------------|
| Concurrency tests | Direct `_polling_state` field manipulation via imported module |
| MCP tool tests | `AsyncMock` services injected via `McpContext` |
| API template tests | `TemplateRegistry` with stubbed template data |
| Frontend tests | `vi.mock()` for hooks, `render()` with test providers |

## Relationships

```
state.py::_polling_state ──writes──▶ polling_loop.py (6 mutation sites)
state.py::_polling_state ──writes──▶ pipeline.py (8 mutation sites)
state.py::_polling_task  ──writes──▶ __init__.py::ensure_polling_started()
```

No foreign key, cascade, or migration changes.
