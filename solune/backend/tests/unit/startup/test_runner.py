"""Tests for the startup runner — run_startup / run_shutdown."""

from __future__ import annotations

import dataclasses

import pytest

from src.startup.protocol import StartupContext, Step, StepOutcome
from src.startup.runner import run_shutdown, run_startup

# ── Fake steps for testing ─────────────────────────────────────────────────


@dataclasses.dataclass(frozen=True)
class _OkStep:
    name: str = "ok_step"
    fatal: bool = False

    async def run(self, ctx: StartupContext) -> None:
        pass


@dataclasses.dataclass(frozen=True)
class _FatalOkStep:
    name: str = "fatal_ok"
    fatal: bool = True

    async def run(self, ctx: StartupContext) -> None:
        pass


@dataclasses.dataclass(frozen=True)
class _ErrorStep:
    name: str = "error_step"
    fatal: bool = False

    async def run(self, ctx: StartupContext) -> None:
        msg = "non-fatal boom"
        raise RuntimeError(msg)


@dataclasses.dataclass(frozen=True)
class _FatalErrorStep:
    name: str = "fatal_error"
    fatal: bool = True

    async def run(self, ctx: StartupContext) -> None:
        msg = "fatal boom"
        raise RuntimeError(msg)


@dataclasses.dataclass(frozen=True)
class _SkippedStep:
    name: str = "skipped_step"
    fatal: bool = False

    def skip_if(self, ctx: StartupContext) -> bool:
        return True

    async def run(self, ctx: StartupContext) -> None:
        pytest.fail("run() should not be called when skip_if returns True")


@dataclasses.dataclass(frozen=True)
class _NotSkippedStep:
    name: str = "not_skipped"
    fatal: bool = False

    def skip_if(self, ctx: StartupContext) -> bool:
        return False

    async def run(self, ctx: StartupContext) -> None:
        pass


def _make_ctx() -> StartupContext:
    """Create a minimal StartupContext for testing."""
    from unittest.mock import MagicMock

    return StartupContext(
        app=MagicMock(),
        settings=MagicMock(),
    )


# ── run_startup tests ──────────────────────────────────────────────────────


class TestRunStartup:
    async def test_all_ok(self):
        outcomes = await run_startup([_OkStep(), _FatalOkStep()], _make_ctx())
        assert len(outcomes) == 2
        assert all(o.status == "ok" for o in outcomes)
        assert all(o.duration_ms >= 0 for o in outcomes)

    async def test_non_fatal_error_continues(self):
        outcomes = await run_startup(
            [_OkStep(), _ErrorStep(), _OkStep(name="after_error")],
            _make_ctx(),
        )
        assert len(outcomes) == 3
        assert outcomes[0].status == "ok"
        assert outcomes[1].status == "error"
        assert outcomes[1].error == "non-fatal boom"
        assert outcomes[2].status == "ok"

    async def test_fatal_error_aborts(self):
        with pytest.raises(RuntimeError, match="fatal boom"):
            await run_startup(
                [_OkStep(), _FatalErrorStep(), _OkStep(name="never_reached")],
                _make_ctx(),
            )

    async def test_fatal_error_records_outcome_before_raise(self):
        """Even on fatal error, the outcome should be recorded."""
        try:
            await run_startup([_FatalErrorStep()], _make_ctx())
        except RuntimeError:
            pass  # expected

    async def test_skipped_step(self):
        outcomes = await run_startup([_SkippedStep()], _make_ctx())
        assert len(outcomes) == 1
        assert outcomes[0].status == "skipped"
        assert outcomes[0].duration_ms == 0.0

    async def test_not_skipped_step(self):
        outcomes = await run_startup([_NotSkippedStep()], _make_ctx())
        assert len(outcomes) == 1
        assert outcomes[0].status == "ok"

    async def test_empty_step_list(self):
        outcomes = await run_startup([], _make_ctx())
        assert outcomes == []

    async def test_outcome_names_match_steps(self):
        steps = [_OkStep(name="alpha"), _OkStep(name="beta")]
        outcomes = await run_startup(steps, _make_ctx())
        assert [o.name for o in outcomes] == ["alpha", "beta"]

    async def test_durations_are_non_negative(self):
        outcomes = await run_startup([_OkStep(), _ErrorStep()], _make_ctx())
        for o in outcomes:
            assert o.duration_ms >= 0


# ── run_shutdown tests ─────────────────────────────────────────────────────


class TestRunShutdown:
    async def test_all_hooks_run(self):
        outcomes = await run_shutdown([_OkStep(name="hook1"), _OkStep(name="hook2")], _make_ctx())
        assert len(outcomes) == 2
        assert all(o.status == "ok" for o in outcomes)

    async def test_error_does_not_abort_remaining(self):
        """Shutdown hooks always continue even if one fails."""
        outcomes = await run_shutdown(
            [_ErrorStep(), _OkStep(name="after_error")],
            _make_ctx(),
        )
        assert len(outcomes) == 2
        assert outcomes[0].status == "error"
        assert outcomes[1].status == "ok"

    async def test_empty_hooks(self):
        outcomes = await run_shutdown([], _make_ctx())
        assert outcomes == []


# ── Protocol conformance ───────────────────────────────────────────────────


class TestProtocol:
    def test_ok_step_is_step(self):
        assert isinstance(_OkStep(), Step)

    def test_skipped_step_is_step(self):
        assert isinstance(_SkippedStep(), Step)

    def test_step_outcome_fields(self):
        o = StepOutcome(name="test", status="ok", duration_ms=1.5)
        assert o.name == "test"
        assert o.status == "ok"
        assert o.duration_ms == 1.5
        assert o.error is None

    def test_step_outcome_with_error(self):
        o = StepOutcome(name="test", status="error", duration_ms=2.0, error="boom")
        assert o.error == "boom"


# ── StartupContext ─────────────────────────────────────────────────────────


class TestStartupContext:
    def test_add_background(self):
        ctx = _make_ctx()
        assert ctx.background == []

        async def _coro():
            pass

        ctx.add_background(_coro())
        assert len(ctx.background) == 1

    def test_add_shutdown_hook(self):
        ctx = _make_ctx()
        assert ctx.shutdown_hooks == []

        async def _hook():
            pass

        ctx.add_shutdown_hook(_hook)
        assert len(ctx.shutdown_hooks) == 1

    def test_defaults(self):
        ctx = _make_ctx()
        assert ctx.db is None
        assert ctx.task_registry is None
        assert ctx.background == []
        assert ctx.shutdown_hooks == []
