# Feature Specification: Increase Backend Test Coverage & Fix Bugs

**Feature Branch**: `002-backend-test-coverage`  
**Created**: 2026-03-31  
**Status**: Draft  
**Input**: User description: "Plan: Increase Backend Test Coverage & Fix Bugs"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Fix Broken Tests to Restore Green Suite (Priority: P1)

As a developer, I need all existing backend tests to pass so the team can trust the test suite as a reliable quality gate. Currently, 9 tests in the agent provider test module fail due to async/await mismatches. These must be fixed before any new test work begins.

**Why this priority**: A failing test suite undermines confidence in all test results. No other coverage work is meaningful until the existing suite is green. This is the foundation for all subsequent phases.

**Independent Test**: Can be verified by running the full backend test suite and confirming zero failures across all existing tests.

**Acceptance Scenarios**:

1. **Given** the backend test suite has 9 failing tests due to async/await mismatches, **When** the tests are corrected to use proper async patterns, **Then** the full suite runs with zero failures.
2. **Given** the corrected async tests, **When** timeout configuration is passed through to the agent provider, **Then** a dedicated test validates the timeout value is correctly forwarded.
3. **Given** the corrected async tests, **When** MCP server configurations are passed through, **Then** a dedicated test validates the MCP server config is correctly forwarded.

---

### User Story 2 - Increase Project Management Coverage (Priority: P2)

As a developer, I need comprehensive tests for the project management layer so that rate limiting, caching, fallback behavior, and real-time subscription logic are verified. This module currently has the lowest coverage (37.7%) and handles critical user-facing workflows including project listing, task retrieval, and WebSocket subscriptions.

**Why this priority**: The project management layer is user-facing and handles rate limit detection from external services. Untested error paths here can lead to silent data loss or degraded user experiences without any warning.

**Independent Test**: Can be verified by running only the project management test module and confirming all new scenarios pass, then checking the per-file coverage report shows improvement toward the 70% target.

**Acceptance Scenarios**:

1. **Given** the external service returns a 403 status with a rate-limit-remaining header of zero, **When** the system processes this response, **Then** rate limiting is correctly detected and handled gracefully.
2. **Given** the external service returns a 403 status with an empty rate limit dictionary, **When** the system processes this response, **Then** the system does not falsely trigger rate limit handling.
3. **Given** the task retrieval service encounters an exception, **When** the fallback mechanism activates, **Then** the system retrieves completed items from the local cache instead.
4. **Given** the project list cache is empty (empty list vs. None), **When** a project listing is requested, **Then** the system distinguishes between "no projects" and "cache not populated" and behaves appropriately for each case.
5. **Given** a non-rate-limit error occurs during project listing, **When** the fallback activates, **Then** the system uses the appropriate error handling path without triggering rate limit logic.
6. **Given** a requested project is not in the cached project list, **When** the system looks up the project, **Then** it handles the miss gracefully.
7. **Given** a project refresh is requested but an error occurs, **When** the refresh=True parameter is used, **Then** the system handles the error and falls back appropriately.
8. **Given** an active WebSocket subscription, **When** the stale revalidation counter triggers, **Then** the system performs hash diffing and pushes updates only when data has changed.
9. **Given** an active WebSocket subscription, **When** the client disconnects unexpectedly, **Then** the subscription is cleaned up without errors.

---

### User Story 3 - Increase Agent Creator Coverage (Priority: P3)

As a developer, I need comprehensive tests for the agent creation service so that admin authentication edge cases, status resolution logic, the multi-step creation pipeline, and AI service failure handling are all verified. This module currently has 39.4% coverage.

**Why this priority**: The agent creation pipeline is a complex multi-step process involving authentication, status resolution, resource creation, and AI-powered configuration. Untested paths can lead to orphaned resources or security gaps in admin privilege escalation.

**Independent Test**: Can be verified by running only the agent creator test module and confirming all new scenarios pass, then checking the per-file coverage report shows improvement toward the 65% target.

