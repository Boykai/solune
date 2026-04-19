"""Tests for LoggingStep."""

from unittest.mock import patch

import pytest

from src.startup.protocol import Step
from src.startup.steps.s01_logging import LoggingStep
from tests.unit.startup.conftest import make_test_ctx


def test_logging_step_conforms_to_protocol():
    step = LoggingStep()
    assert isinstance(step, Step)
    assert step.name == "logging"
    assert step.fatal is True


@pytest.mark.asyncio
async def test_logging_step_calls_setup_logging():
    step = LoggingStep()
    ctx = make_test_ctx()
    ctx.settings.debug = False
    with patch("src.config.setup_logging") as mock_setup:
        await step.run(ctx)
    mock_setup.assert_called_once_with(False, structured=True)


@pytest.mark.asyncio
async def test_logging_step_debug_mode_disables_structured():
    """When debug=True, structured=False (human-readable logs)."""
    step = LoggingStep()
    ctx = make_test_ctx()
    ctx.settings.debug = True
    with patch("src.config.setup_logging") as mock_setup:
        await step.run(ctx)
    mock_setup.assert_called_once_with(True, structured=False)
