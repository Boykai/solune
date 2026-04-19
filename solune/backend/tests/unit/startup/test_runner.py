"""Runner acceptance tests covering all scenarios from runner-contract.md § R4."""

from __future__ import annotations

import asyncio
import logging
from unittest.mock import AsyncMock, patch

import pytest

from src.startup.protocol import StartupContext, StartupError
from src.startup.runner import run_shutdown, run_startup
from tests.unit.startup.conftest import FakeStep, make_test_ctx

# ── run_startup scenarios ──────────────────────────────────────────────


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


# ── run_shutdown scenarios ─────────────────────────────────────────────


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


# ── Additional run_startup coverage ────────────────────────────────────


@pytest.mark.asyncio
async def test_startup_report_stored_on_success():
    """Successful run stores all outcomes on app.state.startup_report."""
    ctx = make_test_ctx()
    steps = [FakeStep(name="x"), FakeStep(name="y")]
    outcomes = await run_startup(steps, ctx)
    assert ctx.app.state.startup_report is outcomes
    assert len(ctx.app.state.startup_report) == 2


@pytest.mark.asyncio
async def test_fatal_error_has_cause_chain():
    """StartupError.__cause__ is the original exception for diagnostics."""
    ctx = make_test_ctx()
    original = RuntimeError("root-cause")
    steps = [FakeStep(name="f", fatal=True, run_side_effect=original)]
    with pytest.raises(StartupError) as exc_info:
        await run_startup(steps, ctx)
    assert exc_info.value.__cause__ is original


@pytest.mark.asyncio
async def test_request_id_var_reset_after_exception():
    """request_id_var is restored even when a step raises."""
    from src.middleware.request_id import request_id_var

    sentinel = "before-test"
    token = request_id_var.set(sentinel)
    try:
        ctx = make_test_ctx()
        steps = [FakeStep(name="err", fatal=False, run_side_effect=RuntimeError("boom"))]
        await run_startup(steps, ctx)
        # After run_startup, the var should NOT retain "startup-err"
        assert request_id_var.get(sentinel) == sentinel
    finally:
        request_id_var.reset(token)


@pytest.mark.asyncio
async def test_structured_log_extras_on_success(caplog):
    """Log records carry step, status, and duration_ms extra keys."""
    ctx = make_test_ctx()
    steps = [FakeStep(name="extras-check")]
    with caplog.at_level(logging.INFO, logger="src.startup.runner"):
        await run_startup(steps, ctx)
    records = [r for r in caplog.records if getattr(r, "step", None) == "extras-check"]
    assert len(records) == 1
    assert records[0].step == "extras-check"
    assert records[0].status == "ok"
    assert records[0].duration_ms >= 0


@pytest.mark.asyncio
async def test_structured_log_extras_on_non_fatal_failure(caplog):
    """Non-fatal failure produces a warning log with step/status/duration_ms extras."""
    ctx = make_test_ctx()
    steps = [FakeStep(name="warn-step", fatal=False, run_side_effect=ValueError("oops"))]
    with caplog.at_level(logging.WARNING, logger="src.startup.runner"):
        await run_startup(steps, ctx)
    records = [r for r in caplog.records if getattr(r, "step", None) == "warn-step"]
    assert len(records) == 1
    assert records[0].status == "failed"
    assert records[0].duration_ms >= 0


@pytest.mark.asyncio
async def test_structured_log_extras_on_fatal_failure(caplog):
    """Fatal failure produces an error log with step/status/duration_ms extras."""
    ctx = make_test_ctx()
    steps = [FakeStep(name="fatal-log", fatal=True, run_side_effect=RuntimeError("die"))]
    with caplog.at_level(logging.ERROR, logger="src.startup.runner"):
        with pytest.raises(StartupError):
            await run_startup(steps, ctx)
    records = [r for r in caplog.records if getattr(r, "step", None) == "fatal-log"]
    assert len(records) == 1
    assert records[0].status == "failed"
    assert records[0].duration_ms >= 0


@pytest.mark.asyncio
async def test_structured_log_extras_on_skip(caplog):
    """Skipped step produces an info log with status='skipped'."""
    ctx = make_test_ctx()
    steps = [FakeStep(name="skip-log", skip=True)]
    with caplog.at_level(logging.INFO, logger="src.startup.runner"):
        await run_startup(steps, ctx)
    records = [r for r in caplog.records if getattr(r, "step", None) == "skip-log"]
    assert len(records) == 1
    assert records[0].status == "skipped"


