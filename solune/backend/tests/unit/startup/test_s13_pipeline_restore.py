"""Tests for PipelineRestoreStep."""

from src.startup.protocol import Step
from src.startup.steps.s13_pipeline_restore import PipelineRestoreStep


def test_step_conforms_to_protocol():
    step = PipelineRestoreStep()
    assert isinstance(step, Step)
    assert step.name == "app_pipeline_polling_restore"
    assert step.fatal is False
