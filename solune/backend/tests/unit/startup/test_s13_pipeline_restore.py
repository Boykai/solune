"""Tests for PipelineRestoreStep."""

from unittest.mock import AsyncMock, patch

import pytest

from src.startup.protocol import Step
from src.startup.steps.s13_pipeline_restore import PipelineRestoreStep
from tests.unit.startup.conftest import make_test_ctx


def test_step_conforms_to_protocol():
    step = PipelineRestoreStep()
    assert isinstance(step, Step)
    assert step.name == "app_pipeline_polling_restore"
    assert step.fatal is False


@pytest.mark.asyncio
async def test_run_delegates_to_restore():
    """run() delegates to _restore_app_pipeline_polling with ctx.settings."""
    step = PipelineRestoreStep()
    ctx = make_test_ctx()
    with patch(
        "src.startup.steps.s13_pipeline_restore._restore_app_pipeline_polling",
        new_callable=AsyncMock,
        return_value=0,
    ) as mock_restore:
        await step.run(ctx)
    mock_restore.assert_awaited_once_with(ctx.settings)


@pytest.mark.asyncio
async def test_run_propagates_exception():
    """Since fatal=False the runner swallows it, but run() itself propagates."""
    step = PipelineRestoreStep()
    ctx = make_test_ctx()
    with patch(
        "src.startup.steps.s13_pipeline_restore._restore_app_pipeline_polling",
        new_callable=AsyncMock,
        side_effect=RuntimeError("restore-fail"),
    ):
        with pytest.raises(RuntimeError, match="restore-fail"):
            await step.run(ctx)
