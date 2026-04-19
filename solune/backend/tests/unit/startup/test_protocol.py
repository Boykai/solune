"""Protocol conformance tests."""

import pytest

from src.startup.protocol import StartupContext, Step, StepOutcome
from tests.unit.startup.conftest import FakeStep


def test_fake_step_is_instance_of_step_protocol():
    step = FakeStep(name="test", fatal=True)
    assert isinstance(step, Step)


def test_step_with_missing_name_fails_isinstance():
    class BadStep:
        fatal = False

        async def run(self, ctx):
            pass

    assert not isinstance(BadStep(), Step)


def test_step_with_missing_fatal_fails_isinstance():
    class BadStep:
        name = "bad"

        async def run(self, ctx):
            pass

    assert not isinstance(BadStep(), Step)


def test_step_without_skip_if_is_valid():
    """skip_if is optional — steps without it still satisfy the Protocol."""
    step = FakeStep(name="no-skip", fatal=False)
    assert isinstance(step, Step)
    assert not hasattr(FakeStep, "skip_if") or callable(getattr(step, "skip_if", None))


def test_step_outcome_frozen():
    outcome = StepOutcome(name="test", status="ok", duration_ms=1.0)
    with pytest.raises((AttributeError, TypeError)):
        outcome.name = "other"  # pyright: ignore[reportAttributeAccessIssue] — reason: intentionally testing frozen dataclass immutability


def test_step_outcome_error_field():
    outcome = StepOutcome(name="test", status="failed", duration_ms=1.0, error="oops")
    assert outcome.error == "oops"
    assert outcome.status == "failed"


def test_step_outcome_default_error_is_none():
    outcome = StepOutcome(name="test", status="ok", duration_ms=0.5)
    assert outcome.error is None


def test_startup_context_defaults():
    """StartupContext has sensible defaults for background and shutdown_hooks."""
    from unittest.mock import MagicMock

    ctx = StartupContext(
        app=MagicMock(),
        settings=MagicMock(),
        task_registry=MagicMock(),
    )
    assert ctx.db is None
    assert ctx.background == []
    assert ctx.shutdown_hooks == []


def test_startup_steps_list_all_unique_names():
    """STARTUP_STEPS has no duplicate step names."""
    from src.startup.steps import STARTUP_STEPS

    names = [s.name for s in STARTUP_STEPS]
    assert len(names) == len(set(names)), f"Duplicate names: {names}"


def test_startup_steps_list_all_conform_to_protocol():
    """Every entry in STARTUP_STEPS satisfies the Step protocol."""
    from src.startup.steps import STARTUP_STEPS

    for step in STARTUP_STEPS:
        assert isinstance(step, Step), f"{step!r} does not satisfy Step protocol"


def test_startup_steps_count():
    """STARTUP_STEPS contains all 15 expected steps."""
    from src.startup.steps import STARTUP_STEPS

    assert len(STARTUP_STEPS) == 15
