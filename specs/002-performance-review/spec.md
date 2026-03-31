# Feature Specification: Performance Review

**Feature Branch**: `002-performance-review`
**Created**: 2026-03-31
**Status**: Draft
**Input**: User description: "Perform a balanced first pass focused on measurable, low-risk performance gains across backend and frontend. Start by capturing baselines and instrumentation, then fix the highest-value issues already surfaced by the codebase: backend GitHub API churn around board refreshes and polling, and frontend board responsiveness issues caused by broad query invalidation, full-list rerenders, and hot event listeners. Defer broader architectural refactors like virtualization and large service decomposition unless the first pass fails to meet targets."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Idle Board Stops Wasting Background Requests (Priority: P1)

A user opens a project board and leaves it idle in their browser tab. Today, the system continues to send repeated requests to the external project-management service even when the board data has not changed. After this improvement, an idle board consumes significantly fewer background requests, preserving the shared request budget for actual user-initiated work.

**Why this priority**: Unnecessary background request consumption is the single highest-cost issue. It directly erodes the shared request budget that every user depends on, and it worsens as more users keep boards open simultaneously. Fixing this unlocks headroom for all other features that depend on the external service.

**Independent Test**: Can be fully tested by opening a board, leaving it idle for a fixed observation window (e.g., 5 minutes), and counting the number of outgoing requests to the external project-management service. Success is verified by comparing the idle request count against an established baseline.

**Acceptance Scenarios**:

1. **Given** a user has a board open and no data changes have occurred on the external service, **When** the board remains idle for 5 minutes, **Then** the system sends no redundant refresh requests beyond the minimum keep-alive or change-detection checks.
2. **Given** a user has a board open and a real data change occurs on the external service, **When** the change-detection mechanism detects it, **Then** the board refreshes promptly with the updated data without requiring a manual action.
3. **Given** the real-time connection is unavailable and the system falls back to periodic checking, **When** the fallback mechanism runs, **Then** it performs only lightweight change-detection checks and does not trigger a full board data reload unless changes are actually detected.

---

### User Story 2 - Board Interactions Feel Responsive (Priority: P2)

A user interacts with their project board — scrolling through columns, dragging tasks between columns, hovering over cards for details, or opening popovers. Today, these interactions can feel sluggish due to the entire board re-rendering on every minor data update, heavy derived-data recalculations on each render cycle, and event listeners firing at excessive rates. After this improvement, board interactions are noticeably smoother and more responsive.

**Why this priority**: Board responsiveness is the most visible user-facing quality signal. While it does not consume shared service budget like idle API churn, sluggish interactions erode user trust and productivity. This is the second priority because the baseline measurement phase (User Story 1) also captures the render data needed here.

**Independent Test**: Can be fully tested by profiling board load time and interaction responsiveness on a representative board (e.g., 5+ columns, 50+ visible tasks), measuring time-to-interactive and frame rates during drag, scroll, and popover interactions. Verified by comparing against baseline measurements.

**Acceptance Scenarios**:

1. **Given** a user loads a board with a typical number of columns and tasks, **When** the board finishes loading, **Then** it becomes interactive within a reasonable time (target: measurably faster than baseline).
2. **Given** a user drags a task card between columns, **When** the drag is in progress, **Then** the visual feedback is smooth without noticeable frame drops or lag.
3. **Given** a lightweight task update arrives via the real-time connection, **When** the update is applied, **Then** only the affected task card and its immediate context re-render rather than the entire board surface.
4. **Given** a user opens a popover (e.g., agent assignment) on a board card, **When** the popover is displayed and the user interacts with it, **Then** positioning updates are throttled and do not cause visible jank.

---

### User Story 3 - Refresh Paths Are Coherent and Predictable (Priority: P2)

A user relies on multiple ways their board data stays current: real-time updates via the live connection, automatic background refreshes, fallback checking when the live connection is down, and explicit manual refresh. Today, these paths overlap and can trigger redundant expensive operations (e.g., fallback polling invalidating the full board data query). After this improvement, each refresh path has a clear role, and they do not duplicate each other's work.

**Why this priority**: This is tied with User Story 2 because incoherent refresh paths cause both unnecessary backend requests (User Story 1) and unexpected frontend re-renders (User Story 2). Fixing the refresh contract is a prerequisite for the other improvements to hold.

**Independent Test**: Can be fully tested by simulating each refresh path independently (live update, auto-refresh timer, fallback poll, manual refresh button) and verifying which data queries each one triggers. Verified by inspecting network activity and confirming no unexpected full board reloads.

**Acceptance Scenarios**:

1. **Given** a live connection update arrives for a single task, **When** the update is processed, **Then** only the lightweight task-level data refreshes and the expensive full board data query is not triggered.
2. **Given** the live connection is unavailable and fallback checking activates, **When** the fallback check runs, **Then** it detects whether changes occurred without triggering a full board data reload unless changes are confirmed.
3. **Given** a user clicks the manual refresh button, **When** the refresh executes, **Then** it bypasses all caches and performs a full board data reload as intended.
4. **Given** multiple refresh sources fire within a short window, **When** the system processes them, **Then** redundant refresh operations are deduplicated and only one board data reload occurs.

---

### User Story 4 - Baselines Prove Improvements Are Real (Priority: P1)

Before any optimization work begins, the team captures performance baselines covering both backend request patterns and frontend rendering behavior. After optimizations are applied, the same measurements are repeated to produce a before/after comparison. This ensures that claimed improvements are data-driven and verifiable rather than assumed.

**Why this priority**: Tied with User Story 1 as the highest priority because all success criteria depend on having baselines. Without measurement, there is no way to confirm improvements or detect regressions. This story blocks all other optimization work.

**Independent Test**: Can be fully tested by executing the baseline measurement procedure on the current (unmodified) system, recording the results, and verifying that the measurement methodology produces consistent and repeatable numbers.

**Acceptance Scenarios**:

1. **Given** the system is running in its current unmodified state, **When** the baseline measurement procedure is executed, **Then** it produces documented measurements for idle request count over a fixed interval, board load time, interaction frame rates, and render hot-spot frequency.
2. **Given** optimization changes have been applied, **When** the same measurement procedure is repeated, **Then** the results can be directly compared to the baseline with clear before/after values for each metric.
3. **Given** a future code change is made after the optimization pass, **When** the existing automated test suite runs, **Then** it detects regressions in cache behavior, refresh deduplication, and polling safety without requiring manual profiling.

---

### User Story 5 - Regression Coverage Prevents Backsliding (Priority: P3)

After performance improvements are delivered, the team extends automated test coverage to guard against regressions. The tests cover backend cache behavior, change-detection logic, fallback polling safety, and frontend refresh coordination. Future changes that accidentally reintroduce wasteful patterns are caught by the test suite before reaching production.

**Why this priority**: This is a sustainability concern rather than an immediate user-facing improvement. It depends on the optimization work being completed first, but it is essential for long-term value retention.

**Independent Test**: Can be fully tested by running the backend and frontend automated test suites and confirming that new regression tests pass. Verified by intentionally breaking a guarded behavior (e.g., removing change detection) and confirming the relevant test fails.

**Acceptance Scenarios**:

1. **Given** backend cache and change-detection logic are working correctly, **When** the backend test suite runs, **Then** all new regression tests covering cache TTL behavior, stale-data fallback, and change-detection pass.
2. **Given** frontend refresh coordination is working correctly, **When** the frontend test suite runs, **Then** all new regression tests covering refresh path separation, deduplication, and fallback safety pass.
3. **Given** a developer accidentally removes change detection from the refresh subscription logic, **When** the test suite runs, **Then** at least one test fails explicitly indicating the regression.

### Edge Cases

- What happens when the real-time connection drops during an active drag-and-drop operation? The in-progress interaction should complete locally, and the refresh should reconcile state once the connection is restored rather than interrupting the user.
- What happens when the external service rate limit is already near exhaustion? The system should respect rate-limit headers and back off gracefully, avoiding retry storms that further deplete the budget.
- What happens when a board has zero tasks or only one column? Optimization logic (memoization, deduplication) should not error on empty or minimal data structures.
- What happens when multiple users view the same board simultaneously? Cache behavior should serve shared data efficiently without one user's manual refresh forcing another user's cache to invalidate prematurely.
- What happens when the fallback polling activates at the same moment the real-time connection recovers? The system should detect the restored connection and stop fallback polling without triggering a duplicate refresh.

## Requirements *(mandatory)*

### Functional Requirements

#### Phase 1 — Baseline and Guardrails

- **FR-001**: System MUST provide a documented procedure for measuring idle backend request activity for an open board over a fixed observation interval (e.g., 5 minutes).
- **FR-002**: System MUST provide a documented procedure for measuring frontend board load time, interaction frame rates, and identifying rerender hot spots on a representative board.
- **FR-003**: System MUST reuse existing automated tests around cache behavior, polling logic, and refresh coordination to establish a before/after regression checklist.
- **FR-004**: System MUST confirm the current implementation state of board cache TTL alignment, change detection on the real-time subscription, and sub-issue cache invalidation before optimization work begins.

#### Phase 2 — Backend Request Reduction

- **FR-005**: System MUST suppress redundant board refresh requests when the real-time subscription detects no data changes on the external service.
- **FR-006**: System MUST ensure that warm sub-issue caches materially reduce the number of outgoing requests during a board data refresh.
- **FR-007**: System MUST ensure that fallback polling (when the real-time connection is unavailable) performs lightweight change detection rather than triggering a full board data reload.
- **FR-008**: System MUST eliminate any duplicate resolution logic for repository identification that adds unnecessary external service calls.

#### Phase 2 — Frontend Refresh Path Cleanup

- **FR-009**: System MUST decouple lightweight task-level updates received via the real-time connection from the expensive full board data query, so that a single-task update does not trigger a full board reload.
- **FR-010**: System MUST ensure that fallback polling does not invalidate the full board data query; it should only trigger a full reload when changes are confirmed.
- **FR-011**: System MUST ensure that manual refresh explicitly bypasses all caches and performs a complete board data reload.
- **FR-012**: System MUST deduplicate refresh operations when multiple refresh sources (real-time, auto-refresh, fallback, manual) fire within a short window.

#### Phase 3 — Frontend Render Optimization

- **FR-013**: System MUST reduce unnecessary re-computation of derived board data (sorting, filtering, aggregation) on renders where the underlying data has not changed.
- **FR-014**: System MUST stabilize component inputs for high-frequency render targets (task cards, board columns) so that unchanged items do not re-render when sibling items update.
- **FR-015**: System MUST throttle high-frequency event listeners (drag positioning, popover positioning) to prevent excessive re-render cycles during user interactions.

#### Phase 3 — Verification and Regression Coverage

- **FR-016**: System MUST extend backend automated test coverage to validate cache TTL behavior, stale-data fallback, change-detection logic, and polling safety.
- **FR-017**: System MUST extend frontend automated test coverage to validate refresh path separation (real-time vs. fallback vs. auto-refresh vs. manual), deduplication behavior, and board query invalidation rules.
- **FR-018**: System MUST pass all existing automated tests after optimizations are applied, confirming no functional regressions.

### Key Entities

- **Board Data**: The complete project board state including all columns, tasks, and their metadata. This is the expensive resource that should be fetched sparingly.
- **Task Update**: A lightweight change to a single task's attributes (status, assignee, labels). Should be processable without a full board data reload.
- **Sub-Issue Cache**: Cached sub-issue data associated with board tasks. When warm, it reduces the number of outgoing requests during board refresh.
- **Refresh Source**: The origin of a data refresh request — one of: real-time subscription, auto-refresh timer, fallback polling, or manual user action. Each source has different cache-bypass semantics.
- **Performance Baseline**: A recorded set of measurements (idle request count, board load time, interaction frame rates, rerender frequency) captured before optimization work begins.

## Assumptions

- The external service rate limit budget is shared across all features, so reducing idle consumption has broad positive impact beyond just board viewing.
- The existing 300-second cache TTL on the board endpoint is a reasonable default and does not need to change, only needs to be verified as consistently applied.
- The current real-time connection mechanism already supports change detection at the subscription level; the optimization work targets ensuring it is fully wired rather than building it from scratch.
- A "representative board" for baseline measurement means approximately 5+ columns and 50+ visible tasks, which reflects typical usage patterns.
- Low-risk optimizations (memoization, throttling, deduplication) are sufficient for the first pass. Board virtualization, new dependencies, and major service decomposition are explicitly deferred unless first-pass measurements prove them necessary.
- Fallback polling interval and auto-refresh interval are already configured at reasonable defaults; the optimization targets what they trigger, not their timing.

## Scope Boundaries

**In scope for the first pass**:

- Baseline measurement and documentation
- Backend idle request reduction (change detection, cache reuse, polling safety)
- Frontend refresh path cleanup (decouple task updates from board queries, fix fallback invalidation)
- Low-risk frontend render optimization (memoize, stabilize props, throttle listeners)
- Regression test extension for optimized behaviors

**Explicitly out of scope unless measurements justify it**:

- Board virtualization for large boards
- Major service decomposition of the project-fetching pipeline
- Introduction of new external dependencies
- Changes to cache TTL values (only verify current values are applied correctly)
- Changes to polling or auto-refresh intervals
- Larger architectural rewrites

## Dependencies

- Phase 1 (baselines) blocks all optimization work in Phases 2 and 3.
- Phase 2 backend and frontend work can proceed in parallel once baselines are captured and the refresh contract is confirmed.
- Phase 3 render optimization can proceed in parallel with Phase 2 backend work but depends on Phase 2 frontend refresh path cleanup being at least defined.
- Phase 3 verification depends on Phase 2 and Phase 3 optimization work being complete.
- Phase 4 (optional second-wave) is blocked by Phase 3 verification results and is out of scope unless metrics prove it necessary.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An idle board (no data changes on the external service) generates at least 50% fewer background requests over a 5-minute observation window compared to the pre-optimization baseline.
- **SC-002**: Board load time on a representative board (5+ columns, 50+ tasks) is measurably faster than the pre-optimization baseline, with a target improvement of at least 20%.
- **SC-003**: A single-task update received via the real-time connection does not trigger a full board data reload, reducing the per-update request cost to the minimum necessary (task-level only).
- **SC-004**: Fallback polling, when active, does not trigger full board data reloads unless actual changes are detected, reducing unnecessary refresh-triggered requests to zero when data is unchanged.
- **SC-005**: Board drag-and-drop and popover interactions maintain smooth visual feedback without user-perceptible frame drops, as verified by interaction profiling.
- **SC-006**: All existing automated tests continue to pass after optimizations, and new regression tests cover the key optimized behaviors (cache, change detection, refresh deduplication, polling safety).
- **SC-007**: The before/after performance comparison is documented with specific numbers for each measured metric, providing a verifiable record of improvements.
