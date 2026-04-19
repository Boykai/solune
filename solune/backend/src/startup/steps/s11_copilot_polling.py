"""Startup step: auto-resume Copilot polling.

The caller (startup runner) sets ``request_id_var`` to
``startup-{step.name}`` so correlated logging works without the step
needing its own request-ID dance.
"""
# pyright: basic
# reason: Extracted from main.py; imports private helpers.

from __future__ import annotations

import dataclasses

from src.logging_utils import get_logger
from src.startup.protocol import StartupContext

logger = get_logger(__name__)


@dataclasses.dataclass(frozen=True)
class CopilotPollingAutostartStep:
    """Auto-resume Copilot polling so agent pipelines survive restarts."""

    name: str = "copilot_polling_autostart"
    fatal: bool = False

    async def run(self, ctx: StartupContext) -> None:
        from src.main import _auto_start_copilot_polling

        await _auto_start_copilot_polling()
