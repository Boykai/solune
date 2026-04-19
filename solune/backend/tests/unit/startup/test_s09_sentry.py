"""Tests for SentryStep."""

from unittest.mock import patch

import pytest

from src.startup.protocol import Step
from src.startup.steps.s09_sentry import SentryStep
from tests.unit.startup.conftest import make_test_ctx


def test_step_conforms_to_protocol():
    step = SentryStep()
    assert isinstance(step, Step)
    assert step.name == "sentry"
    assert step.fatal is False


def test_skip_if_when_no_dsn():
    step = SentryStep()
    ctx = make_test_ctx()
    ctx.settings.sentry_dsn = ""
    assert step.skip_if(ctx) is True


def test_skip_if_when_dsn_set():
    step = SentryStep()
    ctx = make_test_ctx()
    ctx.settings.sentry_dsn = "https://key@sentry.io/123"
    assert step.skip_if(ctx) is False


@pytest.mark.asyncio
async def test_runs_when_dsn_set():
    step = SentryStep()
    ctx = make_test_ctx()
    ctx.settings.sentry_dsn = "https://key@sentry.io/123"
    with (
        patch("sentry_sdk.init") as mock_init,
        patch("sentry_sdk.integrations.fastapi.FastApiIntegration"),
    ):
        await step.run(ctx)
    mock_init.assert_called_once()
