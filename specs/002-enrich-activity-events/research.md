# Research: Enrich Activity Page with Meaningful Events

**Feature**: 002-enrich-activity-events
**Date**: 2026-03-31
**Status**: Complete

## Research Tasks

### RT-001: Activity Logger Integration Pattern for New Event Points

**Context**: The spec requires ~12 new `log_event` calls across 5 backend files (settings, projects, pipelines, orchestrator, webhooks). Need to confirm the existing `log_event` pattern and determine how to integrate into each endpoint consistently.

**Decision**: Use the existing fire-and-forget `log_event()` from `src/services/activity_logger.py` at all new call sites. The function signature is `log_event(db, *, event_type, entity_type, entity_id, project_id, actor, action, summary, detail)`. It never raises — all exceptions are caught and logged. Each call is a simple one-liner inserted after the primary operation succeeds.

**Rationale**: The `log_event` function is already used across `pipelines.py` (5 call sites), `webhooks.py` (1 call site), and `orchestrator.py` (1 call site). The pattern is well-established: call after the primary operation, pass structured detail as a dict, use `actor=session.github_username` for user-initiated events or `actor="system"` for automated events. No wrapper or abstraction needed.

**Alternatives considered**:
- **Decorator-based logging**: Would require refactoring endpoint functions; adds indirection; different endpoints need different event_type/action combinations. Rejected per Constitution Principle V (Simplicity).
- **Event bus / pub-sub**: Over-engineered for fire-and-forget inserts; adds framework complexity and failure modes. The current inline pattern is simpler and more debuggable.
- **Background task queue**: Unnecessary — `log_event` already commits immediately and catches all exceptions. Adding a task queue would increase latency and complexity for zero benefit at this scale.

---

### RT-002: Stats Endpoint SQL Aggregation Strategy

**Context**: The spec requires a `GET /activity/stats` endpoint returning total count, last-24h count, event counts grouped by type for last 7 days, and last event timestamp. Need to determine the SQL approach.

**Decision**: Use three SQL queries within a single `get_activity_stats()` function in `activity_service.py`:
1. `SELECT COUNT(*), MAX(created_at) FROM activity_events WHERE project_id = ?` — total count + last event timestamp
2. `SELECT COUNT(*) FROM activity_events WHERE project_id = ? AND created_at >= ?` — last-24h count (using `datetime('now', '-1 day')`)
3. `SELECT event_type, COUNT(*) FROM activity_events WHERE project_id = ? AND created_at >= ? GROUP BY event_type` — last-7d breakdown (using `datetime('now', '-7 days')`)

**Rationale**: SQLite handles these queries efficiently with the existing `idx_activity_project_time` index on `(project_id, created_at DESC)`. Three simple queries are clearer and more maintainable than a single complex CTE or UNION query. At the expected event volume (hundreds to low thousands per project), query time will be well under 2 seconds (SC-002).

**Alternatives considered**:
- **Single CTE/subquery**: More compact SQL but harder to read, debug, and maintain. Marginal performance benefit at this scale.
- **Materialized view / cache**: Premature optimization; SQLite aggregation on indexed columns is fast enough. Rejected per YAGNI (Constitution Principle V).
- **Client-side aggregation**: Explicitly rejected by spec (FR-009 mandates server-side SQL aggregation). Would require fetching all events to the client.

---

### RT-003: Stats Endpoint Route Placement

**Context**: The existing activity API has `GET /activity` (feed) and `GET /activity/{entity_type}/{entity_id}` (entity history). A new `GET /activity/stats` route must be added without conflicting with the `{entity_type}` path parameter.

**Decision**: Place the `GET /activity/stats` route **before** the `GET /activity/{entity_type}/{entity_id}` route in the FastAPI router definition. FastAPI matches routes in declaration order, so "stats" will be matched as a literal path before being captured as an `entity_type` parameter.

**Rationale**: This is the standard FastAPI pattern for mixing literal and parameterized paths. No router restructuring needed — just add the new route above the existing entity history route.

