"""Tests for AlertDispatcherStep."""

from unittest.mock import MagicMock, patch

import pytest

from src.startup.protocol import Step
from src.startup.steps.s07_alert_dispatcher import AlertDispatcherStep
from tests.unit.startup.conftest import make_test_ctx


def test_step_conforms_to_protocol():
    step = AlertDispatcherStep()
    assert isinstance(step, Step)
    assert step.name == "alert_dispatcher"
    assert step.fatal is False


@pytest.mark.asyncio
async def test_creates_and_assigns_alert_dispatcher():
    step = AlertDispatcherStep()
    ctx = make_test_ctx()
    mock_dispatcher = MagicMock()

    with (
        patch(
            "src.services.alert_dispatcher.AlertDispatcher", return_value=mock_dispatcher
        ) as mock_cls,
        patch("src.services.alert_dispatcher.set_dispatcher") as mock_set,
    ):
        await step.run(ctx)

    mock_cls.assert_called_once()
    mock_set.assert_called_once_with(mock_dispatcher)
    assert ctx.app.state.alert_dispatcher is mock_dispatcher
