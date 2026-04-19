"""Startup step: restore scoped app-pipeline polling tasks."""
# pyright: basic
# reason: Extracted from main.py; imports private helpers.

from __future__ import annotations

import dataclasses

from src.logging_utils import get_logger
from src.startup.protocol import StartupContext

logger = get_logger(__name__)


@dataclasses.dataclass(frozen=True)
class AppPipelinePollingRestoreStep:
    """Restore scoped app-pipeline polling for new-repo/external-repo apps."""

    name: str = "app_pipeline_polling_restore"
    fatal: bool = False

    async def run(self, ctx: StartupContext) -> None:
        from src.main import _restore_app_pipeline_polling

        await _restore_app_pipeline_polling()
