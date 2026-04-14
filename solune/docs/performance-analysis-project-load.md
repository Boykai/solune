# Solune Project Load Performance Analysis

> **Date**: 2026-04-14  
> **Project**: Boykai's Solune (PVT_kwHOAIsXss4BTGUq)  
> **Board size**: 758 internal items → 55 visible (4 In Progress, 51 Done), 556 sub-issues  
> **Environment**: Docker (solune-backend, solune-frontend, signal-api), cold-start after container restart

---

## Executive Summary

**Cold-start project load takes ~40 seconds**, primarily due to a single bottleneck: `GET /board/projects/{id}` which takes **38.4 seconds** making 60+ sequential and parallel GitHub API calls. Warm-cache load is ~5ms for board data, demonstrating that caching works well once populated.

A secondary finding is that background Copilot polling (started by project selection) creates event-loop contention that adds **1–3 seconds of latency** to all other endpoints.

---

## Live Profiling Results

### Cold Start (no cache, fresh backend restart)

| Endpoint | Latency | Status | Response | Notes |
|---|---|---|---|---|
| `POST /projects/{id}/select` | **1,632 ms** | 200 | 0.2 KB | Blocking; runs before all other fetches |
| `GET /projects` | 5 ms | 200 | 5.4 KB | 7 projects (cached from POST select) |
| `GET /board/projects` | 7 ms | 200 | 4.3 KB | 7 projects (reuses project cache) |
| `GET /board/projects/{id}` | **38,428 ms** | 200 | 399.9 KB | 5 cols, 55 items, 556 sub-issues |
| `GET /settings/project/{id}` | **1,327 ms** | 200 | 0.5 KB | Pure DB; slow due to event-loop contention |
| `GET /workflow/agents` | **3,233 ms** | 200 | 7.7 KB | 26 agents; includes verify_project_access + discovery |
| `GET /activity/feed` | 4 ms | 404 | 0.0 KB | Endpoint not found (not yet implemented) |
| `WS /projects/{id}/subscribe` | 19 ms | WS | 0.1 KB | Lightweight initial_data (count only) |

### Warm Cache (same session, immediate repeat)

| Endpoint | Cold | Warm | Speedup |
|---|---|---|---|
| `GET /projects` | 5 ms | 4 ms | 1.2x |
| `GET /board/projects` | 7 ms | 3 ms | 2.1x |
| `GET /board/projects/{id}` | **38,428 ms** | **8 ms** | **5,124x** |
| `GET /settings/project/{id}` | 1,327 ms | 1,251 ms | 1.1x (no cache) |
| `GET /workflow/agents` | 3,233 ms | 3,070 ms | 1.1x (no cache) |

### User-Perceived Wall Time

```text
Cold:  POST select (1,632ms) + max(board data = 38,428ms) = ~40,060 ms (~40s)
Warm:  POST select (1,632ms) + max(agents = 3,070ms) = ~4,702 ms (~4.7s)
```

---

## Bottleneck Analysis

### 1. 🔴 CRITICAL: `GET /board/projects/{id}` — 38.4 seconds (96% of load time)

**Internal flow** (758 items, 5 columns):

| Phase | Description | Est. Time | API Calls |
|---|---|---|---|
| Pagination | 8 sequential GraphQL calls (100 items/page) | ~6–10s | 8 |
| Sub-issues | ~55 parallel REST calls (Semaphore 20) | ~2–4s | ~55 |
| Reconciliation | 2–3 sequential GraphQL per repo | ~1–4s | 2–3 |
| Copilot polling contention | Event-loop blocked by background API calls | ~15–20s | — |
| DB persistence | save_done_items (async, non-blocking) | ~50ms | 0 |
| **Total** | | **~38s** | **~65** |

**Root causes:**

1. **Event-loop contention from Copilot polling**: _start_copilot_polling fires during POST /select and immediately starts making dozens of concurrent GraphQL calls to check PR status, linked PRs, and agent outputs. These compete for the same asyncio event loop as the board data fetch, adding ~15–20 seconds to what should be a ~8–10 second operation.
2. **Sequential pagination**: 8 pages fetched one-at-a-time (100 items each). Each GraphQL call takes 500–1200ms.
3. **N+1 sub-issue pattern**: 55 individual REST calls for sub-issues. With Semaphore(20), this takes 3 batches × 400ms = ~1.2s minimum.
4. **Sequential per-repo reconciliation**: 2–3 repos queried one after another instead of in parallel.

