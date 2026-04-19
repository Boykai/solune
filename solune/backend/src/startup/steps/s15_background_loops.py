"""Startup step: enqueue background loops into the TaskGroup.

The session cleanup loop and polling watchdog loop are long-running
background tasks started inside the same TaskGroup as before — no
behaviour change to task lifetime management.

The loop functions themselves remain in ``src.main`` for backward
compatibility; this step simply enqueues them.
"""
# pyright: basic
# reason: Extracted from main.py; imports private helpers.

from __future__ import annotations

import dataclasses

from src.startup.protocol import StartupContext


@dataclasses.dataclass(frozen=True)
class BackgroundLoopsStep:
    """Enqueue session-cleanup and polling-watchdog loops into ctx.background."""

    name: str = "background_loops"
    fatal: bool = True

    async def run(self, ctx: StartupContext) -> None:
        from src.main import _polling_watchdog_loop, _session_cleanup_loop

        ctx.add_background(_session_cleanup_loop())
        ctx.add_background(_polling_watchdog_loop())
