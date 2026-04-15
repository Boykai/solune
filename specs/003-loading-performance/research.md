# Research: Loading Performance

**Feature**: Loading Performance | **Date**: 2026-04-15 | **Status**: Complete

## R1: Initial Board Load Shape

**Decision**: Keep `GET /api/v1/board/projects/{project_id}` as the single board-read endpoint, but split its behavior into an interactive initial phase and deferred background phases.

**Rationale**: The existing frontend already depends on `useProjectBoard()` and `boardApi.getBoardData()` for both the first load and later polling. Reusing the same endpoint avoids adding a second transport or a new client state machine. The performance problem lives inside the backend sequencing of pagination, sub-issue fetches, and reconciliation, so changing the internal phases is lower risk than redesigning the API surface.

**Alternatives considered**:

| Alternative | Why Rejected |
|-------------|-------------|
| Add a brand-new `/board/projects/{id}/initial` endpoint | Splits board state across two read paths and forces extra frontend orchestration for little gain. |
| Use SSE/WebSocket streaming for initial board hydration | More complex than needed for the quick-win scope described in the issue; existing polling/query invalidation can merge deferred data later. |
| Keep the current monolithic `get_board_data()` flow | Leaves pagination, sub-issue fetches, and reconciliation on the critical path, which is the core performance problem. |

---

## R2: Done/Closed Sub-Issue Strategy

**Decision**: Skip fresh sub-issue fetches for Done-column or closed parent issues during initial load, and render their pills from existing stored/cached data until a manual full refresh or reactivation requires a fresh fetch.

**Rationale**: The specification explicitly states that sub-issue metadata is not displayed in the board UX beyond pill links, and the live backend already persists Done items in `done_items_store` plus per-parent sub-issue caches. That existing persistence is enough to preserve user-visible behavior without paying the high N+1 cost for historical items that rarely change. The manual refresh path remains the correctness backstop for rare Done/closed changes.

**Alternatives considered**:

| Alternative | Why Rejected |
|-------------|-------------|
| Continue fetching all Done/closed sub-issues on every load | Directly contradicts the performance analysis and keeps the dominant large-board bottleneck in place. |
| Stop showing Done-column pills entirely | Violates the spec requirement to preserve existing board behavior. |
| Add a new database table just for Done sub-issue metadata | Unnecessary because existing Done-item and sub-issue cache mechanisms already exist. |

---

## R3: Reconciliation Timing

**Decision**: Defer reconciliation until after the first interactive board payload has been returned and cached, then merge any reconciled items back into the board through the existing refresh/query mechanisms.

**Rationale**: The current board service performs reconciliation synchronously even though the issue analysis shows it often finds zero items and still costs hundreds of milliseconds. Reconciliation is valuable for correctness, but it is not required before users can start interacting with active work. Running it immediately after the board becomes interactive preserves eventual correctness without blocking the initial response.

**Alternatives considered**:

| Alternative | Why Rejected |
|-------------|-------------|
| Keep reconciliation inline but parallelize it harder | Still pays the reconciliation cost before first paint and does not solve the user-perceived delay. |
| Remove reconciliation completely | Risks losing items because the GitHub Projects eventual-consistency gap is already documented in the code. |
| Only reconcile on manual refresh | Makes data completeness depend on a user action instead of preserving automatic background correctness. |

---

## R4: Project Selection Warm-Up

**Decision**: Start a best-effort board warm-up task during `POST /api/v1/projects/{project_id}/select`, but keep the selection response itself lightweight and never block it on the warm-up result.

**Rationale**: The frontend currently selects a project and then separately requests board data. Pre-warming the board cache as part of selection lets the subsequent board request arrive against already-started work, shaving cold-start latency without changing the user flow. Because selection is on the critical path too, the warm-up must be fire-and-forget and cancellable/supersedable when the selected project changes.

**Alternatives considered**:

| Alternative | Why Rejected |
|-------------|-------------|
| Do nothing and wait for the first board GET | Leaves a known quick win unused and forces the board request to start from a cold cache every time. |
| Block `select_project()` until the board is fully loaded | Moves the same work to an earlier endpoint without reducing user-visible latency. |
| Warm every project in the user’s list proactively | Wastes GitHub API quota and work on projects the user may never open. |

---

## R5: Request Deduplication Scope

**Decision**: Reuse the existing GraphQL in-flight coalescing in `github_projects/service.py`, then add request-level coalescing only around the remaining cold-start hotspots: project list reads, board-project list reads, and selection-triggered board warm-up.

**Rationale**: The live code already avoids some duplicate GraphQL work, and recent fixes have removed one select-path duplicate plus shared `GET /projects` and `GET /board/projects` upstream calls. The remaining improvement opportunity is at the API/cache orchestration layer, where multiple concurrent HTTP requests can still independently decide to fetch or warm the same data. Limiting the scope to known hotspots keeps the solution small and testable.

**Alternatives considered**:

| Alternative | Why Rejected |
|-------------|-------------|
| Add a generic dedup layer around every backend function | Too broad for the issue scope and increases the chance of accidental stale-result coupling. |
| Rely only on TanStack Query deduplication in the browser | Does not help backend cold-start races, cross-route requests, or simultaneous `/projects` and `/board/projects` calls. |
| Ignore dedup because recent fixes already helped | The issue still calls out duplicate project-list work and cold-start contention, so the plan needs explicit regression-proofing here. |
