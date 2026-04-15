# Data Model: Loading Performance

**Feature**: Loading Performance | **Date**: 2026-04-15 | **Status**: Complete

## Entity: BoardLoadPolicy

Defines how a board request should behave for a specific trigger.

### Fields

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `trigger` | `enum` (`initial`, `refresh`, `background`, `selection_warmup`) | Required | Why the board load is running. |
| `include_done_sub_issues` | `bool` | Required | Whether Done/closed parent issues should fetch fresh sub-issue metadata. |
| `run_reconciliation_inline` | `bool` | Required | Whether reconciliation runs before the response is returned. |
| `allow_cached_done_items` | `bool` | Required | Whether existing Done-item persistence may be used to render historical items/pills. |
| `allow_background_completion` | `bool` | Required | Whether remaining work may continue after the initial payload is available. |

### Usage

- `initial` and `selection_warmup` policies optimize for interactivity.
- `refresh` optimizes for completeness and cache refresh.
- `background` finishes deferred work (Done/history backfill and reconciliation) after the board is interactive.

---

## Entity: BoardLoadState

Response metadata that tells the frontend what portion of the board is ready and what work is still pending.

### Fields

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `project_id` | `string` | Required | Target project. |
| `phase` | `enum` (`interactive`, `backfilling_done`, `reconciling`, `complete`) | Required | Current board-load phase visible to the UI. |
| `active_columns_ready` | `bool` | Required | True when non-Done columns are safe to render and interact with. |
| `done_column_source` | `enum` (`live`, `cached`, `pending`) | Required | Where Done/history content came from for the current payload. |
| `pending_sections` | `string[]` | Optional | Human-readable sections still loading, such as `done_column` or `reconciliation`. |
| `last_completed_at` | `datetime` | Optional | Most recent time a full-fidelity board snapshot completed. |
| `warmed_by_selection` | `bool` | Required | Whether the payload came from a selection-triggered warm-up path. |

### Relationships

- `BoardLoadState` is attached to the board response returned by `GET /board/projects/{project_id}`.
- `ProjectsPage` / `useProjectBoard()` consume it to decide whether to show the subtle Done-progress indicator or treat the board as fully complete.

---

## Entity: DoneBoardSnapshot

Represents the already-existing persisted Done/history board data reused by the optimization.

### Fields

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `project_id` | `string` | Required | Project owner for the cached Done payload. |
| `item_type` | `"board"` | Existing constant | Uses the current `done_items_store` record type. |
| `items_json` | `json` | Existing persisted payload | Serialized Done `BoardItem` data, including any stored sub-issue pills. |
| `item_count` | `int` | `>= 0` | Count of persisted Done items. |
| `data_hash` | `string` | Existing SHA-256 hash | Used to detect changes and avoid unnecessary cache churn. |
| `updated_at` | `datetime` | Existing field | Freshness indicator for stale fallback / background refresh. |

### Validation Rules

- No new schema is required; the optimization reuses the existing store.
- Manual full refresh updates this snapshot after live Done/history refresh completes.
- Initial loads may serve this snapshot while live Done/history work is still pending.

---

## Entity: InFlightLoadKey

Tracks coalesced work so concurrent requests can wait on the same result instead of starting duplicate upstream calls.

### Fields

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `scope` | `enum` (`projects`, `board_projects`, `board_data`, `selection_warmup`) | Required | The category of request being deduplicated. |
| `cache_key` | `string` | Required | Stable identifier for the underlying fetch. |
| `project_id` | `string?` | Optional | Included for board and warm-up paths. |
| `session_user_id` | `string?` | Optional | Included for user-scoped list fetches. |
| `started_at` | `datetime` | Required | When the shared task began. |
| `waiter_count` | `int` | `>= 1` | Number of callers sharing the same task. |

### Relationships

- `InFlightLoadKey` complements the existing GraphQL coalescing in `GitHubProjectsService._graphql()`.
- The API layer uses it to ensure concurrent HTTP requests share warmed/list results before deciding to hit GitHub again.

---

## Entity: DeferredBoardTask

Describes post-interactive work spawned from the initial load.

### Fields

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `project_id` | `string` | Required | Target project. |
| `task_type` | `enum` (`done_backfill`, `reconciliation`, `polling_resume`) | Required | The deferred action to run. |
| `origin` | `enum` (`initial_load`, `selection_warmup`, `manual_refresh`) | Required | Where the deferred task was created. |
| `status` | `enum` (`scheduled`, `running`, `completed`, `cancelled`, `failed`) | Required | Lifecycle state. |
| `superseded_by_project_id` | `string?` | Optional | Populated when a rapid project switch cancels stale work. |
| `completed_at` | `datetime?` | Optional | Terminal timestamp. |

### State Transitions

```text
scheduled -> running -> completed
scheduled -> cancelled
running -> cancelled
running -> failed
failed -> scheduled  (retry path, if background refresh is retried)
```

The important transition for this feature is cancellation/supersession when the user switches projects before background completion finishes.
