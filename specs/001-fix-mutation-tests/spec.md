# Feature Specification: Fix Mutation Tests

**Feature Branch**: `001-fix-mutation-tests`  
**Created**: 2026-04-02  
**Status**: Draft  
**Input**: User description: "Fix Mutation Tests"

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Backend Mutation Shards Run Cleanly (Priority: P1)

As a developer pushing changes to the backend, I need every backend mutation shard to execute its full mutant set and produce a meaningful survivor report, rather than aborting early because workspace files are missing. Today all four CI shards fail on the same app-template test, making every backend mutation report useless.

**Why this priority**: This is the root blocker. Until the backend mutation workspace contains the files that tests actually need, no backend shard can produce actionable results. Every other backend improvement depends on this fix.

**Independent Test**: Run each backend mutation shard locally and in CI. A successful run completes without "not checked" aborts and produces a survivor count per module.

**Acceptance Scenarios**:

1. **Given** a developer triggers the backend mutation workflow, **When** each shard executes, **Then** no shard aborts due to missing app-template assets and each shard produces a valid survivor report.
2. **Given** the backend mutation workspace is built from project configuration, **When** the mutant workspace is created, **Then** the app-template directory and all files referenced by the template registry are present and resolvable.
3. **Given** the template registry and template-file helper both resolve paths at runtime, **When** running inside the mutant workspace, **Then** both resolve to the correct copied assets without errors.

---

### User Story 2 — Backend Shard–Workflow Alignment (Priority: P2)

As a developer reviewing mutation results, I need the CI workflow to run exactly the same shards that the shard runner defines, so that no module is silently excluded from mutation coverage. Currently the shard runner defines five shards but the CI workflow only runs four, omitting the api-and-middleware shard.

**Why this priority**: Missing a shard means an entire category of backend code goes untested for mutation resilience. Aligning shards is a quick configuration change that closes a coverage gap.

**Independent Test**: Compare the list of shards in the CI workflow against the shard runner definition and the developer documentation. All three must list the same set of shards.

**Acceptance Scenarios**:

1. **Given** the shard runner defines five shards, **When** the CI mutation workflow runs, **Then** five shard jobs execute (one per defined shard).
2. **Given** the developer documentation lists available shards, **When** a developer reads the docs, **Then** the documented shard list matches both the CI workflow and the shard runner.

---

### User Story 3 — Frontend Mutation Sharding (Priority: P2)

As a developer working on frontend hooks and utilities, I need the frontend mutation run to be split into multiple CI shards so that each shard completes within the CI time limit and produces a focused survivor report. Today the single frontend job times out at roughly 71 % progress, producing an incomplete and unusable report.

**Why this priority**: The frontend mutation scope (6,580+ mutants across 73 source files) is too large for a single CI job. Sharding is required before any survivor cleanup work can begin.

**Independent Test**: Trigger the frontend mutation workflow and verify that each shard completes within the CI time limit, all source files are covered by exactly one shard, and each shard produces its own artifact.

**Acceptance Scenarios**:

1. **Given** the frontend mutation workflow is triggered, **When** shards execute, **Then** each shard completes within the three-hour CI time limit.
2. **Given** the frontend source scope is divided among shards, **When** all shards finish, **Then** the union of their mutate globs covers every file in the original scope with no overlaps.
3. **Given** each shard completes, **When** artifacts are uploaded, **Then** each shard produces a separate, downloadable mutation report.

---

### User Story 4 — Developer-Facing Focused Mutation Commands (Priority: P3)

As a developer investigating a specific survivor, I need focused mutation commands that let me target a single file or area without rerunning all 6,580+ frontend mutants or all backend modules. Today, local reproduction requires running the full mutation suite.

**Why this priority**: Developer productivity. Focused commands reduce the local feedback loop from hours to minutes, making survivor cleanup practical.

**Independent Test**: Run a focused mutation command targeting a single file and verify it completes in under five minutes and produces results only for that file.

**Acceptance Scenarios**:

