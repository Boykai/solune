"""Bootstrap helpers — startup/shutdown functions extracted from main.py.

These functions encapsulate the background-task and service-discovery logic
that was previously inline in ``main.lifespan``.  The lifespan delegates
to these helpers so they can be tested and evolved independently.

Phase 1 of the modularity refactoring extracts them here; the originals
in ``main.py`` are preserved as thin wrappers that delegate to these
functions.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.logging_utils import get_logger

if TYPE_CHECKING:
    import aiosqlite

logger = get_logger(__name__)


async def auto_start_copilot_polling() -> bool:
    """Resume Copilot polling after a restart using a persisted session.

    Delegates to the original ``_auto_start_copilot_polling`` in main.py
    so the bootstrap module can be used as the canonical entry-point while
    main.py still contains the full implementation.
    """
    from src.main import _auto_start_copilot_polling

    return await _auto_start_copilot_polling()


async def discover_and_register_active_projects() -> int:
    """Discover projects with active pipelines and register for monitoring.

    Delegates to ``_discover_and_register_active_projects`` in main.py.
    """
    from src.main import _discover_and_register_active_projects

    return await _discover_and_register_active_projects()


async def restore_app_pipeline_polling() -> int:
    """Restore scoped app-pipeline polling tasks after a container restart.

    Delegates to ``_restore_app_pipeline_polling`` in main.py.
    """
    from src.main import _restore_app_pipeline_polling

    return await _restore_app_pipeline_polling()


async def startup_agent_mcp_sync(db: aiosqlite.Connection) -> None:
    """Run agent MCP sync on startup to reconcile drift.

    Delegates to ``_startup_agent_mcp_sync`` in main.py.
    """
    from src.main import _startup_agent_mcp_sync

    await _startup_agent_mcp_sync(db)


async def polling_watchdog_loop() -> None:
    """Watchdog task: restart the Copilot polling loop if it stops.

    Delegates to ``_polling_watchdog_loop`` in main.py.
    """
    from src.main import _polling_watchdog_loop

    return await _polling_watchdog_loop()


async def session_cleanup_loop() -> None:
    """Periodic background task to purge expired sessions.

    Delegates to ``_session_cleanup_loop`` in main.py.
    """
    from src.main import _session_cleanup_loop

    return await _session_cleanup_loop()
