"""Projects API endpoints."""

import asyncio
from collections.abc import AsyncGenerator
from datetime import timedelta
from typing import Annotated, Any, cast

from fastapi import APIRouter, Depends, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from githubkit.exception import PrimaryRateLimitExceeded, RequestFailed

from src.api.auth import get_current_session, get_session_dep
from src.constants import SESSION_COOKIE_NAME
from src.dependencies import verify_project_access
from src.exceptions import GitHubAPIError, NotFoundError, RateLimitError
from src.logging_utils import get_logger
from src.models.project import GitHubProject, ProjectListResponse
from src.models.task import TaskListResponse
from src.models.user import UserResponse, UserSession
from src.services import app_service as _app_service
from src.services.activity_logger import log_event
from src.services.cache import (
    cache,
    cached_fetch,
    coalesced_fetch,
    get_project_items_cache_key,
    get_user_projects_cache_key,
)
from src.services.database import get_db
from src.services.done_items_store import get_done_items
from src.services.github_auth import github_auth_service
from src.services.github_projects import github_projects_service
from src.services.websocket import connection_manager
from src.utils import resolve_repository

logger = get_logger(__name__)
router = APIRouter()
_selection_warmup_tasks: dict[str, asyncio.Task[Any]] = {}

# Re-export for monkeypatching in tests; bound through Any to satisfy strict mode
# without modifying the upstream service signature.
create_standalone_project: Any = getattr(  # noqa: B009 - reason: service factory is resolved lazily so monkeypatches stay visible
    _app_service, "create_standalone_project"
)


def _is_github_rate_limit_error(exc: Exception) -> bool:
    """Return True when GitHub rejected the request due to rate limits."""
    if isinstance(exc, PrimaryRateLimitExceeded):
        return True
    if isinstance(exc, RequestFailed):
        response = cast(Any, exc).response
        status_code = getattr(response, "status_code", None)
        if status_code == 429:
            return True
        if status_code == 403:
            headers = getattr(response, "headers", {})
            remaining = headers.get("X-RateLimit-Remaining")
            return remaining is not None and remaining.strip() == "0"
    rl = github_projects_service.get_last_rate_limit()
    return isinstance(rl, dict) and rl.get("remaining") == 0


def _retry_after_seconds(exc: Exception) -> int:
    """Extract retry-after seconds from a GitHub exception when available."""
    retry_after = getattr(exc, "retry_after", None)
    if retry_after is None:
        args = getattr(exc, "args", ())
        if len(args) > 1:
            retry_after = args[1]

    if isinstance(retry_after, timedelta):
        return max(1, int(retry_after.total_seconds()))

    if isinstance(retry_after, int):
        return max(1, retry_after)

    return 60


def _rate_limit_details() -> dict[str, object]:
    """Return serialized rate-limit details from the shared GitHub client state."""
    rl = github_projects_service.get_last_rate_limit()
    if not isinstance(rl, dict):
        return {}
    expected_keys = {"limit", "remaining", "reset_at", "used"}
    if not expected_keys.issubset(rl):
        return {}
    return {
        "rate_limit": {
            "limit": rl["limit"],
            "remaining": rl["remaining"],
            "reset_at": rl["reset_at"],
            "used": rl["used"],
        }
    }


@router.post("/create", status_code=201)
async def create_project_endpoint(
    request: Request,
    body: dict[str, Any],
    session: Annotated[UserSession, Depends(get_session_dep)],
) -> dict[str, Any]:
    """Create a standalone GitHub Project V2.

    Request body: ``{title, owner, repo_owner?, repo_name?}``
    Response: ``{project_id, project_number, project_url}``
    """
    from src.dependencies import get_github_service as _get_gh
    from src.exceptions import ValidationError

    title = body.get("title")
    owner = body.get("owner")
    if not title or not owner:
        raise ValidationError("Both 'title' and 'owner' are required.")

    github_service = _get_gh(request)
    result = cast(
        "dict[str, Any]",
        await create_standalone_project(
            access_token=session.access_token,
            owner=owner,
            title=title,
            github_service=github_service,
            repo_owner=body.get("repo_owner"),
            repo_name=body.get("repo_name"),
        ),
    )
    await log_event(
        get_db(),
        event_type="project",
        entity_type="project",
        entity_id=str(result.get("project_id", "")),
        project_id=str(result.get("project_id", "")),
        actor=session.github_username,
        action="created",
        summary=f"Project created: {title}",
        detail={"project_name": title, "owner": owner},
    )
    return result


