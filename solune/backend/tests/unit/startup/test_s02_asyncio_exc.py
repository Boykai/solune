"""Tests for AsyncioExcHandlerStep."""

import asyncio
import logging

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


@pytest.mark.asyncio
async def test_handler_logs_exception(caplog):
    """Installed handler logs exceptions via logger.error."""
    step = AsyncioExcHandlerStep()
    ctx = make_test_ctx()
    loop = asyncio.get_running_loop()
    original_handler = loop.get_exception_handler()
    try:
        await step.run(ctx)
        handler = loop.get_exception_handler()
        assert handler is not None
        # Simulate what asyncio does when it catches an unhandled exception
        exc = RuntimeError("test-async-error")
        with caplog.at_level(logging.ERROR):
            handler(loop, {"message": "Task exception", "exception": exc})
        assert any("test-async-error" in r.getMessage() for r in caplog.records)
    finally:
        loop.set_exception_handler(original_handler)


@pytest.mark.asyncio
async def test_handler_logs_without_exception(caplog):
    """Handler works when no exception is in the context dict."""
    step = AsyncioExcHandlerStep()
    ctx = make_test_ctx()
    loop = asyncio.get_running_loop()
    original_handler = loop.get_exception_handler()
    try:
        await step.run(ctx)
        handler = loop.get_exception_handler()
        assert handler is not None
        with caplog.at_level(logging.ERROR):
            handler(loop, {"message": "Something happened"})
        assert any("Something happened" in r.getMessage() for r in caplog.records)
    finally:
        loop.set_exception_handler(original_handler)
