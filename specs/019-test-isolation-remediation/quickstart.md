# Quickstart: Test Isolation & State-Leak Remediation

**Feature**: 019-test-isolation-remediation | **Date**: 2026-04-07

> Step-by-step developer guide for implementing the test isolation fixes. Each step is independently verifiable — run the validation command after completing each step.

## Prerequisites

```bash
cd solune/backend
PATH=$HOME/.local/bin:$PATH uv sync --extra dev

cd solune/frontend
npm ci
```

## Validation Commands

```bash
# Backend unit tests (run after each backend step)
cd solune/backend && PATH=$HOME/.local/bin:$PATH uv run pytest tests/unit/ -x -q

# Backend with random ordering (run after Phase 2)
cd solune/backend && PATH=$HOME/.local/bin:$PATH uv run pytest tests/unit/ --randomly-seed=12345 -x -q

# Frontend tests (run after each frontend step)
cd solune/frontend && npx vitest run --reporter=verbose

# Coverage check
cd solune/backend && PATH=$HOME/.local/bin:$PATH uv run pytest tests/ --cov --cov-fail-under=75
cd solune/frontend && npx vitest run --coverage
```

---

## Phase 1 — Backend: Expand Central Autouse Fixture

### Step 1.1: Expand `_clear_test_caches` in `conftest.py`

**File**: `solune/backend/tests/conftest.py` (lines 245-267)

1. Replace the existing fixture with the expanded version that clears ALL discovered globals:

```python
@pytest.fixture(autouse=True)
def _clear_test_caches():
    """Clear **all** global caches and mutable module state between tests.

    Prevents cross-test contamination from module-level globals across the
    entire backend. Clears before AND after each test for isolation.
    """
    from src.config import clear_settings_cache
    from src.services.cache import cache as _cache

    # ── api/chat.py ──
    from src.api.chat import _locks, _messages, _proposals, _recommendations

    # ── pipeline_state_store.py ──
    from src.services import pipeline_state_store

    # ── workflow_orchestrator ──
    from src.services.workflow_orchestrator import (
        _issue_main_branches,
        _issue_sub_issue_map,
        _pipeline_states,
        _transitions,
        _workflow_configs,
    )
    from src.services.workflow_orchestrator.transitions import _agent_trigger_inflight
    import src.services.workflow_orchestrator.orchestrator as orch_mod

    # ── copilot_polling/state.py ──
    import src.services.copilot_polling.state as poll_state

    # ── websocket.py ──
    from src.services import websocket

    # ── settings_store.py ──
    from src.services.settings_store import _auto_merge_cache, _queue_mode_cache

    # ── signal_chat.py ──
    from src.services.signal_chat import _signal_pending

    # ── github_auth.py ──
    from src.services.github_auth import _oauth_states

    # ── agent_creator.py ──
    from src.services.agent_creator import _agent_sessions

    # ── template_files.py ──
    import src.services.template_files as tmpl_mod

    # ── app_templates/registry.py ──
    import src.services.app_templates.registry as reg_mod

    # ── done_items_store.py ──
    import src.services.done_items_store as done_mod

    # ── session_store.py ──
    import src.services.session_store as sess_mod

    def _reset():
        # Core cache + settings
        _cache.clear()
        clear_settings_cache()

        # api/chat
        _messages.clear()
        _proposals.clear()
        _recommendations.clear()
        _locks.clear()

        # pipeline_state_store
        _pipeline_states.clear()
        _issue_main_branches.clear()
        _issue_sub_issue_map.clear()
        _agent_trigger_inflight.clear()
        pipeline_state_store._project_launch_locks.clear()
        pipeline_state_store._store_lock = None
        pipeline_state_store._db = None

        # workflow_orchestrator
        _transitions.clear()
        _workflow_configs.clear()
        orch_mod._orchestrator_instance = None
        orch_mod._tracking_table_cache.clear()

        # copilot_polling/state — collections
        poll_state._monitored_projects.clear()
        poll_state._processed_issue_prs.clear()
        poll_state._review_requested_cache.clear()
        poll_state._posted_agent_outputs.clear()
        poll_state._claimed_child_prs.clear()
        poll_state._pending_agent_assignments.clear()
        poll_state._system_marked_ready_prs.clear()
        poll_state._copilot_review_first_detected.clear()
        poll_state._copilot_review_requested_at.clear()
        poll_state._recovery_last_attempt.clear()
        poll_state._merge_failure_counts.clear()
        poll_state._pending_auto_merge_retries.clear()
        poll_state._pending_post_devops_retries.clear()
        poll_state._background_tasks.clear()
        poll_state._app_polling_tasks.clear()
        # copilot_polling/state — locks
        # Lazy-init locks (_ws_lock, _store_lock) → None (recreated on demand)
        # Direct-use polling locks → fresh asyncio.Lock() (no lazy getter)
        poll_state._polling_state_lock = asyncio.Lock()
        poll_state._polling_startup_lock = asyncio.Lock()
        # copilot_polling/state — scalars
        poll_state._polling_task = None
        poll_state._polling_state = poll_state.PollingState()
        poll_state._activity_window.clear()
        poll_state._consecutive_idle_polls = 0
        poll_state._adaptive_tier = "medium"
        poll_state._consecutive_poll_failures = 0

        # websocket
        websocket._ws_lock = None

        # settings_store
        _queue_mode_cache.clear()
        _auto_merge_cache.clear()

        # signal_chat
        _signal_pending.clear()

        # github_auth
        _oauth_states.clear()

        # agent_creator
        _agent_sessions.clear()

        # template_files
        tmpl_mod._cached_files = None
        tmpl_mod._cached_warnings = None

        # app_templates/registry
        reg_mod._cache = None

        # done_items_store
        done_mod._db = None

        # session_store
        sess_mod._encryption_service = None

    _reset()
    yield
    _reset()
```

