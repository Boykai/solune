"""Tests for BackgroundLoopsStep."""

import pytest

from src.startup.protocol import Step
from src.startup.steps.s15_background_loops import BackgroundLoopsStep
from tests.unit.startup.conftest import make_test_ctx


def test_step_conforms_to_protocol():
    step = BackgroundLoopsStep()
    assert isinstance(step, Step)
    assert step.name == "background_loops"
    assert step.fatal is True


@pytest.mark.asyncio
async def test_appends_exactly_two_coroutines_to_background():
    step = BackgroundLoopsStep()
    ctx = make_test_ctx()
    await step.run(ctx)
    assert len(ctx.background) == 2
    # Clean up coroutines to avoid warnings
    for coro in ctx.background:
        coro.close()
