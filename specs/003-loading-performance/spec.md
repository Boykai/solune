# Feature Specification: Loading Performance

**Feature Branch**: `003-loading-performance`
**Created**: 2026-04-15
**Status**: Draft
**Input**: User description: "Reducing initial Project import/load time in Solune. When user selects a GitHub project after login."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Fast Project Board Load on Selection (Priority: P1)

A user logs into Solune, sees their list of GitHub projects, and selects one. The project board loads and becomes interactive noticeably faster than before. For small projects (12–13 items), the board appears in under 2 seconds. For large projects (hundreds of items), the user sees meaningful content within 5 seconds, with remaining data loading progressively in the background.

**Why this priority**: This is the core user pain point — every user experiences the project load delay on every session. Reducing the critical-path time from project selection to usable board delivers the highest-impact improvement to the most users.

**Independent Test**: Can be fully tested by logging in, selecting a project, and measuring the time until the board is interactive. Delivers immediate value by eliminating the most visible wait time in the application.

**Acceptance Scenarios**:

1. **Given** a user is on the project list after login, **When** they select a small project (under 50 items), **Then** the project board loads and becomes interactive in under 2 seconds.
2. **Given** a user is on the project list after login, **When** they select a large project (hundreds of items), **Then** the project board displays meaningful content within 5 seconds, with remaining data appearing progressively.
3. **Given** a user selects a project, **When** the board data begins loading, **Then** the system begins preparing board data immediately upon project selection rather than waiting for the frontend to request it.
4. **Given** a user selects a project, **When** the board loads, **Then** sub-issue metadata that is not displayed in the board UI is not fetched during the initial load.

---

### User Story 2 - Skip Unnecessary Work for Completed Items (Priority: P1)

When a project board loads, parent issues in the "Done" column or with a "closed" status do not trigger sub-issue fetching. Since these items have a very low probability of metadata changes, the system avoids wasting time and external service calls on data that is unlikely to have changed and is not needed for the initial board display.

**Why this priority**: Sub-issue fetching for closed/done items is a major contributor to load time on large projects (55 individual sub-issue requests in the profiled large project). Eliminating this unnecessary work directly reduces the largest bottleneck identified in the performance analysis.

**Independent Test**: Can be tested by loading a project with items in the "Done" column and verifying that sub-issues for those items are not fetched during the initial load. Delivers value by reducing load time proportional to the number of completed items.

**Acceptance Scenarios**:

1. **Given** a project has parent issues in the "Done" column, **When** the board loads, **Then** sub-issues for those "Done" items are not fetched during the initial load.
2. **Given** a project has closed parent issues, **When** the board loads, **Then** sub-issues for those closed items are not fetched during the initial load.
3. **Given** a "Done" parent issue is moved back to an active column by the user, **When** the board refreshes, **Then** sub-issues for that item are fetched at that time.
4. **Given** all parent issues in a project are in the "Done" column, **When** the board loads, **Then** zero sub-issue fetches occur and the board loads with only the parent issue data.

---

### User Story 3 - Eliminate Duplicate Data Fetches (Priority: P2)

When a user first opens Solune and selects a project, the system avoids making duplicate requests for the same data. Currently, the frontend fires two simultaneous requests for project list data that both miss the cache and hit the external service. The system deduplicates these in-flight requests so only one external call is made.

**Why this priority**: Duplicate fetches waste external service quota and add unnecessary latency on the critical path. While the savings (~1.1 seconds) are modest compared to the board data bottleneck, deduplication is a low-effort fix that also reduces rate-limit risk.

**Independent Test**: Can be tested by monitoring network requests during project selection and verifying that only one external call is made for project list data, even when multiple components request the same data simultaneously.

**Acceptance Scenarios**:

1. **Given** the user opens Solune for the first time in a session, **When** multiple components simultaneously request the project list, **Then** only one external request is made and the result is shared across all requestors.
2. **Given** the project list has been fetched once, **When** another component requests the same data before the cache expires, **Then** the cached result is returned without an additional external call.
3. **Given** an in-flight request for project list data exists, **When** a second request for the same data arrives, **Then** the second request waits for and reuses the result of the first request.

---

### User Story 4 - Non-Blocking Background Processing (Priority: P2)

When a user selects a project, any background processing that is not essential for the initial board display is deferred until after the board is fully loaded and interactive. Background tasks such as automated polling and reconciliation run after the user can see and interact with the board, rather than competing for resources during the critical load window.

**Why this priority**: Background processing contention adds 15–20 seconds on large boards and causes visible slowdown even on small boards. Deferring non-essential processing is a low-complexity change that eliminates contention without altering the processing logic itself.

**Independent Test**: Can be tested by selecting a project and verifying that background tasks do not begin until after the board is interactive, and that the board loads without competing for resources with background operations.

**Acceptance Scenarios**:

1. **Given** a user selects a project, **When** the board begins loading, **Then** automated polling does not start until the board is fully loaded and interactive.
2. **Given** a user selects a large project, **When** the board loads, **Then** background processing does not degrade the board load time.
3. **Given** background processing is deferred, **When** the board finishes loading, **Then** deferred background tasks begin automatically without user intervention.
4. **Given** the board has loaded and background tasks are running, **When** the user interacts with the board, **Then** background tasks do not cause noticeable UI lag or data staleness.

