"""Tests for OtelStep."""

from unittest.mock import MagicMock, patch

import pytest

from src.startup.protocol import Step
from src.startup.steps.s08_otel import OtelStep
from tests.unit.startup.conftest import make_test_ctx


def test_step_conforms_to_protocol():
    step = OtelStep()
    assert isinstance(step, Step)
    assert step.name == "otel"
    assert step.fatal is False


def test_skip_if_returns_true_when_otel_disabled():
    step = OtelStep()
    ctx = make_test_ctx()
    ctx.settings.otel_enabled = False
    assert step.skip_if(ctx) is True


def test_skip_if_returns_false_when_otel_enabled():
    step = OtelStep()
    ctx = make_test_ctx()
    ctx.settings.otel_enabled = True
    assert step.skip_if(ctx) is False


@pytest.mark.asyncio
async def test_runs_when_otel_enabled():
    step = OtelStep()
    ctx = make_test_ctx()
    ctx.settings.otel_enabled = True
    ctx.settings.otel_service_name = "test"
    ctx.settings.otel_endpoint = "http://localhost:4317"
    mock_tracer = MagicMock()
    mock_meter = MagicMock()
    with patch("src.services.otel_setup.init_otel", return_value=(mock_tracer, mock_meter)):
        await step.run(ctx)
    assert ctx.app.state.otel_tracer is mock_tracer
    assert ctx.app.state.otel_meter is mock_meter
