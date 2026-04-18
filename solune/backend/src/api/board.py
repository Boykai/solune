"""Board API endpoints for the Project Board feature."""

from __future__ import annotations

import asyncio
from datetime import timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from githubkit.exception import PrimaryRateLimitExceeded, RequestFailed

from src.api.auth import get_session_dep
from src.exceptions import (
    AuthenticationError,
    GitHubAPIError,
    NotFoundError,
    RateLimitError,
    ValidationError,
)
from src.logging_utils import get_logger
from src.models.board import (
    BoardDataResponse,
    BoardLoadMode,
    BoardLoadPhase,
    BoardLoadState,
    BoardProject,
    BoardProjectListResponse,
    DoneColumnSource,
    RateLimitInfo,
    StatusColor,
    StatusField,
    StatusOption,
    StatusUpdateRequest,
    StatusUpdateResponse,
)
from src.models.project import GitHubProject
from src.models.user import UserSession
from src.services.cache import (
    cache,
    coalesced_fetch,
    compute_data_hash,
    get_cache_key,
    get_sub_issues_cache_key,
    get_user_projects_cache_key,
)
from src.services.done_items_store import get_done_items
from src.services.github_projects import github_projects_service

_background_board_completion_tasks: dict[str, asyncio.Task[Any]] = {}


def _is_github_auth_error(exc: Exception) -> bool:
    """Return True if *exc* indicates the GitHub token is invalid/expired.

    Covers httpx status errors (401/403) and GraphQL "FORBIDDEN" / "UNAUTHORIZED"
    errors that GitHub returns inside a 200 response.

    A 403 with ``X-RateLimit-Remaining: 0`` is a primary rate-limit response,
    NOT an auth error — those are handled separately by the retry logic.
    """
    if isinstance(exc, RequestFailed):
        response = exc.response
        code = response.status_code
        if code == 401:
            return True
        if code == 403:
            # GitHub uses 403 for both auth/permission errors AND primary rate
            # limiting.  When rate-limited, X-RateLimit-Remaining is "0".
            remaining = response.headers.get("X-RateLimit-Remaining")
            if remaining is not None and remaining.strip() == "0":
                return False
            return True
        return False
    # GraphQL wraps auth problems in ValueError("GraphQL error: ...")
    msg = str(exc).lower()
    if any(
        keyword in msg
        for keyword in (
            "bad credentials",
            "unauthorized",
            "forbidden",
            "insufficient scopes",
            "401",
            "403",
        )
    ):
        return True
    return False


def _classify_github_error(exc: Exception) -> str:
    """Return a safe, user-facing error classification for *exc*.

    Never exposes raw internal strings (URLs, hostnames, stack traces).
    """
    msg = str(exc).lower()
    if isinstance(exc, RequestFailed):
        code = exc.response.status_code
        if code == 429:
            return "GitHub API rate limit exceeded"
        if code >= 500:
            return "GitHub API is temporarily unavailable"
        return f"GitHub API returned status {code}"
    if "graphql error" in msg:
        return "GitHub GraphQL query failed"
    if "timeout" in msg or "timed out" in msg:
        return "Request to GitHub API timed out"
    if "connect" in msg:
        return "Could not connect to GitHub API"
    return "Unexpected error communicating with GitHub"


def _is_github_rate_limit_error(exc: Exception) -> bool:
    """Return True if *exc* represents a GitHub rate-limit response."""
    if isinstance(exc, PrimaryRateLimitExceeded):
        return True
    if isinstance(exc, RequestFailed):
        response = exc.response
        if response.status_code == 429:
            return True
        if response.status_code == 403:
            remaining = response.headers.get("X-RateLimit-Remaining")
            return remaining is not None and remaining.strip() == "0"
    rate_limit = _get_rate_limit_info()
    return rate_limit is not None and rate_limit.remaining == 0


def _rate_limit_details() -> dict[str, object]:
    """Return serialized rate-limit details when available."""
    rate_limit = _get_rate_limit_info()
    return {"rate_limit": rate_limit.model_dump()} if rate_limit is not None else {}


def _retry_after_seconds(exc: Exception) -> int:
    """Best-effort extraction of retry-after seconds from GitHub exceptions."""
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


