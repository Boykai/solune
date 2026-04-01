# Quickstart: Enrich Activity Page with Meaningful Events

**Feature**: 002-enrich-activity-events
**Date**: 2026-03-31
**Prerequisites**: [plan.md](./plan.md), [data-model.md](./data-model.md), [contracts/](./contracts/)

## Overview

This feature enriches the Activity page by adding ~12 new backend log points across settings, projects, pipelines, orchestrator, and webhooks; a new `GET /activity/stats` endpoint for summary statistics; and frontend enhancements including a stats dashboard header, time-bucketed grouping, status badges, and entity context pills. No database migration is needed — all new event types reuse the existing `activity_events` schema.

## New Files

### 1. `solune/frontend/src/hooks/useActivityStats.ts`

React hook for fetching activity stats from the new `GET /activity/stats` endpoint. Returns `{ stats, isLoading, error }` using the standard SWR/fetch pattern already used by `useActivityFeed`.

## Modified Files

### Backend

### 1. `solune/backend/src/models/activity.py` — Add `ActivityStats` model

Add a new Pydantic model for the stats endpoint response:

```python
class ActivityStats(BaseModel):
    """Response model for activity summary statistics."""

    total_count: int
    today_count: int
    by_type: dict[str, int]
    last_event_at: str | None
```

### 2. `solune/backend/src/services/activity_service.py` — Add `get_activity_stats()`

Add a new function that runs 3 SQL queries to compute stats:

```python
async def get_activity_stats(
    db,
    *,
    project_id: str,
) -> dict:
    """Compute activity summary statistics for a project."""
    # Query 1: Total count + last event timestamp
    row = await db.execute(
        "SELECT COUNT(*), MAX(created_at) FROM activity_events WHERE project_id = ?",
        (project_id,),
    )
    result = await row.fetchone()
    total_count = result[0] if result else 0
    last_event_at = result[1] if result else None

    # Query 2: Last 24h count
    row = await db.execute(
        "SELECT COUNT(*) FROM activity_events WHERE project_id = ? AND created_at >= datetime('now', '-1 day')",
        (project_id,),
    )
    result = await row.fetchone()
    today_count = result[0] if result else 0

    # Query 3: Last 7 days grouped by event_type
    rows = await db.execute(
        "SELECT event_type, COUNT(*) FROM activity_events WHERE project_id = ? AND created_at >= datetime('now', '-7 days') GROUP BY event_type",
        (project_id,),
    )
    results = await rows.fetchall()
    by_type = {row[0]: row[1] for row in results}

    return {
        "total_count": total_count,
        "today_count": today_count,
        "by_type": by_type,
        "last_event_at": last_event_at,
    }
```

### 3. `solune/backend/src/api/activity.py` — Add `GET /activity/stats` route

Add a new route **before** `GET /activity/{entity_type}/{entity_id}` to avoid path conflict:

```python
@router.get("/stats")
async def get_activity_stats(
    request: Request,
    session: Annotated[UserSession, Depends(get_session_dep)],
    project_id: Annotated[str, Query(description="Project ID to scope the stats")],
    db=Depends(get_database),
) -> dict:
    """Activity summary statistics for a project."""
    await verify_project_access(request, project_id, session)
    return await _get_activity_stats(db, project_id=project_id)
```

### 4. `solune/backend/src/api/settings.py` — Add `log_event` calls

In each settings PUT endpoint (user, global, project), add after the update succeeds:

```python
from src.services.activity_logger import log_event

# Compute changed fields by comparing old vs new settings
changed_fields = [f for f in new_settings.model_fields if getattr(new_settings, f) != getattr(old_settings, f)]

await log_event(
    db,
    event_type="settings",
    entity_type="settings",
    entity_id=project_id or scope,
    project_id=project_id,
    actor=session.github_username,
    action="updated",
    summary=f"Settings updated: {scope} ({len(changed_fields)} fields changed)",
    detail={"scope": scope, "changed_fields": changed_fields},
)
```

### 5. `solune/backend/src/api/projects.py` — Add `log_event` calls

In the project creation endpoint, add after project is created:

```python
await log_event(
    db,
    event_type="project",
    entity_type="project",
    entity_id=project_id,
    project_id=project_id,
    actor=session.github_username,
    action="created",
    summary=f"Project created: {project_name}",
    detail={"project_name": project_name},
)
```

In the project selection endpoint, add after project is selected:

```python
await log_event(
    db,
    event_type="project",
    entity_type="project",
    entity_id=project_id,
    project_id=project_id,
    actor=session.github_username,
    action="selected",
    summary=f"Project selected: {project_name}",
    detail={"project_name": project_name},
)
```

### 6. `solune/backend/src/api/pipelines.py` — Add `log_event` for pipeline launch

In `execute_pipeline_launch()`, after issue creation succeeds:

```python
await log_event(
    db,
    event_type="pipeline_run",
    entity_type="pipeline",
    entity_id=pipeline_id,
    project_id=project_id,
    actor=session.github_username,
    action="launched",
    summary=f"Pipeline launched: {pipeline_name} (#{issue_number}, {agent_count} agents)",
    detail={"issue_number": issue_number, "agent_count": agent_count, "pipeline_name": pipeline_name},
)
```

