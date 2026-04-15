# Feature Specification: Loading Performance

**Feature Branch**: `loading-performance`
**Created**: 2026-04-15
**Status**: Draft
**Input**: User description: "Reducing initial Project import/load time in Solune. When user selects a GitHub project after login."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Fast Project Load on Small Boards (Priority: P1)

A user logs into Solune and selects a GitHub project that contains 12–13 items. The board view loads quickly, showing all columns, items, and parent issue cards with their sub-issue pill links. The user perceives a responsive, near-instant experience with the board appearing in under 2 seconds after project selection.

**Why this priority**: Small projects are the most common use case and the first impression for new users. Reducing the 1.8–2.2 second critical-path load to under 2 seconds ensures the majority of users experience a fast, responsive application. This directly impacts user retention and satisfaction.

**Independent Test**: Can be fully tested by logging in, selecting a small project (≤20 items), and measuring the time from clicking "Select" to the board becoming fully interactive. Delivers value by making the most common user flow feel instant.

**Acceptance Scenarios**:

1. **Given** a user has logged in and sees their project list, **When** they select a small project (≤20 items), **Then** the board view loads and becomes interactive within 2 seconds.
2. **Given** a user selects a small project, **When** the board is loading, **Then** a loading indicator is displayed until the board is ready, and the user is never shown a blank or broken state.
3. **Given** a user has previously loaded a project in the same session, **When** they navigate back to it, **Then** cached data is shown immediately while any background refresh occurs silently.

---

### User Story 2 - Usable Board on Large Projects (Priority: P1)

A user selects a large GitHub project containing hundreds of items and hundreds of sub-issues. Instead of waiting 40+ seconds for the entire board to load, the user sees active columns (non-Done) appear within a few seconds. Closed or Done parent issues load progressively in the background without blocking the user from interacting with the board. The user can begin triaging, reviewing, and navigating active items while historical data streams in behind the scenes.

**Why this priority**: Large projects represent the highest-value users — teams managing significant workloads. A 40-second blocking load is unacceptable and risks abandonment. Progressive loading keeps these users productive while data continues to arrive.

**Independent Test**: Can be fully tested by selecting a large project (500+ items) and verifying that active columns appear within the target time while Done column items load progressively. Delivers value by making large projects usable from the moment the board appears.

**Acceptance Scenarios**:

1. **Given** a user selects a large project (500+ items), **When** the board is loading, **Then** active (non-Done) columns and their items are visible and interactive within 8 seconds.
2. **Given** a large project is selected, **When** active columns have loaded, **Then** Done/closed parent issues and their sub-issues load progressively in the background without blocking user interaction.
3. **Given** a large project is loading, **When** historical items are still being fetched, **Then** the board displays a subtle progress indicator for the Done column while other columns are fully interactive.
4. **Given** a large project has completed loading, **When** the user inspects Done column items, **Then** all parent issues and sub-issue pills are present and correct.

---

### User Story 3 - Smooth Cold-Start Experience (Priority: P2)

A user logs in for the first time in a session (cold start) and selects a project. The system avoids making redundant requests to external services. The user does not experience additional latency caused by duplicate data fetches or background processes competing for resources during the initial load.

**Why this priority**: Cold starts are unavoidable and happen every login. Eliminating wasted work (duplicate requests, premature background tasks) improves load time without requiring architectural changes. This is a "free" performance gain that benefits every user on every session.

**Independent Test**: Can be tested by clearing all caches, logging in, selecting a project, and verifying that external service calls are not duplicated and that background processes do not compete with the critical load path. Delivers value by shaving seconds off every first-load experience.

**Acceptance Scenarios**:

1. **Given** a user logs in for the first time in a session, **When** they select a project, **Then** the system makes at most one request per distinct data need (no duplicate fetches for the same information).
2. **Given** a user selects a project, **When** the project data is being loaded, **Then** non-essential background processes (such as polling for agent activity) do not start until the board has finished its initial load.
3. **Given** a user has previously loaded a project in the same session, **When** they navigate back to it, **Then** cached data is served instantly and only a background refresh is triggered if the data is stale.

---

### User Story 4 - Sub-Issue Optimization for Completed Work (Priority: P2)

A user's project board contains parent issues in the Done column or with a closed status. The system recognizes that these completed items are unlikely to change and avoids fetching their sub-issue metadata during the initial board load. Sub-issue pills for Done/closed parent issues still appear correctly using previously cached or stored data. If the user explicitly requests a refresh, sub-issues for completed items are fetched on demand.

**Why this priority**: The performance analysis shows that Done column items represent 99.5% of the board payload on large projects (398 KB out of 399 KB). Skipping sub-issue fetches for these stable items dramatically reduces load time without impacting the user experience, since sub-issue metadata is not displayed in the board UX — only hyperlinked pills are shown.

**Independent Test**: Can be tested by loading a project with many Done/closed parent issues, verifying that active items load quickly, and confirming that Done column sub-issue pills still render correctly from stored data. Delivers value by eliminating the largest single performance bottleneck.

**Acceptance Scenarios**:

1. **Given** a project has parent issues in the Done column, **When** the board initially loads, **Then** sub-issue data for Done/closed parent issues is not fetched from the external service.
2. **Given** Done column parent issues have previously fetched sub-issue data, **When** the board loads, **Then** the stored sub-issue pills are displayed correctly using cached data.
3. **Given** a parent issue transitions from active to Done between sessions, **When** the user loads the board, **Then** the parent issue's previously fetched sub-issue data is retained and displayed in the Done column.
4. **Given** the user explicitly triggers a full board refresh, **When** the refresh completes, **Then** sub-issues for Done/closed parent issues are also refreshed.