**Alternatives considered**:
- **Separate router prefix** (`/activity-stats`): Breaks REST convention; activity stats are logically part of the activity resource.
- **Query parameter approach** (`GET /activity?mode=stats`): Overloads the existing feed endpoint; mixes paginated list and aggregation responses.
- **Add "stats" to ALLOWED_ENTITY_TYPES**: Would conflict semantically and break the entity history contract.

---

### RT-004: Webhook Action Classification

**Context**: The spec requires distinguishing `action="pr_merged"` and `action="copilot_pr_ready"` instead of generic `action="received"` for webhook events (FR-007).

**Decision**: Inspect the webhook payload in `api/webhooks.py` to classify the action:
- For `pull_request` events: check `payload["action"]` — if `"closed"` and `payload["pull_request"]["merged"]` is true, log `action="pr_merged"`
- For `pull_request` events with a Copilot-authored PR (check `payload["pull_request"]["user"]["login"]` contains "copilot" or `payload["pull_request"]["head"]["ref"]` starts with "copilot/"): log `action="copilot_pr_ready"`
- For all other webhook events: fall back to `action="received"`

**Rationale**: GitHub webhook payloads include all the data needed for classification. The PR merge detection is standard (`action=closed` + `merged=true`). Copilot PR detection uses branch naming convention (`copilot/` prefix) which is the pattern already used by the Solune orchestrator for Copilot-authored branches.

**Alternatives considered**:
- **Separate webhook handler per type**: Over-engineered; the current single handler with conditional logic is simpler and matches existing code structure.
- **External webhook classification service**: Unnecessary indirection for a simple conditional check.
- **Label/tag-based classification**: Requires additional GitHub API calls; the payload already contains sufficient information.

---

### RT-005: Frontend Time-Bucketed Grouping Implementation

**Context**: The spec requires grouping events into "Today", "Yesterday", "This Week", "Earlier" with sticky section headers (FR-012). This is frontend-only, no backend change.

**Decision**: Implement a pure utility function `groupEventsByTimeBucket(events: ActivityEvent[])` that categorizes events based on their `created_at` timestamp relative to the current date. Apply this grouping to the paginated result set in `ActivityPage.tsx`. Use CSS `position: sticky` for section headers.

**Rationale**: Client-side grouping on the paginated result set is bounded by page size (default 50 events), so performance is not a concern. A pure utility function is easily testable. Sticky headers use native CSS with no library needed.

**Alternatives considered**:
- **Backend grouping via SQL**: Adds backend complexity for a purely visual feature; would require a new response format. Spec explicitly states "frontend-only, no backend change."
- **Virtual scrolling library**: Unnecessary at current scale (50 items per page); adds a dependency for minimal benefit.
- **Date header component library**: No suitable lightweight option; CSS sticky + a simple header component is sufficient.

---

### RT-006: Stats Dashboard Card Pattern

**Context**: The spec calls for 4 stat cards ("Total Events", "Today", "Most Common", "Last Activity") following the "moonwell stat-box pattern from CelestialCatalogHero" (FR-010).

**Decision**: Render a responsive grid of 4 stat cards above the filter chips in `ActivityPage.tsx`. Each card shows a label, a primary value (number or text), and an optional subtitle. Use the existing TailwindCSS utility classes for styling, matching the stat-box pattern already used in the application (grid layout, rounded cards, consistent padding/typography).

**Rationale**: Number cards are simpler than charts and match the existing `PipelineAnalytics` pattern. No charting library is needed (explicit design decision in the spec). The existing design system provides all the styling primitives needed.

**Alternatives considered**:
- **Charting library (recharts, chart.js)**: Explicitly excluded by spec. Adds a dependency for a feature that shows 4 numbers.
- **Separate stats page/tab**: Fragments the user experience; the spec explicitly places stats above the event list for at-a-glance monitoring.
- **Server-sent events for live stats**: Over-engineered; stats are a snapshot at page load time. Refreshing on tab focus is sufficient.

