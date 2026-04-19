"""Tests for BackgroundLoopsStep."""

import inspect

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
    # Verify they are actual coroutines (not functions)
    for coro in ctx.background:
        assert inspect.iscoroutine(coro)
    # Clean up coroutines to avoid warnings
    for coro in ctx.background:
        coro.close()


@pytest.mark.asyncio
async def test_background_coroutines_are_session_cleanup_and_watchdog():
    """Verify the two enqueued coroutines correspond to the expected loops."""
    step = BackgroundLoopsStep()
    ctx = make_test_ctx()
    await step.run(ctx)
    names = [coro.__qualname__ for coro in ctx.background]
    assert "_session_cleanup_loop" in names[0]
    assert "_polling_watchdog_loop" in names[1]
    for coro in ctx.background:
        coro.close()


@pytest.mark.asyncio
async def test_multiple_runs_accumulate_coroutines():
    """Running the step twice appends 4 total coroutines (not idempotent)."""
    step = BackgroundLoopsStep()
    ctx = make_test_ctx()
    await step.run(ctx)
    await step.run(ctx)
    assert len(ctx.background) == 4
    for coro in ctx.background:
        coro.close()
