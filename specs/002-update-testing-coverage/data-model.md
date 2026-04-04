# Data Model: Update Testing Coverage

**Feature**: 002-update-testing-coverage | **Date**: 2026-04-04

## Overview

This feature does not introduce new persistent data models. It operates on the existing codebase's test infrastructure. The "entities" below represent the conceptual model of the testing improvement workflow.

## Entities

### CoverageTarget

Represents a source file targeted for coverage improvement.

| Field | Type | Description |
|-------|------|-------------|
| `file_path` | string | Relative path from backend/frontend root |
| `current_line_coverage` | float | Current line coverage percentage (0-100) |
| `current_branch_coverage` | float | Current branch coverage percentage (0-100) |
| `target_line_coverage` | float | Target line coverage after improvement |
| `target_branch_coverage` | float | Target branch coverage after improvement |
| `missing_lines` | int | Number of uncovered lines |
| `missing_branches` | int | Number of uncovered branches |
| `priority` | enum(P1,P2,P3) | Based on impact score (missing × inverse coverage) |
| `category` | enum(api, service, hook, component, e2e) | Source classification |

### TestAction

Represents an action to take on a test file.

| Field | Type | Description |
|-------|------|-------------|
| `test_file_path` | string | Path to the test file |
| `action` | enum(add, update, remove) | What to do with this test |
| `reason` | string | Why this action is needed |
| `target_source` | string | Which source file this test covers |
| `estimated_coverage_gain` | float | Expected coverage improvement in pp |

### CoverageThreshold

Represents a coverage enforcement threshold.

| Field | Type | Description |
|-------|------|-------------|
| `scope` | enum(backend, frontend) | Which codebase |
| `metric` | enum(statements, branches, functions, lines) | Coverage metric |
| `current_value` | float | Current threshold value |
| `target_value` | float | New threshold value |
| `config_file` | string | Where the threshold is configured |

## Relationships

```
CoverageTarget 1..* -- 1..* TestAction    (each target may have multiple test actions)
CoverageThreshold 1 -- * CoverageTarget  (thresholds gate the targets within a scope)
```

## State Transitions

### CoverageTarget Lifecycle

```
IDENTIFIED → ANALYZED → TESTS_WRITTEN → VERIFIED → MERGED
```

- **IDENTIFIED**: File flagged by coverage analysis
- **ANALYZED**: Missing lines/branches mapped to testable scenarios
- **TESTS_WRITTEN**: New test code written for the target
- **VERIFIED**: Tests pass and coverage meets target
- **MERGED**: PR merged with coverage improvement

### TestAction Lifecycle

```
PROPOSED → REVIEWED → APPLIED → VALIDATED
```

- **PROPOSED**: Action identified during analysis
- **REVIEWED**: Action verified as worthwhile (not removing critical coverage)
- **APPLIED**: Code change made
- **VALIDATED**: CI passes with the change

## Validation Rules

1. A `CoverageTarget` with priority P1 MUST have `target_line_coverage >= current_line_coverage + 15`
2. A `TestAction` with action `remove` MUST have a documented `reason` and MUST NOT reduce overall coverage
3. `CoverageThreshold.target_value` MUST be >= `CoverageThreshold.current_value` (ratchet — never decrease)
4. Backend `fail_under` in pyproject.toml MUST be >= 75 (current) and increase to >= 80 after improvements

## Priority Tiers

### Tier 1 — Backend Critical (P1, highest impact)

| # | Source File | Missing Lines | Current Coverage |
|---|-------------|---------------|------------------|
| 1 | `services/copilot_polling/pipeline.py` | 310 | 65.7% |
| 2 | `services/agents/service.py` | 281 | 47.4% |
| 3 | `api/chat.py` | 275 | 59.6% |
| 4 | `services/agent_creator.py` | 240 | 39.4% |
| 5 | `api/projects.py` | 155 | 37.7% |

### Tier 2 — Backend Important (P1-P2)

| # | Source File | Missing Lines | Current Coverage |
|---|-------------|---------------|------------------|
| 6 | `services/chores/service.py` | 154 | 51.3% |
| 7 | `services/copilot_polling/recovery.py` | 138 | 64.3% |
| 8 | `workflow_orchestrator/orchestrator.py` | 136 | 79.8% |
| 9 | `services/app_service.py` | 130 | 61.6% |
| 10 | `services/signal_bridge.py` | 127 | 60.9% |

### Tier 3 — Backend Secondary (P2)

| # | Source File | Missing Lines | Current Coverage |
|---|-------------|---------------|------------------|
| 11 | `api/pipelines.py` | 101 | 62.2% |
| 12 | `github_projects/board.py` | 91 | 63.0% |
| 13 | `main.py` | 89 | 68.2% |
| 14 | `api/board.py` | 85 | 64.5% |
| 15 | `copilot_polling/agent_output.py` | 80 | 73.0% |

### Frontend Coverage Targets

| Metric | Current Threshold | Target Threshold |
|--------|-------------------|------------------|
| Statements | 50% | 60% |
| Branches | 44% | 55% |
| Functions | 41% | 52% |
| Lines | 50% | 60% |