---

### RT-007: Action Badge and Entity Pill Color Mapping

**Context**: The spec requires color-coded action badges (green=created, red=deleted, blue=updated, purple=started/launched/triggered) and entity-type pills (FR-013, FR-014).

**Decision**: Define a static mapping from action strings to badge colors and from entity_type strings to pill labels:

Action badge colors:
- `created` → green (`bg-green-100 text-green-800`)
- `deleted` → red (`bg-red-100 text-red-800`)
- `updated` → blue (`bg-blue-100 text-blue-800`)
- `launched`, `triggered`, `started`, `completed` → purple (`bg-purple-100 text-purple-800`)
- Default/other → gray (`bg-gray-100 text-gray-800`)

Entity pills: Display the `entity_type` value (e.g., "pipeline", "agent", "settings") in a neutral pill badge next to the event summary.

**Rationale**: Static mapping is simple, deterministic, and requires no external configuration. TailwindCSS color utilities are already available. The color scheme follows the spec requirements exactly and provides sufficient visual distinction.

**Alternatives considered**:
- **Dynamic color generation from hash**: Non-deterministic; same action could render differently. Harder to maintain accessibility contrast ratios.
- **Icon-only badges (no text)**: Less accessible; users need to learn icon meanings. Text badges are more immediately understandable.
- **Theme-aware color tokens**: Adds complexity; the application currently uses direct Tailwind classes. Can be refactored later if a theme system is added.

---

### RT-008: Settings Change Detection for Detail Logging

**Context**: The spec requires logging which fields were changed when settings are updated (FR-004). Settings endpoints accept the full settings object on PUT.

**Decision**: In each settings PUT endpoint handler, compare the incoming request body against the current stored settings before applying the update. Compute a `changed_fields` list of field names where values differ. Pass this list in the `detail` dict of the `log_event` call. For no-op saves (zero changed fields), still log the event with an empty `changed_fields` list (per spec edge case).

**Rationale**: Field-level diff is straightforward with Pydantic models — iterate over fields and compare values. This provides the audit trail required by FR-004 without storing full before/after snapshots (which would bloat the detail JSON).

**Alternatives considered**:
- **Store full before/after in detail**: More complete audit trail but significantly increases storage per event. Field names are sufficient for the stated use case.
- **Skip logging on no-op saves**: The spec explicitly states no-op saves should still be logged with empty changed-fields list.
- **Database trigger for change detection**: SQLite triggers are harder to maintain and debug; application-level detection is more transparent and testable.

---

### RT-009: New Event Type and Category Mapping

**Context**: Need to define the new event_type string values and map them to frontend filter categories. Must not break existing event types.

**Decision**: New event_type values added to the existing string-based schema:
- `"settings"` — for user/global/project settings changes (maps to "Project" category)
- `"project"` — for project creation/selection (maps to "Project" category)

Existing event types enriched with new actions:
- `"pipeline_run"` — existing, add `action="launched"` (maps to existing "Pipeline" category)
- `"webhook"` — existing, add `action="pr_merged"` and `action="copilot_pr_ready"` (maps to existing "Webhook" category)

Orchestrator events use existing `"agent_execution"` type with new actions:
- `action="completed"` for workflow completion
- `action="triggered"` for agent execution start

Frontend category additions:
- **"Project"** category: types `["project", "settings"]`
- **"Execution"** category: types `["agent_execution"]` (already partially covered by "Agent" but this provides a dedicated filter)

**Rationale**: Reusing the existing string-based `event_type` column avoids database migration (FR-016). New string values are additive — existing queries and filters continue to work unchanged. Category mapping is frontend-only configuration.

**Alternatives considered**:
- **Enum constraint on event_type column**: Would require a migration for every new event type. The string-based approach is more flexible.
- **Hierarchical event types** (e.g., "pipeline.launched"): Adds parsing complexity; flat strings are simpler and match existing convention.
- **Separate category column**: Redundant with event_type; categories are a UI concern, not a data concern.
