"""Tests for SignalWsStep."""

from unittest.mock import AsyncMock, patch

import pytest

from src.startup.protocol import Step
from src.startup.steps.s10_signal_ws import SignalWsStep
from tests.unit.startup.conftest import make_test_ctx


def test_step_conforms_to_protocol():
    step = SignalWsStep()
    assert isinstance(step, Step)
    assert step.name == "signal_ws_listener"
    assert step.fatal is False


@pytest.mark.asyncio
async def test_registers_shutdown_hook():
    step = SignalWsStep()
    ctx = make_test_ctx()
    mock_stop = AsyncMock()
    with (
        patch(
            "src.services.signal_bridge.start_signal_ws_listener",
            new_callable=AsyncMock,
        ),
        patch("src.services.signal_bridge.stop_signal_ws_listener", mock_stop),
    ):
        await step.run(ctx)
    assert len(ctx.shutdown_hooks) == 1
    assert ctx.shutdown_hooks[0] is mock_stop