logger = get_logger(__name__)
router = APIRouter()

CACHE_PREFIX_BOARD_PROJECTS = "board_projects"
CACHE_PREFIX_BOARD_DATA = "board_data"


def _normalize_status_color(color: str | None) -> StatusColor:
    if not color:
        return StatusColor.GRAY
    normalized = color.upper()
    try:
        return StatusColor(normalized)
    except ValueError:
        return StatusColor.GRAY


def _to_board_projects(projects: list[GitHubProject]) -> list[BoardProject]:
    board_projects: list[BoardProject] = []
    for project in projects:
        valid_columns = [c for c in project.status_columns if c.field_id and c.option_id]
        if not valid_columns:
            continue

        field_id = valid_columns[0].field_id
        options = [
            StatusOption(
                option_id=column.option_id,
                name=column.name,
                color=_normalize_status_color(column.color),
                description=None,
            )
            for column in valid_columns
            if column.field_id == field_id
        ]
        if not options:
            continue

        board_projects.append(
            BoardProject(
                project_id=project.project_id,
                name=project.name,
                description=project.description,
                url=project.url,
                owner_login=project.owner_login,
                status_field=StatusField(field_id=field_id, options=options),
            )
        )

    return board_projects


def _get_rate_limit_info() -> RateLimitInfo | None:
    """Build RateLimitInfo from the last GitHub API response headers."""
    rl = github_projects_service.get_last_rate_limit()
    if not isinstance(rl, dict):
        return None
    try:
        return RateLimitInfo(
            limit=rl["limit"],
            remaining=rl["remaining"],
            reset_at=rl["reset_at"],
            used=rl["used"],
        )
    except (KeyError, TypeError):
        return None


def _board_cache_key(project_id: str) -> str:
    return get_cache_key(CACHE_PREFIX_BOARD_DATA, project_id)


def _board_inflight_key(project_id: str, load_mode: BoardLoadMode) -> str:
    return get_cache_key(CACHE_PREFIX_BOARD_DATA, f"{project_id}:{load_mode}")


def _board_needs_background_completion(board_data: BoardDataResponse) -> bool:
    return board_data.load_state.phase != BoardLoadPhase.COMPLETE and bool(
        board_data.load_state.pending_sections
    )


def _cache_board_data(project_id: str, board_data: BoardDataResponse) -> None:
    board_hash = compute_data_hash(board_data.model_dump(mode="json", exclude={"rate_limit"}))
    cache.set(_board_cache_key(project_id), board_data, ttl_seconds=300, data_hash=board_hash)


async def _apply_board_runtime_state(board_data: BoardDataResponse) -> BoardDataResponse:
    board_data.rate_limit = _get_rate_limit_info()

    from src.services.workflow_orchestrator import get_pipeline_state

    for col in board_data.columns:
        for item in col.items:
            if item.number is not None:
                ps = get_pipeline_state(item.number)
                if ps is not None and getattr(ps, "queued", False):
                    item.queued = True

    return board_data


async def _fetch_and_cache_board_data(
    session: UserSession,
    project_id: str,
    *,
    load_mode: BoardLoadMode,
    warmed_by_selection: bool = False,
) -> BoardDataResponse:
    async def _fetch() -> BoardDataResponse:
        board_data = await github_projects_service.get_board_data(
            session.access_token,
            project_id,
            load_mode=load_mode,
            warmed_by_selection=warmed_by_selection,
        )
        await _apply_board_runtime_state(board_data)
        _cache_board_data(project_id, board_data)
        return board_data

    return await coalesced_fetch(
        _board_inflight_key(project_id, load_mode),
        _fetch,
        task_name=f"board-{project_id[-8:]}-{load_mode}",
    )