### 7. `solune/backend/src/services/workflow_orchestrator/orchestrator.py` — Add `log_event` calls

In `handle_completion()`, after workflow is marked complete:

```python
await log_event(
    db,
    event_type="agent_execution",
    entity_type="pipeline",
    entity_id=pipeline_id,
    project_id=project_id,
    actor="system",
    action="completed",
    summary=f"Workflow completed: {pipeline_name}",
    detail={"workflow_id": workflow_id, "pipeline_name": pipeline_name},
)
```

In `assign_agent_for_status()`, when an agent is triggered:

```python
await log_event(
    db,
    event_type="agent_execution",
    entity_type="agent",
    entity_id=agent_name,
    project_id=project_id,
    actor="system",
    action="triggered",
    summary=f"Agent triggered: {agent_name} for status {status}",
    detail={"agent_name": agent_name, "status": status},
)
```

### 8. `solune/backend/src/api/webhooks.py` — Enrich webhook logging

Replace the existing generic `action="received"` with classified actions:

```python
# Determine specific webhook action
if webhook_type == "pull_request":
    pr_data = payload.get("pull_request", {})
    if payload.get("action") == "closed" and pr_data.get("merged"):
        webhook_action = "pr_merged"
    elif pr_data.get("head", {}).get("ref", "").startswith("copilot/"):
        webhook_action = "copilot_pr_ready"
    else:
        webhook_action = payload.get("action", "received")
else:
    webhook_action = payload.get("action", "received")

await log_event(db, ..., action=webhook_action, ...)
```

### Frontend

### 9. `solune/frontend/src/services/api.ts` — Add `stats()` method

```typescript
export const activityApi = {
  // ... existing methods ...
  stats(projectId: string): Promise<ActivityStats> {
    return apiClient.get(`/activity/stats`, { params: { project_id: projectId } });
  },
};
```

### 10. `solune/frontend/src/types/index.ts` — Add `ActivityStats` type

```typescript
export interface ActivityStats {
  total_count: number;
  today_count: number;
  by_type: Record<string, number>;
  last_event_at: string | null;
}
```

### 11. `solune/frontend/src/pages/ActivityPage.tsx` — Enrich Activity page

Key changes:
- Add "Project" and "Execution" to `EVENT_CATEGORIES`
- Import and render stats dashboard (4 cards) above filter chips
- Add time-bucketed grouping with sticky headers
- Add color-coded action badges and entity-type pills to event rows

## Implementation Order

1. **Add `ActivityStats` model** to `models/activity.py`
2. **Add `get_activity_stats()`** to `activity_service.py`
3. **Add `GET /activity/stats` route** to `api/activity.py`
4. **Add backend tests** for stats endpoint in `test_api_activity.py`
5. **Add `log_event` to settings** endpoints in `api/settings.py`
6. **Add `log_event` to projects** endpoints in `api/projects.py`
7. **Add `log_event` for pipeline launch** in `api/pipelines.py`
8. **Add `log_event` for orchestrator** events in `orchestrator.py`
9. **Enrich webhook logging** in `api/webhooks.py`
10. **Add `ActivityStats` type** to frontend `types/index.ts`
11. **Add `activityApi.stats()`** to frontend `api.ts`
12. **Create `useActivityStats` hook** in frontend `hooks/`
13. **Add stats dashboard** to `ActivityPage.tsx`
14. **Add new filter categories** ("Project", "Execution") to `ActivityPage.tsx`
15. **Add time-bucketed grouping** to `ActivityPage.tsx`
16. **Add action badges and entity pills** to `ActivityPage.tsx`
17. **Add frontend tests** for stats, time bucketing, and categories

## Verification

After implementation, verify each component:

```bash
# Run backend unit tests (stats endpoint + existing activity tests)
cd solune/backend
uv run pytest tests/unit/test_api_activity.py -q

# Run full backend test suite
uv run pytest tests/unit/ -q --tb=short

# Lint backend
.venv/bin/ruff check src/api/activity.py src/api/settings.py src/api/projects.py src/api/pipelines.py src/api/webhooks.py src/services/activity_service.py src/services/workflow_orchestrator/orchestrator.py src/models/activity.py
.venv/bin/ruff format --check src tests
uv run pyright src

# Frontend tests
cd solune/frontend
npm test

# Integration verification (Docker)
# docker compose up → Activity page shows stats header
# Trigger pipeline run → "launched" event appears
# Change settings → "settings" event logged
# Empty state → stat cards show 0 and "No activity"
```

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| No database migration | New event types are stored as new string values in existing columns (FR-016) |
| Server-side SQL stats | Efficient aggregation on indexed columns; client-side would require fetching all events (FR-009) |
| Three separate SQL queries for stats | Clearer and more maintainable than complex CTE/UNION; marginal performance difference at expected scale |
| Stats route before entity history route | FastAPI matches routes in declaration order; prevents "stats" being captured as entity_type |
| Frontend-only time bucketing | Grouping is visual; applied to paginated results so performance is bounded by page size |
| No charting library | Stats as number cards matches existing PipelineAnalytics pattern; avoids new dependency |
| Fire-and-forget logging | Uses existing `log_event` pattern; never blocks primary operations |
| Changed fields in settings detail | Provides audit trail without storing full before/after snapshots |
