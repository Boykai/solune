"""Protocol conformance tests."""

import pytest

from src.startup.protocol import Step, StepOutcome
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
        outcome.name = "other"  # type: ignore[misc]


def test_step_outcome_error_field():
    outcome = StepOutcome(name="test", status="failed", duration_ms=1.0, error="oops")
    assert outcome.error == "oops"
    assert outcome.status == "failed"
