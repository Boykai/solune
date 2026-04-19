"""Tests for MultiProjectStep."""

from src.startup.protocol import Step
from src.startup.steps.s12_multi_project import MultiProjectStep


def test_step_conforms_to_protocol():
    step = MultiProjectStep()
    assert isinstance(step, Step)
    assert step.name == "multi_project_discovery"
    assert step.fatal is False
