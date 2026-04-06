from __future__ import annotations

import asyncio

import pytest

from src.services.copilot_polling import state as polling_state_module


@pytest.mark.asyncio
async def test_forced_interleaving_should_preserve_latest_error(
    isolated_polling_globals,
    fresh_polling_state,
) -> None:
    fresh_polling_state.last_error = "initial"

    gate = asyncio.Event()

    async def first_writer() -> None:
        await gate.wait()
        async with polling_state_module._polling_state_lock:
            observed = fresh_polling_state.last_error
            polling_state_module._polling_state.last_error = f"{observed}-stale"

    async def second_writer() -> None:
        await gate.wait()
        async with polling_state_module._polling_state_lock:
            polling_state_module._polling_state.last_error = "newest"

    first_task = asyncio.create_task(first_writer())
    second_task = asyncio.create_task(second_writer())

    await asyncio.sleep(0)
    gate.set()

    await asyncio.gather(first_task, second_task)

    assert polling_state_module._polling_state.last_error == "newest"
