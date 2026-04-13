# Data Model: Remove Fleet Dispatch & Copilot CLI Code

**Feature**: 006-remove-fleet-dispatch-cli
**Date**: 2026-04-13

## Overview

This feature is a **deletion-focused refactor** — no new entities are introduced. The data model documents entities being removed and the entities that remain after cleanup.

## Entities Removed

### 1. FleetDispatchModel (Base)

**Source**: `solune/backend/src/models/pipeline.py:141`
**Action**: DELETE

Base Pydantic model for all fleet-dispatch configuration records.

### 2. FleetDispatchRepository

**Source**: `solune/backend/src/models/pipeline.py:147`
**Action**: DELETE

| Field | Type | Description |
|-------|------|-------------|
| owner | str | GitHub repository owner |
| name | str | GitHub repository name |

### 3. FleetDispatchDefaults

**Source**: `solune/backend/src/models/pipeline.py:154`
**Action**: DELETE

| Field | Type | Description |
|-------|------|-------------|
| baseRef | str | Default base branch |
| errorStrategy | str | Error handling strategy |
| pollIntervalSeconds | int | Polling interval |
| taskTimeoutSeconds | int | Task timeout |

### 4. FleetDispatchSubIssue

**Source**: `solune/backend/src/models/pipeline.py:169`
**Action**: DELETE

| Field | Type | Description |
|-------|------|-------------|
| titleTemplate | str | Sub-issue title template |
| bodyTemplate | str | Sub-issue body template |
| labels | list[str] | Labels to apply |

### 5. FleetDispatchAgent

**Source**: `solune/backend/src/models/pipeline.py:176`
**Action**: DELETE

| Field | Type | Description |
|-------|------|-------------|
| slug | str | Agent identifier |
| displayName | str | Human-readable name |
| customAgent | str \| None | Custom agent ID |
| model | str \| None | LLM model override |
| instructionTemplate | str | Template file name |
| subIssue | FleetDispatchSubIssue | Sub-issue config |
| retryable | bool | Whether retries are allowed |

### 6. FleetDispatchExecutionGroup

**Source**: `solune/backend/src/models/pipeline.py:188`
**Action**: DELETE

| Field | Type | Description |
|-------|------|-------------|
| name | str | Group name |
| parallel | bool | Parallel execution flag |
| agents | list[FleetDispatchAgent] | Agents in this group |

### 7. FleetDispatchConfig

**Source**: `solune/backend/src/models/pipeline.py:198`
**Action**: DELETE

| Field | Type | Description |
|-------|------|-------------|
| version | str | Config version |
| repository | FleetDispatchRepository | Repository metadata |
| defaults | FleetDispatchDefaults | Default settings |
| groups | list[FleetDispatchExecutionGroup] | Execution groups |

### 8. FleetDispatchStatus (Enum)

**Source**: `solune/backend/src/models/pipeline.py:208`
**Action**: DELETE

| Value | Description |
|-------|-------------|
| PENDING | Initial state |
| QUEUED | Task queued |
| IN_PROGRESS | Task running |
| COMPLETED | Task succeeded |
| FAILED | Task failed |
| TIMED_OUT | Task timed out |
| SKIPPED | Task skipped |

### 9. FleetDispatchRecord

**Source**: `solune/backend/src/models/pipeline.py:220`
**Action**: DELETE

| Field | Type | Description |
|-------|------|-------------|
| agent_slug | str | Agent identifier |
| task_id | str | GitHub task ID |
| status | FleetDispatchStatus | Current state |
| created_at | datetime | Creation timestamp |
| updated_at | datetime | Last update |

## Fields Removed from Existing Entities

### PipelineState (dataclass)

**Source**: `solune/backend/src/services/workflow_orchestrator/models.py:200-201`
**Action**: REMOVE FIELD

| Field Removed | Type | Reason |
|---------------|------|--------|
| agent_task_ids | dict[str, str] | Fleet-only: maps agent slug → GitHub task ID |

### PipelineStateInfo (frontend type)

**Source**: `solune/frontend/src/types/index.ts:576-577`
**Action**: REMOVE FIELDS

| Field Removed | Type | Reason |
|---------------|------|--------|
| agent_task_ids | Record\<string, string\> | Fleet-only |
| dispatch_backend | 'fleet' \| 'classic' | Fleet-only |

### Pipeline Zod Schema (frontend)

**Source**: `solune/frontend/src/services/schemas/pipeline.ts:15-16`
**Action**: REMOVE FIELDS

| Field Removed | Type | Reason |
|---------------|------|--------|
| agent_task_ids | z.record(z.string(), z.string()) | Fleet-only |
| dispatch_backend | z.enum(['fleet', 'classic']) | Fleet-only |

## Entities Preserved (Unchanged)

The following pipeline models in `models/pipeline.py` are **not** related to fleet dispatch and must be preserved:

- `PipelineAgentNode` — Agent node in pipeline graph
- `ExecutionGroup` — Generic execution group
- `PipelineStage` — Pipeline stage definition
- `PipelineConfig` — Pipeline configuration
- All other non-fleet models in the file

## State Serialization Impact

The `pipeline_state_store.py` module serializes `PipelineState` to JSON for SQLite persistence:
- **Write path** (`_serialize`): `agent_task_ids` will no longer be included
- **Read path** (`_deserialize`): Existing rows with `agent_task_ids` in JSON will be safely ignored (field absent from model)
- **No migration needed**: The deserialization uses `dict.get()` with defaults, making the field removal backward-compatible

## Relationship Diagram

```
DELETED                              PRESERVED
────────                             ─────────
FleetDispatchService ──uses──→ FleetDispatchConfig     PipelineAgentNode
       │                            │                   ExecutionGroup
       ├──uses──→ FleetDispatchAgent ─→ FleetDispatchSubIssue    PipelineStage
       │                            │                   PipelineConfig
       ├──uses──→ FleetDispatchRecord ─→ FleetDispatchStatus
       │
       └──reads──→ fleet-dispatch.json
                   pipeline-config.schema.json
                   templates/*.md (12 files)
```
