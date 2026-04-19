from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.startup.steps import s15_background_loops as loops


@pytest.mark.asyncio
async def test_polling_watchdog_attempts_restart_after_detecting_stopped_loop(monkeypatch) -> None:
    sleep_calls: list[float] = []
    restart = AsyncMock()
    register_projects = AsyncMock(return_value=0)

    async def fake_sleep(delay: float) -> None:
        sleep_calls.append(delay)
        if len(sleep_calls) > 1:
            raise asyncio.CancelledError()

    monkeypatch.setattr(loops.asyncio, "sleep", fake_sleep)
    monkeypatch.setattr(
        "src.config.get_settings",
        lambda: SimpleNamespace(
            github_webhook_token="tok",
            default_repo_owner="owner",
            default_repo_name="repo",
        ),
    )
    monkeypatch.setattr(
        "src.services.copilot_polling.get_polling_status",
        MagicMock(
            side_effect=[
                {"is_running": False, "errors_count": 1, "last_error": "boom"},
                {"is_running": True, "errors_count": 1, "last_error": "boom"},
            ]
        ),
    )
    monkeypatch.setattr(
        "src.startup.steps.s11_copilot_polling._auto_start_copilot_polling",
        restart,
    )
    monkeypatch.setattr(
        "src.startup.steps.s12_multi_project._discover_and_register_active_projects",
        register_projects,
    )
    monkeypatch.setattr("src.services.copilot_polling.get_monitored_projects", lambda: [])
    monkeypatch.setattr("src.services.copilot_polling.unregister_project", MagicMock())

    await loops._polling_watchdog_loop()

    assert sleep_calls[0] == 30
    restart.assert_awaited_once()
    register_projects.assert_awaited_once()


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