@pytest.mark.asyncio
async def test_non_fatal_error_message_captured():
    """Non-fatal failure records the exception string in the outcome."""
    ctx = make_test_ctx()
    steps = [FakeStep(name="nf", fatal=False, run_side_effect=ValueError("detail-msg"))]
    outcomes = await run_startup(steps, ctx)
    assert outcomes[0].error == "detail-msg"


@pytest.mark.asyncio
async def test_skip_if_fatal_raises_propagates():
    """Fatal step whose skip_if raises should raise StartupError."""
    ctx = make_test_ctx()
    steps = [
        FakeStep(name="fatal-skip", fatal=True, skip_raises=RuntimeError("skip-boom")),
    ]
    with pytest.raises(StartupError) as exc_info:
        await run_startup(steps, ctx)
    assert exc_info.value.step_name == "fatal-skip"


@pytest.mark.asyncio
async def test_step_without_skip_if_runs_normally():
    """A step class that has no skip_if method at all runs its body."""

    class MinimalStep:
        name = "minimal"
        fatal = False

        async def run(self, ctx: StartupContext) -> None:
            ctx.app.state.minimal_ran = True

    ctx = make_test_ctx()
    outcomes = await run_startup([MinimalStep()], ctx)
    assert outcomes[0].status == "ok"
    assert ctx.app.state.minimal_ran is True


# ── Additional run_shutdown coverage ───────────────────────────────────


@pytest.mark.asyncio
async def test_shutdown_with_no_hooks():
    """run_shutdown with empty hook list still runs trailing hooks."""
    ctx = make_test_ctx()
    ctx.shutdown_hooks = []
    outcomes = await run_shutdown(ctx)
    trailing_names = {o.name for o in outcomes}
    assert "shutdown-drain" in trailing_names
    assert "shutdown-stop-polling" in trailing_names
    assert "shutdown-close-db" in trailing_names


@pytest.mark.asyncio
async def test_shutdown_trailing_drain_calls_task_registry():
    """Trailing shutdown-drain calls ctx.task_registry.drain()."""
    ctx = make_test_ctx()
    ctx.shutdown_hooks = []
    await run_shutdown(ctx)
    ctx.task_registry.drain.assert_awaited_once()


@pytest.mark.asyncio
async def test_shutdown_trailing_close_db_when_db_is_none():
    """When ctx.db is None, shutdown-close-db still calls close_database()."""
    ctx = make_test_ctx()
    ctx.db = None
    ctx.shutdown_hooks = []
    with patch("src.services.database.close_database", new_callable=AsyncMock) as mock_close:
        outcomes = await run_shutdown(ctx)
    mock_close.assert_awaited_once()
    close_db = [o for o in outcomes if o.name == "shutdown-close-db"]
    assert len(close_db) == 1
    assert close_db[0].status == "ok"


@pytest.mark.asyncio
async def test_shutdown_trailing_close_db_when_db_exists():
    """When ctx.db exists, shutdown-close-db calls close_database()."""
    mock_db = AsyncMock()
    ctx = make_test_ctx(db=mock_db)
    ctx.shutdown_hooks = []
    with patch("src.services.database.close_database", new_callable=AsyncMock) as mock_close:
        outcomes = await run_shutdown(ctx)
    mock_close.assert_awaited_once()
    close_db = [o for o in outcomes if o.name == "shutdown-close-db"]
    assert close_db[0].status == "ok"


@pytest.mark.asyncio
async def test_shutdown_trailing_stop_polling():
    """Trailing shutdown-stop-polling calls stop_polling when running."""
    ctx = make_test_ctx()
    ctx.shutdown_hooks = []
    with (
        patch(
            "src.services.copilot_polling.get_polling_status",
            return_value={"is_running": True},
        ),
        patch("src.services.copilot_polling.stop_polling", new_callable=AsyncMock) as mock_stop,
    ):
        outcomes = await run_shutdown(ctx)
    mock_stop.assert_awaited_once()
    stop_outcome = [o for o in outcomes if o.name == "shutdown-stop-polling"]
    assert stop_outcome[0].status == "ok"


@pytest.mark.asyncio
async def test_shutdown_trailing_stop_polling_skips_when_not_running():
    """Trailing shutdown-stop-polling does not call stop_polling when not running."""
    ctx = make_test_ctx()
    ctx.shutdown_hooks = []
    with (
        patch(
            "src.services.copilot_polling.get_polling_status",
            return_value={"is_running": False},
        ),
        patch("src.services.copilot_polling.stop_polling", new_callable=AsyncMock) as mock_stop,
    ):
        outcomes = await run_shutdown(ctx)
    mock_stop.assert_not_awaited()
    stop_outcome = [o for o in outcomes if o.name == "shutdown-stop-polling"]
    assert stop_outcome[0].status == "ok"
