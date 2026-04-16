# Feature Specification: Replace Built-in Pipeline Presets

**Feature Branch**: `001-replace-pipeline-presets`  
**Created**: 2026-04-16  
**Status**: Draft  
**Input**: User description: "Replace the 6 backend pipeline presets with 4 that match the frontend's existing definitions. All presets use a single 'In progress' stage with one sequential Group 1."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Backend–Frontend Preset Alignment (Priority: P1)

As a user, when I open a project and its pipeline presets are loaded, I see the same four presets (GitHub, Spec Kit, Default, App Builder) whether I am viewing the frontend UI or the backend is seeding configurations. The preset names, agent lists, and stage layouts are identical across both layers.

**Why this priority**: This is the core motivation for the entire feature. Today the backend defines 6 presets with multi-stage layouts while the frontend defines 4 presets each with a single "In progress" stage. The mismatch causes confusion, potential runtime errors when a frontend preset ID has no backend counterpart, and makes maintenance harder.

**Independent Test**: Can be fully tested by seeding presets on a fresh project and verifying the returned preset IDs, names, and agent lists match the four frontend definitions exactly.

**Acceptance Scenarios**:

1. **Given** a fresh project with no pipeline configurations, **When** presets are seeded, **Then** exactly 4 preset pipelines are created: `github`, `spec-kit`, `default`, and `app-builder`.
2. **Given** a project where presets were previously seeded with the old 6-preset set, **When** presets are re-seeded, **Then** the old presets (easy, medium, hard, expert, github-copilot) are replaced or cleaned up by drift detection, and only the 4 new presets remain as system presets.
3. **Given** any of the 4 seeded presets, **When** its stages are inspected, **Then** there is exactly one stage named "In progress" containing one sequential execution group with agents matching the frontend definition for that preset.

---

### User Story 2 - Difficulty-Based Preset Selection (Priority: P1)

As a system component that auto-selects a pipeline based on issue difficulty, when a difficulty level (XS, S, M, L, XL) is assessed, the system maps it to one of the 4 new preset IDs so the correct pipeline is launched.

**Why this priority**: The difficulty-to-preset mapping is used by automated agent tools during project configuration. If mappings reference removed preset IDs, pipeline selection fails silently or errors out, blocking all automated workflows.

**Independent Test**: Can be tested by calling the difficulty mapping function with each difficulty level and verifying the returned preset ID is one of the four valid new preset IDs.

**Acceptance Scenarios**:

1. **Given** a difficulty of "XS" or "S", **When** the preset is selected, **Then** the system returns the `github` preset.
2. **Given** a difficulty of "M", **When** the preset is selected, **Then** the system returns the `spec-kit` preset.
3. **Given** a difficulty of "L", **When** the preset is selected, **Then** the system returns the `default` preset.
4. **Given** a difficulty of "XL", **When** the preset is selected, **Then** the system returns the `app-builder` preset.
5. **Given** an unrecognized difficulty string, **When** the preset is selected, **Then** the system falls back to a sensible default (the `default` preset).

---

### User Story 3 - Agent Display Names and Default Mappings (Priority: P2)

As a user viewing the pipeline configuration or agent activity in the UI, I see human-readable display names for all agents that appear in the new presets, including agents that were not previously named (architect, quality-assurance, tester, linter, judge).

**Why this priority**: Without display names, new agents show raw slugs in the UI, which degrades user experience. Default agent mappings also need to align with the simplified single-stage layout to avoid errors in status-based agent lookups.

**Independent Test**: Can be tested by asserting that every agent slug used across the 4 preset definitions has a corresponding entry in the display names registry, and that the default agent mappings reference a single "In Progress" status.

**Acceptance Scenarios**:

1. **Given** the agent display names registry, **When** checked against all agent slugs in the 4 presets, **Then** every slug has a human-readable display name entry.
2. **Given** the default agent mappings, **When** inspected, **Then** they reference a single "In Progress" status containing the default pipeline's agent list (matching the agents in the `default` preset).

---

### User Story 4 - Backward Compatibility for Customized Pipelines (Priority: P2)

As a user who has previously customized a pipeline based on an old preset, my customized configuration is preserved. Only system-managed presets (is_preset=1) are updated or removed; user-customized pipelines (is_preset=0) remain unchanged.

**Why this priority**: Data loss of user customizations would be a critical regression. The system must cleanly separate preset management from user data.

**Independent Test**: Can be tested by creating a customized pipeline derived from an old preset (e.g., "medium"), re-seeding presets, and verifying the customized pipeline still exists with its original configuration.

**Acceptance Scenarios**:

1. **Given** a user-customized pipeline (is_preset=0) derived from the old "medium" preset, **When** presets are re-seeded with the new definitions, **Then** the user-customized pipeline is not deleted or modified.
2. **Given** a system preset (is_preset=1) with the old "easy" ID, **When** presets are re-seeded, **Then** the old preset is removed or updated by drift detection and does not appear alongside the new presets.

---

### User Story 5 - Frontend Remains Unchanged (Priority: P3)

As a frontend developer, I do not need to make any changes because the frontend already defines the 4 target presets. After the backend changes, the frontend tests continue to pass without modification.