---

### User Story 5 - Defer Reconciliation to Background (Priority: P3)

After the board loads, the system runs a data reconciliation check in the background to ensure consistency between different data sources. This reconciliation previously ran during the initial load (adding 683–791ms even when no discrepancies were found). By deferring it, the initial load is faster while data integrity is still maintained.

**Why this priority**: Reconciliation is important for data integrity but does not need to block the initial display. Users see the board faster while consistency checks happen transparently after the board is interactive.

**Independent Test**: Can be tested by loading a project board, verifying the board appears without reconciliation delay, and then confirming that reconciliation completes in the background within a reasonable time window.

**Acceptance Scenarios**:

1. **Given** a user selects a project, **When** the board loads, **Then** reconciliation does not run as part of the initial load sequence.
2. **Given** the board has loaded, **When** background reconciliation runs, **Then** any discrepancies found are resolved without disrupting the user's current view.
3. **Given** reconciliation finds zero discrepancies (the common case), **When** it completes in the background, **Then** no visible change occurs on the board.
4. **Given** reconciliation finds discrepancies, **When** it resolves them, **Then** the board updates smoothly to reflect the corrected data.

---

### Edge Cases

- What happens when a project has zero items? The board loads immediately with an empty state, and no sub-issue or reconciliation work is triggered.
- What happens when the external service is rate-limited during board load? The system displays whatever data it has already retrieved and retries failed requests after a delay, showing a non-blocking notification to the user.
- What happens when a user rapidly switches between projects? The system cancels pending data fetches for the previously selected project and starts fresh for the newly selected one, preventing resource contention.
- What happens when all items in a project are in the "Done" column? The board loads with only parent issue data and zero sub-issue fetches, resulting in the fastest possible load time.
- What happens when a background reconciliation is still running and the user switches projects? The in-progress reconciliation is cancelled to free up resources for the new project's load.
- What happens when the project list cache expires during a session? The next project-related request triggers a fresh fetch, but any in-flight or recent results are reused rather than duplicated.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST begin preparing board data immediately when the user selects a project, rather than waiting for a separate frontend request.
- **FR-002**: System MUST skip sub-issue fetching for parent issues that are in the "Done" column or have a "closed" status during the initial board load.
- **FR-003**: System MUST deduplicate simultaneous in-flight requests for the same project list data so that only one external call is made.
- **FR-004**: System MUST defer automated polling until after the project board is fully loaded and interactive.
- **FR-005**: System MUST defer data reconciliation from the initial load sequence to a background process that runs after the board is displayed.
- **FR-006**: System MUST ensure that sub-issues for "Done" or "closed" parent issues are fetched when those items are moved back to an active column.
- **FR-007**: System MUST cancel pending data fetches and background tasks for a previously selected project when the user switches to a different project.
- **FR-008**: System MUST display a non-blocking notification to the user if external service rate limits or errors prevent some data from loading, while still showing any data that was successfully retrieved.
- **FR-009**: System MUST ensure that deferred background tasks (reconciliation, polling) start automatically after the board is interactive, without requiring user action.
- **FR-010**: System MUST preserve all existing board functionality — the performance optimizations must not remove, alter, or degrade any user-visible features.
- **FR-011**: System MUST NOT display sub-issue metadata in the board UI, consistent with the current design where only parent issues are shown on the board and sub-issues appear as linked pills that navigate to GitHub.

### Assumptions

- The current board UI design, where only parent GitHub issues are displayed and sub-issues appear as attached pills linking to GitHub, will remain unchanged for this feature.
- Sub-issue metadata is not displayed or used in the board UI; it is only used for linked pill rendering (title and URL), which can be derived from the parent issue data or fetched lazily.
- "Done" column identification and "closed" status detection are already available from the existing board data structure.
- The performance profiling data (small project: 1.8–2.2s critical path; large project: ~40s) is representative of typical user scenarios and can be used as a baseline.
- Industry-standard web application performance expectations apply: interactive UI within 2 seconds for small datasets, 5 seconds for large datasets.
- The existing cache infrastructure can be leveraged for request deduplication without architectural changes.
- Background reconciliation and polling logic does not need to be rewritten — only the timing of when it starts needs to change.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users with small projects (under 50 items) experience project board load times of under 2 seconds from project selection to interactive board.
- **SC-002**: Users with large projects (hundreds of items) see meaningful board content within 5 seconds of project selection, with remaining data loading progressively.
- **SC-003**: The number of external service calls made during initial project load is reduced by at least 50% compared to the current baseline.
- **SC-004**: No duplicate external service requests are made for the same data within a single project load sequence.
- **SC-005**: Background processing (polling, reconciliation) does not begin until after the board is interactive, eliminating resource contention during the critical load window.
- **SC-006**: Sub-issue fetching for "Done" or "closed" parent issues is eliminated from the initial load, reducing load time proportionally to the number of completed items.
- **SC-007**: All existing board features continue to function correctly after performance optimizations are applied — zero regressions in user-visible functionality.
- **SC-008**: Users can interact with the board (scroll, click, drag) within the target load time without waiting for background tasks to complete.
- **SC-009**: 90% of users perceive the project load as "fast" or "acceptable" based on the sub-2-second (small) and sub-5-second (large) targets.
