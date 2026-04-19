"""Unit tests for GitHubProjectsService._best_effort().

Tests the 5 contract cases from contracts/best-effort-helper-contract.md § B6:
1. Success path: fn returns a value → _best_effort returns that value.
2. Failure path: fn raises ValueError → returns fallback and logs at specified level.
3. Non-catchable: fn raises KeyboardInterrupt → exception propagates.
4. Custom log level: log_level=logging.WARNING → log message emitted at WARNING.
5. Kwargs forwarding: fn receives the correct *args and **kwargs.
"""

import logging

import pytest

from src.services.github_projects.service import GitHubProjectsService


class TestBestEffort:
    """Tests for _best_effort() best-effort wrapper contract."""

    @pytest.fixture
    def service(self) -> GitHubProjectsService:
        return GitHubProjectsService()

    # ------------------------------------------------------------------
    # B6-1: Success path
    # ------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_success_returns_fn_value(self, service: GitHubProjectsService):
        """fn returns a value → _best_effort returns that value, no fallback used."""

        async def fn() -> str:
            return "ok"

        result = await service._best_effort(fn, fallback="default", context="test success")
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_success_no_log_emitted(
        self, service: GitHubProjectsService, caplog: pytest.LogCaptureFixture
    ):
        """Success path should NOT emit any log message."""

        async def fn() -> int:
            return 42

        with caplog.at_level(logging.DEBUG):
            result = await service._best_effort(fn, fallback=0, context="test no log")

        assert result == 42
        assert "test no log" not in caplog.text

    # ------------------------------------------------------------------
    # B6-2: Failure path (ValueError)
    # ------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_failure_returns_fallback(self, service: GitHubProjectsService):
        """fn raises ValueError → _best_effort returns the fallback value."""

        async def fn() -> list[str]:
            raise ValueError("boom")

        result = await service._best_effort(fn, fallback=[], context="test failure")
        assert result == []

    @pytest.mark.asyncio
    async def test_failure_logs_at_default_error_level(
        self, service: GitHubProjectsService, caplog: pytest.LogCaptureFixture
    ):
        """fn raises → log message emitted at ERROR level (the default)."""

        async def fn() -> str:
            raise ValueError("boom")

        with caplog.at_level(logging.DEBUG):
            await service._best_effort(fn, fallback="safe", context="test error log")

        error_records = [r for r in caplog.records if r.levelno == logging.ERROR]
        assert any("test error log" in r.message and "boom" in r.message for r in error_records)

    @pytest.mark.asyncio
    async def test_failure_log_format(
        self, service: GitHubProjectsService, caplog: pytest.LogCaptureFixture
    ):
        """Log message format should be '{context}: {exc}' per contract B2."""

        async def fn() -> None:
            raise RuntimeError("oops")

        with caplog.at_level(logging.DEBUG):
            await service._best_effort(fn, fallback=None, context="fetch PR #42")

        error_records = [r for r in caplog.records if r.levelno == logging.ERROR]
        assert any("fetch PR #42: oops" in r.message for r in error_records)

    # ------------------------------------------------------------------
    # B6-3: Non-catchable exceptions propagate
    # ------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_keyboard_interrupt_propagates(self, service: GitHubProjectsService):
        """fn raises KeyboardInterrupt → exception propagates to caller."""

        async def fn() -> str:
            raise KeyboardInterrupt

        with pytest.raises(KeyboardInterrupt):
            await service._best_effort(fn, fallback="safe", context="test propagate")

    @pytest.mark.asyncio
    async def test_system_exit_propagates(self, service: GitHubProjectsService):
        """fn raises SystemExit → exception propagates to caller."""

        async def fn() -> str:
            raise SystemExit(1)

        with pytest.raises(SystemExit):
            await service._best_effort(fn, fallback="safe", context="test exit propagate")

    # ------------------------------------------------------------------
    # B6-4: Custom log level
    # ------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_custom_log_level_warning(
        self, service: GitHubProjectsService, caplog: pytest.LogCaptureFixture
    ):
        """log_level=logging.WARNING → log message emitted at WARNING, not ERROR."""

        async def fn() -> str:
            raise ValueError("non-critical")

        with caplog.at_level(logging.DEBUG):
            result = await service._best_effort(
                fn,
                fallback="safe",
                context="optional fetch",
                log_level=logging.WARNING,
            )

        assert result == "safe"
        warning_records = [r for r in caplog.records if r.levelno == logging.WARNING]
        error_records = [r for r in caplog.records if r.levelno == logging.ERROR]
        assert any("optional fetch" in r.message for r in warning_records)
        assert not any("optional fetch" in r.message for r in error_records)

    @pytest.mark.asyncio
    async def test_custom_log_level_debug(
        self, service: GitHubProjectsService, caplog: pytest.LogCaptureFixture
    ):
        """log_level=logging.DEBUG → log message emitted at DEBUG."""

        async def fn() -> str:
            raise OSError("disk full")

        with caplog.at_level(logging.DEBUG):
            result = await service._best_effort(
                fn,
                fallback="",
                context="nice-to-have",
                log_level=logging.DEBUG,
            )

        assert result == ""
        debug_records = [r for r in caplog.records if r.levelno == logging.DEBUG]
        assert any("nice-to-have" in r.message for r in debug_records)

    # ------------------------------------------------------------------
    # B6-5: Args and kwargs forwarding
    # ------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_args_forwarded(self, service: GitHubProjectsService):
        """Positional args are forwarded to fn."""
        received: list[object] = []

        async def fn(a: int, b: str) -> str:
            received.extend([a, b])
            return f"{a}-{b}"

        result = await service._best_effort(fn, 1, "two", fallback="", context="test args")
        assert result == "1-two"
        assert received == [1, "two"]

    @pytest.mark.asyncio
    async def test_kwargs_forwarded(self, service: GitHubProjectsService):
        """Keyword args are forwarded to fn."""
        received: dict[str, object] = {}

        async def fn(*, x: int, y: str) -> str:
            received.update(x=x, y=y)
            return f"{x}:{y}"

        result = await service._best_effort(fn, fallback="", context="test kwargs", x=10, y="hello")
        assert result == "10:hello"
        assert received == {"x": 10, "y": "hello"}

    @pytest.mark.asyncio
    async def test_mixed_args_and_kwargs(self, service: GitHubProjectsService):
        """Both positional and keyword args are correctly forwarded."""
        received_args: tuple[object, ...] = ()
        received_kwargs: dict[str, object] = {}

        async def fn(a: int, b: str, *, flag: bool = False) -> dict[str, object]:
            nonlocal received_args, received_kwargs
            received_args = (a, b)
            received_kwargs = {"flag": flag}
            return {"a": a, "b": b, "flag": flag}

        result = await service._best_effort(
            fn, 5, "test", fallback={}, context="mixed args", flag=True
        )
        assert result == {"a": 5, "b": "test", "flag": True}
        assert received_args == (5, "test")
        assert received_kwargs == {"flag": True}

    # ------------------------------------------------------------------
    # Additional edge cases
    # ------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_fallback_none(self, service: GitHubProjectsService):
        """fallback=None should be returned on failure."""

        async def fn() -> dict | None:
            raise RuntimeError("fail")

        result = await service._best_effort(fn, fallback=None, context="nullable")
        assert result is None

    @pytest.mark.asyncio
    async def test_fallback_empty_list(self, service: GitHubProjectsService):
        """fallback=[] should return an empty list on failure."""

        async def fn() -> list[dict]:
            raise RuntimeError("fail")

        result = await service._best_effort(fn, fallback=[], context="list fallback")
        assert result == []

    @pytest.mark.asyncio
    async def test_exception_does_not_propagate(self, service: GitHubProjectsService):
        """Exception subclasses should NOT propagate to caller."""

        async def fn() -> str:
            raise ConnectionError("network down")

        # Should NOT raise — fallback should be returned
        result = await service._best_effort(fn, fallback="offline", context="network check")
        assert result == "offline"
