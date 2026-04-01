# Feature Specification: Enrich Activity Page with Meaningful Events

**Feature Branch**: `002-enrich-activity-events`
**Created**: 2026-03-31
**Status**: Draft
**Input**: User description: "Enrich Activity Page with Meaningful Events"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Track Pipeline Launches and Workflow Completions (Priority: P1)

As a project administrator, I want the Activity page to capture pipeline launch events and workflow completion events so that I can trace the full lifecycle of automated operations without checking external logs.

**Why this priority**: Pipeline launches and workflow completions are the most frequently occurring and operationally critical events currently missing from the activity log. Without them, users cannot answer "Did my pipeline run?" or "When did it finish?" from the Activity page alone. This delivers immediate, high-frequency value.

**Independent Test**: Can be fully tested by launching a pipeline and verifying that both a "launched" event (with issue number and agent count) and a "completed" event appear in the Activity page event list.

**Acceptance Scenarios**:

1. **Given** a user triggers a pipeline launch, **When** the pipeline creates its issue and begins execution, **Then** an activity event with type "pipeline_run" and action "launched" is recorded, including the issue number and agent count in the event detail.
2. **Given** a pipeline workflow completes all its agents, **When** the orchestrator marks the workflow done, **Then** an activity event with type "agent_execution" and action "completed" is recorded.
3. **Given** the orchestrator triggers an individual agent execution, **When** the agent begins work, **Then** an activity event with type "agent_execution" and action "triggered" is recorded with the agent identifier in the detail.
4. **Given** the Activity page is open, **When** a user filters by the "Execution" category, **Then** only pipeline launch and orchestrator events are shown.

---

### User Story 2 - View Activity Summary Statistics (Priority: P1)

As a project administrator, I want to see a summary dashboard at the top of the Activity page showing key statistics (total events, events today, most common event type, and last activity timestamp) so that I can quickly assess system health and activity levels at a glance.

**Why this priority**: A stats dashboard transforms the Activity page from a raw log viewer into an operational overview. It provides immediate situational awareness without scrolling through individual events, making the page significantly more useful for daily monitoring.

**Independent Test**: Can be fully tested by loading the Activity page with existing events and verifying that four stat cards render above the event list, displaying accurate counts and timestamps sourced from a dedicated stats endpoint.

**Acceptance Scenarios**:

1. **Given** the Activity page loads, **When** events exist in the system, **Then** four stat cards are displayed above the filter chips: "Total Events" (count of all events), "Today" (count of events in the last 24 hours), "Most Common" (the event type with the highest count in the last 7 days), and "Last Activity" (relative timestamp of the most recent event).
2. **Given** the Activity page loads, **When** no events exist in the system, **Then** the stat cards display zeros or "No activity" gracefully without errors.
3. **Given** the stats endpoint is called, **When** the request completes, **Then** it returns total count, last-24h count, last-7d count grouped by event type, and the timestamp of the last event.

---

### User Story 3 - Track Settings and Project Lifecycle Changes (Priority: P2)

As a project administrator, I want settings changes (user, global, and project settings) and project lifecycle events (creation, selection) logged in the Activity page so that I have an audit trail of configuration and project management actions.

**Why this priority**: Settings and project changes are infrequent but high-impact events. Tracking them provides essential audit capability—when something breaks after a configuration change, users need to trace what changed and when. This is lower priority than pipeline events because it occurs less frequently.

**Independent Test**: Can be fully tested by changing a setting and creating/selecting a project, then verifying that corresponding events appear in the Activity page under the "Project" filter category.

**Acceptance Scenarios**:

1. **Given** a user updates any setting (user, global, or project), **When** the update is saved, **Then** an activity event with type "settings" and the appropriate action is recorded, including which fields were changed in the event detail.
2. **Given** a user creates a new project, **When** the project is saved, **Then** an activity event with type "project" and action "created" is recorded.
3. **Given** a user selects a different active project, **When** the selection is confirmed, **Then** an activity event with type "project" and action "selected" is recorded.
4. **Given** the Activity page is open, **When** a user filters by the "Project" category, **Then** only settings and project events are shown.

---

### User Story 4 - Distinguish Granular Webhook Events (Priority: P2)

As a project administrator, I want webhook events to be logged with specific actions (such as "PR merged" or "Copilot PR ready") instead of a generic "received" action so that I can understand exactly what triggered each webhook without inspecting payloads.

