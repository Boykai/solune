"""Tests for DoneItemsCacheStep."""

from unittest.mock import AsyncMock, patch

import pytest

from src.startup.protocol import Step
from src.startup.steps.s05_done_items_cache import DoneItemsCacheStep
from tests.unit.startup.conftest import make_test_ctx


def test_step_conforms_to_protocol():
    step = DoneItemsCacheStep()
    assert isinstance(step, Step)
    assert step.name == "done_items_cache"
    assert step.fatal is True


@pytest.mark.asyncio
async def test_calls_init_done_items_store():
    step = DoneItemsCacheStep()
    mock_db = AsyncMock()
    ctx = make_test_ctx(db=mock_db)
    with patch(
        "src.services.done_items_store.init_done_items_store",
        new_callable=AsyncMock,
    ) as mock_init:
        await step.run(ctx)
    mock_init.assert_called_once_with(mock_db)
