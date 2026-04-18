# Resettable State Contract

**Feature**: 002-dual-init-singleton
**Owners**: `solune/backend/src/services/resettable_state.py` (new module), `solune/backend/tests/conftest.py`
**Consumers**: Every module with mutable state that must be reset between tests.

This contract specifies the API, behaviour, and invariants of the resettable state registry.

---

## S1 — Public API

The module exposes exactly two public functions:

```python
def register_resettable(name: str, reset_fn: Callable[[], None]) -> None:
    """Register a piece of mutable state for automatic test cleanup.

    Parameters
    ----------
    name : str
        Human-readable identifier for logging (e.g., "copilot_polling._devops_tracking").
    reset_fn : Callable[[], None]
        Zero-argument callable that resets the state to its initial value.
        Called by ``reset_all()`` during test teardown.
    """
    ...

def reset_all() -> None:
    """Reset all registered state entries.

    Iterates the registry in registration order. If a reset function raises,
    the exception is logged and iteration continues (FR-006).
    """
    ...
```

---

## S2 — Registration patterns

### Pattern A — Dictionary or collection (`.clear()`)

```python
# In src/services/copilot_polling/state.py
from src.services.resettable_state import register_resettable

_devops_tracking: BoundedDict[str, DevOpsEntry] = BoundedDict(max_size=1000)

register_resettable(
    "copilot_polling.state._devops_tracking",
    _devops_tracking.clear,
)
```

### Pattern B — Nullable singleton (`= None`)

```python
# In src/services/template_files.py
from src.services.resettable_state import register_resettable
import src.services.template_files as _self

_cached_files: list[TemplateFile] | None = None

def _reset_cached_files() -> None:
    _self._cached_files = None

register_resettable("template_files._cached_files", _reset_cached_files)
```

### Pattern C — Event-loop-bound lock (replace with fresh instance)

```python
# In src/services/copilot_polling/state.py
import asyncio
from src.services.resettable_state import register_resettable
import src.services.copilot_polling.state as _self

_polling_state_lock: asyncio.Lock = asyncio.Lock()

def _reset_polling_state_lock() -> None:
    _self._polling_state_lock = asyncio.Lock()

register_resettable(
    "copilot_polling.state._polling_state_lock",
    _reset_polling_state_lock,
)
```

---

## S3 — Error handling (FR-006)

`reset_all()` MUST NOT short-circuit on the first error. Each `reset_fn()` is called inside a `try/except` block:

```python
def reset_all() -> None:
    for name, reset_fn in _registry:
        try:
            reset_fn()
        except Exception:
            logger.exception("Failed to reset state: %s", name)
```

This ensures that a failure in one module's cleanup does not prevent cleanup of subsequent modules.

---

## S4 — Autouse fixture integration

The existing `_clear_test_caches()` fixture in `conftest.py` is reduced to:

```python
@pytest.fixture(autouse=True)
def _clear_test_caches():
    """Reset all registered mutable state between tests."""
    from src.services.resettable_state import reset_all

    reset_all()
    yield
    reset_all()
```

The `reset_all()` call before `yield` ensures clean state entering the test. The call after `yield` ensures clean state for the next test, even if the test body mutates state without cleaning up.

---

## S5 — `dependency_overrides` cleanup (FR-008)

`app.dependency_overrides` is NOT part of the resettable registry because it is scoped to the `app` instance created in the `client` fixture. Each test gets a fresh `app` from `create_app()`, so overrides do not bleed between tests.

If a test creates its own `app` instance outside the `client` fixture, it is responsible for clearing `dependency_overrides` in its own teardown.

---

## S6 — Forbidden patterns

- **Registering production-critical state**: The registry is a test utility. Production code MUST NOT call `reset_all()`. The registry has no runtime overhead in production (it is a static list that is never iterated outside tests).
- **Registering state that requires async cleanup**: `reset_fn()` is synchronous. State that requires `await` for cleanup (e.g., closing database connections) must be handled in the lifespan `finally` block, not in the registry.
- **Relying on registration order**: `reset_all()` iterates in registration order (module load order), but tests MUST NOT depend on this ordering. Each reset function must be independently correct.

---

## S7 — Contract acceptance

1. `grep -rn 'register_resettable' solune/backend/src/` returns entries for every variable currently cleared in `_clear_test_caches()`.
2. `_clear_test_caches()` fixture body contains only `reset_all()` calls and `yield`.
3. `uv run pytest` passes with zero test-isolation failures.
4. Injecting a deliberate exception in one `reset_fn` does not prevent other entries from being reset (verified by a dedicated test).
