"""Step 13: Restore scoped app-pipeline polling tasks after a container restart."""

from __future__ import annotations

from typing import Any

from src.logging_utils import get_logger
from src.startup.protocol import StartupContext

logger = get_logger(__name__)


async def _restore_app_pipeline_polling(settings: Any) -> int:
    """Core logic: restore scoped app-pipeline polling tasks.

    Returns the number of restored polling tasks.
    """
    from src.services.copilot_polling import ensure_app_pipeline_polling
    from src.services.database import get_db
    from src.services.pipeline_state_store import get_all_pipeline_states, set_pipeline_state
    from src.utils import resolve_repository

    default_owner = (settings.default_repo_owner or "").lower()
    default_repo_name = (settings.default_repo_name or "").lower()

    db = get_db()
    token: str | None = None
    try:
        from src.services.session_store import get_session

        cursor = await db.execute(
            "SELECT session_id FROM user_sessions "
            "WHERE selected_project_id IS NOT NULL "
            "ORDER BY updated_at DESC LIMIT 1",
        )
        row = await cursor.fetchone()
        if row:
            session = await get_session(db, row["session_id"])
            if session:
                token = session.access_token
    except Exception:  # noqa: BLE001 — reason: best-effort operation; failure logged, execution continues
        logger.debug("Could not fetch session token for app pipeline polling", exc_info=True)

    if not token:
        token = settings.github_webhook_token
    if not token:
        return 0

    import json

    project_repo_map: dict[str, tuple[str, str]] = {}
    try:
        cursor = await db.execute(
            "SELECT project_id, workflow_config FROM project_settings "
            "WHERE workflow_config IS NOT NULL",
        )
        for ps_row in await cursor.fetchall():
            try:
                wf = json.loads(ps_row["workflow_config"])
                wf_owner = wf.get("repository_owner", "")
                wf_repo = wf.get("repository_name", "")
                if wf_owner and wf_repo:
                    project_repo_map[ps_row["project_id"]] = (wf_owner, wf_repo)
            except (json.JSONDecodeError, TypeError):
                continue
    except Exception:  # noqa: BLE001 — reason: best-effort operation; failure logged, execution continues
        logger.debug("Could not load project repo map for app pipeline polling", exc_info=True)

    restored = 0
    for issue_number, state in get_all_pipeline_states().items():
        pid = getattr(state, "project_id", None)
        if not pid:
            continue
        if getattr(state, "is_complete", False):
            continue

        state_owner = getattr(state, "repository_owner", "") or ""
        state_repo_val = getattr(state, "repository_name", "") or ""
        if state_owner and state_repo_val:
            owner, repo = state_owner, state_repo_val
        else:
            owner, repo = project_repo_map.get(pid, ("", ""))

        if not owner or not repo:
            try:
                owner, repo = await resolve_repository(token, pid)
                logger.info(
                    "Resolved project %s via GitHub API for app-pipeline → %s/%s",
                    pid,
                    owner,
                    repo,
                )
                if not (state_owner and state_repo_val):
                    state.repository_owner = owner
                    state.repository_name = repo
                    await set_pipeline_state(issue_number, state)
            except Exception:  # noqa: BLE001 — reason: best-effort operation; failure logged, execution continues
                logger.warning(
                    "Could not resolve repository for project %s via API, "
                    "falling back to default repo",
                    pid,
                )
                owner, repo = default_owner, default_repo_name

        if not owner or not repo:
            continue

        if owner.lower() == default_owner and repo.lower() == default_repo_name:
            continue

        started = await ensure_app_pipeline_polling(
            access_token=token,
            project_id=pid,
            owner=owner,
            repo=repo,
            parent_issue_number=issue_number,
        )
        if started:
            restored += 1
            logger.info(
                "Restored scoped app-pipeline polling for issue #%d on %s/%s",
                issue_number,
                owner,
                repo,
            )

    if restored:
        logger.info(
            "Restored %d scoped app-pipeline polling task(s) after restart",
            restored,
        )
    return restored


class PipelineRestoreStep:
    name = "app_pipeline_polling_restore"
    fatal = False

    async def run(self, ctx: StartupContext) -> None:
        """Restore scoped app-pipeline polling tasks after a container restart."""
        await _restore_app_pipeline_polling(ctx.settings)
