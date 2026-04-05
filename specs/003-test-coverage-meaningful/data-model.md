# Data Model: Increase Test Coverage with Meaningful Tests

## Overview

This feature does not introduce new production persistence entities. Its design model tracks the planning objects that implementation must create or update so coverage work remains measurable, meaningful, and reviewable.

## Entities

### 1. TestTarget

Represents a source module or component whose behavior and coverage are explicitly in scope.

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Stable identifier, typically derived from the absolute source path |
| `kind` | enum | `backend_api`, `backend_service`, `backend_utility`, `frontend_component`, `frontend_context`, `frontend_utility` |
| `source_path` | string | Absolute path to the production file under test |
| `test_path` | string | Absolute path to the primary test file that covers the target |
| `coverage_metric_type` | enum | `line`, `branch`, `statement`, `function` |
| `baseline_threshold` | number \| null | Known baseline where available |
| `target_threshold` | number | Required threshold from the feature spec |
| `priority` | enum | `P1`, `P2`, `P3` |
| `notes` | string | Behavior/risk summary for the target |

**Relationships**
- One `TestTarget` has many `TestCase` records.
- One `TestTarget` may have one or more `CoverageMetric` records.
- One `TestTarget` may have zero or more associated `BugFix` records.

**Validation Rules**
- `source_path` and `test_path` must stay within `/home/runner/work/solune/solune/solune`.
- `target_threshold` must match the applicable success criteria or functional requirement.
- `kind` must align with the directory of `source_path`.

### 2. TestCase

Represents a single meaningful behavioral assertion.

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Test function/spec identifier |
| `target_id` | string | Parent `TestTarget` identifier |
| `scenario` | string | Human-readable behavior or error path being verified |
| `test_level` | enum | `unit`, `behavioral` |
| `failure_mode` | string | Expected failure/guardrail being exercised |
| `expected_outcome` | string | Observable result or assertion |
| `regression_for_bug` | string \| null | Linked `BugFix.id` when applicable |
| `uses_shared_fixture` | boolean | Whether existing shared setup is required |
| `status` | enum | `planned`, `failing`, `passing`, `stable` |

**Relationships**
- Many `TestCase` records belong to one `TestTarget`.
- A `TestCase` may guard one `BugFix`.

**Validation Rules**
- Every `TestCase` must map to a concrete user-visible or contract-visible behavior.
- Coverage-padding cases with no behavioral assertion are invalid for this feature.
- New tests must reuse existing repo conventions: async pytest patterns for backend, Testing Library behavior-first patterns for frontend.

**State Transitions**
- `planned` → `failing` → `passing` → `stable`
- `planned` → `passing` is allowed only for pure coverage-gap scenarios without a pre-existing defect.

### 3. BugFix

Represents a production defect that the new tests expose and then protect.

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Stable bug identifier |
| `source_path` | string | Absolute path to the affected production file |
| `root_cause` | string | Short description of the defect |
| `visible_symptom` | string | Behavior seen by callers/users/tests before the fix |
| `regression_test_id` | string | `TestCase.id` proving the defect |
| `fix_scope` | string | Smallest code change needed to satisfy the regression |
| `status` | enum | `identified`, `reproduced`, `fixed`, `guarded` |

**Relationships**
- One `BugFix` belongs to one `TestTarget`.
- One `BugFix` is guarded by at least one `TestCase`.

**Validation Rules**
- `source_path` must match one of the bug-bearing modules named in the spec.
- `fix_scope` must remain inline with the tests that expose the issue.
- Breaking API changes are not allowed under this feature; such cases would move to a follow-up.

**State Transitions**
- `identified` → `reproduced` → `fixed` → `guarded`

### 4. CoverageMetric

Represents measurable improvement for a target module or the aggregate suite.

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Metric identifier |
| `target_id` | string \| null | Linked `TestTarget`, or `null` for aggregate repo metrics |
| `scope` | enum | `module`, `suite`, `project` |
| `metric_type` | enum | `line`, `branch`, `statement`, `function` |
| `baseline_value` | number \| null | Starting point if known |
| `target_value` | number | Required threshold |
| `measured_value` | number \| null | Observed result after verification |
| `tool` | enum | `pytest-cov`, `vitest-v8` |
| `status` | enum | `unverified`, `in_progress`, `met`, `missed` |

**Relationships**
- A `CoverageMetric` may belong to one `TestTarget`.
- A `VerificationRun` produces many `CoverageMetric` observations.

**Validation Rules**
- Aggregate backend metrics must align with SC-001 and SC-002.
- Aggregate frontend metrics must align with SC-003.
- Module metrics must align with the thresholds called out in FR-001 through FR-022 and SC-008/SC-009 as applicable.

**State Transitions**
- `unverified` → `in_progress` → `met`
- `unverified` → `in_progress` → `missed`

### 5. VerificationRun

Represents a planned validation pass over targeted tests or whole suites.

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Run identifier |
| `scope` | enum | `backend_targeted`, `backend_full`, `frontend_targeted`, `frontend_full`, `smoke_checks` |
| `command` | string | Absolute-path-safe command to execute |
| `outputs` | string | Coverage/test result summary |
| `status` | enum | `planned`, `running`, `passed`, `failed` |

**Relationships**
- One `VerificationRun` may update many `CoverageMetric` records.

**Validation Rules**
- Commands must use existing repository tools only.
- Smoke checks must include lint/type-check expectations from the spec’s success criteria.

## Key Relationships Summary

- `TestTarget 1 --- N TestCase`
- `TestTarget 1 --- N BugFix`
- `TestTarget 1 --- N CoverageMetric`
- `BugFix 1 --- 1..N TestCase`
- `VerificationRun 1 --- N CoverageMetric`

## Planned Target Inventory

### Backend

- `/home/runner/work/solune/solune/solune/backend/src/api/chat.py`
- `/home/runner/work/solune/solune/solune/backend/src/api/board.py`
- `/home/runner/work/solune/solune/solune/backend/src/api/apps.py`
- `/home/runner/work/solune/solune/solune/backend/src/utils.py`
- `/home/runner/work/solune/solune/solune/backend/src/api/settings.py`
- `/home/runner/work/solune/solune/solune/backend/src/api/onboarding.py`
- `/home/runner/work/solune/solune/solune/backend/src/api/templates.py`
- `/home/runner/work/solune/solune/solune/backend/src/services/pipeline_estimate.py`
- `/home/runner/work/solune/solune/solune/backend/src/services/completion_providers.py`

### Frontend

- `/home/runner/work/solune/solune/solune/frontend/src/components/agents/AgentsPanel.tsx`
- `/home/runner/work/solune/solune/solune/frontend/src/components/agents/AddAgentModal.tsx`
- `/home/runner/work/solune/solune/solune/frontend/src/components/agents/AgentChatFlow.tsx`
- `/home/runner/work/solune/solune/solune/frontend/src/components/pipeline/ExecutionGroupCard.tsx`
- `/home/runner/work/solune/solune/solune/frontend/src/components/pipeline/PipelineModelDropdown.tsx`
- `/home/runner/work/solune/solune/solune/frontend/src/components/pipeline/PipelineRunHistory.tsx`
- `/home/runner/work/solune/solune/solune/frontend/src/lib/route-suggestions.ts`
- `/home/runner/work/solune/solune/solune/frontend/src/lib/commands/registry.ts`
- `/home/runner/work/solune/solune/solune/frontend/src/context/SyncStatusContext.tsx`