@router.get("", response_model=ProjectListResponse)
async def list_projects(
    session: Annotated[UserSession, Depends(get_session_dep)],
    refresh: Annotated[bool, Query(description="Force refresh from GitHub API")] = False,
) -> ProjectListResponse:
    """List user's accessible GitHub Projects."""
    cache_key = get_user_projects_cache_key(session.github_user_id)

    # Check cache unless refresh requested
    if not refresh:
        cached = cache.get(cache_key)
        if cached:
            logger.info("Returning cached projects for user %s", session.github_username)
            return ProjectListResponse(projects=cached)

    # Fetch from GitHub
    logger.info("Fetching projects for user %s", session.github_username)

    try:

        async def _fetch_projects() -> list[GitHubProject]:
            return await github_projects_service.list_user_projects(
                session.access_token, session.github_username
            )

        all_projects = await coalesced_fetch(
            get_user_projects_cache_key(session.github_user_id),
            _fetch_projects,
            task_name=f"user-projects-{session.github_user_id}",
        )

        # Cache results
        cache.set(cache_key, all_projects)

        return ProjectListResponse(projects=all_projects)
    except Exception as e:
        if _is_github_rate_limit_error(e):
            if not refresh:
                stale = cache.get_stale(cache_key)
                if stale:
                    logger.warning(
                        "Serving stale cached projects for user %s due to rate limit",
                        session.github_username,
                    )
                    return ProjectListResponse(projects=stale)

            raise RateLimitError(
                message="GitHub API rate limit exceeded",
                retry_after=_retry_after_seconds(e),
                details=_rate_limit_details(),
            ) from e
        if not refresh:
            stale = cache.get_stale(cache_key)
            if stale:
                logger.warning(
                    "Serving stale cached projects for user %s due to GitHub error: %s",
                    session.github_username,
                    e,
                )
                return ProjectListResponse(projects=stale)
        raise GitHubAPIError("Failed to fetch projects from GitHub") from e


@router.get(
    "/{project_id}", response_model=GitHubProject, dependencies=[Depends(verify_project_access)]
)
async def get_project(
    project_id: str,
    session: Annotated[UserSession, Depends(get_session_dep)],
) -> GitHubProject:
    """Get project details including status columns."""
    # First check if we have the project cached in the list
    cache_key = get_user_projects_cache_key(session.github_user_id)
    cached_projects = cache.get(cache_key)

    if cached_projects:
        for project in cached_projects:
            if project.project_id == project_id:
                return project

    # If not cached, fetch projects list
    projects_response = await list_projects(session, refresh=True)

    for project in projects_response.projects:
        if project.project_id == project_id:
            return project

    raise NotFoundError(f"Project not found: {project_id}")


@router.get(
    "/{project_id}/tasks",
    response_model=TaskListResponse,
    dependencies=[Depends(verify_project_access)],
)
async def get_project_tasks(
    project_id: str,
    session: Annotated[UserSession, Depends(get_session_dep)],
    refresh: Annotated[bool, Query(description="Force refresh from GitHub API")] = False,
) -> TaskListResponse:
    """Get tasks/items for a project."""
    cache_key = get_project_items_cache_key(project_id)

    async def _fetch():
        logger.info("Fetching tasks for project %s", project_id)
        return await github_projects_service.get_project_items(session.access_token, project_id)

    try:
        tasks = await cached_fetch(cache, cache_key, _fetch, refresh=refresh)
    except Exception:
        # On API failure, try returning DB-cached Done tasks as partial result
        cached_done = await get_done_items(project_id, item_type="task")
        if cached_done:
            from src.models.task import Task

            logger.warning(
                "Returning %d DB-cached Done tasks as fallback for project %s",
                len(cached_done),
                project_id,
            )
            return TaskListResponse(tasks=[Task.model_validate(d) for d in cached_done])
        raise

    return TaskListResponse(tasks=tasks)


