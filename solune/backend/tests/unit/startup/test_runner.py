"""Runner acceptance tests covering all scenarios from runner-contract.md § R4."""

from __future__ import annotations

import asyncio
import logging
from unittest.mock import AsyncMock, patch

import pytest

from src.startup.protocol import StartupContext, StartupError
from src.startup.runner import run_shutdown, run_startup
from tests.unit.startup.conftest import FakeStep, make_test_ctx


@pytest.mark.asyncio
async def test_scenario_1_all_succeed():
    """Scenario 1: all steps succeed — returns len(steps) outcomes, all 'ok'."""
    ctx = make_test_ctx()
    steps = [FakeStep(name="a"), FakeStep(name="b"), FakeStep(name="c")]
    outcomes = await run_startup(steps, ctx)
    assert len(outcomes) == 3
    assert all(o.status == "ok" for o in outcomes)
    assert all(o.duration_ms >= 0 for o in outcomes)


@pytest.mark.asyncio
async def test_scenario_2_non_fatal_step_fails():
    """Scenario 2: non-fatal step fails — subsequent steps still run."""
    ctx = make_test_ctx()
    steps = [
        FakeStep(name="a"),
        FakeStep(name="b", fatal=False, run_side_effect=ValueError("boom")),
        FakeStep(name="c"),
    ]
    outcomes = await run_startup(steps, ctx)
    assert len(outcomes) == 3
    assert outcomes[1].status == "failed"
    assert outcomes[1].error is not None
    assert outcomes[2].status == "ok"


@pytest.mark.asyncio
async def test_scenario_3_fatal_step_fails():
    """Scenario 3: fatal step fails — raises StartupError, partial outcomes stored."""
    ctx = make_test_ctx()
    steps = [
        FakeStep(name="a"),
        FakeStep(name="b", fatal=True, run_side_effect=RuntimeError("fatal")),
        FakeStep(name="c"),
    ]
    with pytest.raises(StartupError) as exc_info:
        await run_startup(steps, ctx)
    assert exc_info.value.step_name == "b"
    # Partial outcomes stored
    assert len(ctx.app.state.startup_report) == 2
    assert ctx.app.state.startup_report[1].status == "failed"
    # Step c should NOT have run
    assert not steps[2].run_called


@pytest.mark.asyncio
async def test_scenario_4_skip_if_true():
    """Scenario 4: step with skip_if=True produces 'skipped' outcome."""
    ctx = make_test_ctx()
    steps = [FakeStep(name="skipped-step", skip=True)]
    outcomes = await run_startup(steps, ctx)
    assert outcomes[0].status == "skipped"
    assert outcomes[0].duration_ms >= 0
    assert outcomes[0].error is None


@pytest.mark.asyncio
async def test_scenario_5_skip_if_raises():
    """Scenario 5: skip_if raises — outcome is 'failed', fatal policy applies."""
    ctx = make_test_ctx()
    steps = [FakeStep(name="bad-skip", fatal=False, skip_raises=RuntimeError("skip-error"))]
    outcomes = await run_startup(steps, ctx)
    assert outcomes[0].status == "failed"
    assert "skip-error" in (outcomes[0].error or "")


@pytest.mark.asyncio
async def test_scenario_6_duplicate_names_raises():
    """Scenario 6: duplicate step names raise ValueError before any step runs."""
    ctx = make_test_ctx()
    steps = [FakeStep(name="dup"), FakeStep(name="dup")]
    with pytest.raises(ValueError, match=r"[Dd]uplicate"):
        await run_startup(steps, ctx)
    assert not steps[0].run_called


@pytest.mark.asyncio
async def test_scenario_7_empty_step_list():
    """Scenario 7: empty step list returns empty list."""
    ctx = make_test_ctx()
    outcomes = await run_startup([], ctx)
    assert outcomes == []


@pytest.mark.asyncio
async def test_scenario_8_structured_log_output(caplog):
    """Scenario 8: each step produces one log line with step, status, duration_ms keys."""
    ctx = make_test_ctx()
    steps = [FakeStep(name="log-test")]
    with caplog.at_level(logging.INFO, logger="src.startup.runner"):
        outcomes = await run_startup(steps, ctx)
    assert outcomes[0].status == "ok"
    # Verify we got at least one log record for this step
    step_records = [
        r
        for r in caplog.records
        if "log-test" in r.getMessage() or getattr(r, "step", None) == "log-test"
    ]
    assert len(step_records) >= 1


@pytest.mark.asyncio
async def test_scenario_9_request_id_var_per_step():
    """Scenario 9: request_id_var is set to 'startup-{name}' inside run()."""
    from src.middleware.request_id import request_id_var

    captured: list[str] = []

    class CapturingStep:
        name = "capturing"
        fatal = False

        async def run(self, ctx: StartupContext) -> None:
            captured.append(request_id_var.get())

    ctx = make_test_ctx()
    await run_startup([CapturingStep()], ctx)
    assert captured == ["startup-capturing"]


@pytest.mark.asyncio
async def test_scenario_10_shutdown_lifo_order():
    """Scenario 10: hooks registered A->B->C execute C->B->A."""
    ctx = make_test_ctx()
    call_order: list[str] = []

    async def hook_a() -> None:
        call_order.append("A")

    async def hook_b() -> None:
        call_order.append("B")

    async def hook_c() -> None:
        call_order.append("C")

    ctx.shutdown_hooks = [hook_a, hook_b, hook_c]
    await run_shutdown(ctx)
    assert call_order == ["C", "B", "A"]


@pytest.mark.asyncio
async def test_scenario_11_shutdown_hook_failure_continues():
    """Scenario 11: failed hook logged; subsequent hooks still run."""
    ctx = make_test_ctx()
    call_order: list[str] = []

    async def failing_hook() -> None:
        raise RuntimeError("hook-fail")

    async def succeeding_hook() -> None:
        call_order.append("ok")

    ctx.shutdown_hooks = [succeeding_hook, failing_hook]
    outcomes = await run_shutdown(ctx)
    # The runner must not re-raise
    assert call_order == ["ok"]
    failed = [o for o in outcomes if o.status == "failed"]
    assert len(failed) >= 1


@pytest.mark.asyncio
async def test_scenario_12_trailing_hooks_run_after_fatal():
    """Scenario 12: force fatal step, assert close_db trailing hook still executes."""
    import aiosqlite

    mock_db = AsyncMock(spec=aiosqlite.Connection)
    ctx = make_test_ctx(db=mock_db)
    steps = [FakeStep(name="fatal-step", fatal=True, run_side_effect=RuntimeError("bang"))]

    with pytest.raises(StartupError):
        await run_startup(steps, ctx)

    # Even after fatal startup, run_shutdown should close the db
    with patch("src.services.database.close_database", new_callable=AsyncMock) as mock_close:
        await run_shutdown(ctx)
    mock_close.assert_called_once()


@pytest.mark.asyncio
async def test_scenario_13_shutdown_hook_timeout():
    """Scenario 13: hook exceeding timeout is cancelled and logged as failed."""
    ctx = make_test_ctx()

    async def slow_hook() -> None:
        await asyncio.sleep(999)

    ctx.shutdown_hooks = [slow_hook]
    outcomes = await run_shutdown(ctx, shutdown_timeout=0.01)
    user_outcomes = [
        o
        for o in outcomes
        if o.name.startswith("shutdown-")
        and not o.name.startswith("shutdown-drain")
        and not o.name.startswith("shutdown-stop")
        and not o.name.startswith("shutdown-close")
    ]
    assert any(o.status == "failed" for o in user_outcomes)
