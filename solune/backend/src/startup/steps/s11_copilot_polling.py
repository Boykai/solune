"""Step 11: Auto-resume Copilot polling after restart."""

from __future__ import annotations

from typing import Any

from src.logging_utils import get_logger
from src.startup.protocol import StartupContext

logger = get_logger(__name__)


async def _auto_start_copilot_polling(settings: Any) -> None:
    """Core logic: resume Copilot polling after restart using persisted sessions.

    Note: request_id_var is set by the startup runner when called as a step,
    or by the caller (e.g. watchdog loop) when called independently.
    """
    from src.services.copilot_polling import ensure_polling_started, get_polling_status
    from src.services.copilot_polling.state import register_project
    from src.services.database import get_db
    from src.services.pipeline_state_store import get_all_pipeline_states
    from src.services.session_store import get_session
    from src.utils import resolve_repository

    polling_status = get_polling_status()
    if polling_status["is_running"]:
        return

    db = get_db()

    # Collect project_ids that have active (non-complete) pipeline states.
    active_project_ids: set[str] = set()
    for state in get_all_pipeline_states().values():
        pid = getattr(state, "project_id", None)
        if pid and not getattr(state, "is_complete", False):
            active_project_ids.add(pid)

    # ── Strategy 1: Use persisted user sessions ──
    cursor = await db.execute(
        """
        SELECT session_id, selected_project_id FROM user_sessions
        WHERE selected_project_id IS NOT NULL
        ORDER BY updated_at DESC
        """,
    )
    rows = await cursor.fetchall()

    first_started = False
    for row in rows:
        session = await get_session(db, row["session_id"])
        if not session or not session.selected_project_id:
            continue

        if active_project_ids and session.selected_project_id not in active_project_ids:
            continue

        try:
            owner, repo = await resolve_repository(
                session.access_token, session.selected_project_id
            )
        except Exception as e:
            logger.warning(
                "Could not resolve repo for project %s — skipping: %s",
                session.selected_project_id,
                e,
            )
            continue

        # Register this project for multi-project monitoring
        register_project(session.selected_project_id, owner, repo, session.access_token)

        if not first_started:
            started = await ensure_polling_started(
                access_token=session.access_token,
                project_id=session.selected_project_id,
                owner=owner,
                repo=repo,
                caller="lifespan_auto_start",
            )
            if started:
                logger.info(
                    "Auto-started Copilot polling for project %s (%s/%s)",
                    session.selected_project_id,
                    owner,
                    repo,
                )
                first_started = True

    if first_started:
        return

    # ── Strategy 2: Webhook token + project_settings fallback ──
    token = settings.github_webhook_token
    owner_name = settings.default_repo_owner
    repo_name = settings.default_repo_name

    if not token or not owner_name or not repo_name:
        logger.info(
            "No active session and no GITHUB_WEBHOOK_TOKEN/DEFAULT_REPOSITORY "
            "configured — polling not auto-started"
        )
        return

    project_id: str | None = settings.default_project_id

    if not project_id:
        import json

        cursor2 = await db.execute(
            """
            SELECT project_id, workflow_config FROM project_settings
            WHERE workflow_config IS NOT NULL
            ORDER BY updated_at DESC
            LIMIT 50
            """,
        )
        owner_only_fallback: str | None = None
        for ps_row in await cursor2.fetchall():
            try:
                wf = json.loads(ps_row["workflow_config"])
                wf_repo = wf.get("repository_name", "")
                wf_owner = wf.get("repository_owner", "")

                if wf_repo == repo_name and (not wf_owner or wf_owner == owner_name):
                    project_id = ps_row["project_id"]
                    break

                if not wf_repo and wf_owner == owner_name and not owner_only_fallback:
                    owner_only_fallback = ps_row["project_id"]
            except (json.JSONDecodeError, TypeError):
                continue

        if not project_id:
            project_id = owner_only_fallback

    if not project_id:
        logger.info(
            "No project_settings entry found for %s/%s — polling not auto-started",
            owner_name,
            repo_name,
        )
        return

    started = await ensure_polling_started(
        access_token=token,
        project_id=project_id,
        owner=owner_name,
        repo=repo_name,
        caller="webhook_token_fallback",
    )
    if started:
        logger.info(
            "Auto-started Copilot polling via webhook token for project %s (%s/%s)",
            project_id,
            owner_name,
            repo_name,
        )


async def auto_start_copilot_polling(settings: Any) -> None:
    """Public wrapper for restart/resume logic shared with the watchdog loop."""
    await _auto_start_copilot_polling(settings)


class CopilotPollingStep:
    name = "copilot_polling_autostart"
    fatal = False

    async def run(self, ctx: StartupContext) -> None:
        """Resume Copilot polling after a restart using persisted sessions."""
        await _auto_start_copilot_polling(ctx.settings)
