# Data Model: Test Isolation & State-Leak Remediation

**Feature**: 019-test-isolation-remediation | **Date**: 2026-04-07

> This feature modifies test infrastructure, not runtime data models. This document defines the **global state inventory** — all module-level mutable variables that must be cleared between tests — and the **fixture structure** that manages them.

## Backend Global State Inventory

### Entity: API Chat State (`src/api/chat.py`)

| Variable | Type | Default | Line | Clear Method |
|----------|------|---------|------|-------------|
| `_messages` | `dict[str, list[ChatMessage]]` | `{}` | 92 | `.clear()` |
| `_proposals` | `dict[str, AITaskProposal]` | `{}` | 93 | `.clear()` |
| `_recommendations` | `dict[str, IssueRecommendation]` | `{}` | 94 | `.clear()` |
| `_locks` | `dict[str, asyncio.Lock]` | `{}` | 95 | `.clear()` |

### Entity: Pipeline State Store (`src/services/pipeline_state_store.py`)

| Variable | Type | Default | Line | Clear Method |
|----------|------|---------|------|-------------|
| `_pipeline_states` | `BoundedDict[int, Any]` | `BoundedDict(maxlen=50_000)` | 28 | `.clear()` |
| `_issue_main_branches` | `BoundedDict[int, Any]` | `BoundedDict(maxlen=50_000)` | 29 | `.clear()` |
| `_issue_sub_issue_map` | `BoundedDict[int, dict]` | `BoundedDict(maxlen=50_000)` | 30 | `.clear()` |
| `_agent_trigger_inflight` | `BoundedDict[str, datetime]` | `BoundedDict(maxlen=50_000)` | 31 | `.clear()` |
| `_store_lock` | `asyncio.Lock \| None` | `None` | 34 | `= None` |
| `_project_launch_locks` | `dict[str, asyncio.Lock]` | `{}` | 38 | `.clear()` ⚠️ BUG: never cleared |
| `_db` | `aiosqlite.Connection \| None` | `None` | 41 | `= None` |

### Entity: Workflow Orchestrator (`src/services/workflow_orchestrator/orchestrator.py`)

| Variable | Type | Default | Line | Clear Method |
|----------|------|---------|------|-------------|
| `_orchestrator_instance` | `WorkflowOrchestrator \| None` | `None` | 2798 | `= None` |
| `_tracking_table_cache` | `BoundedDict[int, list]` | `BoundedDict(maxlen=200)` | 70 | `.clear()` |

### Entity: Workflow Config (`src/services/workflow_orchestrator/config.py`)

| Variable | Type | Default | Line | Clear Method |
|----------|------|---------|------|-------------|
| `_transitions` | `list[WorkflowTransition]` | `[]` | 38 | `.clear()` |
| `_workflow_configs` | `BoundedDict[str, WorkflowConfiguration]` | `BoundedDict(maxlen=100)` | 41 | `.clear()` |

### Entity: Copilot Polling State (`src/services/copilot_polling/state.py`)

**Collections (clear with `.clear()`):**

| Variable | Type | Default | Line |
|----------|------|---------|------|
| `_monitored_projects` | `dict[str, MonitoredProject]` | `{}` | 47 |
| `_processed_issue_prs` | `BoundedSet[str]` | `BoundedSet(maxlen=1000)` | 125 |
| `_review_requested_cache` | `BoundedSet[str]` | `BoundedSet(maxlen=500)` | 132 |
| `_posted_agent_outputs` | `BoundedSet[str]` | `BoundedSet(maxlen=500)` | 135 |
| `_claimed_child_prs` | `BoundedSet[str]` | `BoundedSet(maxlen=500)` | 141 |
| `_pending_agent_assignments` | `BoundedDict[str, datetime]` | `BoundedDict(maxlen=500)` | 147 |
| `_system_marked_ready_prs` | `BoundedSet[int]` | `BoundedSet(maxlen=500)` | 159 |
| `_copilot_review_first_detected` | `BoundedDict[int, datetime]` | `BoundedDict(maxlen=200)` | 166 |
| `_copilot_review_requested_at` | `BoundedDict[int, datetime]` | `BoundedDict(maxlen=200)` | 187 |
| `_recovery_last_attempt` | `BoundedDict[int, datetime]` | `BoundedDict(maxlen=200)` | 193 |
| `_merge_failure_counts` | `BoundedDict[int, int]` | `BoundedDict(maxlen=200)` | 201 |
| `_pending_auto_merge_retries` | `BoundedDict[int, int]` | `BoundedDict(maxlen=200)` | 209 |
| `_pending_post_devops_retries` | `BoundedDict[int, dict]` | `BoundedDict(maxlen=200)` | 217 |
| `_background_tasks` | `set[asyncio.Task[None]]` | `set()` | 226 |
| `_app_polling_tasks` | `dict[str, asyncio.Task]` | `{}` | 122 |

**Locks (direct-use — reset to fresh `asyncio.Lock()`):**

| Variable | Type | Default | Line |
|----------|------|---------|------|
| `_polling_state_lock` | `asyncio.Lock` | `asyncio.Lock()` | 112 |
| `_polling_startup_lock` | `asyncio.Lock` | `asyncio.Lock()` | 113 |

**Scalars (reset to default value):**

