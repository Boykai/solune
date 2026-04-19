"""Tests for MultiProjectStep."""

from unittest.mock import AsyncMock, patch

import pytest

from src.startup.protocol import Step
from src.startup.steps.s12_multi_project import MultiProjectStep
from tests.unit.startup.conftest import make_test_ctx


def test_step_conforms_to_protocol():
    step = MultiProjectStep()
    assert isinstance(step, Step)
    assert step.name == "multi_project_discovery"
    assert step.fatal is False


@pytest.mark.asyncio
async def test_run_delegates_to_discover():
    """run() delegates to _discover_and_register_active_projects with ctx.settings."""
    step = MultiProjectStep()
    ctx = make_test_ctx()
    with patch(
        "src.startup.steps.s12_multi_project._discover_and_register_active_projects",
        new_callable=AsyncMock,
        return_value=0,
    ) as mock_discover:
        await step.run(ctx)
    mock_discover.assert_awaited_once_with(ctx.settings)


@pytest.mark.asyncio
async def test_run_propagates_exception():
    """Since fatal=False the runner swallows it, but run() itself propagates."""
    step = MultiProjectStep()
    ctx = make_test_ctx()
    with patch(
        "src.startup.steps.s12_multi_project._discover_and_register_active_projects",
        new_callable=AsyncMock,
        side_effect=RuntimeError("discover-fail"),
    ):
        with pytest.raises(RuntimeError, match="discover-fail"):
            await step.run(ctx)
