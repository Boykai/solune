"""Registry for mutable state that must be reset between tests.

Production code registers state entries at module-load time via
:func:`register_resettable`.  The pytest autouse fixture in ``conftest.py``
calls :func:`reset_all` before and after every test to prevent cross-test
state leaks.

This module is a test-time utility — :func:`reset_all` is never called in
production code paths and the registry has zero runtime overhead.
"""

from __future__ import annotations

from collections.abc import Callable

from src.logging_utils import get_logger

logger = get_logger(__name__)

_registry: list[tuple[str, Callable[[], None]]] = []


def register_resettable(name: str, reset_fn: Callable[[], None]) -> None:
    """Register a piece of mutable state for automatic test cleanup.

    Parameters
    ----------
    name:
        Human-readable identifier for logging
        (e.g. ``"copilot_polling.state._devops_tracking"``).
    reset_fn:
        Zero-argument callable that resets the state to its initial value.
        Called by :func:`reset_all` during test teardown.
    """
    _registry.append((name, reset_fn))


def reset_all() -> None:
    """Reset all registered state entries.

    Iterates the registry in registration order.  If a reset function
    raises, the exception is logged and iteration continues (FR-006).
    """
    for name, reset_fn in _registry:
        try:
            reset_fn()
        except Exception:
            logger.exception("Failed to reset state: %s", name)