**Why this priority**: Granular webhook events improve the diagnostic value of the Activity page. Currently, all webhooks appear identical. Distinguishing them enables users to quickly identify which external events are driving system activity, which is critical for debugging integration issues.

**Independent Test**: Can be fully tested by triggering different webhook types (PR merge, Copilot PR ready) and verifying that each produces a distinct action label in the Activity page.

**Acceptance Scenarios**:

1. **Given** a PR merge webhook is received, **When** the webhook handler processes it, **Then** an activity event with type "webhook" and action "pr_merged" is recorded instead of the generic "received" action.
2. **Given** a Copilot PR ready webhook is received, **When** the webhook handler processes it, **Then** an activity event with type "webhook" and action "copilot_pr_ready" is recorded.
3. **Given** a webhook of an unrecognized type is received, **When** the webhook handler processes it, **Then** an activity event with action "received" is recorded as a fallback.

---

### User Story 5 - Browse Events with Time-Bucketed Grouping (Priority: P3)

As a project administrator, I want activity events grouped by time periods ("Today", "Yesterday", "This Week", "Earlier") with sticky section headers so that I can quickly navigate to the timeframe I care about without manually scanning timestamps.

**Why this priority**: Time-bucketed grouping is a visual enhancement that improves usability for the Activity page, especially when there are many events. It is lower priority because the existing chronological list is still functional; this adds navigational convenience rather than new data.

**Independent Test**: Can be fully tested by loading the Activity page with events spanning multiple days and verifying that events are grouped under the correct time-bucket headers, and that headers remain visible while scrolling.

**Acceptance Scenarios**:

1. **Given** events exist across multiple days, **When** the Activity page loads, **Then** events are grouped under "Today", "Yesterday", "This Week", and "Earlier" section headers based on their timestamps.
2. **Given** no events exist for a particular time bucket, **When** the Activity page loads, **Then** that time-bucket header is not displayed.
3. **Given** the user scrolls through a long list of events, **When** a time-bucket header scrolls past the top of the viewport, **Then** the header remains visible as a sticky element until the next time-bucket section begins.

---

### User Story 6 - Identify Event Actions and Entity Types at a Glance (Priority: P3)

As a project administrator, I want color-coded action badges (created, deleted, updated, started) and entity-type pills displayed next to each event summary so that I can visually distinguish event types without reading each event's full description.

**Why this priority**: Visual badges and pills are a polish enhancement that improves scanning speed on the Activity page. They build on top of the core event logging and stats features and add visual differentiation rather than new functionality.

**Independent Test**: Can be fully tested by loading the Activity page with events of different action types and entity types, then verifying that each event row displays the correct color-coded badge and entity pill.

**Acceptance Scenarios**:

1. **Given** an event with action "created" is displayed, **When** the Activity page renders, **Then** a green badge with the text "created" appears next to the event summary.
2. **Given** an event with action "deleted" is displayed, **When** the Activity page renders, **Then** a red badge with the text "deleted" appears.
3. **Given** an event with action "updated" is displayed, **When** the Activity page renders, **Then** a blue badge with the text "updated" appears.
4. **Given** an event with action "launched" or "triggered" is displayed, **When** the Activity page renders, **Then** a purple badge with the text "started" appears.
5. **Given** an event related to a specific entity type (e.g., pipeline, agent, settings), **When** the Activity page renders, **Then** an entity-type pill displaying the entity type name appears next to the event summary.

---

### Edge Cases