def _schedule_board_warmup(session: UserSession, project_id: str) -> bool:
    """Start best-effort board warm-up for the selected project."""
    from src.api.board import (
        _board_needs_background_completion,  # pyright: ignore[reportPrivateUsage]
        _fetch_and_cache_board_data,  # pyright: ignore[reportPrivateUsage]
        _schedule_background_board_completion,  # pyright: ignore[reportPrivateUsage]
    )
    from src.models.board import BoardLoadMode
    from src.services.task_registry import task_registry

    existing = _selection_warmup_tasks.get(session.github_user_id)
    if existing is not None and not existing.done():
        existing.cancel()

    async def _warm() -> None:
        try:
            board_data = await _fetch_and_cache_board_data(
                session,
                project_id,
                load_mode=BoardLoadMode.INITIAL,
                warmed_by_selection=True,
            )
            if _board_needs_background_completion(board_data):
                _schedule_background_board_completion(session, project_id)
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001 — reason: best-effort operation; failure logged, execution continues
            logger.debug(
                "Non-critical: board warm-up failed for user %s project %s",
                session.github_username,
                project_id,
                exc_info=True,
            )

    task = task_registry.create_task(
        _warm(),
        name=f"board-warmup-{session.github_user_id}-{project_id}",
    )
    _selection_warmup_tasks[session.github_user_id] = task

    def _cleanup_finished_warmup(finished: asyncio.Task[Any]) -> None:
        if _selection_warmup_tasks.get(session.github_user_id) is finished:
            _selection_warmup_tasks.pop(session.github_user_id, None)

    task.add_done_callback(_cleanup_finished_warmup)
    return True


@router.post(
    "/{project_id}/select",
    response_model=UserResponse,
    dependencies=[Depends(verify_project_access)],
)
async def select_project(
    request: Request,
    project_id: str,
    session: Annotated[UserSession, Depends(get_session_dep)],
) -> UserResponse:
    """Select a project as the active project and start Copilot polling."""
    # Reuse project list already fetched by verify_project_access dependency
    # to avoid a duplicate list_user_projects GraphQL call.
    verified_projects = getattr(request.state, "verified_projects", None)
    project = None
    if verified_projects:
        project = next((p for p in verified_projects if p.project_id == project_id), None)
    if project is None:
        project = await get_project(project_id, session)

    # Update session
    session.selected_project_id = project_id
    await github_auth_service.update_session(session)

    logger.info("User %s selected project %s", session.github_username, project_id)

    await log_event(
        get_db(),
        event_type="project",
        entity_type="project",
        entity_id=project_id,
        project_id=project_id,
        actor=session.github_username,
        action="selected",
        summary=f"Project selected: {project.name}",
        detail={"project_name": project.name},
    )

    board_warmup_started = _schedule_board_warmup(session, project_id)

    # Auto-start Copilot polling for this project
    await _start_copilot_polling(session, project_id)

    # Fire-and-forget prefetch of agent data so the first GET /workflow/agents
    # hits a warm cache.  Errors are silently swallowed.
    from src.services.task_registry import task_registry

    task_registry.create_task(
        _restore_app_pipelines_for_project(session.access_token, project_id),
        name=f"restore-app-pipelines-{project_id}",
    )
    task_registry.create_task(
        _prefetch_agents(session.access_token, project_id),
        name=f"prefetch-agents-{project_id}",
    )

    return UserResponse.from_session(session, board_warmup_started=board_warmup_started)


async def _start_copilot_polling(session: UserSession, project_id: str) -> None:
    """Start Copilot PR completion polling for the selected project."""
    from src.services.copilot_polling import (
        ensure_polling_started,
        get_polling_status,
        stop_polling,
    )

    # Stop any existing polling first — cancel the task so it stops immediately
    # even if it's in the middle of a long-running API call.
    status = get_polling_status()
    if status["is_running"]:
        await stop_polling()
        # Give the cancelled task a chance to clean up
        await asyncio.sleep(0.1)

    # Resolve repository info for the project
    try:
        owner, repo = await resolve_repository(session.access_token, project_id)
    except Exception:  # noqa: BLE001 — reason: best-effort operation; failure logged, execution continues
        logger.warning(
            "Could not determine repository for project %s, polling not started",
            project_id,
        )
        return

    await ensure_polling_started(
        access_token=session.access_token,
        project_id=project_id,
        owner=owner,
        repo=repo,
        delay_seconds=45,
        caller="select_project",
    )


