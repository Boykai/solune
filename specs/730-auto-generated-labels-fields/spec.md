# Feature Specification: Auto-Generated Project Labels & Fields on Pipeline Launch

**Feature ID**: 730  
**Branch**: `730-auto-generated-labels-fields`  
**Date**: 2026-04-04  
**Status**: Draft  

## Overview

When a GitHub Parent Issue is created via pipeline launch, auto-compute and set project fields (Priority, Size, Estimate, Start/End date) and ensure existing label infrastructure (agent, type, stalled) is properly utilized.

## Current State

- `classify_labels()` already generates type labels (bug, feature, etc.) via AI
- `agent:` and `pipeline:` labels already applied during execution
- `stalled` label already applied/removed during recovery/resume
- `set_issue_metadata()` exists and sets Priority, Size, Estimate, Start/Target date on project items
- **Gap**: `execute_pipeline_launch()` never calls `set_issue_metadata()` — project fields are left empty

## User Stories

### P1: Pipeline Launch Sets Estimate & Metadata

**As** a project manager,  
**I want** pipeline-launched issues to automatically have Priority, Size, Estimate, and dates set,  
**So that** the project board immediately reflects accurate planning data without manual intervention.

**Acceptance Criteria**:
- Given a pipeline is launched with N configured agents
- When the parent issue is created and added to the project
- Then Priority=P2, Size=derived, Estimate=derived, Start=today, Target=today+estimate are set
- And the pipeline launch does not fail if metadata setting fails (non-blocking)

**Independent Test**: Launch a 3-agent pipeline → verify project fields show ~0.75h, Size S, P2, today's date.

### P2: AI Priority Override

**As** a project manager,  
**I want** the AI classifier to detect urgency in issue titles/descriptions,  
**So that** critical issues (security vulnerabilities, production outages) are automatically prioritized higher.

**Acceptance Criteria**:
- Given an issue with urgency signals ("critical", "security vulnerability", "production down")
- When labels are classified
- Then the AI may return P0 or P1 priority
- And the AI priority overrides the default P2 heuristic
- And heuristic estimate/size/dates remain unchanged (AI can't know agent count)

**Independent Test**: Classify issue titled "Critical security vulnerability in auth" → verify P0/P1 returned.

### P3: Verify Existing Label Lifecycle

**As** a developer,  
**I want** confirmation that existing agent:/stalled label lifecycles work correctly,  
**So that** no regressions exist in the label infrastructure.

**Acceptance Criteria**:
- Given agent labels are applied at first assignment via `_swap_agent_labels()`
- Then verify test coverage exists
- Given stalled labels are added during recovery and removed on agent swap
- Then verify test coverage exists

**Independent Test**: Review existing test coverage for agent/stalled label transitions.

## Estimate Heuristic

| Agents | Estimate | Size |
|--------|----------|------|
| 1-2    | 0.5h     | XS   |
| 3-4    | 0.75-1h  | S    |
| 5-8    | 1.25-2h  | M    |
| 9-16   | 2.25-4h  | L    |
| 17+    | 4.25-8h  | XL   |

Formula: `estimate_hours = max(0.5, min(8.0, agent_count * 0.25))`

## Out of Scope

- Changing existing label taxonomy
- Manual override UI for project fields
- Changing existing agent/stalled/pipeline label behavior
- Retroactive metadata population for existing issues