**Why this priority**: Confirming no frontend regression is important but lower priority because the frontend is already in the target state. This story exists to verify the contract, not to drive changes.

**Independent Test**: Can be tested by running the existing frontend preset pipeline tests and confirming they all pass.

**Acceptance Scenarios**:

1. **Given** the existing frontend preset pipeline definitions and tests, **When** the backend changes are deployed, **Then** all frontend preset tests pass without any modifications.

---

### Edge Cases

- What happens when a project has a pipeline assigned using one of the removed preset IDs (e.g., "easy" or "expert")? The system should handle graceful fallback or reassignment to the closest new preset during the next seed operation.
- What happens when `seed_presets()` is called concurrently for the same project? The idempotent seeding logic should handle concurrent calls without creating duplicate presets.
- What happens when the difficulty mapping receives an empty string or null value? The system should fall back to the `default` preset.
- What happens when an agent slug in a preset (e.g., "architect") does not have a matching entry in the fleet dispatch configuration? The system should resolve the agent gracefully via fallback resolution, without crashing.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST replace the 6 existing backend preset definitions (spec-kit, github-copilot, easy, medium, hard, expert) with exactly 4 new presets: `github`, `spec-kit`, `default`, and `app-builder`.
- **FR-002**: Each of the 4 new presets MUST have a single stage named "In progress" with one sequential execution group containing the specified agents:
  - `github`: copilot
  - `spec-kit`: speckit.specify, speckit.plan, speckit.tasks, speckit.analyze, speckit.implement
  - `default`: speckit.specify, speckit.plan, speckit.tasks, speckit.analyze, speckit.implement, quality-assurance, tester, linter, copilot-review, judge
  - `app-builder`: speckit.specify, speckit.plan, speckit.tasks, speckit.analyze, speckit.implement, architect, quality-assurance, tester, linter, copilot-review, judge
- **FR-003**: The difficulty-to-preset mapping MUST be updated across all locations where it is defined, using the following mapping: XS → github, S → github, M → spec-kit, L → default, XL → app-builder.
- **FR-004**: The fallback preset ID for unrecognized difficulty values MUST be changed from the old default ("medium") to the new default ("default").
- **FR-005**: System MUST provide human-readable display names for all agents used in the new presets, including: architect → "Architect", quality-assurance → "Quality Assurance", tester → "Tester", linter → "Linter", judge → "Judge".
- **FR-006**: The default agent mappings MUST be simplified to a single "In Progress" status containing the agents from the default pipeline preset.
- **FR-007**: The `seed_presets()` function MUST continue to handle drift detection — removing old system presets that no longer match any current preset definition while preserving user-customized pipelines (is_preset=0).
- **FR-008**: All existing backend tests that reference old preset IDs, difficulty mappings, or agent display names MUST be updated to assert the new values.
- **FR-009**: Frontend preset definitions and tests MUST remain unchanged and continue to pass.

### Key Entities

- **Pipeline Preset**: A system-defined pipeline configuration template identified by a `preset_id`. Contains a name, description, and ordered list of stages with execution groups and agents. Marked as `is_preset=1` in the database.
- **Difficulty-to-Preset Map**: A lookup that maps issue complexity ratings (XS, S, M, L, XL) to a preset ID, used by automated agent tools to select the appropriate pipeline.
- **Agent Display Name**: A human-readable label for an agent slug, used in the UI to present friendly names instead of raw identifiers.
- **Default Agent Mapping**: A mapping from pipeline status names to lists of agent slugs, used as a fallback when no specific pipeline configuration is assigned.

## Assumptions

- The frontend `preset-pipelines.ts` already contains exactly the 4 target preset definitions and requires no changes.
- The `seed_presets()` drift detection logic will handle cleanup of old preset IDs (easy, medium, hard, expert, github-copilot) on the next project load without requiring a separate migration step.
- The "architect" agent slug resolves in fleet dispatch either via a direct entry in the dispatch configuration or through a graceful fallback mechanism (`resolve_custom_agent()`).
- The `spec-kit` preset ID is reused (not renamed) — only its stage layout changes from multi-stage to single-stage "In progress".
- The "github-copilot" preset ID is renamed to "github" to match the frontend.
- Performance characteristics of the system remain unchanged since the number of presets decreases and structure simplifies.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: After seeding, exactly 4 system presets exist for any project — no more, no fewer.
- **SC-002**: All backend tests covering preset definitions, difficulty mappings, agent display names, and default agent mappings pass with 100% of assertions reflecting the new values.
- **SC-003**: All frontend preset pipeline tests pass without any modifications to the frontend codebase.
- **SC-004**: Every agent slug used across the 4 presets has a corresponding human-readable display name entry.
- **SC-005**: The difficulty-to-preset mapping resolves correctly for all 5 standard difficulty levels (XS, S, M, L, XL) and falls back gracefully for unrecognized values.
- **SC-006**: User-customized pipelines (is_preset=0) are fully preserved after re-seeding, with zero data loss.
- **SC-007**: The preset seeding operation completes without errors on both fresh projects and projects with previously seeded old presets.
