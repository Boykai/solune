"""Settings API endpoints — user preferences, global settings, project settings."""

import json
from collections.abc import Awaitable, Callable
from typing import Annotated, Any, cast

import aiosqlite
from fastapi import APIRouter, Depends, Query

from src.api.auth import get_session_dep
from src.dependencies import require_admin, verify_project_access
from src.logging_utils import get_logger
from src.models.settings import (
    AIProvider,
    EffectiveProjectSettings,
    EffectiveUserSettings,
    GlobalSettingsResponse,
    GlobalSettingsUpdate,
    ModelsResponse,
    ProjectSettingsUpdate,
    UserPreferencesUpdate,
)
from src.models.user import UserSession
from src.services import settings_store as _settings_store
from src.services.activity_logger import log_event
from src.services.database import get_db
from src.services.model_fetcher import get_model_fetcher_service
from src.services.settings_store import (
    get_effective_project_settings,
    get_effective_user_settings,
    get_global_settings,
)

# Wrap settings_store helpers whose signatures use bare ``dict`` so the strict
# floor sees concrete dict[str, Any] arguments/results.
flatten_global_settings_update: Callable[[dict[str, Any]], dict[str, Any]] = cast(
    "Callable[[dict[str, Any]], dict[str, Any]]",
    getattr(_settings_store, "flatten_global_settings_update"),  # noqa: B009 - reason: strict wrapper intentionally binds service helper via getattr for tests
)
flatten_user_preferences_update: Callable[[dict[str, Any]], dict[str, Any]] = cast(
    "Callable[[dict[str, Any]], dict[str, Any]]",
    getattr(_settings_store, "flatten_user_preferences_update"),  # noqa: B009 - reason: strict wrapper intentionally binds service helper via getattr for tests
)
update_global_settings: Callable[
    [aiosqlite.Connection, dict[str, Any]], Awaitable[GlobalSettingsResponse]
] = cast(
    "Callable[[aiosqlite.Connection, dict[str, Any]], Awaitable[GlobalSettingsResponse]]",
    getattr(_settings_store, "update_global_settings"),  # noqa: B009 - reason: strict wrapper intentionally binds service helper via getattr for tests
)
upsert_project_settings: Callable[
    [aiosqlite.Connection, str, str, dict[str, Any]], Awaitable[None]
] = cast(
    "Callable[[aiosqlite.Connection, str, str, dict[str, Any]], Awaitable[None]]",
    getattr(_settings_store, "upsert_project_settings"),  # noqa: B009 - reason: strict wrapper intentionally binds service helper via getattr for tests
)
upsert_user_preferences: Callable[[aiosqlite.Connection, str, dict[str, Any]], Awaitable[None]] = (
    cast(
        "Callable[[aiosqlite.Connection, str, dict[str, Any]], Awaitable[None]]",
        getattr(_settings_store, "upsert_user_preferences"),  # noqa: B009 - reason: strict wrapper intentionally binds service helper via getattr for tests
    )
)

logger = get_logger(__name__)
router = APIRouter()


async def _log_settings_update(
    *,
    db: aiosqlite.Connection,
    session: UserSession,
    project_id: str,
    scope: str,
    entity_id: str,
    changed_fields: list[str],
) -> None:
    """Record a scoped settings update in the activity log."""
    await log_event(
        db,
        event_type="settings",
        entity_type="settings",
        entity_id=entity_id,
        project_id=project_id,
        actor=session.github_username,
        action="updated",
        summary=f"Settings updated: {scope} ({len(changed_fields)} fields changed)",
        detail={
            "scope": scope,
            "changed_fields": changed_fields,
        },
    )


@router.get("/user", response_model=EffectiveUserSettings)
async def get_user_settings(
    session: Annotated[UserSession, Depends(get_session_dep)],
) -> EffectiveUserSettings:
    """Get authenticated user's effective settings (merged with global defaults)."""
    db = get_db()
    return await get_effective_user_settings(db, session.github_user_id)


@router.put("/user", response_model=EffectiveUserSettings)
async def update_user_settings(
    body: UserPreferencesUpdate,
    session: Annotated[UserSession, Depends(get_session_dep)],
) -> EffectiveUserSettings:
    """Update authenticated user's preferences (partial update)."""
    db = get_db()

    # Flatten nested update structure to flat column dict
    flat = flatten_user_preferences_update(body.model_dump(exclude_unset=True))

    if flat:
        await upsert_user_preferences(db, session.github_user_id, flat)
        await _log_settings_update(
            db=db,
            session=session,
            project_id=session.selected_project_id or "",
            scope="user",
            entity_id=session.github_user_id,
            changed_fields=sorted(flat),
        )
        logger.info("Updated user preferences for %s", session.github_username)

    return await get_effective_user_settings(db, session.github_user_id)


@router.get("/global", response_model=GlobalSettingsResponse)
async def get_global_settings_endpoint(
    session: Annotated[UserSession, Depends(get_session_dep)],
) -> GlobalSettingsResponse:
    """Get global/instance-level settings."""
    db = get_db()
    return await get_global_settings(db)


@router.put("/global", response_model=GlobalSettingsResponse)
async def update_global_settings_endpoint(
    body: GlobalSettingsUpdate,
    session: Annotated[UserSession, Depends(require_admin)],
) -> GlobalSettingsResponse:
    """Update global/instance-level settings (partial update). Requires admin."""
    db = get_db()

    flat = flatten_global_settings_update(body.model_dump(exclude_unset=True))

    if flat:
        result = await update_global_settings(db, flat)
        await _log_settings_update(
            db=db,
            session=session,
            project_id=session.selected_project_id or "",
            scope="global",
            entity_id="global",
            changed_fields=sorted(flat),
        )
        logger.info("Updated global settings by %s", session.github_username)
        return result

    return await get_global_settings(db)


