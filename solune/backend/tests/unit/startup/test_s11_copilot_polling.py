"""Tests for CopilotPollingStep."""

from src.startup.protocol import Step
from src.startup.steps.s11_copilot_polling import CopilotPollingStep


def test_step_conforms_to_protocol():
    step = CopilotPollingStep()
    assert isinstance(step, Step)
    assert step.name == "copilot_polling_autostart"
    assert step.fatal is False
