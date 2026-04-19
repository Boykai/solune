"""Activity feed API — paginated activity events and entity-scoped history."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Annotated, Any, cast

import aiosqlite
from fastapi import APIRouter, Depends, Query, Request

from src.api.auth import get_session_dep
from src.dependencies import get_database, verify_project_access
from src.models.activity import ActivityStats
from src.models.user import UserSession
from src.services import activity_service as _activity_service

# The underlying service functions are typed as returning bare ``dict``; wrap
# them in typed Callables so the strict floor sees concrete dict[str, Any]
# results. ``cast`` accepts the raw callables (Any-typed via getattr) and
# narrows them to the desired signatures.
get_activity_stats: Callable[..., Awaitable[dict[str, Any]]] = cast(
    "Callable[..., Awaitable[dict[str, Any]]]",
    getattr(_activity_service, "get_activity_stats"),  # noqa: B009 - reason: strict wrapper intentionally binds service helper via getattr for tests
)
_query_events: Callable[..., Awaitable[dict[str, Any]]] = cast(
    "Callable[..., Awaitable[dict[str, Any]]]",
    getattr(_activity_service, "query_events"),  # noqa: B009 - reason: strict wrapper intentionally binds service helper via getattr for tests
)

router = APIRouter()

ALLOWED_ENTITY_TYPES = {"pipeline", "chore", "agent", "app", "tool", "issue", "project", "settings"}


@router.get("")
async def get_activity_feed(
    request: Request,
    session: Annotated[UserSession, Depends(get_session_dep)],
    project_id: Annotated[str, Query(description="Project ID to scope the feed")],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    cursor: Annotated[str | None, Query(description="Pagination cursor")] = None,
    event_type: Annotated[
        str | None, Query(description="Comma-separated event type filter")
    ] = None,
    db: aiosqlite.Connection = Depends(get_database),  # noqa: B008 — reason: FastAPI Depends() pattern — evaluated per-request, not at import time
) -> dict[str, Any]:
    """Paginated activity feed scoped to a project."""
    await verify_project_access(request, project_id, session)
    return await _query_events(
        db,
        project_id=project_id,
        event_type_filter=event_type,
        limit=limit,
        cursor=cursor,
    )


@router.get("/stats", response_model=ActivityStats)
async def get_activity_stats_endpoint(
    request: Request,
    session: Annotated[UserSession, Depends(get_session_dep)],
    project_id: Annotated[str, Query(description="Project ID to scope the stats")],
    db: aiosqlite.Connection = Depends(get_database),  # noqa: B008 — reason: FastAPI Depends() pattern — evaluated per-request, not at import time
) -> dict[str, Any]:
    """Aggregated activity statistics scoped to a project."""
    await verify_project_access(request, project_id, session)
    return await get_activity_stats(db, project_id=project_id)


@router.get("/{entity_type}/{entity_id}")
async def get_entity_history(
    request: Request,
    entity_type: str,
    entity_id: str,
    session: Annotated[UserSession, Depends(get_session_dep)],
    project_id: Annotated[str, Query(description="Project ID to scope entity history")],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    cursor: Annotated[str | None, Query(description="Pagination cursor")] = None,
    db: aiosqlite.Connection = Depends(get_database),  # noqa: B008 — reason: FastAPI Depends() pattern — evaluated per-request, not at import time
) -> dict[str, Any]:
    """Activity history for a specific entity."""
    if entity_type not in ALLOWED_ENTITY_TYPES:
        from src.exceptions import ValidationError

        raise ValidationError(  # noqa: TRY003 — reason: domain exception with descriptive message
            f"Invalid entity_type '{entity_type}'. "
            f"Must be one of: {', '.join(sorted(ALLOWED_ENTITY_TYPES))}"
        )

    await verify_project_access(request, project_id, session)
    return await _query_events(
        db,
        project_id=project_id,
        entity_type=entity_type,
        entity_id=entity_id,
        limit=limit,
        cursor=cursor,
    )