**Acceptance Scenarios**:

1. **Given** a debug environment, **When** an auto-promote action occurs for admin authentication, **Then** the system correctly elevates privileges in debug mode only.
2. **Given** an admin user ID configured via environment variable, **When** authentication is checked, **Then** the configured user is recognized as admin.
3. **Given** a database exception during admin authentication, **When** the check fails, **Then** the system handles the error gracefully without exposing internal details.
4. **Given** a fuzzy or empty input for status resolution, **When** the system attempts to match, **Then** it handles the edge case without crashing.
5. **Given** a normalized status match, **When** the system resolves the status, **Then** it correctly maps to the canonical status.
6. **Given** an out-of-range selection for status, **When** the user provides an invalid index, **Then** the system rejects it gracefully.
7. **Given** a new column is needed during status resolution, **When** the column doesn't exist, **Then** the system creates it appropriately.
8. **Given** a duplicate agent name during creation, **When** step 3 of the pipeline runs, **Then** the system handles the conflict appropriately.
9. **Given** a failure in the AI configuration generation step, **When** generate_agent_config() fails, **Then** the system handles the error and cleans up partial resources.
10. **Given** an AI service that returns a non-list value for tools, **When** the pipeline processes the response, **Then** the system handles the unexpected format gracefully.

---

### User Story 4 - Increase Agent Service Coverage (Priority: P4)

As a developer, I need comprehensive tests for the agent service so that caching, agent source mixing, YAML frontmatter parsing, tool resolution, and agent creation logic are verified. This module currently has 47.4% coverage and can be worked on in parallel with the agent creator tests.

**Why this priority**: The agent service manages the lifecycle of agents including caching, configuration parsing, and tool resolution. Untested edge cases in caching or YAML parsing can lead to stale data being served or misconfigured agents.

**Independent Test**: Can be verified by running only the agent service test module and confirming all new scenarios pass, then checking the per-file coverage report shows improvement toward the 70% target.

**Acceptance Scenarios**:

1. **Given** a cached agent list with user preference overlays, **When** the list is retrieved, **Then** preferences are correctly merged with cached data.
2. **Given** stale cached data, **When** the fresh source is unavailable, **Then** the system falls back to stale data rather than returning nothing.
3. **Given** active sessions that are no longer valid, **When** session pruning runs, **Then** stale sessions are removed without affecting active ones.
4. **Given** agents from both repository and local sources, **When** a bulk model update runs, **Then** both sources are correctly merged.
5. **Given** a partial failure during bulk update, **When** some agents fail to update, **Then** the system processes successful updates and reports failures.
6. **Given** agents with tombstone markers, **When** the agent list is retrieved, **Then** tombstoned agents are excluded.
7. **Given** an agent file with missing YAML frontmatter fields, **When** the file is parsed, **Then** the system uses defaults for missing fields.
8. **Given** an agent file with YAML parse errors, **When** the file is read, **Then** the system falls back gracefully without crashing.
9. **Given** an agent file with no YAML frontmatter at all, **When** the file is read, **Then** the system handles the absence gracefully.
10. **Given** MCP tool configurations with varying formats, **When** tool resolution runs, **Then** wildcards, explicit entries, and duplicates are handled correctly with proper normalization.
11. **Given** a special-character agent name, **When** a slug is generated, **Then** the slug is valid and sanitized.
12. **Given** an AI failure during agent creation, **When** the fallback activates, **Then** a basic agent configuration is created without AI enhancement.

---

### User Story 5 - Increase Chores Service Coverage (Priority: P5)

As a developer, I need comprehensive tests for the chores (scheduled tasks) service so that preset seeding, update validation, and trigger state management are verified. This module currently has 51.3% coverage and can be worked on in parallel with the agent service tests.

**Why this priority**: The chores service handles scheduled task execution with compare-and-swap (CAS) semantics to prevent double-firing. Untested trigger state logic can lead to duplicate task execution or missed scheduled tasks.

