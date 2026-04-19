from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.startup.steps import s15_background_loops as loops


@pytest.mark.asyncio
async def test_polling_watchdog_attempts_restart_after_detecting_stopped_loop(monkeypatch) -> None:
    sleep_calls: list[float] = []
    restart = AsyncMock(return_value=True)

    async def fake_sleep(delay: float) -> None:
        sleep_calls.append(delay)
        if len(sleep_calls) > 1:
            raise asyncio.CancelledError()

    # Mock a DB that returns one session row for the inline restart logic
    mock_cursor = AsyncMock()
    mock_cursor.fetchall = AsyncMock(
        return_value=[{"session_id": "sid1", "selected_project_id": "PVT_1"}],
    )
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_cursor)

    mock_session = MagicMock(access_token="tok", selected_project_id="PVT_1")

    monkeypatch.setattr(loops.asyncio, "sleep", fake_sleep)
    monkeypatch.setattr(
        "src.services.copilot_polling.get_polling_status",
        lambda: {"is_running": False, "errors_count": 1, "last_error": "boom"},
    )
    monkeypatch.setattr("src.services.copilot_polling.ensure_polling_started", restart)
    monkeypatch.setattr("src.services.database.get_db", lambda: mock_db)
    monkeypatch.setattr(
        "src.services.session_store.get_session", AsyncMock(return_value=mock_session)
    )
    monkeypatch.setattr("src.utils.resolve_repository", AsyncMock(return_value=("owner", "repo")))
    monkeypatch.setattr("src.services.copilot_polling.state.register_project", MagicMock())
    monkeypatch.setattr("src.services.pipeline_state_store.get_all_pipeline_states", lambda: {})
    monkeypatch.setattr("src.services.copilot_polling.get_monitored_projects", lambda: [])
    monkeypatch.setattr("src.services.copilot_polling.unregister_project", MagicMock())

    await loops._polling_watchdog_loop()

    assert sleep_calls[0] == 30
    restart.assert_awaited_once()


@pytest.mark.asyncio
async def test_session_cleanup_loop_uses_exponential_backoff_after_failures(monkeypatch) -> None:
    sleep_calls: list[int] = []
    purge = AsyncMock(side_effect=[RuntimeError("db down"), 0])

    async def fake_sleep(delay: int) -> None:
        sleep_calls.append(delay)
        if len(sleep_calls) > 2:
            raise asyncio.CancelledError()

    monkeypatch.setattr(loops.asyncio, "sleep", fake_sleep)
    monkeypatch.setattr(
        "src.config.get_settings", lambda: SimpleNamespace(session_cleanup_interval=5)
    )
    monkeypatch.setattr("src.services.database.get_db", lambda: object())
    monkeypatch.setattr("src.services.session_store.purge_expired_sessions", purge)

    await loops._session_cleanup_loop()

    assert sleep_calls[:2] == [5, 10]