1. **Given** a developer wants to check mutations in a specific frontend file, **When** they run the focused command for that file, **Then** only mutants from that file are generated and tested.
2. **Given** a developer wants to check mutations in a specific backend module, **When** they run the focused shard command for that module, **Then** only mutants from that module are generated and tested.
3. **Given** focused commands are documented, **When** a developer reads the testing documentation, **Then** they find clear examples of how to run focused mutation tests for both frontend and backend.

---

### User Story 5 — Frontend Test-Utils Provider Bug Fix (Priority: P3)

As a developer writing component tests, I need the shared test utility's provider wrapper to nest providers correctly instead of rendering children twice. The current implementation renders children in two separate provider branches, which affects both test correctness and test runtime.

**Why this priority**: This is a confirmed bug that affects every test using the shared wrapper. Fixing it improves test reliability and performance across the entire frontend test suite.

**Independent Test**: Render a component with the shared wrapper and verify it appears in the DOM exactly once, not twice.

**Acceptance Scenarios**:

1. **Given** a component is rendered using the shared test wrapper, **When** the render completes, **Then** the component appears exactly once in the rendered output.
2. **Given** the shared test wrapper nests multiple providers, **When** a test inspects the provider hierarchy, **Then** all providers are properly nested (not siblings rendering children independently).

---

### User Story 6 — Mutation Survivor Cleanup for Key Frontend Hooks (Priority: P3)

As a developer responsible for frontend quality, I need targeted mutation-killing tests for confirmed survivor gaps in the adaptive polling hook and board projection hook, so that behavioral edge cases in these performance-critical hooks are covered by deterministic assertions.

**Why this priority**: These hooks drive core user-facing performance behavior (polling frequency and lazy-loading). Survivors here mean untested behavioral branches that could regress silently.

**Independent Test**: Run mutation testing scoped to each hook file and verify that the survivor count drops compared to the baseline report.

**Acceptance Scenarios**:

1. **Given** the adaptive polling hook has surviving mutants around tier transitions, **When** new deterministic tests assert on tier boundaries and transitions, **Then** those survivors are killed.
2. **Given** the board projection hook has surviving mutants around expansion ranges, **When** new deterministic tests assert on projection boundaries and batch sizes, **Then** those survivors are killed.
3. **Given** visibility-triggered immediate poll behavior has surviving mutants, **When** new tests assert on the visibility-change-to-poll sequence, **Then** those survivors are killed.

---

### User Story 7 — Documentation and Changelog Updates (Priority: P3)

As a developer onboarding to the project or reviewing recent changes, I need the testing documentation and changelog to reflect the new shard layout, focused commands, and infrastructure fixes, so that the documentation stays accurate and discoverable.

**Why this priority**: Documentation drift causes confusion and wasted time. Updating docs as part of the infrastructure change prevents a separate cleanup effort later.

**Independent Test**: Read the testing documentation and changelog and verify they describe the current shard layout, commands, and behavior accurately.

**Acceptance Scenarios**:

1. **Given** the backend shards have been aligned, **When** a developer reads the testing docs, **Then** all five backend shards are documented with their module scopes.
2. **Given** the frontend has been sharded, **When** a developer reads the testing docs, **Then** the frontend shard layout and focused commands are documented.
3. **Given** all mutation infrastructure changes are complete, **When** a developer reads the changelog, **Then** the changes are listed under the appropriate version heading.

---

### Edge Cases

