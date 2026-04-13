# API Contract Changes: Remove Fleet Dispatch

**Branch**: `002-remove-fleet-dispatch` | **Date**: 2026-04-13

This feature removes fields from the workflow API response. No new endpoints or fields are added.

## Workflow Status Endpoint

### Fields Removed from Response

```yaml
# BEFORE (in workflow status response)
{
  "pipeline_state": {
    "dispatch_backend": "fleet" | "classic",
    "agent_task_ids": { "<agent_name>": "<task_id>", ... },
    # ... other fields preserved ...
  }
}

# AFTER
{
  "pipeline_state": {
    # dispatch_backend: REMOVED
    # agent_task_ids: REMOVED
    # ... other fields preserved unchanged ...
  }
}
```

### Breaking Change Assessment

**Risk**: None.
- `dispatch_backend` and `agent_task_ids` are not consumed by any frontend component (zero references in UI code).
- No documented external API consumers.
- The Zod schema in the frontend used `.optional().default()` for both fields — even if old cached responses include them, they are harmlessly parsed then dropped at the type level once the schema fields are removed.

## Endpoints Unchanged

All other API endpoints are unaffected:
- Issue dispatch triggers
- Pipeline status polling
- Auto-merge workflows
- App plan orchestration

## Copilot API Methods Removed (Internal)

These internal methods (never exposed as HTTP endpoints) are deleted from `copilot.py`:
- `list_agent_tasks()` — listed Copilot agent tasks
- `get_agent_task(task_id)` — fetched a single agent task
- `_discover_agent_task_endpoint()` — discovered the agent task API endpoint

These were only called by `FleetDispatchService` which is also being deleted. `assign_copilot_to_issue()` is preserved.