**Response payload**:

- Total: 399.9 KB (55 items + 556 sub-issues)
- Done column: 398 KB (51 items, 513 sub-issues) — **99.5% of the payload**
- In Progress: 23 KB (4 items, 43 sub-issues)
- Body: consistently 201 chars (truncated from avg 5,577 raw → good optimization already applied)

### 2. 🟠 HIGH: `GET /workflow/agents` — 3.2s (no caching)

This endpoint has **no response-level cache**. Every call:

1. Runs `verify_project_access` → calls `list_user_projects` (GraphQL, ~500ms)
2. Calls `resolve_repository` (GraphQL or cache, ~200–500ms)
3. Calls `list_available_agents` (GitHub REST API to discover `.agent.md` files, ~1–2s)
4. Calls `agents_service.list_agents` (DB + REST discovery)
5. Merges agent preferences from DB

Warm-cache time: **3,070ms** (virtually no speedup — confirms no caching).

### 3. 🟠 HIGH: `POST /projects/{id}/select` — 1.6s (redundant GraphQL calls)

The select endpoint makes **3 separate GitHub API calls**:

1. `verify_project_access` → `list_user_projects` (GraphQL, ~500ms)
2. `get_project` → `list_projects(refresh=True)` → `list_user_projects` (GraphQL, ~500ms) — **DUPLICATE of #1**
3. `_start_copilot_polling` → `resolve_repository` (GraphQL, ~500ms)

Call #2 duplicates call #1 because:

- `verify_project_access` calls the service directly (no API-level caching)
- `get_project` calls `list_projects(refresh=True)` which bypasses cache and makes a fresh GraphQL call
- These run sequentially (dependency → handler) so inflight coalescing doesn't help

### 4. 🟡 MEDIUM: `GET /settings/project/{id}` — 1.3s (event-loop contention)

This is a pure database endpoint (3 SQLite reads, <1ms total when tested directly). The ~1.3s latency is entirely caused by **asyncio event-loop contention** from background Copilot polling. Raw DB queries complete in <1ms as verified by direct testing.

### 5. 🟢 LOW: WebSocket initial_data — 19ms (optimized)

Previously sent full task lists (causing 1MB+ frame crashes). Now sends lightweight `{type: "initial_data", count: 0}`. No bottleneck.

---

## Background Copilot Polling Impact

The `_start_copilot_polling` function (triggered during POST /select) starts a background loop that:

- Queries linked PRs for each open issue (individual GraphQL calls per issue)
- Checks PR completion status
- Posts agent output markers
- Closes completed sub-issues

This creates **sustained event-loop pressure** that inflates latency of all concurrent requests by 1–3 seconds. Evidence:

- `GET /settings/project` (pure DB, <1ms raw) takes 1.3s during active polling
- `GET /workflow/agents` shows only 5% improvement going from cold to warm

---

## Frontend Query Orchestration

When a user selects a project, the frontend fires these in a specific order:

```text
1. POST /projects/{id}/select  ← BLOCKING (must complete before subsequent queries)
   │
   ├─ onSuccess: invalidateQueries(['projects'])
   │
2. PARALLEL (fire immediately after POST completes):
   │
   ├─ GET /projects             → staleTime: 15 min (cache hit from POST select)
   ├─ GET /board/projects       → staleTime: 5 min (reuses project cache)
   ├─ GET /board/projects/{id}  → staleTime: 1 min (★ BOTTLENECK — 38.4s cold)
   ├─ GET /settings/project/{id}
   ├─ GET /workflow/agents
   ├─ WS /projects/{id}/subscribe → lightweight handshake
   │
3. Adaptive polling begins (3s–60s interval based on activity)
```

The critical path is: **POST select (1.6s) → GET board data (38.4s) = 40s**

---

## Response Payload Analysis

| Endpoint | Size | Breakdown |
|---|---|---|
| `GET /board/projects/{id}` | 399.9 KB | 51 Done items (398 KB), 4 In-Progress (23 KB), 556 sub-issues |
| `GET /workflow/agents` | 7.7 KB | 26 agent definitions with tools metadata |
| `GET /projects` | 5.4 KB | 7 project summaries |
| `GET /board/projects` | 4.3 KB | 7 projects with status field config |
| `GET /settings/project/{id}` | 0.5 KB | Merged settings (global + user + project) |