- What happens when the app-template directory is empty or contains malformed template files during mutation workspace creation?
- How does the system handle a backend shard that completes with zero mutants (e.g., if the shard glob matches no source files)?
- What happens when a frontend shard's mutate glob overlaps with another shard's glob, creating duplicate mutant coverage?
- How does the CI workflow handle a shard that times out — does it still upload a partial report artifact?
- What happens when a developer runs a focused mutation command for a file that has no corresponding tests?
- How does the test-utils provider fix affect tests that were accidentally relying on the double-render behavior?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The backend mutation workspace MUST include app-template assets so that the template registry and all tests exercising app-template flows resolve their paths correctly inside the mutant workspace.
- **FR-002**: The backend mutation workspace MUST preserve correct path resolution for both the template registry (which resolves paths relative to its own file location) and the template-file helper (which resolves paths relative to its own file location or an environment variable).
- **FR-003**: The CI mutation workflow MUST execute all shards defined in the backend shard runner, with no shard omitted or undefined.
- **FR-004**: The frontend mutation scope MUST be split into 3–4 CI shards, each with its own mutate glob pattern, so that every file in the original scope is covered by exactly one shard.
- **FR-005**: Each frontend mutation shard MUST produce a separate downloadable artifact containing its mutation report.
- **FR-006**: The project MUST provide focused mutation commands that allow developers to target individual files or areas for both frontend and backend mutation testing.
- **FR-007**: The shared frontend test utility provider wrapper MUST nest all providers correctly so that children are rendered exactly once.
- **FR-008**: New frontend tests MUST add deterministic assertions targeting confirmed survivor gaps in the adaptive polling hook (tier transitions, visibility-triggered polls) and the board projection hook (expansion ranges, batch sizes).
- **FR-009**: Testing documentation MUST be updated to reflect the current shard layout, focused commands, and mutation infrastructure behavior for both frontend and backend.
- **FR-010**: The changelog MUST be updated to describe the mutation testing infrastructure changes introduced by this feature.
- **FR-011**: Mutation thresholds MUST NOT be lowered and risky scope MUST NOT be permanently shrunk as a means of resolving failures. Fixes must come from workspace parity, sharding, and better tests.
- **FR-012**: Backend bugs discovered during mutation hardening MUST be treated as in-scope and fixed with behavioral assertions rather than mutation-tool-specific workarounds.

### Key Entities

- **Mutation Shard**: A named subdivision of the mutation testing scope (e.g., "auth-and-projects", "board-polling-hooks"). Each shard covers a specific set of source files and produces its own report. Backend defines five shards; frontend will define 3–4 shards.
- **Mutant Workspace**: The temporary directory tree created by the mutation tool (mutmut for backend, Stryker for frontend) where source files are copied and individual mutations are applied. Must contain all files needed by tests, not just the files being mutated.
- **Survivor**: A mutant that was not killed by any test. Survivors indicate behavioral gaps in the test suite. Survivors are grouped by shard and module for prioritized cleanup.
- **Focused Mutation Command**: A developer-facing command (in package.json or via the shard runner) that targets a single file or module for mutation testing, enabling rapid local feedback.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All five backend mutation shards complete without workspace-related aborts and each produces a report with zero "not checked" mutants caused by missing assets.
- **SC-002**: Each frontend mutation shard completes within the three-hour CI time limit, and the combined shard coverage equals 100 % of the original mutation scope.
- **SC-003**: A developer can run a focused frontend mutation command targeting a single file and receive results in under five minutes for a typical hook or utility file.
- **SC-004**: The shared test utility provider wrapper renders children exactly once, verified by an explicit test assertion.
- **SC-005**: The survivor count for the adaptive polling hook and board projection hook decreases compared to the pre-fix baseline, with deterministic assertions killing previously surviving mutants around tier transitions, visibility polls, and projection ranges.
- **SC-006**: The CI mutation workflow definition, the backend shard runner, and the testing documentation all list the same set of backend shards with no discrepancies.
- **SC-007**: No mutation threshold is lowered and no source file is removed from the mutation scope as part of this change.

## Assumptions

- The weekly CI schedule (Sundays at 2 AM UTC) and manual-dispatch trigger for the mutation workflow remain unchanged.
- The backend shard runner's approach of dynamically patching configuration at runtime to narrow mutation scope is the accepted pattern and will be preserved.
- The frontend mutation tool (Stryker) supports shard-level configuration via separate mutate globs without requiring multiple configuration files.
- The "api-and-middleware" shard was unintentionally omitted from the CI workflow (not deliberately excluded), and adding it is the correct resolution.
- The three-hour CI time limit per job is a platform constraint that cannot be increased.
- The frontend shard boundaries (board/polling hooks, data/query hooks, general hooks, lib/utils) are a reasonable starting point and can be adjusted based on initial shard run results.
- Existing tests that relied on the double-render behavior of the test-utils wrapper are either nonexistent or will surface as obvious test failures that can be fixed as part of this work.
- Property tests (e.g., buildGitHubMcpConfig.property.test.ts, pipelineMigration.property.test.ts) remain in scope but are lower priority for mutation-killing improvements than deterministic assertion tests.
