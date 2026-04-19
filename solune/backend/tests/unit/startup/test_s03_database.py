"""Tests for DatabaseStep."""

from unittest.mock import AsyncMock, patch

import pytest

from src.startup.protocol import Step
from src.startup.steps.s03_database import DatabaseStep
from tests.unit.startup.conftest import make_test_ctx


def test_step_conforms_to_protocol():
    step = DatabaseStep()
    assert isinstance(step, Step)
    assert step.name == "database"
    assert step.fatal is True


@pytest.mark.asyncio
async def test_sets_ctx_db_and_app_state_db():
    step = DatabaseStep()
    ctx = make_test_ctx()
    mock_db = AsyncMock()
    with (
        patch("src.services.database.init_database", return_value=mock_db) as mock_init,
        patch("src.services.database.seed_global_settings", new_callable=AsyncMock) as mock_seed,
    ):
        await step.run(ctx)
    mock_init.assert_called_once()
    mock_seed.assert_called_once_with(mock_db)
    assert ctx.db is mock_db
    assert ctx.app.state.db is mock_db
