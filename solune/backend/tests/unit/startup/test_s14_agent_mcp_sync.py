"""Tests for AgentMcpSyncStep."""

from unittest.mock import AsyncMock

import pytest

from src.startup.protocol import Step
from src.startup.steps.s14_agent_mcp_sync import AgentMcpSyncStep
from tests.unit.startup.conftest import make_test_ctx


def test_step_conforms_to_protocol():
    step = AgentMcpSyncStep()
    assert isinstance(step, Step)
    assert step.name == "agent_mcp_sync"
    assert step.fatal is False


@pytest.mark.asyncio
async def test_fires_via_task_registry():
    step = AgentMcpSyncStep()
    mock_db = AsyncMock()
    ctx = make_test_ctx(db=mock_db)
    await step.run(ctx)
    ctx.task_registry.create_task.assert_called_once()
    call_kwargs = ctx.task_registry.create_task.call_args
    assert call_kwargs[1].get("name") == "startup-mcp-sync"
