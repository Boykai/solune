"""Tests for STARTUP_STEPS list invariants and protocol conformance."""

from __future__ import annotations

from src.startup.protocol import Step
from src.startup.steps import STARTUP_STEPS


class TestStartupStepsList:
    def test_all_steps_implement_protocol(self):
        for step in STARTUP_STEPS:
            assert isinstance(step, Step), f"{step!r} does not implement Step protocol"

    def test_step_names_are_unique(self):
        names = [s.name for s in STARTUP_STEPS]
        assert len(names) == len(set(names)), f"Duplicate step names: {names}"

    def test_step_names_are_non_empty(self):
        for step in STARTUP_STEPS:
            assert step.name, f"Step {step!r} has empty name"

    def test_step_count(self):
        """Inventory should have 15 steps as specified in the issue."""
        assert len(STARTUP_STEPS) == 15

    def test_fatal_steps_come_before_non_fatal_polling_steps(self):
        """Database and cache steps (fatal) should come before polling steps (non-fatal)."""
        step_names = [s.name for s in STARTUP_STEPS]
        assert step_names.index("database") < step_names.index("copilot_polling_autostart")
        assert step_names.index("pipeline_state_cache") < step_names.index(
            "multi_project_discovery"
        )

    def test_background_loops_is_last(self):
        """Background loops must be the last step (it enqueues coros for the TaskGroup)."""
        assert STARTUP_STEPS[-1].name == "background_loops"

    def test_expected_step_order(self):
        names = [s.name for s in STARTUP_STEPS]
        expected = [
            "logging",
            "asyncio_exception_handler",
            "database",
            "pipeline_state_cache",
            "done_items_cache",
            "singleton_services",
            "alert_dispatcher",
            "otel",
            "sentry",
            "signal_ws_listener",
            "copilot_polling_autostart",
            "multi_project_discovery",
            "app_pipeline_polling_restore",
            "agent_mcp_sync",
            "background_loops",
        ]
        assert names == expected

    def test_fatal_flags(self):
        """Verify fatal flags match the spec."""
        fatal_map = {s.name: s.fatal for s in STARTUP_STEPS}
        assert fatal_map["logging"] is True
        assert fatal_map["asyncio_exception_handler"] is False
        assert fatal_map["database"] is True
        assert fatal_map["pipeline_state_cache"] is True
        assert fatal_map["done_items_cache"] is True
        assert fatal_map["singleton_services"] is True
        assert fatal_map["alert_dispatcher"] is False
        assert fatal_map["otel"] is False
        assert fatal_map["sentry"] is False
        assert fatal_map["signal_ws_listener"] is False
        assert fatal_map["copilot_polling_autostart"] is False
        assert fatal_map["multi_project_discovery"] is False
        assert fatal_map["app_pipeline_polling_restore"] is False
        assert fatal_map["agent_mcp_sync"] is False
        assert fatal_map["background_loops"] is True

    def test_skip_if_on_otel(self):
        """OtelStep should have skip_if that checks otel_enabled."""
        from unittest.mock import MagicMock

        from src.startup.protocol import StartupContext

        otel_step = next(s for s in STARTUP_STEPS if s.name == "otel")
        skip_fn = getattr(otel_step, "skip_if", None)
        assert callable(skip_fn)

        ctx_disabled = StartupContext(app=MagicMock(), settings=MagicMock(otel_enabled=False))
        assert skip_fn(ctx_disabled) is True

        ctx_enabled = StartupContext(app=MagicMock(), settings=MagicMock(otel_enabled=True))
        assert skip_fn(ctx_enabled) is False

    def test_skip_if_on_sentry(self):
        """SentryStep should have skip_if that checks sentry_dsn."""
        from unittest.mock import MagicMock

        from src.startup.protocol import StartupContext

        sentry_step = next(s for s in STARTUP_STEPS if s.name == "sentry")
        skip_fn = getattr(sentry_step, "skip_if", None)
        assert callable(skip_fn)

        ctx_no_dsn = StartupContext(app=MagicMock(), settings=MagicMock(sentry_dsn=""))
        assert skip_fn(ctx_no_dsn) is True

        ctx_with_dsn = StartupContext(
            app=MagicMock(), settings=MagicMock(sentry_dsn="https://sentry.io/123")
        )
        assert skip_fn(ctx_with_dsn) is False