def _schedule_background_board_completion(session: UserSession, project_id: str) -> None:
    from src.services.task_registry import task_registry

    task_key = f"{session.github_user_id}:{project_id}"
    existing = _background_board_completion_tasks.get(task_key)
    if existing is not None and not existing.done():
        return

    async def _complete() -> None:
        try:
            cached = cache.get(_board_cache_key(project_id))
            if isinstance(cached, BoardDataResponse) and not _board_needs_background_completion(
                cached
            ):
                return
            await _fetch_and_cache_board_data(
                session,
                project_id,
                load_mode=BoardLoadMode.FULL,
            )
        except Exception:
            logger.debug(
                "Non-critical: background board completion failed for project %s",
                project_id,
                exc_info=True,
            )

    task = task_registry.create_task(
        _complete(),
        name=f"board-complete-{session.github_user_id}-{project_id[-8:]}",
    )
    _background_board_completion_tasks[task_key] = task

    def _cleanup_finished_completion(finished: asyncio.Task[Any]) -> None:
        if _background_board_completion_tasks.get(task_key) is finished:
            _background_board_completion_tasks.pop(task_key, None)

    task.add_done_callback(_cleanup_finished_completion)


@router.get("/projects", response_model=BoardProjectListResponse)
async def list_board_projects(
    session: Annotated[UserSession, Depends(get_session_dep)],
    refresh: Annotated[bool, Query(description="Force refresh from GitHub API")] = False,
) -> BoardProjectListResponse:
    """List available GitHub Projects with status field configuration for board display."""
    cache_key = get_cache_key(CACHE_PREFIX_BOARD_PROJECTS, session.github_user_id)
    user_projects_cache_key = get_user_projects_cache_key(session.github_user_id)

    if not refresh:
        cached = cache.get(cache_key)
        if cached:
            logger.info("Returning cached board projects for user %s", session.github_username)
            return BoardProjectListResponse(projects=cached, rate_limit=_get_rate_limit_info())

        cached_user_projects = cache.get(user_projects_cache_key)
        if cached_user_projects:
            board_projects = _to_board_projects(cached_user_projects)
            if board_projects:
                logger.info(
                    "Reusing cached generic projects for board projects (user %s)",
                    session.github_username,
                )
                cache.set(cache_key, board_projects)
                return BoardProjectListResponse(
                    projects=board_projects,
                    rate_limit=_get_rate_limit_info(),
                )

    logger.info("Fetching board projects for user %s", session.github_username)

    try:

        async def _fetch_user_projects() -> list[GitHubProject]:
            # Use list_user_projects (which populates the shared user-projects
            # cache) instead of list_board_projects (a separate GraphQL call).
            # On cold start both GET /projects and GET /board/projects fire;
            # by sharing the upstream call we avoid a duplicate GraphQL round-trip
            # (~875 ms saved).
            return await github_projects_service.list_user_projects(
                session.access_token, session.github_username
            )

        user_projects = await coalesced_fetch(
            user_projects_cache_key,
            _fetch_user_projects,
            task_name=f"user-projects-{session.github_user_id}",
        )
        cache.set(user_projects_cache_key, user_projects)
        projects = _to_board_projects(user_projects) or []
    except Exception as e:
        if _is_github_rate_limit_error(e):
            logger.warning(
                "Rate limit exceeded while fetching board projects for user %s",
                session.github_username,
            )
            raise RateLimitError(
                message="GitHub API rate limit exceeded",
                retry_after=_retry_after_seconds(e),
                details=_rate_limit_details(),
            ) from e
        if _is_github_auth_error(e):
            logger.warning(
                "GitHub token invalid/expired for user %s — returning 401",
                session.github_username,
            )
            raise AuthenticationError(
                "Your GitHub session has expired. Please log in again."
            ) from e

        if not refresh:
            stale_cached = cache.get_stale(cache_key)
            if stale_cached:
                logger.warning(
                    "Serving stale cached board projects for user %s due to GitHub error: %s",
                    session.github_username,
                    e,
                )
                return BoardProjectListResponse(
                    projects=stale_cached,
                    rate_limit=_get_rate_limit_info(),
                )

            stale_user_projects = cache.get_stale(user_projects_cache_key)
            if stale_user_projects:
                stale_board_projects = _to_board_projects(stale_user_projects)
                if stale_board_projects:
                    logger.warning(
                        "Serving stale transformed projects for user %s due to GitHub error: %s",
                        session.github_username,
                        e,
                    )
                    return BoardProjectListResponse(
                        projects=stale_board_projects,
                        rate_limit=_get_rate_limit_info(),
                    )

        logger.error("Failed to fetch board projects: %s", e, exc_info=True)
        raise GitHubAPIError(
            message="Failed to fetch board projects from GitHub.",
            details={"reason": _classify_github_error(e)},
        ) from e

    cache.set(cache_key, projects)
    return BoardProjectListResponse(projects=projects, rate_limit=_get_rate_limit_info())


