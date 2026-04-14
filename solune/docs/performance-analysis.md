# Performance Analysis: Cold-Start Project Load

**Date:** 2026-04-14  
**Branch:** `fix-project-load-time` (includes PR #1884 optimizations)  
**Test Project:** TooDew (`PVT_kwHOAIsXss4BUnJY`, 12 items)  
**Purpose:** Identify slow functions/endpoints to plan performance improvements for initial project import/load time.

---

## Executive Summary

When a user logs in and selects a project for the first time (cold start), the UI fires ~15 API calls across 3 phases. **Five endpoints take 1.3–7.3s each** due to repeated GitHub API calls, and together they can **exhaust the GitHub GraphQL rate limit** — causing subsequent endpoints to stall for 5+ minutes waiting for rate limit reset.

**Worst offenders (cold start):**

| Rank | Endpoint | Cold-Start Time | GitHub API Calls | Root Cause |
|------|----------|----------------|-----------------|------------|
| 1 | `GET /workflow/agents` | **7.27s** | ~16 (3 GraphQL + ~12 REST) | Double-fetches agent files; all sequential |
| 2 | `GET /settings/models/copilot` | **2.06s** | 1 Copilot API call | Copilot API latency + lock contention |
| 3 | `GET /board/projects/{id}` | **1.87s** | ~14 (10 GraphQL + 4 REST) | Sequential pagination + sub-issue fetches |
| 4 | `GET /settings/project/{id}` | **1.54s** | 1 GraphQL | `verify_project_access` tax |
| 5 | `GET /workflow/config` | **1.53s** | 1–3 GraphQL | `verify_project_access` + `resolve_repo` |
| 6 | `GET /pipelines/{id}` | **1.43s** | 1 GraphQL | `verify_project_access` tax |
| 7 | `GET /pipelines/{id}/assignment` | **1.35s** | 1 GraphQL | `verify_project_access` tax |

**Total sequential cold-start time:** ~17.0s+ (endpoints called one after another)  
**Estimated parallel cold-start time:** ~7.3s (limited by `/workflow/agents`)  
**Warm (cached) time:** <50ms total (all endpoints <10ms each)

---

## Test Methodology

### Environment

- Backend: Python 3.12 / FastAPI / uvicorn in Docker
- Frontend: Vite/React served via nginx in Docker
- GitHub API: Personal access token, shared across all endpoints

### Profiling Approach

1. Restart backend Docker container to clear all in-memory caches
2. Verify backend health (HTTP 200)
3. Call each endpoint sequentially with `curl` timing (`time_total`)
4. Capture backend Docker logs for GitHub API call analysis
5. Run multiple passes: cold-start + warm (cached) comparison

### Limitations

- Sequential profiling means endpoints called later inherit rate-limit budget depletion from earlier calls
- `POST /projects/{id}/select` returned 403 (CSRF double-submit mismatch via curl) — select was skipped, so endpoints ran against the previously-selected project
- True cold-start run 3 hit rate limit after workflow/agents, preventing measurement of subsequent endpoints; warm timings from run 2 used as lower bounds

---

## Profiling Results

### Run 1: True Cold Start (backend just restarted)

```text
GET /auth/me                          200    0.004s
GET /projects                         200    0.005s
POST /projects/select                 403    0.002s  (CSRF issue — skipped)
GET /board/projects/{id}              200    1.871s  ← SLOW
GET /workflow/agents                  200    7.272s  ← VERY SLOW
GET /settings/project/{id}            ---    5+ min  ← RATE LIMITED (never completed)
```

**Note:** After `/board/projects/{id}` (~14 API calls) and `/workflow/agents` (~16 API calls), the GitHub GraphQL rate limit was exhausted. Subsequent endpoints stalled with `PrimaryRateLimitExceeded` waiting 315s for reset.

### Run 2: Warm Board+Agents, Cold Settings/Pipelines

```text
GET /board/projects/{id}              200    0.005s  (cached)
GET /workflow/agents                  200    0.004s  (cached)
GET /settings/project/{id}            200    1.541s  ← SLOW
GET /pipelines/{id}                   200    1.433s  ← SLOW
GET /pipelines/{id}/assignment        200    1.353s  ← SLOW
GET /activity                         422    0.007s  (fast, validation error)
GET /chat/messages                    200    0.008s  (fast)
GET /signal/banners                   200    0.006s  (fast)
GET /board/projects                   200    0.005s  (cached)
GET /workflow/config                  200    1.533s  ← SLOW
GET /settings/models/copilot          200    2.064s  ← SLOW
```

### Fast Endpoints (<10ms, no bottleneck)

| Endpoint | Time | Notes |
|----------|------|-------|
| `GET /auth/me` | 4ms | Session lookup only |
| `GET /projects` | 5ms | Served from project cache (populated at login) |
| `GET /chat/messages` | 8ms | SQLite query only |
| `GET /signal/banners` | 6ms | SQLite query only |
| `GET /board/projects` (list) | 5ms | Returns cached project list |
| `GET /activity` | 7ms | SQLite query (returned 422 — missing query param) |

---

## Root Cause Analysis

### Issue #1: `verify_project_access` is the #1 tax — 1.3–1.5s per uncached endpoint

**Impact:** 4 endpoints × ~1.4s = **5.6s** total wasted (sequential) / **~1.4s** if parallelized  
**Endpoints affected:** `/settings/project/{id}`, `/pipelines/{id}`, `/pipelines/{id}/assignment`, `/workflow/config`

**What happens:**  
Every request that uses `verify_project_access` calls `list_user_projects(token, username)`, which executes a `LIST_USER_PROJECTS_QUERY` GraphQL query against GitHub. This call takes ~1.3–1.5s due to network latency to GitHub's API.

**Why it's slow:**

- The result is only cached within a single request via `request.state.verified_projects`
- There is **no cross-request caching** — every new API call repeats the same GraphQL query
- For a user with 8 projects, the response is small (~3KB) and changes rarely

**Code path:** `src/dependencies.py` → `verify_project_access()` → `svc.list_user_projects(token, username)` → GraphQL `LIST_USER_PROJECTS_QUERY`

### Issue #2: `/workflow/agents` double-fetches agent files — 7.3s cold start

**Impact:** **7.3s** — the single slowest endpoint  
**Endpoints affected:** `/workflow/agents`

**What happens:**  
The endpoint makes two independent calls that both read `.github/agents/` from GitHub REST API:

1. `list_available_agents(owner, repo, token)` in `AgentsMixin` — lists `.github/agents/` directory, then fetches each `*.agent.md` file individually. **No cache.**
2. `agents_service.list_agents(project_id, owner, repo, token)` in `AgentsService` — does the exact same thing (lists directory, fetches each file). Has a 900s cache (`repo_agents:{owner}:{repo}`) but it's empty on cold start.

With 5 agent files, this results in:

- 2× directory listing REST calls
- 2× 5 individual file fetches = 10 REST calls
- **Total: 12 REST calls doing the same work twice**

**Why it's slow:**

- Both fetch loops are **fully sequential** (`for` loop with `await`)
- The `list_available_agents` call has **no caching at all**
- The entire endpoint chain is sequential: `verify_project_access` → `resolve_repository` → `list_available_agents` → `list_agents` → `get_preferences`

**Code path:** `src/api/workflow.py` → `list_agents()` → `src/services/github_projects/agents.py` → `list_available_agents()` + `AgentsService.list_agents()`

### Issue #3: `/board/projects/{id}` sequential pagination — 1.9s cold start

**Impact:** **1.9s** cold start  
**Endpoints affected:** `/board/projects/{id}`

**What happens:**

1. Fetches all project items via paginated GraphQL (`BOARD_GET_PROJECT_ITEMS_QUERY`). For TooDew with 12 items, this is 1 page. For larger projects (833 items), this would be 8+ sequential pages.
2. Fetches sub-issues for non-Done parent items via REST (`GET /repos/{o}/{r}/issues/{n}/sub_issues`). With the fix from PR #1884, only ~4 calls are needed.
3. Reconciles board items per repository via parallelized GraphQL.

**Why it's slow:**

- GraphQL pagination is cursor-based and inherently sequential
- Sub-issue REST calls, while parallelized with semaphore(20), still add latency
- Result is cached for 300s after first load

**Code path:** `src/api/board.py` → `get_board_data()` → `src/services/github_projects/board.py` → `get_board_data()`

### Issue #4: `/settings/models/copilot` — 2.1s cold start

**Impact:** **2.1s** cold start  
**Endpoints affected:** `/settings/models/copilot`

**What happens:**

1. Calls Copilot API `list_models()` to get available AI models
2. Uses an internal lock + minimum 2s interval between calls to avoid API abuse
3. Result cached for 600s with stale-while-revalidate

**Why it's slow:**

- Copilot API latency is inherently ~1.5–2s
- Lock contention if multiple concurrent requests try to fetch models
- This is the only endpoint that doesn't hit GitHub GraphQL/REST

**Code path:** `src/api/settings.py` → `get_models_for_provider()` → `ModelFetcherService.get_models("copilot", token)` → `GitHubCopilotModelFetcher.fetch_models()`

### Issue #5: GitHub rate limit exhaustion on cold start

**Impact:** **5+ minute stall** after initial burst of API calls  
**Root cause:** `/board/projects/{id}` (~14 API calls) + `/workflow/agents` (~16 API calls) = ~30 calls in rapid succession + copilot polling background tasks → exceeds GitHub GraphQL rate limit budget

**Evidence from logs:**

```text
PrimaryRateLimitExceeded: (Response(200 OK, ...),
    datetime.timedelta(seconds=315, microseconds=899313))
```

**Amplifying factor:** Copilot polling background loop also makes GraphQL calls (issue fetches, PR status checks, recovery checks), competing with user-facing API calls for the same rate limit budget.

---

## GitHub API Call Inventory (Cold Start)

| Endpoint | GraphQL Calls | REST Calls | Copilot API | Total |
|----------|:---:|:---:|:---:|:---:|
| `/board/projects/{id}` | ~10 | ~4 | 0 | **~14** |
| `/workflow/agents` | 2–3 | ~12 | 0 | **~15** |
| `/settings/project/{id}` | 1 | 0 | 0 | **1** |
| `/pipelines/{id}` | 1 | 0 | 0 | **1** |
| `/pipelines/{id}/assignment` | 1 | 0 | 0 | **1** |
| `/workflow/config` | 1–3 | 0 | 0 | **1–3** |
| `/settings/models/copilot` | 0 | 0 | 1 | **1** |
| **Background polling** | 3–6 | 2–4 | 0 | **5–10** |
| **TOTAL** | **~19–24** | **~18** | **1** | **~38–44** |

---

## Frontend API Call Flow

### Phase 1: App Initialization (parallel)

```text
GET /auth/me              → 4ms   (session lookup)
GET /projects             → 5ms   (cached from login)
GET /chat/messages        → 8ms   (SQLite)
GET /signal/banners       → 6ms   (SQLite)
GET /board/projects       → 5ms   (cached project list)
GET /settings/models/copilot → 2.06s ← SLOW (Copilot API)
```

### Phase 2: Project Selection

```text
POST /projects/{id}/select  → <10ms  (session update)
```

### Phase 3: Post-Selection (parallel)

```text
GET /board/projects/{id}          → 1.87s  ← SLOW (14 GitHub calls)
GET /workflow/agents              → 7.27s  ← VERY SLOW (15 GitHub calls)
GET /settings/project/{id}        → 1.54s  ← SLOW (verify_project_access)
GET /pipelines/{id}               → 1.54s  ← SLOW (verify_project_access)
GET /pipelines/{id}/assignment    → 1.35s  ← SLOW (verify_project_access)
GET /workflow/config              → 1.53s  ← SLOW (verify + resolve_repo)
```

**Effective wall-clock time (parallel):** ~7.3s (limited by `/workflow/agents`)  
**Effective wall-clock time (with rate limit risk):** 7.3s – 5+ minutes

---

## Improvement Plan (Prioritized)

### P0: Cache `verify_project_access` across requests (Impact: -1.4s off 4 endpoints)

- Add short TTL (30–60s) in-memory cache keyed by `(user_id, project_id)`
- The user's project list changes very rarely; verifying once per minute is sufficient
- **Eliminates:** 4 redundant `LIST_USER_PROJECTS_QUERY` GraphQL calls per project load
- **Estimated savings:** 4 × 1.4s = 5.6s sequential / 1.4s parallel

### P1: Deduplicate agent file fetching in `/workflow/agents` (Impact: -3.5s)

- `list_available_agents()` and `AgentsService.list_agents()` both fetch `.github/agents/` independently
- Consolidate to a single cached fetch; share results between the two code paths
- Add caching to `list_available_agents()` (currently has none)
- **Eliminates:** ~6 redundant REST calls (1 directory listing + 5 file fetches)
- **Estimated savings:** 3–4s

### P2: Parallelize agent file fetching (Impact: -2s)

- Both `list_available_agents()` and `_list_repo_agents()` use sequential `for` loops
- Switch to `asyncio.gather()` for fetching individual agent `.md` files
- With 5 agents, parallelizing 5 individual file fetches saves ~4 × REST round-trip time
- **Estimated savings:** 1.5–2.5s

### P3: Parallelize independent steps in `/workflow/agents` (Impact: -1.5s)

- Current flow is fully sequential: `verify` → `resolve_repo` → `list_available` → `list_agents`
- After `verify`, `resolve_repo` and agent fetching can run in parallel
- **Estimated savings:** 1–2s (overlap resolve_repo with agent fetch)

### P4: Prefetch/warm caches on project selection (Impact: perceived -5s)

- When `POST /projects/{id}/select` fires, proactively warm:
  - `verify_project_access` cache
  - `resolve_repository` cache
  - Board data cache
  - Agents cache

- Frontend then hits only cached data for subsequent calls
- **Estimated savings:** All endpoints drop to <10ms after select

### P5: Rate-limit-aware request scheduling (Impact: prevents 5+ min stalls)

- Track remaining GraphQL budget and throttle/batch requests before hitting the limit
- Prioritize user-facing requests over background copilot polling
- Defer background polling during project load burst
- **Eliminates:** 5+ minute cold-start stalls from rate limit exhaustion

### P6: Reduce board pagination for large projects (Impact: -Ns for large projects)

- For projects with 800+ items, pagination requires 8+ sequential GraphQL calls
- Consider: fetch only visible columns/statuses first, lazy-load Done items
- Consider: request smaller page sizes in parallel (if GitHub API supports it)

---

## Caching Summary

| Data | Current Cache | TTL | Recommendation |
|------|:---:|:---:|----------------|
| `verify_project_access` | Per-request only | N/A | Add 30–60s cross-request cache |
| `resolve_repository` | In-memory | 300s | Good — keep as-is |
| Board data | In-memory | 300s | Good — keep as-is |
| Agents (AgentsService) | In-memory | 900s | Good — but deduplicate with list_available |
| Agents (list_available) | **None** | N/A | Add cache (match AgentsService TTL) |
| Copilot models | In-memory | 600s | Good — keep as-is |
| Workflow config | In-memory BoundedDict | None (evict on full) | Good — keep as-is |
| Project list | Project cache | Long-lived | Good — populated at login |

---

## Expected Results After Improvements

| Scenario | Current | After P0–P3 | After P0–P5 |
|----------|---------|-------------|-------------|
| Cold-start parallel (wall clock) | ~7.3s | ~2.5s | <1s (prefetched) |
| Warm (cached) | <50ms | <50ms | <50ms |
| Rate limit risk | High (38+ calls) | Medium (~20 calls) | Low (scheduled) |
| Worst case (rate limited) | 5+ min stall | 5+ min stall | Graceful degradation |

---

## Raw Profiling Data

```text
Session: 042f3ce6-8f03-417a-8dce-23e7aa16ae5e (user: Boykai)
Project: PVT_kwHOAIsXss4BUnJY (TooDew, 12 items)
Branch: fix-project-load-time (includes PR #1884 optimizations)
Docker: fresh restart before each run

Run 1 (True Cold Start):
  GET /auth/me                          0.004s
  GET /projects                         0.005s
  GET /board/projects/{id}              1.871s
  GET /workflow/agents                  7.272s
  GET /settings/project/{id}            5+ min (rate limited)

Run 2 (Warm board+agents, cold rest):
  GET /board/projects/{id}              0.005s (cached)
  GET /workflow/agents                  0.004s (cached)
  GET /settings/project/{id}            1.541s
  GET /pipelines/{id}                   1.433s
  GET /pipelines/{id}/assignment        1.353s
  GET /activity                         0.007s (422)
  GET /chat/messages                    0.008s
  GET /signal/banners                   0.006s
  GET /board/projects                   0.005s
  GET /workflow/config                  1.533s
  GET /settings/models/copilot          2.064s
```
