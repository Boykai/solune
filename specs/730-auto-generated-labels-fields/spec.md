# Feature Specification: Auto-Generated Project Labels & Fields on Pipeline Launch

**Feature Branch**: `730-auto-generated-labels-fields`  
**Created**: 2026-04-04  
**Status**: Draft  
**Input**: User description: "When a GitHub Parent Issue is created via pipeline launch, auto-compute and set project fields (Priority, Size, Estimate, Start/End date) and ensure existing label infrastructure (agent, type, stalled) is properly utilized."

## User Scenarios & Testing

### User Story 1 - Auto-Set Project Fields on Pipeline Launch (Priority: P1)

As a project manager, I want pipeline-launched issues to automatically have Priority, Size, Estimate, and Start/Target dates set on the project board, so that newly created issues immediately show accurate planning data without manual data entry.

Today, when a pipeline is launched, the parent issue is created with AI-generated labels and added to the project board, but all project fields (Priority, Size, Estimate, Start date, Target date) remain empty. This forces project managers to manually fill in these fields for every pipeline-launched issue.

The system should derive planning metadata from the number of agents configured in the pipeline:

| Agent Count | Estimate     | Size |
| ----------- | ------------ | ---- |
| 1–2         | 0.5 h        | XS   |
| 3–4         | 0.75–1 h     | S    |
| 5–8         | 1.25–2 h     | M    |
| 9–16        | 2.25–4 h     | L    |
| 17+         | 4.25–8 h     | XL   |

Formula: `estimate_hours = max(0.5, min(8.0, agent_count × 0.25))`

Default priority is P2 (medium) for all pipeline-launched issues unless overridden by AI (see Story 2).

**Why this priority**: This is the core gap — every pipeline-launched issue currently lacks planning data. Filling this gap provides immediate, high-frequency value because every single pipeline launch benefits. Without it, the project board is incomplete and requires manual intervention.

**Independent Test**: Launch a pipeline with 3 configured agents. Verify the parent issue's project fields show Estimate ≈ 0.75 h, Size = S, Priority = P2, Start date = today, Target date = today + 1 day.

**Acceptance Scenarios**:

1. **Given** a pipeline with 3 configured agents is launched, **When** the parent issue is created and added to the project, **Then** the project fields are set to Priority = P2, Size = S, Estimate = 0.75, Start date = today, Target date = today + 1 day.
2. **Given** a pipeline with 1 configured agent is launched, **When** the parent issue is added to the project, **Then** Size = XS, Estimate = 0.5, and Target date = today (same day).
3. **Given** a pipeline with 20 configured agents is launched, **When** the parent issue is added to the project, **Then** Size = XL, Estimate = 5.0 (clamped to 8.0 max), and Target date is calculated accordingly.
4. **Given** a pipeline is launched and the metadata-setting step fails (e.g., project field not found, network error), **When** the failure occurs, **Then** the pipeline launch continues without error — the failure is logged but does not block issue creation or agent assignment.
5. **Given** a pipeline is launched, **When** the parent issue is created, **Then** existing label behavior (AI-generated labels, pipeline label) is unchanged and all labels are applied as before.

---

### User Story 2 - AI-Driven Priority Override for Urgent Issues (Priority: P2)

As a project manager, I want the AI label classifier to detect urgency signals in issue titles and descriptions (e.g., "critical security vulnerability", "production outage"), so that high-urgency issues are automatically assigned P0 or P1 priority instead of the default P2.

The AI classifier already analyzes issue content to determine type labels. This story extends that analysis to optionally return a priority suggestion when urgency indicators are detected. The AI-suggested priority overrides the default P2, but the heuristic-derived estimate, size, and dates remain unchanged (since the AI cannot know the agent count).

**Why this priority**: This adds intelligence on top of the P1 heuristic. While P1 ensures every issue gets some priority, P2 ensures that truly urgent issues surface immediately. It builds on P1 and can be implemented after the baseline metadata flow is in place.

**Independent Test**: Submit an issue with the title "Critical security vulnerability in authentication module" through the classifier. Verify that the returned priority is P0 or P1 rather than the default P2.

**Acceptance Scenarios**:

1. **Given** a pipeline is launched with an issue titled "Critical security vulnerability in auth", **When** the AI classifier analyzes the title and description, **Then** the classifier returns a priority of P0 or P1 and this overrides the default P2 on the project board.
2. **Given** a pipeline is launched with a routine issue title like "Add pagination to user list", **When** the AI classifier analyzes the title, **Then** no priority override is returned and the default P2 is used.
3. **Given** the AI classifier times out or fails during urgency detection, **When** the failure occurs, **Then** the default P2 priority is used as a fallback and the pipeline proceeds without error.

---

### User Story 3 - Verify Existing Label Lifecycle Integrity (Priority: P3)

As a developer, I want confirmation that the existing label lifecycles (agent assignment labels, stalled detection labels) continue to function correctly alongside the new metadata-setting behavior, so that no regressions are introduced.

The existing label infrastructure handles:
- **Agent labels** (`agent:<slug>`): applied when an agent is assigned, swapped when a different agent takes over
- **Stalled label** (`stalled`): applied when a pipeline agent is detected as unresponsive, removed when a new agent is assigned
- **Pipeline label** (`pipeline:<name>`): applied at issue creation and preserved throughout

This story confirms that the new metadata-setting step does not interfere with these existing label operations.

**Why this priority**: This is a verification/validation concern rather than new functionality. The existing label flows already work; this story ensures they remain correct after introducing the metadata step.

**Independent Test**: Run the existing label lifecycle test suite (agent swap tests, stalled label tests, pipeline label tests) after integrating the metadata-setting changes and verify all tests pass without modification.

**Acceptance Scenarios**:

1. **Given** a pipeline is launched and the first agent is assigned, **When** the agent label is applied, **Then** the `agent:<slug>` label appears on the parent issue and the metadata-setting step does not remove or alter it.
2. **Given** a pipeline agent is detected as stalled, **When** the stalled label is applied, **Then** the `stalled` label appears on the issue and project field values remain unchanged.
3. **Given** a stalled agent is replaced by a new agent, **When** the agent swap occurs, **Then** the `stalled` label is removed, the old `agent:<slug>` label is replaced with the new one, and project field values remain unchanged.

---

### Edge Cases

- What happens when `agent_count` is 0? The system should treat this as invalid input and either default to 1 agent or skip metadata setting entirely (with a warning log).
- What happens when the project does not have the expected fields (Priority, Size, Estimate, Start date, Target date)? The system should log which fields could not be set and succeed for the fields that exist.
- What happens when the pipeline is launched but the issue is not added to a project? Metadata setting is skipped gracefully since there is no project item to update.
- What happens when two pipelines are launched simultaneously for the same issue description? Each creates its own parent issue — metadata is set independently on each.
- What happens when the AI classifier returns an invalid priority value (e.g., "P5" or "urgent")? The system should ignore the invalid value and fall back to the default P2.
- What happens when the estimated target date falls on a weekend or holiday? The system uses calendar days without business-day adjustments (documented assumption).

## Requirements

### Functional Requirements

- **FR-001**: The system MUST compute an estimate in hours from the number of configured pipeline agents using the formula `max(0.5, min(8.0, agent_count × 0.25))`.
- **FR-002**: The system MUST derive a size category (XS, S, M, L, XL) from the computed estimate based on the defined agent-count-to-size mapping.
- **FR-003**: The system MUST set the Priority field to P2 (medium) by default for all pipeline-launched issues.
- **FR-004**: The system MUST set the Start date field to the current date (UTC) when the pipeline is launched.
- **FR-005**: The system MUST compute the Target date by adding the estimated hours (converted to whole days, rounded up) to the Start date.
- **FR-006**: The system MUST call the existing project field update mechanism to set Priority, Size, Estimate, Start date, and Target date on the parent issue's project item after it is added to the project.
- **FR-007**: The system MUST NOT fail the pipeline launch if any metadata field cannot be set — all metadata-setting failures MUST be logged and the pipeline MUST continue.
- **FR-008**: The system MUST preserve all existing label behavior (AI-generated labels, pipeline labels, agent labels, stalled labels) without modification.
- **FR-009**: The AI label classifier SHOULD optionally return a priority suggestion when urgency signals are detected in the issue title or description.
- **FR-010**: When the AI classifier returns a valid priority value, the system MUST use the AI-suggested priority instead of the default P2.
- **FR-011**: When the AI classifier fails, times out, or returns no priority, the system MUST fall back to the default P2 priority.
- **FR-012**: The system MUST treat an agent count of 0 as invalid and either default to 1 or skip metadata setting with a warning.
- **FR-013**: The system MUST log the computed metadata values (priority, size, estimate, dates) for observability.

### Key Entities

- **Pipeline Metadata**: Represents the computed planning data for a pipeline-launched issue. Includes priority (P0–P3), size (XS–XL), estimate in hours (0.5–8.0), start date, and target date. Derived from the pipeline's agent count and optionally from AI urgency analysis.
- **Pipeline Configuration**: The existing configuration that defines which agents participate in a pipeline. The agent count from this configuration drives the estimate heuristic.
- **Project Item**: An issue's representation on a GitHub Project V2 board. Has fields (Priority, Size, Estimate, Start date, Target date) that can be set via the existing project field update mechanism.
- **Label Classification Result**: The output of the AI label classifier. Currently returns a list of labels. This feature extends it to optionally include a priority suggestion alongside the labels.

## Success Criteria

### Measurable Outcomes

- **SC-001**: 100% of pipeline-launched issues have Priority, Size, Estimate, Start date, and Target date populated on the project board within 10 seconds of issue creation — no manual data entry required.
- **SC-002**: Pipeline launch success rate remains at or above the current baseline — metadata-setting failures never cause a pipeline launch to fail.
- **SC-003**: Issues with urgency signals (security, outage, critical) are assigned P0 or P1 priority at least 80% of the time when analyzed by the AI classifier.
- **SC-004**: All existing label lifecycle tests (agent swap, stalled detection/removal, pipeline labels) pass without modification after the metadata feature is integrated.
- **SC-005**: Time from pipeline launch to all project fields being populated is under 5 seconds for typical pipelines (1–8 agents).
- **SC-006**: Project managers no longer need to manually set planning fields on pipeline-launched issues, reducing per-issue setup time to zero.

## Assumptions

- The GitHub Project V2 board used for pipeline issues has the standard fields: Priority (select), Size (select), Estimate (number), Start date (date), Target date (date). If any field is missing, the system logs a warning and sets the remaining fields.
- The estimate-to-target-date conversion uses calendar days (not business days). A 0.5h estimate results in a same-day target; an 8h estimate results in a +1 day target (assuming an 8-hour workday).
- The default priority of P2 is appropriate for the majority of pipeline-launched issues. Only issues with clear urgency signals warrant higher priority.
- The existing `set_issue_metadata()` function handles the actual field updates; no changes to its interface are needed.
- The AI classifier's 5-second timeout is sufficient for urgency detection without adding latency to the pipeline launch.

## Out of Scope

- Changing the existing label taxonomy (type, scope, domain labels)
- Manual override UI for project fields after auto-population
- Changing existing agent/stalled/pipeline label behavior
- Retroactive metadata population for issues created before this feature
- Business-day-aware date calculations for target dates
- Custom per-pipeline priority or estimate overrides
