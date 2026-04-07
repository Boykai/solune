# Research: Test Isolation & State-Leak Remediation

**Feature**: 019-test-isolation-remediation | **Date**: 2026-04-07

## R1: asyncio Lock Lifecycle in pytest-asyncio

**Context**: Several modules use lazy-initialized `asyncio.Lock()` at module level (`_ws_lock`, `_store_lock`, `_polling_state_lock`, `_polling_startup_lock`). These locks bind to the event loop active at creation time. Since `pytest-asyncio` creates a fresh event loop per test by default, a lock created in one test's event loop becomes invalid in the next test.

**Decision**: For lazy-init locks (`_ws_lock`, `_store_lock`) that use a `_get_*_lock()` getter pattern (`if _lock is None: _lock = asyncio.Lock()`), reset to `None` in the autouse fixture so the lock is recreated on demand in the correct event loop. For polling locks (`_polling_state_lock`, `_polling_startup_lock`) that are used directly without a lazy getter, reset to fresh `asyncio.Lock()` instances in the autouse fixture.

**Rationale**: Lazy-init locks benefit from `None` reset because the production code recreates them in the correct event loop context on first use. Polling locks lack lazy-init getters and are referenced directly via `async with _polling_state_lock:`, so they must be replaced with fresh instances. The autouse fixture runs synchronously before each test, so the fresh `asyncio.Lock()` is not yet bound to any event loop until the test's async code first acquires it.

**Alternatives considered**:
- Blanket reset all locks to `None`: Rejected — polling locks don't have lazy-init getters, so `None` would cause `AttributeError` on first use
- Blanket reset all locks to `asyncio.Lock()`: Rejected — lazy-init locks should follow their existing `None` → create-on-demand pattern
- Use `asyncio.Lock()` with explicit loop parameter: Rejected — `loop` parameter deprecated since Python 3.8, removed in 3.10
- Refactor to dependency injection: Rejected — architectural change, out of scope per issue #1077

## R2: pytest-randomly Configuration and Best Practices

**Context**: Adding `pytest-randomly` to surface hidden test-ordering dependencies. The plugin randomizes test execution order by default, with a seed printed at the start of the run for reproducibility.

**Decision**: Add `pytest-randomly>=3.16.0` to `[project.optional-dependencies] dev` in `pyproject.toml`. No additional configuration needed.

**Rationale**: pytest-randomly works out of the box — it hooks into pytest's collection phase and shuffles test order automatically. The seed is printed as the first line of output (`Using --randomly-seed=XXXX`), making failures reproducible. Version 3.16.0+ supports Python 3.12+ and pytest 8+.

**Alternatives considered**:
- `pytest-random-order`: Rejected — less maintained, fewer features; pytest-randomly is the de facto standard
- `pytest-xdist` with random ordering: Rejected — xdist is for parallelization, not ordering; explicitly out of scope
- Custom pytest plugin: Rejected — unnecessary when a well-maintained plugin exists

**Configuration notes**:
- No `pytest.ini` / `pyproject.toml` config needed — defaults are correct
- To reproduce a failure: `pytest --randomly-seed=XXXX`
- To disable temporarily: `pytest -p no:randomly`
- Compatible with existing `pytest-repeat`, `pytest-timeout`, `pytest-cov`

## R3: Vitest Timer Leak Pattern

**Context**: `useFileUpload.test.ts` calls `vi.useFakeTimers()` in `beforeEach` but never calls `vi.useRealTimers()`. Fake timers replace global `setTimeout`, `setInterval`, `Date.now()`, etc. When not restored, subsequent tests in the same Vitest worker inherit fake timers.

**Decision**: Add `afterEach(() => { vi.useRealTimers(); })` to `useFileUpload.test.ts`.

**Rationale**: Vitest's `vi.useFakeTimers()` replaces global timer functions. Without `vi.useRealTimers()`, the fake implementation leaks into other tests. This can cause:
- `setTimeout` callbacks never firing (tests hang or fail with timeouts)
- `Date.now()` returning unexpected values
- Promise microtask timing issues

**Alternatives considered**:
- Global `afterEach` in `setup.ts`: Rejected — only tests that use fake timers should manage them; global restoration would conflict with tests that intentionally use fake timers across `beforeEach`/test/`afterEach`
- `vi.restoreAllMocks()` instead: Rejected — `restoreAllMocks()` does NOT restore timers; timers require explicit `useRealTimers()` call