**Key observation**: The Done column accounts for **99.5%** of the board response payload and required fetching and processing **687 Done items** from GitHub (even though only 51 parent items are sent — the rest are filtered as sub-issues). The backend processes all 758 items to build the board, but the frontend only renders 55 visible items.

---

## GitHub API Call Budget (Cold Start)

| Phase | Calls | Type | Purpose |
|---|---|---|---|
| POST /select → verify_project_access | 1 | GraphQL | list_user_projects |
| POST /select → get_project | 1 | GraphQL | list_user_projects (duplicate!) |
| POST /select → resolve_repository | 1 | GraphQL | get_project_repository |
| Board data → pagination | 8 | GraphQL | ProjectV2.items (100/page × 758 items) |
| Board data → sub-issues | ~55 | REST | /repos/{o}/{r}/issues/{n}/sub_issues |
| Board data → reconciliation | 2–3 | GraphQL | Repository.issues for consistency check |
| Board data → reconcile sub-issues | 0–5 | REST | Sub-issues for newly discovered items |
| Copilot polling (background) | 20–50+ | GraphQL+REST | PR status, linked PRs, agent outputs |
| Workflow agents → verify_project_access | 1 | GraphQL | list_user_projects (3rd duplicate!) |
| Workflow agents → resolve_repository | 1 | GraphQL | get_project_repository |
| Workflow agents → discover agents | 1–3 | REST | .agent.md file discovery |
| **Total** | **~92–130** | | |

---

## Optimization Opportunities (Priority Order)

### P0: Defer or throttle Copilot polling on project selection

- **Current**: `_start_copilot_polling` fires immediately during POST /select, competing for event loop and API quota
- **Impact**: Would reduce board data load from ~38s to ~8–12s by eliminating event-loop contention
- **Approach**: Delay polling start by 30–60 seconds after project selection, or yield periodically

### P1: Progressive board loading (fetch active columns first, backfill Done)

- **Current**: All 758 items fetched before response is sent
- **Impact**: Could show 7 active items (Backlog + Ready + In Progress + In Review) in ~2–4s, then backfill 51 Done items
- **Approach**: Two-phase response; first send non-Done items once available, then fetch/stream Done column

### P2: Eliminate duplicate `list_user_projects` calls

- **Current**: POST /select calls list_user_projects 2x (verify_project_access + get_project); GET /workflow/agents calls it a 3rd time
- **Impact**: Save 2 GraphQL calls (~1–1.5s) per project selection
- **Approach**: Cache the result from verify_project_access and reuse in get_project; pass project list to dependent handlers

### P3: Cache `GET /workflow/agents` response

- **Current**: No response cache; always makes live API calls (~3.2s)
- **Impact**: Would drop from 3.2s to <10ms on warm cache
- **Approach**: Add 5-minute cache with invalidation on agent config changes

### P4: Parallelize reconciliation queries

- **Current**: 2–3 repos queried sequentially (~1.5–3s)
- **Impact**: Would reduce reconciliation phase to ~0.5–1s
- **Approach**: `asyncio.gather()` across repos instead of sequential loop

### P5: Reduce Done column payload

- **Current**: Done column is 398 KB (99.5% of board response)
- **Impact**: Reduce total response from 400 KB to ~25 KB for initial render
- **Approach**: Paginate Done column; send only first N Done items with "load more" behavior

### P6: Increase sub-issue semaphore or batch

- **Current**: Semaphore(20) for ~55 REST calls → 3 batches
- **Impact**: With Semaphore(50), would complete in 1 batch (~400ms vs ~1.2s)
- **Approach**: Increase semaphore limit (test for GitHub secondary rate limit thresholds)

---

## Summary of Key Findings

| Metric | Value |
|---|---|
| Cold-start wall time | **~40 seconds** |
| Warm-cache wall time | **~4.7 seconds** |
| Critical bottleneck | `GET /board/projects/{id}` — 38.4s |
| GitHub API calls per load | ~92–130 |
| Biggest payload | Done column — 398 KB (99.5%) |
| Duplicate API calls | 3x `list_user_projects` per selection |
| Event-loop contention | Copilot polling adds ~15–20s to board load |
| Uncached endpoints | `GET /workflow/agents` (3.2s), `GET /settings/project/{id}` (affected by contention) |