async def _restore_app_pipelines_for_project(access_token: str, project_id: str) -> int:
    """Restore scoped app-pipeline polling for the selected project."""
    from src.config import get_settings
    from src.services.copilot_polling import ensure_app_pipeline_polling
    from src.services.workflow_orchestrator import (
        get_all_pipeline_states,
        set_pipeline_state,
    )

    settings = get_settings()
    default_owner = (settings.default_repo_owner or "").lower()
    default_repo = (settings.default_repo_name or "").lower()

    restored = 0
    resolved_repo: tuple[str, str] | None = None
    attempted_resolve = False
    for issue_number, state in get_all_pipeline_states().items():
        if getattr(state, "project_id", None) != project_id:
            continue
        if getattr(state, "is_complete", False):
            continue

        owner = getattr(state, "repository_owner", "") or ""
        repo = getattr(state, "repository_name", "") or ""
        if not owner or not repo:
            if not attempted_resolve:
                attempted_resolve = True
                try:
                    resolved_repo = await resolve_repository(access_token, project_id)
                    logger.info(
                        "Resolved project %s via GitHub API for app-pipeline → %s/%s",
                        project_id,
                        resolved_repo[0],
                        resolved_repo[1],
                    )
                except Exception:  # noqa: BLE001 — reason: best-effort operation; failure logged, execution continues
                    logger.warning(
                        "Could not resolve repository for project %s, "
                        "scoped app-pipeline polling not restored",
                        project_id,
                        exc_info=True,
                    )
            owner, repo = resolved_repo or ("", "")
            if owner and repo:
                state.repository_owner = owner
                state.repository_name = repo
                set_pipeline_state(issue_number, state)
        if not owner or not repo:
            continue
        if owner.lower() == default_owner and repo.lower() == default_repo:
            continue

        started = await ensure_app_pipeline_polling(
            access_token=access_token,
            project_id=project_id,
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
            "Restored %d scoped app-pipeline polling task(s) for project %s",
            restored,
            project_id,
        )
    return restored


async def _prefetch_agents(access_token: str, project_id: str) -> None:
    """Pre-warm the AgentsService repo-agents cache after project selection."""
    try:
        owner, repo = await resolve_repository(access_token, project_id)
    except Exception:  # noqa: BLE001 — reason: best-effort operation; returns fallback value on failure
        return
    try:
        from src.services.agents.service import AgentsService

        svc = AgentsService(get_db())
        await svc.list_agents(
            project_id=project_id,
            owner=owner,
            repo=repo,
            access_token=access_token,
        )
    except Exception:  # noqa: BLE001 — reason: best-effort operation; failure logged, execution continues
        pass  # Best-effort; errors logged inside list_agents


@router.websocket("/{project_id}/subscribe")
async def websocket_subscribe(
    websocket: WebSocket,
    project_id: str,
):
    """
    WebSocket endpoint for real-time project updates.

    On connection, sends all current tasks.
    Periodically checks for updates every 30 seconds (using cached data
    when available; actual GitHub API calls are governed by the cache TTL).
    Also sends real-time updates when tasks are created, updated, or deleted.

    Message format:
    {
        "type": "initial_data" | "refresh" | "task_created" | "task_update" | "status_changed",
        "tasks": [...] | "task_id": "...",
        "data": {...}
    }
    """
    # Get session from cookie to authenticate
    session_id = websocket.cookies.get(SESSION_COOKIE_NAME)
    try:
        session = await get_current_session(session_id)
    except Exception as e:  # noqa: BLE001 — reason: best-effort operation; failure logged, execution continues
        logger.error("WebSocket authentication failed: %s", e)
        await websocket.close(code=1008, reason="Authentication required")
        return

    # Verify the user has access to this project before accepting.
    # Reuse the cached user-projects list when available to avoid an extra
    # upstream API call on every WebSocket connection (R2 optimisation).
    try:
        user_projects_key = get_user_projects_cache_key(session.github_user_id)
        projects = cache.get(user_projects_key)
        if projects is None:
            try:
                projects = await github_projects_service.list_user_projects(
                    session.access_token, session.github_username
                )
                cache.set(user_projects_key, projects)
            except Exception as fetch_err:
                logger.warning(
                    "WebSocket project access revalidation failed for user=%s: %s",
                    session.github_username,
                    fetch_err,
                )
                raise
        if not any(p.project_id == project_id for p in projects):
            logger.warning(
                "WebSocket project access denied: user=%s project=%s",
                session.github_username,
                project_id,
            )
            await websocket.close(code=4403, reason="Project access denied")
            return
    except Exception as e:  # noqa: BLE001 — reason: best-effort operation; failure logged, execution continues
        logger.error("WebSocket project access check failed: %s", e)
        await websocket.close(code=4403, reason="Project access denied")
        return

    await connection_manager.connect(websocket, project_id)

    try:
        # Send a lightweight handshake on connection.  The frontend no
        # longer consumes the full tasks payload from the WebSocket — it
        # relies on REST queries (board data) for rendering.  Sending
        # only a count avoids the 1 MB frame-size crash on large
        # projects (722+ items) while preserving the initial_data
        # contract the frontend expects.
        cache_key = get_project_items_cache_key(project_id)
        cached_tasks = cache.get(cache_key)
        item_count = len(cached_tasks) if cached_tasks is not None else 0
        await websocket.send_json(
            {
                "type": "initial_data",
                "project_id": project_id,
                "count": item_count,
            }
        )
        logger.info(
            "Sent lightweight initial_data (%d items) to WebSocket for project %s",
            item_count,
            project_id,
        )

        # Keep connection alive and periodically push cached data.
        # Actual GitHub API calls are governed by the cache TTL (default
        # 300 s); this interval only controls how often we check/send.
        last_refresh = asyncio.get_running_loop().time()
        refresh_interval = 30.0  # Check for updates every 30 seconds
        last_sent_hash: str | None = None

        while True:
            try:
                # Wait for incoming messages with timeout
                data = await asyncio.wait_for(websocket.receive_json(), timeout=1.0)

                # Handle ping
                if data.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})

            except TimeoutError:
                # Check if we need to refresh
                current_time = asyncio.get_running_loop().time()
                if current_time - last_refresh >= refresh_interval:
                    # Periodic refresh: check the cache entry's hash to
                    # detect changes without re-fetching or re-serialising
                    # all project items.  The cache is populated by the
                    # regular REST endpoints and Copilot polling; we just
                    # piggyback on its data_hash for change detection.
                    entry = cache.get_entry(cache_key)
                    if entry is not None and entry.data_hash is not None:
                        if entry.data_hash != last_sent_hash:
                            entry_value: Any = entry.value
                            item_count = (
                                len(cast("list[Any]", entry_value))
                                if isinstance(entry_value, list)
                                else 0
                            )
                            await websocket.send_json(
                                {
                                    "type": "refresh",
                                    "project_id": project_id,
                                    "count": item_count,
                                }
                            )
                            last_sent_hash = entry.data_hash
                            logger.debug(
                                "Refreshed %d tasks for project %s", item_count, project_id
                            )
                        else:
                            logger.debug(
                                "Skipping refresh for project %s — data unchanged", project_id
                            )
                    last_refresh = current_time

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected for project %s", project_id)
    except Exception as e:  # noqa: BLE001 — reason: best-effort operation; failure logged, execution continues
        logger.error("WebSocket error for project %s: %s", project_id, e)
    finally:
        connection_manager.disconnect(websocket)