## R4: UUID Counter Ordering Dependency

**Context**: `setup.ts` defines `let _counter = 0` for a `crypto.randomUUID` stub. The counter increments globally across the entire test suite, making UUID values ordering-dependent. Test A might get UUID `...000000000001` in one run but `...000000000042` in another, depending on which tests ran first.

**Decision**: Reset `_counter = 0` in a `beforeEach` hook in `setup.ts`.

**Rationale**: The `beforeEach` hook in `setup.ts` runs before every test file (since `setup.ts` is configured as a `setupFiles` entry in `vitest.config.ts`). Resetting the counter ensures each test starts with deterministic UUID generation regardless of execution order.

**Alternatives considered**:
- Use `crypto.randomUUID` polyfill from a library: Rejected — overkill for test-only stub; adds dependency
- Generate truly random UUIDs in tests: Rejected — would make snapshot/assertion testing harder; deterministic stubs are preferred
- Reset per-file instead of per-test: Rejected — `beforeEach` in `setupFiles` gives finer granularity and prevents intra-file leaks

## R5: vi.restoreAllMocks() vs vi.clearAllMocks() vs vi.resetAllMocks()

**Context**: Several test files use `vi.clearAllMocks()` or `vi.resetAllMocks()` in `beforeEach` but lack `vi.restoreAllMocks()` in `afterEach`. These three functions have different behaviors:

- `vi.clearAllMocks()`: Clears call history (`mock.calls`, `mock.results`) but preserves mock implementation
- `vi.resetAllMocks()`: Clears history AND resets implementation to `vi.fn()` (returns `undefined`)
- `vi.restoreAllMocks()`: Restores original implementations — reverses `vi.spyOn()` effects

**Decision**: Add `afterEach(() => { vi.restoreAllMocks(); })` to test files that use `vi.spyOn()` without cleanup: `TopBar.test.tsx`, `AuthGate.test.tsx`, `useAuth.test.tsx`.

**Rationale**: `vi.spyOn()` wraps a real function with a mock. Without `vi.restoreAllMocks()`, the original function remains wrapped in subsequent tests. This is particularly dangerous for:
- `window.history.replaceState` spies (affects navigation in other tests)
- `window.dispatchEvent` spies (affects event handling in other tests)
- `document.addEventListener`/`removeEventListener` spies (affects DOM listeners)

`useAdaptivePolling.test.ts` already correctly uses `afterEach(() => { vi.restoreAllMocks(); })` — it serves as the reference pattern.

**Alternatives considered**:
- Only `vi.clearAllMocks()` in `beforeEach`: Rejected — does not restore original implementations
- `vi.restoreAllMocks()` in `beforeEach` instead of `afterEach`: Rejected — convention is to clean up after yourself, not before; also misses the case where the last test in a file leaks into the next file

## R6: Module-Level Mutable State Inventory

**Context**: The issue specifies 15+ modules with mutable globals. Research confirmed all listed modules plus discovered additional state in `session_store.py:18` (`_encryption_service`) and `workflow_orchestrator/orchestrator.py:70` (`_tracking_table_cache`).

**Decision**: Clear ALL discovered globals in the central fixture, organized by module for maintainability.

**Rationale**: A comprehensive inventory prevents the "whack-a-mole" problem where fixing some leaks reveals others. The fixture should be the single source of truth for global state cleanup.

**Full inventory** (see `data-model.md` for detailed structure):
- **api/chat.py**: 4 dicts
- **pipeline_state_store.py**: 5 BoundedDict/dict + 1 lock + 1 db connection
- **workflow_orchestrator/orchestrator.py**: 1 instance + 1 BoundedDict
- **workflow_orchestrator/config.py**: 1 list + 1 BoundedDict
- **copilot_polling/state.py**: 20+ collections, locks, scalars
- **websocket.py**: 1 lock
- **settings_store.py**: 2 dicts
- **signal_chat.py**: 1 dict
- **github_auth.py**: 1 BoundedDict
- **agent_creator.py**: 1 BoundedDict
- **template_files.py**: 2 optional values
- **app_templates/registry.py**: 1 optional dict
- **done_items_store.py**: 1 optional db connection
- **session_store.py**: 1 optional encryption service
