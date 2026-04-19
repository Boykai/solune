"""Tests for AsyncioExcHandlerStep."""

import asyncio

import pytest

from src.startup.protocol import Step
from src.startup.steps.s02_asyncio_exc import AsyncioExcHandlerStep
from tests.unit.startup.conftest import make_test_ctx


def test_step_conforms_to_protocol():
    step = AsyncioExcHandlerStep()
    assert isinstance(step, Step)
    assert step.name == "asyncio_exception_handler"
    assert step.fatal is False


@pytest.mark.asyncio
async def test_installs_exception_handler():
    step = AsyncioExcHandlerStep()
    ctx = make_test_ctx()
    loop = asyncio.get_running_loop()
    original_handler = loop.get_exception_handler()
    try:
        await step.run(ctx)
        assert loop.get_exception_handler() is not None
    finally:
        loop.set_exception_handler(original_handler)