**Independent Test**: Can be verified by running only the chores service test module and confirming all new scenarios pass, then checking the per-file coverage report shows improvement toward the 75% target.

**Acceptance Scenarios**:

1. **Given** preset chores already exist, **When** the seeding process runs again, **Then** it is idempotent and does not create duplicates.
2. **Given** the preset file is unreadable, **When** seeding is attempted, **Then** the system handles the file read failure gracefully.
3. **Given** the system has 3 built-in presets, **When** seeding completes successfully, **Then** all 3 presets are present with unique identifiers.
4. **Given** a chore update with inconsistent schedule parameters, **When** validation runs, **Then** the inconsistency is rejected with a clear error.
5. **Given** a chore update with boolean values where integer values are expected, **When** the update is processed, **Then** boolean values are correctly converted to integers.
6. **Given** a chore update referencing an invalid column name, **When** the update is processed, **Then** the invalid column is rejected to prevent injection attacks.
7. **Given** a chore that has never been triggered (NULL trigger state), **When** a CAS trigger fires, **Then** the trigger succeeds and records the new state.
8. **Given** a chore with a matching old trigger value, **When** a CAS trigger fires, **Then** the trigger succeeds and updates to the new state.
9. **Given** a chore with a mismatched old trigger value (indicating another process already fired), **When** a CAS trigger fires, **Then** the trigger is rejected to prevent double-fire.
10. **Given** a chore with an active current issue, **When** clear_current_issue() is called, **Then** the issue reference is cleared cleanly.

---

### User Story 6 - Verify Full Suite and Coverage Targets (Priority: P6)

As a developer, I need to verify that all new tests integrate cleanly with the existing suite and that per-file coverage targets are met, so the team can confidently merge the changes.

**Why this priority**: This is the final validation step that ensures all phases produced correct, non-conflicting tests and that the overall coverage goal is on track.

**Independent Test**: Can be verified by running the complete backend test suite and generating a targeted coverage report for the four modified files.

**Acceptance Scenarios**:

1. **Given** all new tests have been added across all phases, **When** the full backend test suite runs, **Then** zero failures are reported.
2. **Given** the full suite passes, **When** a per-file coverage report is generated, **Then** each of the four targeted files shows coverage improvement toward their individual targets.
3. **Given** the per-file coverage deltas, **When** compared against baseline measurements, **Then** all four files show meaningful improvement from their starting coverage levels.

---

### Edge Cases

