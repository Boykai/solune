"""Tests for PipelineCacheStep."""

from unittest.mock import AsyncMock, patch

import pytest

from src.startup.protocol import Step
from src.startup.steps.s04_pipeline_cache import PipelineCacheStep
from tests.unit.startup.conftest import make_test_ctx


def test_step_conforms_to_protocol():
    step = PipelineCacheStep()
    assert isinstance(step, Step)
    assert step.name == "pipeline_state_cache"
    assert step.fatal is True


@pytest.mark.asyncio
async def test_calls_init_pipeline_state_store():
    step = PipelineCacheStep()
    mock_db = AsyncMock()
    ctx = make_test_ctx(db=mock_db)
    with patch(
        "src.services.pipeline_state_store.init_pipeline_state_store",
        new_callable=AsyncMock,
    ) as mock_init:
        await step.run(ctx)
    mock_init.assert_called_once_with(mock_db)