| Variable | Type | Default | Line |
|----------|------|---------|------|
| `_polling_task` | `asyncio.Task \| None` | `None` | 117 |
| `_consecutive_idle_polls` | `int` | `0` | 249 |
| `_adaptive_tier` | `str` | `"medium"` | 271 |
| `_consecutive_poll_failures` | `int` | `0` | 274 |

**Stateful object (reset to fresh instance):**

| Variable | Type | Default | Line |
|----------|------|---------|------|
| `_polling_state` | `PollingState` | `PollingState()` | 109 |
| `_activity_window` | `deque[bool]` | `deque(maxlen=ACTIVITY_WINDOW_SIZE)` | 268 |

### Entity: WebSocket (`src/services/websocket.py`)

| Variable | Type | Default | Line | Clear Method |
|----------|------|---------|------|-------------|
| `_ws_lock` | `asyncio.Lock \| None` | `None` | 12 | `= None` |

### Entity: Settings Store (`src/services/settings_store.py`)

| Variable | Type | Default | Line | Clear Method |
|----------|------|---------|------|-------------|
| `_queue_mode_cache` | `dict[str, tuple[bool, float]]` | `{}` | 506 | `.clear()` |
| `_auto_merge_cache` | `dict[str, tuple[bool, float]]` | `{}` | 543 | `.clear()` |

### Entity: Signal Chat (`src/services/signal_chat.py`)

| Variable | Type | Default | Line | Clear Method |
|----------|------|---------|------|-------------|
| `_signal_pending` | `dict[str, dict]` | `{}` | 33 | `.clear()` |

### Entity: GitHub Auth (`src/services/github_auth.py`)

| Variable | Type | Default | Line | Clear Method |
|----------|------|---------|------|-------------|
| `_oauth_states` | `BoundedDict[str, datetime]` | `BoundedDict(maxlen=1000)` | 35 | `.clear()` |

### Entity: Agent Creator (`src/services/agent_creator.py`)

| Variable | Type | Default | Line | Clear Method |
|----------|------|---------|------|-------------|
| `_agent_sessions` | `BoundedDict[str, AgentCreationState]` | `BoundedDict(maxlen=100)` | 107 | `.clear()` |

### Entity: Template Files (`src/services/template_files.py`)

| Variable | Type | Default | Line | Clear Method |
|----------|------|---------|------|-------------|
| `_cached_files` | `list[dict[str, str]] \| None` | `None` | 49 | `= None` |
| `_cached_warnings` | `list[str] \| None` | `None` | 50 | `= None` |

### Entity: App Templates Registry (`src/services/app_templates/registry.py`)

| Variable | Type | Default | Line | Clear Method |
|----------|------|---------|------|-------------|
| `_cache` | `dict[str, AppTemplate] \| None` | `None` | 13 | `= None` |

### Entity: Done Items Store (`src/services/done_items_store.py`)

| Variable | Type | Default | Line | Clear Method |
|----------|------|---------|------|-------------|
| `_db` | `aiosqlite.Connection \| None` | `None` | 27 | `= None` |

### Entity: Session Store (`src/services/session_store.py`)

| Variable | Type | Default | Line | Clear Method |
|----------|------|---------|------|-------------|
| `_encryption_service` | `EncryptionService \| None` | `None` | 18 | `= None` |

## Frontend State Inventory

### Entity: UUID Counter (`src/test/setup.ts`)

| Variable | Type | Default | Line | Reset Method |
|----------|------|---------|------|-------------|
| `_counter` | `number` | `0` | 16 | `= 0` in `beforeEach` |

### Entity: Fake Timers (`useFileUpload.test.ts`)

| Variable | Type | Current State | Fix |
|----------|------|--------------|-----|
| Global timer functions | Vitest fake timers | Set in `beforeEach`, never restored | Add `afterEach(() => vi.useRealTimers())` |

### Entity: Spy Leaks (multiple test files)

| File | Spies Used | Current Cleanup | Fix |
|------|-----------|----------------|-----|
| `TopBar.test.tsx` | `vi.fn()` for event listener | `vi.clearAllMocks()` in beforeEach | Add `afterEach(() => vi.restoreAllMocks())` |
| `AuthGate.test.tsx` | `vi.fn()` for useAuth mock | `vi.clearAllMocks()` in beforeEach | Add `afterEach(() => vi.restoreAllMocks())` |
| `useAuth.test.tsx` | `vi.spyOn(window.history)`, `vi.spyOn(window)` | `vi.resetAllMocks()` in afterEach | Upgrade to `vi.restoreAllMocks()` |

## Fixture Architecture

### Expanded `_clear_test_caches` (conftest.py)

```
┌─────────────────────────────────────────────────┐
│         _clear_test_caches (autouse)            │
│   Runs before/after EVERY test (unit + integ)   │
├─────────────────────────────────────────────────┤
│ 1. Import all modules with mutable globals      │
│ 2. Clear all dict/BoundedDict/BoundedSet        │
│ 3. Reset all locks to None                      │
│ 4. Reset all scalars to defaults                │
│ 5. Reset all Optional values to None            │
│ 6. Clear settings LRU cache                     │
│ 7. yield (test runs)                            │
│ 8. Repeat steps 2-6 (teardown)                  │
└─────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────┐
│   _reset_integration_state (integration only)   │
│         Defense-in-depth layer                  │
├─────────────────────────────────────────────────┤
│ Clears same state + integration-specific setup  │
│ Kept as-is for backwards compatibility          │
└─────────────────────────────────────────────────┘
```