@router.get("/{project_id}/events", dependencies=[Depends(verify_project_access)])
async def sse_subscribe(
    project_id: str,
    session: Annotated[UserSession, Depends(get_session_dep)],
):
    """
    Server-Sent Events endpoint for real-time updates.

    This is a fallback for clients that don't support WebSocket.
    Uses polling internally with 10-second intervals.
    """

    async def event_generator() -> AsyncGenerator[str]:
        """Generate SSE events by polling for changes."""
        # Get initial state
        cache_key = get_project_items_cache_key(project_id)
        cached_tasks: list[Any] = cast("list[Any] | None", cache.get(cache_key)) or []

        # Send initial connection event
        yield f'event: connected\ndata: {{"project_id": "{project_id}"}}\n\n'

        try:
            while True:
                # Poll for changes
                try:
                    result = cast(
                        "dict[str, Any]",
                        await cast(Any, github_projects_service).poll_project_changes(
                            session.access_token,
                            project_id,
                            cached_tasks,
                        ),
                    )

                    changes = cast("list[dict[str, Any]]", result.get("changes", []))

                    if changes:
                        # Update cache
                        cached_tasks = cast("list[Any]", result.get("current_tasks", []))
                        cache.set(cache_key, cached_tasks)

                        # Send change events
                        for change in changes:
                            import json

                            yield f"event: {change['type']}\ndata: {json.dumps(change)}\n\n"

                    # Send heartbeat
                    yield f'event: heartbeat\ndata: {{"timestamp": "{asyncio.get_running_loop().time()}"}}\n\n'

                except Exception as e:  # noqa: BLE001 — reason: best-effort operation; failure logged, execution continues
                    logger.error("SSE polling error: %s", e)
                    # Serve stale cached data on fetch failure instead of
                    # cascading the error to the client (SC-005 safety).
                    stale = cache.get_stale(cache_key)
                    if stale is not None:
                        cached_tasks = stale
                    yield f'event: heartbeat\ndata: {{"timestamp": "{asyncio.get_running_loop().time()}"}}\n\n'

                # Wait before next poll (30 seconds to reduce API call volume)
                await asyncio.sleep(30)

        except asyncio.CancelledError:
            logger.info("SSE connection closed for project %s", project_id)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )
