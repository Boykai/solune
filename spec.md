# Feature Specification: Performance Review

**Feature Branch**: `001-performance-review`
**Created**: 2026-04-18
**Status**: Draft
**Input**: User description: "Perform a balanced first pass focused on measurable, low-risk performance gains across backend and frontend."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Baseline Measurement and Guardrails (Priority: P1)

As a developer preparing to optimize the application, I need current performance baselines captured for both backend and frontend before any code changes are made, so that every improvement can be measured against a known starting point and regressions can be detected immediately.

**Why this priority**: Without baselines, no optimization can be proven effective. This story blocks all subsequent work because success criteria and regression guardrails depend on captured measurements.

**Independent Test**: Can be fully tested by running baseline measurement procedures against a representative project board and recording idle API call counts, board endpoint response times, WebSocket/polling refresh intervals, and frontend render timings. Delivers a reusable before/after comparison framework.

**Acceptance Scenarios**:

1. **Given** a user has an open board with an active project, **When** the board is left idle for 5 minutes with no user interaction, **Then** the number of backend API calls made to GitHub during that period is recorded as the idle baseline.
2. **Given** a board endpoint request is made, **When** the response is returned, **Then** the request cost (response time, payload size, and GitHub API calls triggered) is recorded as the endpoint cost baseline.
3. **Given** the application is connected via WebSocket, **When** no data changes occur on the board for 5 minutes, **Then** the number of WebSocket-triggered refreshes and their downstream API calls are recorded.
4. **Given** the frontend board is loaded with a representative project, **When** a profiling session captures render timings during initial load and a subsequent interaction (e.g., drag-drop), **Then** render hot spots and rerender counts are recorded as the frontend baseline.
5. **Given** existing tests cover cache, polling, WebSocket fallback, and board refresh behavior, **When** those tests are run before any optimization, **Then** all tests pass and their results form the "before" checklist for regression comparison.

---

### User Story 2 - Reduced Backend API Consumption During Idle Board Viewing (Priority: P1)

As a user viewing a project board without making changes, I expect the application to remain responsive without consuming excessive GitHub API rate-limit budget in the background, so that my rate-limit allocation is preserved for intentional actions like manual refreshes and board interactions.

**Why this priority**: Excessive idle API consumption is the highest-value backend issue. It directly impacts user experience through rate-limit exhaustion and causes unnecessary load on external APIs.

**Independent Test**: Can be fully tested by opening a board, leaving it idle, and measuring the number of GitHub API calls over a fixed interval. Delivers reduced idle API cost and preserved rate-limit budget.

**Acceptance Scenarios**:

1. **Given** a user has an open board connected via WebSocket with no data changes, **When** the board is left idle for 10 minutes, **Then** no repeated unchanged refresh calls are sent to GitHub APIs.
2. **Given** the WebSocket subscription detects no data changes (hash unchanged), **When** the periodic check fires, **Then** only the lightweight hash comparison executes without triggering a full board data fetch.
3. **Given** sub-issue data was previously fetched and cached for a board, **When** the board is refreshed and sub-issue data has not expired, **Then** the cached sub-issue data is reused and no additional GitHub API calls are made for sub-issues.
4. **Given** the polling fallback is active (WebSocket unavailable), **When** a polling cycle executes, **Then** it does not trigger an expensive full board refresh unless data has actually changed.
5. **Given** a user navigates between projects rapidly, **When** switching to a new project, **Then** any in-flight background work for the previous project is cancelled or deprioritized to prevent redundant API consumption.

---

### User Story 3 - Coherent Frontend Refresh Policy (Priority: P2)

As a user interacting with a board, I expect real-time updates (WebSocket), fallback polling, auto-refresh, and manual refresh to work together seamlessly under a single coherent policy, so that lightweight task updates arrive quickly without triggering expensive full board reloads unnecessarily.

**Why this priority**: The frontend refresh path is the second highest-value fix. Incoherent refresh behavior causes redundant network requests, unnecessary full-board rerenders, and potential "polling storms" that freeze the UI.

**Independent Test**: Can be fully tested by simulating WebSocket updates, fallback polling transitions, auto-refresh timer events, and manual refresh actions while monitoring which queries are invalidated and how many board data fetches occur. Delivers a predictable, non-redundant refresh experience.

**Acceptance Scenarios**:

1. **Given** a WebSocket connection is healthy, **When** a lightweight task update arrives (e.g., status change on a single item), **Then** only the affected task data is updated in the UI without invalidating or refetching the full board data query.
2. **Given** the WebSocket connection drops and polling fallback activates, **When** a polling cycle completes, **Then** it refreshes task-level data without triggering a full board data refetch unless the board data is stale beyond the auto-refresh threshold.
3. **Given** a user triggers a manual refresh, **When** the refresh completes, **Then** the board data is fetched fresh from GitHub (bypassing backend caches) and sub-issue caches are cleared as expected.
4. **Given** multiple refresh triggers fire within a short window (e.g., WebSocket reconnection + auto-refresh timer), **When** the debounce window is active, **Then** only one board data fetch executes.
5. **Given** the user's browser tab is hidden and then restored, **When** the tab becomes visible, **Then** the refresh policy evaluates data staleness and refreshes only if the data age exceeds the configured threshold.

---

### User Story 4 - Improved Board Rendering Performance (Priority: P2)

As a user working with a project board containing many columns and items, I expect smooth scrolling, responsive drag-and-drop, and minimal UI lag during normal interactions, so that I can manage my project efficiently without waiting for the interface to catch up.

**Why this priority**: Frontend render performance directly impacts perceived application quality. Low-risk rendering optimizations (memoization, prop stabilization, event listener throttling) can deliver noticeable improvements without introducing new dependencies or architectural changes.

**Independent Test**: Can be fully tested by profiling board interactions (scroll, drag, popover open/close) on a board with a representative number of items and measuring frame rates, rerender counts, and interaction response times. Delivers smoother board interactions.

**Acceptance Scenarios**:

1. **Given** a board with 50+ items across multiple columns is loaded, **When** the user scrolls through a column, **Then** only the visible items and their immediate neighbors rerender (items outside the scroll area do not rerender).
2. **Given** a board item card is dragged from one column to another, **When** the drag is in progress, **Then** the drag interaction maintains responsive frame rates without causing full-column or full-board rerenders.
3. **Given** the user hovers over a board item to open a popover or tooltip, **When** positioning calculations fire, **Then** the positioning listener is throttled so it does not cause excessive layout recalculations.
4. **Given** derived data (sorting, aggregation, filtering) is computed for board display, **When** the underlying data has not changed, **Then** the derived computation is not re-executed on rerender.
5. **Given** the chat popup is open and the user drags to resize it, **When** the drag event fires rapidly, **Then** the drag handler is throttled to prevent excessive state updates and rerenders.

---

### User Story 5 - Verification and Regression Coverage (Priority: P3)

As a developer maintaining the codebase after optimization, I need extended test coverage around the optimized paths so that future changes do not silently regress the performance improvements made in this pass.

**Why this priority**: Test coverage ensures the optimizations are durable. Without regression tests, future feature work could unknowingly reintroduce the performance issues fixed in this pass.

**Independent Test**: Can be fully tested by running the extended test suite and confirming all new and existing tests pass. Also validated by a manual network/profile pass comparing results against the Phase 1 baselines. Delivers confidence that improvements are real and protected.

**Acceptance Scenarios**:

1. **Given** backend cache behavior has been optimized, **When** the cache-related test suite runs, **Then** tests verify correct TTL enforcement, stale fallback behavior, hash-based change detection, and coalesced fetch deduplication.
2. **Given** WebSocket change detection has been validated or improved, **When** the WebSocket-related test suite runs, **Then** tests verify that unchanged data does not trigger downstream refreshes.
3. **Given** the frontend refresh policy has been unified, **When** the refresh hook test suite runs, **Then** tests verify debouncing, auto-refresh suppression during WebSocket connection, and correct manual refresh bypass behavior.
4. **Given** all optimizations are complete, **When** a manual end-to-end check is performed, **Then** the results confirm that WebSocket updates refresh task data quickly, fallback polling remains safe, manual refresh still bypasses caches, and board interactions remain responsive.

---

### User Story 6 - Optional Second-Wave Planning (Priority: P3)

As a product owner reviewing the first-pass results, I want a clear recommendation for whether deeper structural changes are needed based on measured outcomes, so that I can make an informed decision about investing in larger architectural work.

**Why this priority**: This story is explicitly deferred unless first-pass metrics prove it necessary. It ensures the team has a clear path forward if low-risk optimizations are insufficient.

**Independent Test**: Can be fully tested by reviewing the documented measurement comparison (before vs. after baselines) and confirming the recommendation is supported by data. Delivers an actionable follow-on plan or a "no further work needed" conclusion.

**Acceptance Scenarios**:

1. **Given** Phase 1-3 optimizations are complete and measured, **When** large boards (100+ items) still exhibit material UI lag (frame drops, interaction delays exceeding 200ms), **Then** a follow-on plan is prepared recommending board virtualization as the next step.
2. **Given** backend API churn remains above target after targeted fixes, **When** measurement confirms excessive GitHub API calls persist, **Then** a follow-on plan is prepared recommending deeper service consolidation in the GitHub projects service and polling pipeline.
3. **Given** all first-pass targets are met, **When** the before/after comparison shows improvements within goals, **Then** the second-wave plan is documented as "not needed at this time" with the supporting measurements.

---

### Edge Cases

- What happens when the WebSocket connection drops during a manual refresh? The manual refresh should complete independently using the direct API path regardless of WebSocket state.
- How does the system handle a user rapidly switching between multiple projects? In-flight background work for the previous project should be cancelled or deprioritized; the new project's data should take fetch priority.
- What happens when the GitHub API rate limit is exhausted mid-refresh? The system should gracefully fall back to cached/stale data and communicate the rate-limit status to the user without crashing or retrying aggressively.
- How does the system behave when a board has zero items? Empty boards should not trigger sub-issue fetching or expensive derived-data computations.
- What happens when polling fallback and WebSocket reconnection succeed simultaneously? Only one active data channel should remain; the polling fallback should be stopped once WebSocket reconnects.
- What happens when the browser tab has been hidden for an extended period (e.g., overnight)? On tab restore, the system should do a single staleness check and refresh only if needed, not trigger multiple catch-up refreshes.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST capture and record backend performance baselines (idle API call count, board endpoint cost, WebSocket/polling refresh behavior) before any optimization code changes are applied.
- **FR-002**: System MUST capture and record frontend performance baselines (render timings, rerender counts, network activity during board load and interaction) before any optimization code changes are applied.
- **FR-003**: System MUST NOT send repeated refresh requests to GitHub APIs when an idle board's data has not changed, as determined by hash-based change detection.
- **FR-004**: System MUST reuse cached sub-issue data during board refreshes when the sub-issue cache has not expired, reducing the total GitHub API call count for board data retrieval.
- **FR-005**: System MUST ensure that polling fallback does not trigger full board data refreshes when only lightweight task-level updates are needed.
- **FR-006**: System MUST decouple lightweight task updates (delivered via WebSocket or polling) from the expensive full board data query, except during explicit manual refreshes.
- **FR-007**: System MUST enforce a single coherent refresh policy across WebSocket updates, polling fallback, auto-refresh timer, and manual refresh — preventing simultaneous duplicate refresh paths.
- **FR-008**: System MUST debounce concurrent refresh triggers (e.g., WebSocket reconnection + auto-refresh timer) so that only one board data fetch executes within the debounce window.
- **FR-009**: System MUST memoize heavy board components (columns, cards) so that items with unchanged props do not rerender during board-level state changes.
- **FR-010**: System MUST throttle high-frequency event listeners (drag handlers, popover positioning) to prevent excessive layout recalculations and state updates.
- **FR-011**: System MUST avoid re-executing derived data computations (sorting, aggregation, filtering) when the underlying source data has not changed.
- **FR-012**: System MUST extend or adjust unit and integration test coverage to validate the optimized backend cache behavior, WebSocket change detection, polling fallback, and frontend refresh logic.
- **FR-013**: System MUST preserve existing manual refresh behavior: manual refresh bypasses backend caches and clears sub-issue caches as currently designed.
- **FR-014**: System MUST preserve existing rate-limit handling: stale/cached data is served when rate limits are exhausted, and the user is informed of rate-limit status.
- **FR-015**: System MUST cancel or deprioritize in-flight background work for a previous project when the user switches to a different project.

### Key Entities

- **Board Data Cache**: Represents cached board content including items, columns, and metadata. Key attributes: cache key (project ID + load mode), TTL (300 seconds), data hash for change detection, stale-fallback capability.
- **Sub-Issue Cache**: Represents cached sub-issue data associated with board items. Key attributes: parent issue reference, TTL, invalidation on manual refresh.
- **Refresh Policy**: Represents the coordinated rules governing when and how board data is refreshed. Key attributes: source (WebSocket, polling, auto-refresh timer, manual), debounce window, cache bypass rules.
- **Performance Baseline**: Represents a recorded snapshot of system performance metrics at a point in time. Key attributes: measurement timestamp, backend metrics (API call counts, response times), frontend metrics (render timings, rerender counts, network requests).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Idle board viewing (no user interaction, no data changes) produces at least 50% fewer background API calls to GitHub compared to the pre-optimization baseline over a 10-minute observation window.
- **SC-002**: Board data refresh with warm sub-issue caches completes with at least 30% fewer total GitHub API calls compared to a cold-cache refresh of the same board.
- **SC-003**: Lightweight task updates (e.g., single item status change via WebSocket) are reflected in the UI within 2 seconds without triggering a full board data refetch.
- **SC-004**: No more than one board data fetch executes within any 2-second debounce window, regardless of how many refresh triggers fire concurrently.
- **SC-005**: Board interactions (scrolling, drag-and-drop, popover open) on a board with 50+ items maintain a frame rate above 30 frames per second as measured by browser profiling tools.
- **SC-006**: Derived data computations (sorting, filtering, aggregation) for board display do not re-execute when the source data reference is unchanged, as verified by render profiling showing stable computation counts.
- **SC-007**: All existing tests covering cache, polling, WebSocket fallback, and board refresh continue to pass after optimizations are applied (zero regressions).
- **SC-008**: New or extended tests cover the optimized code paths (backend cache behavior, WebSocket change detection, frontend refresh policy, event listener throttling) with at least one test per functional requirement.
- **SC-009**: A manual end-to-end verification confirms that WebSocket updates arrive promptly, fallback polling remains functional, manual refresh bypasses caches as intended, and board interactions remain responsive.
- **SC-010**: Rate-limit budget consumption during idle board viewing is reduced enough that a user maintaining a single open board does not approach rate-limit exhaustion within a typical work session (4+ hours).

## Assumptions

- The current board cache TTL of 300 seconds (5 minutes) and its alignment with the frontend auto-refresh interval is a deliberate and correct design choice that should be preserved.
- The existing hash-based change detection in the cache service and WebSocket subscription is functionally correct; the optimization focus is on ensuring these mechanisms are fully utilized rather than redesigned.
- A "representative project" for baseline measurements contains approximately 50-100 board items across 4-8 columns, reflecting typical usage patterns.
- Board virtualization, major service decomposition, new external dependencies, and large architectural rewrites are explicitly out of scope for this first pass unless measurement data proves they are necessary.
- The coalesced fetch mechanism in the cache service is functioning correctly and preventing duplicate concurrent requests; this does not need to be reimplemented.
- Standard web/mobile application performance expectations apply: page loads under 3 seconds, interactions under 100ms perceived response time, smooth scrolling at 30+ FPS.
- Existing test infrastructure (pytest for backend, Vitest for frontend) is sufficient and does not need replacement or significant tooling changes.
- The stale-fallback mode in the cache service (serving expired data during rate-limit errors) is working correctly and should be preserved as-is.

## Scope Boundaries

### In Scope

- Performance baseline capture (backend and frontend)
- Backend idle API call reduction (WebSocket change detection, sub-issue cache utilization, polling refinement)
- Frontend refresh policy unification (decoupling lightweight updates from full board refetch)
- Frontend render optimization (memoization, prop stabilization, event listener throttling, derived data caching)
- Regression test extension for optimized paths
- Manual verification pass comparing before/after baselines

### Out of Scope (First Pass)

- Board virtualization (deferred unless baseline measurements prove it necessary)
- Major service decomposition in the GitHub projects service or polling pipeline
- Adding new external dependencies or libraries
- Large architectural rewrites or patterns changes
- Performance instrumentation dashboards or monitoring infrastructure beyond what is needed for this pass
- Cache eviction policy changes (LRU, bounded caches) unless a specific issue is identified during measurement
- Image lazy-loading or asset optimization
- Server-side pagination for board data

## Dependencies

- Access to a representative GitHub project with sufficient board items for meaningful baseline measurements
- GitHub API access with adequate rate-limit budget for baseline measurement and testing
- Browser developer tools (or equivalent profiling capabilities) for frontend performance measurement
- Existing test suites must be passing before optimization work begins