@router.get(
    "/project/{project_id}",
    response_model=EffectiveProjectSettings,
    dependencies=[Depends(verify_project_access)],
)
async def get_project_settings_endpoint(
    project_id: str,
    session: Annotated[UserSession, Depends(get_session_dep)],
) -> EffectiveProjectSettings:
    """Get per-project effective settings for authenticated user."""
    db = get_db()
    return await get_effective_project_settings(db, session.github_user_id, project_id)


@router.put(
    "/project/{project_id}",
    response_model=EffectiveProjectSettings,
    dependencies=[Depends(verify_project_access)],
)
async def update_project_settings_endpoint(
    project_id: str,
    body: ProjectSettingsUpdate,
    session: Annotated[UserSession, Depends(get_session_dep)],
) -> EffectiveProjectSettings:
    """Update per-project settings for authenticated user (partial update)."""
    db = get_db()

    updates: dict[str, Any] = {}
    update_data = body.model_dump(exclude_unset=True)

    if "board_display_config" in update_data:
        val = update_data["board_display_config"]
        updates["board_display_config"] = json.dumps(val) if val is not None else None

    if "agent_pipeline_mappings" in update_data:
        val = update_data["agent_pipeline_mappings"]
        updates["agent_pipeline_mappings"] = json.dumps(val) if val is not None else None

    if "queue_mode" in update_data:
        val = update_data["queue_mode"]
        updates["queue_mode"] = int(val) if val is not None else 0

    if "auto_merge" in update_data:
        val = update_data["auto_merge"]
        updates["auto_merge"] = int(val) if val is not None else 0

    if updates:
        await upsert_project_settings(db, session.github_user_id, project_id, updates)
        await _log_settings_update(
            db=db,
            session=session,
            project_id=project_id,
            scope="project",
            entity_id=project_id,
            changed_fields=sorted(update_data),
        )
        logger.info(
            "Updated project settings for user=%s project=%s",
            session.github_username,
            project_id,
        )

        # Sync agent_pipeline_mappings to the canonical __workflow__ row so the
        # workflow orchestrator picks up the user's configuration.  Also
        # invalidate the in-memory config cache for this project.
        if "agent_pipeline_mappings" in updates:
            workflow_updates: dict[str, Any] = {
                "agent_pipeline_mappings": updates["agent_pipeline_mappings"],
            }
            await upsert_project_settings(db, "__workflow__", project_id, workflow_updates)
            logger.info(
                "Synced agent_pipeline_mappings to __workflow__ canonical row for project=%s",
                project_id,
            )
            # Invalidate in-memory workflow config cache
            try:
                from src.services.workflow_orchestrator import config as _workflow_config_mod

                workflow_configs = cast(
                    "dict[str, Any]",
                    getattr(_workflow_config_mod, "_workflow_configs"),  # noqa: B009 - reason: cache invalidation targets module-level state through getattr for tests
                )
                workflow_configs.pop(project_id, None)
            except Exception as e:  # noqa: BLE001 — reason: best-effort operation; failure logged, execution continues
                logger.debug(
                    "Cache invalidation skipped for project=%s: %s", project_id, e, exc_info=True
                )

        # Sync queue_mode to the canonical __workflow__ row and invalidate cache
        if "queue_mode" in updates:
            workflow_updates = {"queue_mode": updates["queue_mode"]}
            await upsert_project_settings(db, "__workflow__", project_id, workflow_updates)
            # Invalidate the queue mode in-memory cache
            queue_mode_cache = cast(
                "dict[str, Any]",
                getattr(_settings_store, "_queue_mode_cache"),  # noqa: B009 - reason: cache invalidation targets module-level state through getattr for tests
            )
            queue_mode_cache.pop(project_id, None)

        # Sync auto_merge to the canonical __workflow__ row and invalidate cache
        if "auto_merge" in updates:
            workflow_updates = {"auto_merge": updates["auto_merge"]}
            await upsert_project_settings(db, "__workflow__", project_id, workflow_updates)
            # Invalidate the auto merge in-memory cache
            auto_merge_cache = cast(
                "dict[str, Any]",
                getattr(_settings_store, "_auto_merge_cache"),  # noqa: B009 - reason: cache invalidation targets module-level state through getattr for tests
            )
            auto_merge_cache.pop(project_id, None)

    return await get_effective_project_settings(db, session.github_user_id, project_id)


# ── Dynamic Model Fetching ──────────────────────────────────────────────────


@router.get("/models/{provider}", response_model=ModelsResponse)
async def get_models_for_provider(
    provider: str,
    session: Annotated[UserSession, Depends(get_session_dep)],
    force_refresh: bool = Query(False, description="Bypass cache and fetch fresh values"),
) -> ModelsResponse:
    """Fetch available models for a provider.

    Returns cached values when available. Checks authentication prerequisites
    before attempting external fetches.
    """
    # Validate provider
    valid_providers = [p.value for p in AIProvider]
    if provider not in valid_providers:
        return ModelsResponse(
            status="error",
            message=f"Unknown provider: {provider}. Valid providers: {', '.join(valid_providers)}",
        )

    # Use the session's access_token for providers that need auth
    token = session.access_token if session else None

    service = get_model_fetcher_service()
    return await service.get_models(provider, token=token, force_refresh=force_refresh)
