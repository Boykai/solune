"""Tests for CopilotPollingStep."""

from unittest.mock import AsyncMock, patch

import pytest

from src.startup.protocol import Step
from src.startup.steps.s11_copilot_polling import CopilotPollingStep
from tests.unit.startup.conftest import make_test_ctx


def test_step_conforms_to_protocol():
    step = CopilotPollingStep()
    assert isinstance(step, Step)
    assert step.name == "copilot_polling_autostart"
    assert step.fatal is False


@pytest.mark.asyncio
async def test_run_delegates_to_auto_start():
    """run() delegates to _auto_start_copilot_polling with ctx.settings."""
    step = CopilotPollingStep()
    ctx = make_test_ctx()
    with patch(
        "src.startup.steps.s11_copilot_polling._auto_start_copilot_polling",
        new_callable=AsyncMock,
    ) as mock_auto:
        await step.run(ctx)
    mock_auto.assert_awaited_once_with(ctx.settings)


@pytest.mark.asyncio
async def test_run_propagates_exception():
    """Since fatal=False the runner swallows it, but run() itself propagates."""
    step = CopilotPollingStep()
    ctx = make_test_ctx()
    with patch(
        "src.startup.steps.s11_copilot_polling._auto_start_copilot_polling",
        new_callable=AsyncMock,
        side_effect=RuntimeError("polling-fail"),
    ):
        with pytest.raises(RuntimeError, match="polling-fail"):
            await step.run(ctx)
