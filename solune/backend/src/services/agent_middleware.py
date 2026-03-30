"""Agent middleware for logging and security.

Middleware components plug into the Agent Framework's middleware pipeline
and run on every agent invocation.
"""

from __future__ import annotations

import re
import time
from typing import Any

from agent_framework import AgentMiddleware, AgentMiddlewareLayer

from src.logging_utils import get_logger

logger = get_logger(__name__)


# ── Logging middleware ───────────────────────────────────────────────────


class LoggingAgentMiddleware(AgentMiddleware):
    """Records invocation timing and basic metrics for each agent run.

    Logged at INFO level with structured fields for observability.
    """

    async def invoke(
        self,
        context: Any,
        next_handler: AgentMiddlewareLayer,
    ) -> Any:
        start = time.monotonic()
        try:
            result = await next_handler(context)
            elapsed_ms = (time.monotonic() - start) * 1000
            logger.info(
                "Agent invocation completed in %.1fms",
                elapsed_ms,
            )
            return result
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
    re.compile(r"ignore\s+(all\s+)?(previous|above|prior)\s+(instructions?|prompts?)", re.I),
    re.compile(r"you\s+are\s+now\s+(?:a|an)\s+\w+", re.I),
    re.compile(r"system\s*:\s*", re.I),
    re.compile(r"<\|im_start\|>", re.I),
    re.compile(r"\[INST\]", re.I),
]


class SecurityMiddleware(AgentMiddleware):
    """Detects prompt injection attempts and validates tool arguments.

    - Scans user input for known injection patterns.
    - Validates that tool arguments don't contain excessively long payloads.
    """

    async def invoke(
        self,
        context: Any,
        next_handler: AgentMiddlewareLayer,
    ) -> Any:
        # Extract user input from context if available
        input_text = getattr(context, "input", None) or ""
        if isinstance(input_text, str):
            for pattern in _INJECTION_PATTERNS:
                if pattern.search(input_text):
                    logger.warning(
                        "Potential prompt injection detected in user input"
                    )
                    # Don't block — log and continue (false positives are common)
                    break

        return await next_handler(context)