---

### User Story 5 - Background Data Reconciliation (Priority: P3)

After the board has loaded and the user is interacting with it, the system performs a background reconciliation pass to catch any items that may have been missed due to external service eventual consistency. This reconciliation happens silently and does not interrupt the user's workflow. Any newly discovered items are seamlessly added to the board.

**Why this priority**: Reconciliation ensures data completeness but costs 683–791ms even when no items are found. Deferring it to after the board is interactive eliminates this cost from the critical load path while still ensuring eventual accuracy.

**Independent Test**: Can be tested by loading a board, waiting for the background reconciliation to complete, and verifying that any newly discovered items appear in the correct columns without a page reload. Delivers value by ensuring data accuracy without sacrificing load speed.

**Acceptance Scenarios**:

1. **Given** the board has finished its initial load, **When** background reconciliation runs, **Then** any newly discovered items appear in the correct columns without requiring a page reload.
2. **Given** the board is loading, **When** reconciliation has not yet run, **Then** the board displays all items found during the initial fetch and does not wait for reconciliation to complete.
3. **Given** reconciliation finds zero new items, **When** it completes, **Then** the board remains unchanged and the user is not notified or interrupted.

---

### Edge Cases

- What happens when a project has only Done/closed items and no active items? The board loads with an empty active area and a message indicating no active items, while Done column data loads in the background.
- What happens when the external service is unreachable during initial load? The system serves the most recent cached board data with a notice that the data may be stale, and retries in the background.
- What happens when a parent issue changes status from Done to active between sessions? The system detects the status change during the next load and fetches fresh sub-issue data for the reactivated item.
- What happens when background reconciliation discovers a large number of missing items? The items are added incrementally to the board without causing a disruptive re-render or layout shift.
- What happens when multiple browser tabs load the same project simultaneously? Each tab loads independently using shared cache data, and redundant external service requests are deduplicated.
- What happens when a user rapidly switches between projects? The system cancels in-flight requests for the previous project and begins loading the newly selected project without accumulated latency.

## Requirements *(mandatory)*

### Functional Requirements

#### Board Data Loading

- **FR-001**: System MUST load and display active (non-Done, non-closed) board items before loading historical items.
- **FR-002**: System MUST display Done/closed parent issue sub-issue pills using previously stored data without fetching fresh sub-issue metadata on initial load.
- **FR-003**: System MUST allow users to trigger a full refresh that includes fetching sub-issue data for Done/closed parent issues on demand.
- **FR-004**: System MUST perform data reconciliation as a background task after the board is interactive, not as part of the initial critical load path.
- **FR-005**: System MUST seamlessly merge background-reconciled items into the board without requiring a page reload or disrupting user interaction.

#### Request Optimization

- **FR-006**: System MUST deduplicate in-flight requests so that concurrent calls for the same data result in a single external service request.
- **FR-007**: System MUST begin preparing board data as soon as the user confirms project selection, before the board view requests it.
- **FR-008**: System MUST defer non-essential background processes (such as agent activity polling) until the board has completed its initial load.

#### Caching

- **FR-009**: System MUST serve cached board data immediately on repeat visits within the same session, triggering a background refresh if the data is stale.
- **FR-010**: System MUST retain sub-issue data for Done/closed parent issues across sessions so that sub-issue pills can be rendered without refetching.

#### User Experience

- **FR-011**: System MUST display a loading indicator while board data is being fetched, and transition smoothly to the loaded state.
- **FR-012**: System MUST not display blank, broken, or partially rendered board states during loading.
- **FR-013**: System MUST display a subtle progress indicator for sections of the board that are still loading (e.g., Done column) while other sections are interactive.

### Assumptions

- Sub-issue metadata is not displayed or used in the board UX. Only parent GitHub Issues are displayed, and sub-issues are shown as attached pill links that navigate to GitHub.
- Done/closed parent issues and their sub-issues have a very low probability of metadata or status changes between user sessions. Deletion is more likely than update.
- The current performance bottleneck is dominated by sequential sub-issue data fetches and data reconciliation, not by network bandwidth or payload size of individual responses.
- The external service supports conditional requests (ETag/If-Modified-Since) that can be leveraged for efficient cache validation.
- The existing in-memory caching infrastructure and stale-fallback mechanisms are stable and can be extended without replacement.
- Standard web application performance expectations apply: page loads under 3 seconds for typical use, progressive rendering for exceptional cases.
- Frontend adaptive polling mechanisms already adjust refetch intervals based on detected activity and do not require modification.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users selecting a small project (≤20 items) see a fully interactive board within 2 seconds, down from the current 1.8–2.2 second baseline.
- **SC-002**: Users selecting a large project (500+ items) see active columns within 8 seconds, down from the current ~40 second full-blocking load.
- **SC-003**: Cold-start project selection completes without any duplicate external service requests for the same data.
- **SC-004**: Background processes do not add measurable latency to the critical board-loading path on any project size.
- **SC-005**: Previously loaded projects serve cached data within 500 milliseconds on repeat visits in the same session.
- **SC-006**: Data reconciliation completes in the background without any user-visible delay or interruption to board interaction.
- **SC-007**: Done/closed parent issues display correct sub-issue pills on initial load without triggering fresh sub-issue fetches.
- **SC-008**: 95% of users can begin interacting with their board (click, scroll, navigate) within the target load times on first attempt.