- What happens when the stats endpoint is called but the activity events table is empty? The endpoint returns zero counts and a null or absent last-event timestamp. The frontend stat cards display "0" and "No activity" gracefully.
- What happens when a settings update changes zero fields (no-op save)? The system still logs the event with an empty changed-fields list so the action is recorded, but the detail indicates no fields were modified.
- What happens when a webhook payload cannot be classified into a known action? The system falls back to the existing generic "received" action rather than failing or dropping the event.
- What happens when thousands of events exist and time-bucketed grouping is applied? Grouping is computed client-side over the paginated result set (not all events), so performance is bounded by the page size.
- What happens if the stats endpoint request fails or times out? The frontend renders the stat cards in a loading or error state and still displays the event list below.
- What happens when the orchestrator completes a workflow but the pipeline state is already marked as done? The system logs the completion event idempotently without creating duplicate entries for the same workflow run.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST log an activity event with type "pipeline_run" and action "launched" whenever a pipeline launch creates its issue, including the issue number and agent count in the event detail.
- **FR-002**: System MUST log an activity event with type "agent_execution" and action "completed" when a workflow finishes all its agents.
- **FR-003**: System MUST log an activity event with type "agent_execution" and action "triggered" when the orchestrator starts an individual agent execution, including the agent identifier in the event detail.
- **FR-004**: System MUST log an activity event with type "settings" whenever user, global, or project settings are updated, including the list of changed field names in the event detail.
- **FR-005**: System MUST log an activity event with type "project" and action "created" when a new project is created.
- **FR-006**: System MUST log an activity event with type "project" and action "selected" when a user switches the active project.
- **FR-007**: System MUST log webhook events with action "pr_merged" for PR merge webhooks and action "copilot_pr_ready" for Copilot PR ready webhooks, falling back to action "received" for unrecognized webhook types.
- **FR-008**: System MUST provide a summary stats endpoint that returns the total event count, event count in the last 24 hours, event counts grouped by event type for the last 7 days, and the timestamp of the most recent event.
- **FR-009**: The stats endpoint MUST be computed server-side using database aggregation for efficiency, not client-side aggregation.
- **FR-010**: The Activity page MUST display four stat cards ("Total Events", "Today", "Most Common", "Last Activity") above the filter chips, sourced from the stats endpoint.
- **FR-011**: The Activity page MUST support "Project" (covering project and settings events) and "Execution" (covering orchestrator events) filter categories in addition to existing categories.
- **FR-012**: The Activity page MUST group events into time buckets ("Today", "Yesterday", "This Week", "Earlier") with sticky section headers, computed client-side from event timestamps.
- **FR-013**: The Activity page MUST display color-coded action badges (green for created, red for deleted, blue for updated, purple for started/launched/triggered) next to each event summary.
- **FR-014**: The Activity page MUST display entity-type pills next to event summaries indicating the entity type (e.g., pipeline, agent, settings, project).
- **FR-015**: The stat cards MUST handle the empty state gracefully, displaying zeros and "No activity" when no events exist.
- **FR-016**: All new event types MUST reuse the existing activity events data schema without requiring database migrations; new event types are stored as new string values in the existing event_type column.

### Key Entities

- **Activity Event**: A record of a discrete system action. Key attributes: event type (string), action (string), detail (structured metadata including changed fields, issue numbers, agent identifiers), timestamp, and associated entity reference.
- **Activity Stats**: An aggregated summary of activity events. Key attributes: total event count, last-24h event count, event counts by type for last 7 days, and last event timestamp.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can identify when their last pipeline was launched and whether it completed by viewing the Activity page, without checking any external system.
- **SC-002**: The Activity page loads summary statistics (total events, today's count, most common type, last activity) within 2 seconds of page load.
- **SC-003**: Users can filter the Activity page to show only project/settings events or only execution events using the new filter categories, reducing visible events to only the relevant subset.
- **SC-004**: 100% of settings changes, project lifecycle events, pipeline launches, workflow completions, and classified webhook events produce corresponding activity log entries.
- **SC-005**: Users can identify the time period of any event within 1 second by scanning time-bucket headers, without reading individual timestamps.
- **SC-006**: Users can distinguish event action types (created, deleted, updated, started) at a glance via color-coded badges without reading event descriptions.
- **SC-007**: The stats summary displays accurate data consistent with the underlying event log, with zero discrepancy between displayed counts and actual event records.
- **SC-008**: The Activity page handles the empty state (no events) gracefully, displaying appropriate placeholder content without errors or broken layouts.

## Assumptions

- The existing `activity_events` database table and schema support storing new event type string values without requiring a migration.
- The existing `log_event` function (or equivalent) is available in the backend to record new event types with structured detail data.
- The frontend Activity page already has a filter chip mechanism that can be extended with new categories.
- Stats are computed via server-side database aggregation and not materialized or cached (acceptable performance for the expected event volume).
- Time-bucketed grouping is applied client-side to the current paginated result set and does not require changes to the backend pagination logic.
- No charting library is added; stats are rendered as number cards following the existing stat-box pattern.
- Excluded from scope: user login/logout tracking, search analytics, and cache invalidation events (deemed low value and high noise).
