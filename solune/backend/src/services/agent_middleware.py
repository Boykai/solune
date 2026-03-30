"""Agent middleware components for logging and security.

This module defines reusable middleware designed to be plugged into the
Agent Framework's middleware pipeline and run on each agent invocation
when registered by the agent creation logic.
"""

from __future__ import annotations

import re
import time
from collections.abc import Awaitable, Callable
from agent_framework import AgentContext, AgentMiddleware

from src.logging_utils import get_logger

logger = get_logger(__name__)


# ── Logging middleware ───────────────────────────────────────────────────


class LoggingAgentMiddleware(AgentMiddleware):
    """Records invocation timing and basic metrics for each agent run.

    Logged at INFO level with structured fields for observability.
    """

    async def process(
        self,
        context: AgentContext,
        call_next: Callable[[], Awaitable[None]],
    ) -> None:
        start = time.monotonic()
        try:
            await call_next()
            elapsed_ms = (time.monotonic() - start) * 1000
            logger.info(
                "Agent invocation completed in %.1fms",
                elapsed_ms,
            )
        except Exception:
            elapsed_ms = (time.monotonic() - start) * 1000
            logger.warning(
                "Agent invocation failed after %.1fms",
                elapsed_ms,
            )
            raise


# ── Security middleware ──────────────────────────────────────────────────

# Common prompt injection patterns to detect
_INJECTION_PATTERNS = [
    re.compile(
        r"ignore\s+(all\s+)?(previous|above|prior)\s+(instructions?|prompts?)", re.IGNORECASE
    ),
    re.compile(r"you\s+are\s+now\s+(?:a|an)\s+\w+", re.IGNORECASE),
    re.compile(r"system\s*:\s*", re.IGNORECASE),
    re.compile(r"<\|im_start\|>", re.IGNORECASE),
    re.compile(r"\[INST\]", re.IGNORECASE),
]


class SecurityMiddleware(AgentMiddleware):
    """Detects potential prompt injection attempts in user input.

    - Scans user input for known injection patterns.
    - Logs suspicious content but does not block execution.
    """

    async def process(
        self,
        context: AgentContext,
        call_next: Callable[[], Awaitable[None]],
    ) -> None:
        # Extract user input from context if available
        input_text = " ".join(message.text for message in context.messages)
        if input_text:
            for pattern in _INJECTION_PATTERNS:
                if pattern.search(input_text):
                    logger.warning("Potential prompt injection detected in user input")
                    # Don't block — log and continue (false positives are common)
                    break

        await call_next()