- What happens when the external service is completely unreachable (not just rate-limited) during project operations?
- How does the system handle concurrent WebSocket subscriptions receiving stale data simultaneously?
- What happens when an agent creation pipeline fails midway (e.g., column created but issue creation fails) — are partial resources cleaned up?
- How does YAML frontmatter parsing handle extremely large files or deeply nested structures?
- What happens when CAS trigger timing overlaps with a chore deletion?
- How does the system behave when the preset configuration file is corrupted (not just missing)?
- What happens when boolean-to-integer conversion encounters unexpected types (e.g., strings, None)?
- How does tool resolution handle circular wildcard patterns or self-referencing configurations?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: All existing backend tests MUST pass with zero failures before any new test work begins.
- **FR-002**: The project management module MUST have test coverage for rate limit detection, including both true rate-limit scenarios (403 + zero remaining) and false positives (403 without rate limit indicators).
- **FR-003**: The project management module MUST have test coverage for task retrieval fallback behavior, including exception handling and local cache fallback.
- **FR-004**: The project management module MUST have test coverage for project list caching edge cases, distinguishing between empty list and unpopulated cache.
- **FR-005**: The project management module MUST have test coverage for WebSocket subscription lifecycle, including stale revalidation, hash-based change detection, and disconnection cleanup.
- **FR-006**: The agent creator module MUST have test coverage for admin authentication edge cases, including debug auto-promote, environment-variable-based admin user configuration, and database exceptions.
- **FR-007**: The agent creator module MUST have test coverage for status resolution, including fuzzy/empty input handling, normalized matching, out-of-range selection, and new column creation.
- **FR-008**: The agent creator module MUST have test coverage for the multi-step creation pipeline (steps 3–7), including duplicate name handling, column creation, issue/PR creation, and cleanup on failure.
- **FR-009**: The agent creator module MUST have test coverage for AI service failure handling, including configuration generation failures, edit retry logic, and non-list tool responses.
- **FR-010**: The agent service module MUST have test coverage for caching behavior, including preference overlay, stale fallback, and session pruning.
- **FR-011**: The agent service module MUST have test coverage for mixed-source agent operations, including bulk update with multiple sources, partial failure handling, and tombstone filtering.
- **FR-012**: The agent service module MUST have test coverage for YAML frontmatter parsing edge cases, including missing fields, parse errors with fallback, and absent frontmatter.
- **FR-013**: The agent service module MUST have test coverage for tool resolution, including MCP normalization, wildcard vs. explicit patterns, deduplication, and invalid configuration handling.
- **FR-014**: The agent service module MUST have test coverage for agent creation, including slug generation from special characters, AI failure fallback, and raw vs. enhanced mode.
- **FR-015**: The chores service module MUST have test coverage for preset seeding, including idempotent re-seeding, file read failure handling, all preset types, and uniqueness enforcement.
- **FR-016**: The chores service module MUST have test coverage for update validation, including schedule consistency, boolean-to-integer conversion, and invalid column rejection as a defense against injection attacks.
- **FR-017**: The chores service module MUST have test coverage for trigger state management using compare-and-swap semantics, including NULL initial state, matching values, mismatched values (double-fire prevention), and issue reference clearing.
- **FR-018**: All new tests MUST follow existing test patterns and fixture conventions without requiring test infrastructure refactoring.
- **FR-019**: The full backend test suite MUST pass with zero failures after all new tests are added.
- **FR-020**: Per-file coverage reports MUST be generated to verify improvement against baseline measurements.

### Key Entities

- **Test Suite**: The collection of all backend tests, currently at 4071+ passing tests with an overall coverage of 78.3%.
- **Coverage Baseline**: Per-file coverage measurements taken before changes: projects.py (37.7%), agent_creator.py (39.4%), agents/service.py (47.4%), chores/service.py (51.3%).
- **Coverage Target**: Per-file goals representing meaningful improvement: projects.py (~70%), agent_creator.py (~65%), agents/service.py (~70%), chores/service.py (~75%).

## Assumptions

- Phase 1 (fixing broken async tests) is already completed and does not need to be re-done.
- The observability infrastructure module (otel_setup.py at 45.8%) is intentionally excluded because it is difficult to unit test meaningfully.
- Existing test patterns, fixtures, and infrastructure are sufficient — no test framework refactoring is needed.
- Async tests use auto-detected async mode, so no explicit mode configuration is required per test.
- The four target files were selected based on having the lowest coverage with the highest potential impact.
- Phases 3/4 and 4/5 can be worked on in parallel since they touch independent modules.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The full backend test suite runs with zero failures after all changes are complete.
- **SC-002**: The project management module achieves approximately 70% test coverage, up from the 37.7% baseline.
- **SC-003**: The agent creator module achieves approximately 65% test coverage, up from the 39.4% baseline.
- **SC-004**: The agent service module achieves approximately 70% test coverage, up from the 47.4% baseline.
- **SC-005**: The chores service module achieves approximately 75% test coverage, up from the 51.3% baseline.
- **SC-006**: Overall backend test coverage reaches approximately 85%, up from the 78.3% baseline.
- **SC-007**: No existing tests are removed or modified in a way that reduces their coverage of existing functionality.
- **SC-008**: All new tests can be run independently without depending on test execution order or shared mutable state.
