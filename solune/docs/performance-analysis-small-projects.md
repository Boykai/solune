# Performance Analysis: Small Project Load (Companion)

> **Date**: 2025-07-18
> **Test Projects**: Colove (13 items, 1 parent), aaaa (12 items, 0 parents)
> **Environment**: Docker Compose, cold cache, live GitHub API
> **Profiling Tool**: `solune/backend/scripts/perf_profile_project_load.py`

---

## Purpose

Supplements the [main performance analysis](performance-analysis-project-load.md) (758 items, ~40s)
with **function-level timing** on small projects to isolate per-call overhead from scaling costs.

---

## Key Finding: Even Tiny Projects Are Slow

| Metric | Colove (13 items) | aaaa (12 items) | Solune (758 items) |
|--------|-------------------|------------------|---------------------|
| Critical path (parallel) | **2,244ms** | **1,827ms** | **~40,000ms** |
| Sequential total | 7,187ms | 6,133ms | N/A |
| `get_board_data` | 2,404ms | 1,586ms | 38,428ms |
| GraphQL items fetch | 1,230ms | 874ms | ~6–10s |
| Sub-issue REST | 354ms (1 parent) | 0ms (0 parents) | ~2–4s (55 parents) |
| Reconciliation | 791ms (**0 found**) | 683ms (**0 found**) | ~1–4s |
| `list_user_projects` | 1,225ms | 1,211ms | ~500ms (cached) |

---

## Per-Function Breakdown: Colove (13 items, 7 columns)

```text
Total sequential: 7,187ms
Total parallel critical path: 2,244ms

├─ 1. list_user_projects ──────────── 1,225ms  (17.1%)  8 projects
├─ 2. resolve_repository ──────────── 241ms    (3.4%)   Boykai/colove
├─ 3. list_board_projects ─────────── 1,055ms  (14.7%)  duplicate of #1
├─ 4. get_board_data ──────────────── 2,404ms  (33.4%)  ★ BOTTLENECK
│   ├─ 4a. GraphQL items (1 page) ─── 1,230ms  (17.1%)  13 items
│   ├─ 4b. REST sub-issues ────────── 354ms    (4.9%)   1 parent → 1 sub
│   └─ 4c. Reconciliation ────────── 791ms    (11.0%)  1 repo → 0 found
├─ 5. get_workflow_config ─────────── 0ms      (0%)
└─ 6. list_agents ─────────────────── 18ms     (0.3%)
```

## Per-Function Breakdown: aaaa (12 items, 3 columns)

```text
Total sequential: 6,133ms
Total parallel critical path: 1,827ms

├─ 1. list_user_projects ──────────── 1,211ms  (19.7%)  8 projects
├─ 2. resolve_repository ──────────── 236ms    (3.8%)   Boykai/aaaa
├─ 3. list_board_projects ─────────── 1,254ms  (20.5%)  duplicate of #1
├─ 4. get_board_data ──────────────── 1,586ms  (25.9%)  ★ BOTTLENECK
│   ├─ 4a. GraphQL items (1 page) ─── 874ms    (14.3%)  12 items
│   ├─ 4b. REST sub-issues ────────── 0ms      (0%)     no parents
│   └─ 4c. Reconciliation ────────── 683ms    (11.1%)  1 repo → 0 found
├─ 5. get_workflow_config ─────────── 2ms      (0%)
└─ 6. list_agents ─────────────────── 18ms     (0.3%)
```

---

## Per-Call Overhead (Irreducible Costs)

These are the **minimum** costs per GitHub API call, independent of data volume:

| Operation | Cost per call | Notes |
|-----------|---------------|-------|
| GraphQL `list_user_projects` | ~1,100–1,250ms | Constant regardless of project count |
| GraphQL `get_project_items` (single page) | ~874–1,230ms | 12–13 items; overhead dominates |
| GraphQL `reconcile_items` | ~683–791ms | Even when finding 0 items |
| REST sub-issue fetch | ~354ms | Per parent issue |
| GraphQL `resolve_repository` | ~236–241ms | First item scan fallback |

**Insight**: GitHub API latency floor is ~600–1,200ms per GraphQL call. Even optimally
structured queries take this long. The key strategy is to **minimize the number of
separate API calls** and **parallelize** those that remain.

---

## Optimization Priority (Updated with Small-Project Data)

### Must-fix (even tiny projects are affected)

1. **Skip reconciliation on initial load** — 683–791ms wasted on every cold load finding 0 items.
   Defer to a background task after board renders.

2. **Deduplicate `list_user_projects`** — Called twice on cold start (~1.1s wasted).
   In-flight promise dedup would eliminate this.

3. **Pre-warm board data on `select_project`** — Fire `get_board_data` as fire-and-forget
   during POST /select so the cache is warm when the frontend asks. Saves ~1.8s on
   critical path.

### Important (scaling concerns from main analysis)

1. **Defer/throttle Copilot polling** — Causes ~15–20s event-loop contention on large projects.
2. **Progressive board loading** — Fetch active columns first, backfill Done.
3. **Cache `GET /workflow/agents`** — 3.2s uncached on every call.

### Combined estimated impact

| Fix | Small Project Saving | Large Project Saving |
|-----|---------------------|---------------------|
| Skip reconciliation | 683–791ms | 1–4s |
| Dedup list_user_projects | ~1.1s (off critical path) | ~1s |
| Pre-warm board data | ~1.8s critical path | ~38s critical path |
| Defer Copilot polling | minimal | ~15–20s |
| Progressive loading | minimal | ~30s (shows active items in ~4s) |
| Cache agents endpoint | ~3s | ~3s |