async def _build_done_fallback_board(
    project_id: str, original_error: Exception
) -> BoardDataResponse | None:
    """Build a partial board from DB-cached Done items when the API fails.

    Returns ``None`` when no cached Done items are available, allowing the
    caller to propagate the original error.  Auth errors are never masked
    — the user must re-authenticate.
    """
    if _is_github_auth_error(original_error):
        return None

    try:
        cached = await get_done_items(project_id, item_type="board")
    except Exception:
        return None

    if not cached:
        return None

    from src.models.board import (
        BoardColumn,
        BoardDataResponse,
        BoardItem,
        BoardProject,
        StatusColor,
        StatusField,
        StatusOption,
    )

    done_items = [BoardItem.model_validate(d) for d in cached]
    done_option = StatusOption(option_id="__done__", name="Done", color=StatusColor.PURPLE)
    done_column = BoardColumn(
        status=done_option,
        items=done_items,
        item_count=len(done_items),
        estimate_total=sum(it.estimate or 0.0 for it in done_items),
    )

    fallback_project = BoardProject(
        project_id=project_id,
        name="(offline)",
        url="",
        owner_login="",
        status_field=StatusField(field_id="", options=[done_option]),
    )

    logger.warning(
        "Returning DB-cached Done column (%d items) as fallback for project %s",
        len(done_items),
        project_id,
    )

    return BoardDataResponse(
        project=fallback_project,
        columns=[done_column],
        load_state=BoardLoadState(
            phase=BoardLoadPhase.BACKFILLING_DONE,
            active_columns_ready=False,
            done_column_source=DoneColumnSource.CACHED,
            pending_sections=["active_columns", "reconciliation"],
        ),
        rate_limit=_get_rate_limit_info(),
    )