2. **Verify**: `cd solune/backend && uv run pytest tests/unit/ -x -q` — all tests pass

### Step 1.2: Verify Integration Conftest

**File**: `solune/backend/tests/integration/conftest.py`

No changes needed — the existing `_reset_integration_state` fixture provides defense-in-depth. The central fixture now covers everything the integration fixture does and more.

**Verify**: `cd solune/backend && uv run pytest tests/integration/ -x -q` — all tests pass

---

## Phase 2 — Backend: Add pytest-randomly

### Step 2.1: Add Dependency

**File**: `solune/backend/pyproject.toml`

Add `pytest-randomly>=3.16.0` to the `[project.optional-dependencies] dev` list:

```toml
[project.optional-dependencies]
dev = [
    "pytest>=9.0.0",
    "pytest-asyncio>=1.3.0",
    "pytest-cov>=7.0.0",
    "pytest-randomly>=3.16.0",   # <-- ADD THIS
    "pytest-repeat>=0.9.3",
    "pytest-timeout>=2.2",
    # ... rest unchanged
]
```

Then: `cd solune/backend && uv sync --extra dev`

### Step 2.2: Verify with Multiple Seeds

```bash
cd solune/backend
uv run pytest tests/unit/ --randomly-seed=12345 -x -q
uv run pytest tests/unit/ --randomly-seed=99999 -x -q
uv run pytest tests/unit/ --randomly-seed=42 -x -q
```

All three runs must pass.

---

## Phase 3 — Frontend: Fix Timer & UUID Leaks

### Step 3.1: Fix Fake Timer Leak

**File**: `solune/frontend/src/hooks/useFileUpload.test.ts`

Add `afterEach` cleanup after the existing `beforeEach`:

```typescript
afterEach(() => {
  vi.useRealTimers();
});
```

**Verify**: `cd solune/frontend && npx vitest run src/hooks/useFileUpload.test.ts`

### Step 3.2: Reset UUID Counter

**File**: `solune/frontend/src/test/setup.ts`

Move the counter variable to module scope and add a `beforeEach` reset:

```typescript
let _counter = 0;

// Reset UUID counter before each test for deterministic values
beforeEach(() => {
  _counter = 0;
});

if (typeof globalThis.crypto === 'undefined') {
  // @ts-expect-error - partial crypto shim for test environments
  globalThis.crypto = {};
}
if (typeof globalThis.crypto.randomUUID !== 'function') {
  globalThis.crypto.randomUUID = () =>
    `00000000-0000-4000-8000-${String(++_counter).padStart(12, '0')}` as `${string}-${string}-${string}-${string}-${string}`;
}
```

**Verify**: `cd solune/frontend && npx vitest run --reporter=verbose`

### Step 3.3: Add Mock Cleanup to Spy-Using Tests

**File**: `solune/frontend/src/layout/TopBar.test.tsx`

Add `afterEach` block:

```typescript
afterEach(() => {
  vi.restoreAllMocks();
});
```

**File**: `solune/frontend/src/layout/AuthGate.test.tsx`

Add `afterEach` block:

```typescript
afterEach(() => {
  vi.restoreAllMocks();
});
```

**File**: `solune/frontend/src/hooks/useAuth.test.tsx`

Change `afterEach` from `vi.resetAllMocks()` to `vi.restoreAllMocks()`:

```typescript
afterEach(() => {
  vi.restoreAllMocks();  // was: vi.resetAllMocks()
});
```

**Verify**: `cd solune/frontend && npx vitest run --reporter=verbose`

---

## Phase 4 — Verification

### Step 4.1-4.3: Backend Random Seed Tests

```bash
cd solune/backend
uv run pytest tests/unit/ --randomly-seed=12345 -x -q
uv run pytest tests/unit/ --randomly-seed=99999 -x -q
uv run pytest tests/unit/ --randomly-seed=42 -x -q
```

### Step 4.4: Frontend Full Run

```bash
cd solune/frontend
npx vitest run --reporter=verbose
```

### Step 4.5: Coverage Check

```bash
cd solune/backend && uv run pytest tests/ --cov --cov-fail-under=75
cd solune/frontend && npx vitest run --coverage
```

### Step 4.6: Integration Tests

```bash
cd solune/backend && uv run pytest tests/integration/ -x -q
cd solune/backend && uv run pytest tests/concurrency/ -x -q
```
