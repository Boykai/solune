# Data Model: Remove Fleet Dispatch & Copilot CLI Code

**Branch**: `002-remove-fleet-dispatch` | **Date**: 2026-04-13

This feature is a removal — no new entities are introduced. This document records the models being deleted and the models being preserved unchanged.

## Models Deleted

### From `solune/backend/src/models/pipeline.py`

All 9 FleetDispatch-related classes are deleted:

| Class | Purpose | Lines (approx) |
|-------|---------|-----------------|
| `FleetDispatchModel` | Base model for fleet dispatch state | 141–150 |
| `FleetDispatchRepository` | Repository config for fleet dispatches | 151–157 |
| `FleetDispatchDefaults` | Default values for fleet config fields | 158–163 |
| `FleetDispatchSubIssue` | Sub-issue metadata for fleet decomposition | 164–170 |
| `FleetDispatchAgent` | Agent assignment within fleet dispatch | 171–180 |
| `FleetDispatchExecutionGroup` | Parallel execution grouping for fleet | 181–190 |
| `FleetDispatchConfig` | Complete fleet dispatch configuration | 191–205 |
| `FleetDispatchStatus` | Enum of fleet dispatch lifecycle states | 206–215 |
| `FleetDispatchRecord` | Persistent record of a fleet dispatch run | 220–234 |

### From API / Frontend

| Field | Location | Type |
|-------|----------|------|
| `dispatch_backend` | `workflow.py` response, `index.ts` interface, `pipeline.ts` Zod schema | `'fleet' \| 'classic'` |
| `agent_task_ids` | `workflow.py` response, `index.ts` interface, `pipeline.ts` Zod schema | `Record<string, string>` |

## Models Preserved (Unchanged)

These models coexist in `pipeline.py` and are not touched:

- `PipelineAgentNode`
- `ExecutionGroup`
- `PipelineStage`
- `PipelineConfig`
- All other non-Fleet* models in the module

## State Writes Affected

The orchestrator's state persistence currently writes `agent_task_ids` as part of pipeline state. This field is removed from state writes. No migration is needed — old state records with this field are harmlessly ignored by Pydantic's model parsing (extra fields are allowed or ignored depending on config).

## Relationship Changes

```
BEFORE:
  PipelineConfig ──uses──▶ FleetDispatchConfig
  orchestrator.py ──uses──▶ FleetDispatchService
  FleetDispatchService ──uses──▶ FleetDispatchConfig, FleetDispatchRecord, FleetDispatchStatus

AFTER:
  PipelineConfig (standalone, no fleet dependency)
  orchestrator.py (classic dispatch only, no fleet service)
```