@router.get("/projects/{project_id}", response_model=BoardDataResponse)
async def get_board_data(
    project_id: str,
    session: Annotated[UserSession, Depends(get_session_dep)],
    refresh: Annotated[bool, Query(description="Force refresh from GitHub API")] = False,
    load_mode: Annotated[
        BoardLoadMode,
        Query(description="initial optimizes for interactivity; full forces complete refresh"),
    ] = BoardLoadMode.INITIAL,
    column_limit: Annotated[
        int | None, Query(ge=1, le=100, description="Items per column page")
    ] = None,
    column_cursors: Annotated[
        str | None, Query(description="JSON map of {status_option_id: cursor}")
    ] = None,
) -> BoardDataResponse:
    """Get board data for a specific project with columns and items."""
    cache_key = _board_cache_key(project_id)
    effective_load_mode = BoardLoadMode.FULL if refresh else load_mode

    if not refresh and effective_load_mode == BoardLoadMode.INITIAL:
        cached = cache.get(cache_key)
        if cached:
            logger.info("Returning cached board data for project %s", project_id)
            if isinstance(cached, BoardDataResponse):
                # Return a shallow copy to avoid mutating the shared cache entry,
                # which could leak stale rate_limit values across requests.
                cached_response = cached.model_copy(update={"rate_limit": _get_rate_limit_info()})
                await _apply_board_runtime_state(cached_response)
                if _board_needs_background_completion(cached_response):
                    _schedule_background_board_completion(session, project_id)
                return cached_response
            return cached

    # On manual refresh, clear sub-issue caches BEFORE fetching board data so
    # that get_board_data() → get_sub_issues() doesn't serve stale cached entries.
    if refresh:
        old_cached = cache.get(cache_key)
        if isinstance(old_cached, BoardDataResponse) and hasattr(old_cached, "columns"):
            for col in old_cached.columns:
                for item in col.items:
                    if item.number is not None and item.repository:
                        si_key = get_sub_issues_cache_key(
                            item.repository.owner, item.repository.name, item.number
                        )
                        cache.delete(si_key)

    logger.info("Fetching board data for project %s", project_id)

    try:
        board_data = await _fetch_and_cache_board_data(
            session,
            project_id,
            load_mode=effective_load_mode,
        )
    except ValueError as e:
        logger.warning("Project not found: %s - %s", project_id, e)
        raise NotFoundError("Project not found") from e
    except Exception as e:
        # On API failure, try serving DB-cached Done items as partial board
        db_fallback = await _build_done_fallback_board(project_id, e)
        if db_fallback is not None:
            logger.info("Serving DB-cached Done items as fallback for project %s", project_id)
            return db_fallback

        if _is_github_rate_limit_error(e):
            logger.warning(
                "Rate limit exceeded while fetching board data for project %s", project_id
            )
            raise RateLimitError(
                message="GitHub API rate limit exceeded",
                retry_after=_retry_after_seconds(e),
                details=_rate_limit_details(),
            ) from e
        if _is_github_auth_error(e):
            logger.warning(
                "GitHub token invalid/expired for user %s — returning 401",
                session.github_username,
            )
            raise AuthenticationError(
                "Your GitHub session has expired. Please log in again."
            ) from e
        logger.error("Failed to fetch board data: %s", e, exc_info=True)
        raise GitHubAPIError(
            message="Failed to fetch board data from GitHub",
            details={"reason": _classify_github_error(e)},
        ) from e

    if effective_load_mode == BoardLoadMode.INITIAL and _board_needs_background_completion(
        board_data
    ):
        _schedule_background_board_completion(session, project_id)

    # Apply per-column pagination when requested
    if column_limit is not None or column_cursors is not None:
        import copy
        import json as _json
        from typing import cast

        from src.services.pagination import apply_pagination

        # Deep copy to avoid mutating cached board_data
        board_data = copy.deepcopy(board_data)

        cursors_map: dict[str, str] = {}
        if column_cursors:
            try:
                parsed = _json.loads(column_cursors)
                if not isinstance(parsed, dict):
                    raise ValidationError(
                        "column_cursors must be a JSON object mapping column IDs to cursor strings"
                    )
                parsed_dict = cast("dict[Any, Any]", parsed)
                cursors_map = {str(k): str(v) for k, v in parsed_dict.items()}
            except (ValueError, TypeError) as exc:
                raise ValidationError(f"column_cursors is not valid JSON: {exc}") from exc

        effective_limit = column_limit or 25
        for col in board_data.columns:
            col_cursor = cursors_map.get(col.status.option_id)
            paginated = apply_pagination(
                col.items,
                limit=effective_limit,
                cursor=col_cursor,
                key_fn=lambda item: item.item_id,
            )
            col.items = paginated.items
            col.next_cursor = paginated.next_cursor
            col.has_more = paginated.has_more

    return board_data


@router.patch(
    "/projects/{project_id}/items/{item_id}/status",
    response_model=StatusUpdateResponse,
)
async def update_board_item_status(
    project_id: str,
    item_id: str,
    body: StatusUpdateRequest,
    session: Annotated[UserSession, Depends(get_session_dep)],
) -> StatusUpdateResponse:
    """Update a board item's status by resolving the given status name."""
    logger.info(
        "Updating status for item %s in project %s to '%s'",
        item_id,
        project_id,
        body.status,
    )

    try:
        success = await github_projects_service.update_item_status_by_name(
            access_token=session.access_token,
            project_id=project_id,
            item_id=item_id,
            status_name=body.status,
        )
    except Exception as e:
        if _is_github_rate_limit_error(e):
            raise RateLimitError(
                message="GitHub API rate limit exceeded",
                retry_after=_retry_after_seconds(e),
                details=_rate_limit_details(),
            ) from e
        if _is_github_auth_error(e):
            raise AuthenticationError(
                "Your GitHub session has expired. Please log in again."
            ) from e
        logger.error("Failed to update item status: %s", e, exc_info=True)
        raise GitHubAPIError(
            message="Failed to update item status",
            details={"reason": _classify_github_error(e)},
        ) from e

    if not success:
        raise NotFoundError("Status not found or update failed")

    # Invalidate board data cache so subsequent fetches reflect the change
    board_cache_key = get_cache_key(CACHE_PREFIX_BOARD_DATA, project_id)
    cache.delete(board_cache_key)

    return StatusUpdateResponse(success=True)
