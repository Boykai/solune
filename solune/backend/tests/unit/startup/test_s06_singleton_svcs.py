"""Tests for SingletonServicesStep."""

from unittest.mock import MagicMock, patch

import pytest

from src.startup.protocol import Step
from src.startup.steps.s06_singleton_svcs import SingletonServicesStep
from tests.unit.startup.conftest import make_test_ctx


def test_step_conforms_to_protocol():
    step = SingletonServicesStep()
    assert isinstance(step, Step)
    assert step.name == "singleton_services"
    assert step.fatal is True


@pytest.mark.asyncio
async def test_sets_singleton_services_on_app_state():
    step = SingletonServicesStep()
    ctx = make_test_ctx()
    mock_github = MagicMock()
    mock_ws = MagicMock()
    with (
        patch("src.services.github_projects.github_projects_service", mock_github),
        patch("src.services.websocket.connection_manager", mock_ws),
    ):
        await step.run(ctx)
    assert ctx.app.state.github_service is mock_github
    assert ctx.app.state.connection_manager is mock_ws
