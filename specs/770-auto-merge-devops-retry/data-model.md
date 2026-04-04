# Data Model: Auto-Merge After All Agents Complete + CI Pass + DevOps Retry

**Feature**: #770 — Auto-Merge After All Agents Complete + CI Pass + DevOps Retry  
**Date**: 2026-04-04

---

## Entities

### 1. AutoMergeResult (existing — no changes)

```python
@dataclass
class AutoMergeResult:
    status: Literal["merged", "devops_needed", "merge_failed", "retry_later"]
    pr_number: int | None = None
    merge_commit: str | None = None
    error: str | None = None
    context: dict[str, Any] = field(default_factory=dict)
```

**States**: `merged` | `devops_needed` | `merge_failed` | `retry_later`

### 2. Pipeline Metadata — DevOps Fields (existing in-memory dict)

```python
# Stored in pipeline_metadata dict (in-memory, per-issue)
{
    "devops_active": bool,       # True while DevOps agent is working
    "devops_attempts": int,      # Incremented on each dispatch (cap: 2)
    "auto_merge": bool,          # True if auto-merge enabled for this pipeline
}
```

### 3. AvailableAgent — DevOps Entry (new BUILTIN_AGENTS entry)

```python
AvailableAgent(
    slug="devops",
    display_name="DevOps",
    description="CI failure diagnosis and resolution agent",
    avatar_url=None,
    icon_name=None,
    source=AgentSource.BUILTIN,
)
```

### 4. Post-DevOps Retry State (new in-memory tracking)

```python
# New BoundedDict in state.py
_pending_post_devops_retries: BoundedDict[int, dict[str, Any]] = BoundedDict(maxlen=200)

# Value structure per issue_number key:
{
    "access_token": str,
    "owner": str,
    "repo": str,
    "issue_number": int,
    "pipeline_metadata": dict[str, Any],
    "project_id": str,
    "poll_count": int,       # Current poll count
    "dispatched_at": float,  # time.monotonic() of DevOps dispatch
}
```

---

## State Transitions

### Auto-Merge State Machine

```
Pipeline Complete
    │
    ▼
┌─────────────────┐
│ _attempt_auto_   │
│     merge()      │
└────────┬────────┘
         │
    ┌────┴────────────┬──────────────┬──────────────┐
    ▼                 ▼              ▼              ▼
 merged          retry_later    devops_needed   merge_failed
    │                 │              │              │
    ▼                 ▼              ▼              ▼
 Done ✅     schedule_retry    dispatch_devops   Broadcast
              (exp backoff)        │             failure
                  │                ▼
                  │         schedule_post_
                  │         devops_retry()
                  │                │
                  │         ┌──────┴──────┐
                  │         ▼             ▼
                  │     "Done!"       Timeout
                  │     detected      (1 hr)
                  │         │             │
                  │         ▼             ▼
                  └──► _attempt_      Broadcast
                      auto_merge()    failure
                           │
                      ┌────┴────┐
                      ▼         ▼
                   merged    devops_needed
                      │         │
                      ▼         ▼
                   Done ✅  Re-dispatch
                           (up to cap=2)
```

### DevOps Agent Lifecycle

```
                    dispatch_devops_agent()
                           │
                    ┌──────┴──────┐
                    ▼             ▼
              devops_active   Skipped
               = True         (active or
                    │          cap reached)
                    ▼
             DevOps agent
             works on PR
                    │
              ┌─────┴─────┐
              ▼            ▼
         Posts "Done!"   Fails/Stalls
              │            │
              ▼            ▼
         devops_active  Timeout after
          = False       POST_DEVOPS_MAX_POLLS
              │            │
              ▼            ▼
         Re-attempt     Broadcast failure
         auto-merge     (devops_attempts
              │          still < cap?)
              │            │
              ▼         ┌──┴──┐
           merged?      ▼     ▼
              │       Re-     Stop
              ▼       dispatch
           Done ✅
```

### Webhook-Triggered Paths

```
check_run (failure/timed_out)         check_suite (success)
         │                                     │
         ▼                                     ▼
  Resolve PR → issue               Resolve PR → issue
         │                                     │
         ▼                                     ▼
  Check auto-merge enabled          Check auto-merge enabled
         │                              + "In Review" status
         ▼                                     │
  dispatch_devops_agent()            _attempt_auto_merge()
  (proactive fast-path)             (proactive fast-path)
```

---

## Configuration Constants

### Existing (state.py — no changes)

| Constant | Value | Purpose |
|----------|-------|---------|
| `MAX_AUTO_MERGE_RETRIES` | 3 | Max retry attempts when CI pending |
| `AUTO_MERGE_RETRY_BASE_DELAY` | 60.0 s | Base delay for exponential backoff |
| `MAX_MERGE_RETRIES` | 3 | Max consecutive merge failures |
| `ASSIGNMENT_GRACE_PERIOD_SECONDS` | 120 | Grace period after agent assignment |

### New (state.py — additions)

| Constant | Value | Purpose |
|----------|-------|---------|
| `POST_DEVOPS_POLL_INTERVAL` | 120.0 s | Interval between "Done!" comment checks |
| `POST_DEVOPS_MAX_POLLS` | 30 | Max polls before timeout (~1 hr) |

---

## Relationships

```
AvailableAgent(slug="devops")
    │
    │ referenced by
    ▼
dispatch_devops_agent()
    │ assigns via
    ▼
assign_copilot_to_issue(custom_agent="devops")
    │ instrumented with
    ▼
_build_devops_instructions()  →  merge_result_context
    │
    │ triggers
    ▼
schedule_post_devops_merge_retry()
    │ polls via
    ▼
_check_devops_done_comment()  →  GitHub REST API
    │
    │ on completion
    ▼
_attempt_auto_merge()  →  AutoMergeResult
```

---

## Validation Rules

1. **DevOps dispatch guard**: `devops_active == False AND devops_attempts < 2`
2. **Retry deduplication**: Only one `_pending_post_devops_retries` entry per `issue_number`
3. **Auto-merge eligibility**: Must check both pipeline-level `auto_merge` and project-level `is_auto_merge_enabled()`
4. **Webhook PR filtering**: Only process PRs with `pull_requests` field non-empty
5. **Comment marker**: Must match exact string `"devops: Done!"` (case-sensitive substring match)
