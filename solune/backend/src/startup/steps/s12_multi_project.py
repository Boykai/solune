"""Step 12: Discover and register active projects for multi-project monitoring."""

from __future__ import annotations

from typing import Any

from src.logging_utils import get_logger
from src.startup.protocol import StartupContext

logger = get_logger(__name__)


async def _discover_and_register_active_projects(settings: Any) -> int:
    """Core logic: discover projects with active pipeline states and register them.

    Returns the number of newly registered projects.
    """
    from src.services.copilot_polling import register_project
    from src.services.database import get_db
    from src.services.pipeline_state_store import get_all_pipeline_states, set_pipeline_state
    from src.utils import resolve_repository

    active_project_ids: set[str] = set()
    state_repo_map: dict[str, tuple[str, str]] = {}
    for state in get_all_pipeline_states().values():
        pid = getattr(state, "project_id", None)
        if pid:
            active_project_ids.add(pid)
            owner = getattr(state, "repository_owner", "") or ""
            repo = getattr(state, "repository_name", "") or ""
            if owner and repo and pid not in state_repo_map:
                state_repo_map[pid] = (owner, repo)

    if not active_project_ids:
        return 0

    db = get_db()
    import json

    fallback_token = settings.github_webhook_token or ""

    session_token: str | None = None
    try:
        cursor = await db.execute(
            "SELECT access_token FROM user_sessions "
            "WHERE selected_project_id IS NOT NULL "
            "ORDER BY updated_at DESC LIMIT 1",
        )
        row = await cursor.fetchone()
        if row:
            session_token = row["access_token"]
    except Exception:  # noqa: BLE001 — reason: best-effort operation; failure logged, execution continues
        logger.debug("Could not fetch recent session token for polling", exc_info=True)

    token = session_token or fallback_token
    if not token:
        return 0

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
        logger.debug("Could not load project repo map from project_settings", exc_info=True)

    default_owner = settings.default_repo_owner or ""
    default_repo_name = settings.default_repo_name or ""

    registered_count = 0
    for pid in active_project_ids:
        owner, repo = state_repo_map.get(pid, project_repo_map.get(pid, ("", "")))

        if not owner or not repo:
            try:
                owner, repo = await resolve_repository(token, pid)
                logger.info(
                    "Resolved project %s via GitHub API → %s/%s",
                    pid,
                    owner,
                    repo,
                )
                for state in get_all_pipeline_states().values():
                    if getattr(state, "project_id", None) == pid:
                        if not (
                            getattr(state, "repository_owner", "")
                            and getattr(state, "repository_name", "")
                        ):
                            state.repository_owner = owner
                            state.repository_name = repo
                            await set_pipeline_state(state.issue_number, state)
            except Exception:  # noqa: BLE001 — reason: best-effort operation; failure logged, execution continues
                logger.warning(
                    "Could not resolve repository for project %s via API, "
                    "falling back to default repo",
                    pid,
                )
                owner, repo = default_owner, default_repo_name

        if not owner or not repo:
            continue
        if register_project(pid, owner, repo, token):
            registered_count += 1

    if registered_count:
        logger.info(
            "Multi-project discovery: registered %d project(s) with active pipelines",
            registered_count,
        )
    return registered_count


async def discover_and_register_active_projects(settings: Any) -> int:
    """Public wrapper for project registration logic shared with the watchdog loop."""
    return await _discover_and_register_active_projects(settings)


class MultiProjectStep:
    name = "multi_project_discovery"
    fatal = False

    async def run(self, ctx: StartupContext) -> None:
        """Discover all projects with active pipeline states and register them."""
        await _discover_and_register_active_projects(ctx.settings)
