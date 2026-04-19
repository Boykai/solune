"""Startup package — declarative, individually-testable startup steps.

Re-exports the public API: ``run_startup``, ``run_shutdown``,
``StartupContext``, ``Step``, ``StepOutcome``, and ``STARTUP_STEPS``.
"""

from src.startup.protocol import StartupContext, Step, StepOutcome
from src.startup.runner import run_shutdown, run_startup
from src.startup.steps import STARTUP_STEPS

__all__ = [
    "STARTUP_STEPS",
    "StartupContext",
    "Step",
    "StepOutcome",
    "run_shutdown",
    "run_startup",
]
