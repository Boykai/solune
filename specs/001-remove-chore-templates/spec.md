# Feature Specification: Chores — Remove Issue Templates, Use DB + Parent Issue Intake Flow

**Feature Branch**: `001-remove-chore-templates`  
**Created**: 2026-04-13  
**Status**: Draft  
**Input**: User description: "Remove all ISSUE_TEMPLATE integration from Chores. Chore descriptions live only in the database. When triggered, a chore's description feeds into the same execute_pipeline_launch() flow used by the Parent Issue Intake panel — getting transcript detection, AI label classification, title derivation, sub-issue creation, and pipeline orchestration for free."

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Trigger a Chore via the Unified Pipeline (Priority: P1)

A project maintainer triggers a chore (manually or via schedule). Instead of the system assembling a GitHub issue from a repo-stored template, it takes the chore's database-stored description and feeds it into the same pipeline launch flow used by the Parent Issue Intake panel. The resulting issue receives AI-classified labels (plus a mandatory "chore" label), uses the chore name as its title, and has sub-issues created and agents assigned — all without any template file or PR involved.

**Why this priority**: This is the core behavioral change. It eliminates ~200 lines of bespoke issue-creation logic in `trigger_chore()` and replaces it with a single delegation to the existing pipeline launch flow, reducing duplication and ensuring chores benefit from every future improvement to the intake pipeline (transcript detection, smarter label classification, etc.).

**Independent Test**: Can be fully tested by creating a chore with a plain-text description, triggering it, and verifying the resulting GitHub issue has the correct title (chore name), labels (including "chore"), sub-issues, and pipeline dispatch — all routed through the unified pipeline flow.

**Acceptance Scenarios**:

1. **Given** a chore with name "Security Review" and a multi-paragraph description stored in the database, **When** the chore is triggered, **Then** a GitHub issue is created with title "Security Review", the body contains the chore description, the issue is labeled with "chore" plus any AI-classified labels, sub-issues are created for pipeline agents, and the first agent is started.
2. **Given** a chore whose current issue is still open, **When** the chore is triggered again, **Then** the system skips creation and returns a skip reason indicating an open instance already exists.
3. **Given** a chore whose previous issue was closed externally, **When** the chore is triggered, **Then** the system clears the stale issue reference and proceeds with a fresh pipeline launch.
4. **Given** the pipeline launch flow is extended with optional parameters for extra labels and title override, **When** the chore trigger passes `["chore"]` as extra labels and the chore name as title override, **Then** the pipeline uses these values instead of AI-derived title and default labels.

---

### User Story 2 — Create and Edit Chores with Plain Descriptions (Priority: P2)

A project maintainer creates a new chore by entering a name and a plain-text description. The description is saved directly to the database — no template file is generated, no PR is opened, and no YAML front matter is prepended. When the maintainer later edits the chore's description inline, the change is persisted to the database immediately without SHA conflict detection or PR workflows.

**Why this priority**: This simplifies the authoring experience and removes the most confusing part of the current flow (PR-based template management). It is a prerequisite for the frontend changes but delivers standalone value: users can create and edit chores without waiting for PRs to merge.

**Independent Test**: Can be tested by creating a chore through the UI, verifying the database record has a `description` field (not `template_content`), editing the description inline, and confirming the change persists without any PR or branch creation.

**Acceptance Scenarios**:

1. **Given** a user opens the chore creation dialog, **When** they enter a name and plain-text description and submit, **Then** a chore record is created in the database with the provided description, and no file is committed to the repository.
2. **Given** an existing chore displayed in the chore card, **When** the user edits the description inline and saves, **Then** the updated description is persisted to the database immediately, with no PR creation and no conflict detection prompt.
3. **Given** a chore creation payload, **When** the payload is sent to the create endpoint, **Then** the system accepts `description` (not `template_content`) and does not require or use `template_path`.

---

### User Story 3 — Migrate Existing Chore Data (Priority: P2)

When the system is upgraded, all existing chore records are migrated automatically. The `template_content` column is renamed to `description`, the `template_path` column is dropped, and any existing YAML front matter in stored content is stripped so that descriptions contain only the user-authored body text.

**Why this priority**: Without this migration, existing chore data would be incompatible with the new schema. This shares P2 priority with Story 2 because both are foundational to the new model — the migration ensures backward compatibility while Story 2 defines the new creation flow.

**Independent Test**: Can be tested by running the migration against a database containing chores with YAML front matter, then querying the migrated records to verify the front matter is stripped and the column names are correct.

**Acceptance Scenarios**:

1. **Given** an existing chore record with `template_content` containing YAML front matter (e.g., `---\nname: Bug Bash\n---\n## Content`), **When** the migration runs, **Then** the record's `description` field contains only `## Content` with the front matter removed.
2. **Given** an existing chore record with `template_content` that has no YAML front matter, **When** the migration runs, **Then** the content is preserved as-is in the `description` field.
3. **Given** the migration completes, **When** querying the chores table, **Then** the `template_path` column no longer exists and the `template_content` column has been renamed to `description`.

---

### User Story 4 — Simplified Frontend Without Template Management (Priority: P3)

The chore creation modal no longer shows a template picker or repository template buttons. The "Template Content" label is renamed to "Description". The chore card no longer shows a "Save & Create PR" button. All PR status indicators, SHA conflict warnings, and template-related UI elements are removed. The frontend sends `description` in payloads instead of `template_content`.

**Why this priority**: This is the cosmetic and UX layer that completes the user-facing transition. It depends on backend changes (Stories 1–3) being in place but delivers value by removing confusing template-management UI that no longer serves a purpose.

**Independent Test**: Can be tested by opening the chore creation modal and verifying the template picker is absent, creating a chore and confirming the payload uses `description`, editing a chore inline and confirming no PR-related UI appears, and verifying the "Save & Create PR" button is gone from chore cards.

**Acceptance Scenarios**:

1. **Given** a user opens the Add Chore modal, **When** the modal renders, **Then** there is no template picker section, no "useChoreTemplates" data fetched, and the content field is labeled "Description".
2. **Given** a user views a chore card, **When** the card renders, **Then** there is no "Save & Create PR" button and no PR status indicator.
3. **Given** a user edits a chore inline, **When** the editor renders, **Then** there is no SHA conflict detection UI and no PR status display.

---

### User Story 5 — Preset Chores as Plain Descriptions (Priority: P3)

The three built-in preset chores (Security Review, Performance Review, Bug Basher) are updated to use plain description text. Their YAML front matter is stripped, and the preset seeding logic stores descriptions rather than template-formatted content. Preset chores behave identically to user-created chores.

**Why this priority**: Presets are a convenience feature. They must be updated for consistency, but they don't block the core flow. Existing presets in the database are handled by the migration (Story 3); this story covers the seed definitions and preset files themselves.

**Independent Test**: Can be tested by seeding presets into a fresh project and verifying the stored description does not contain YAML front matter, the `template_path` field is absent, and triggering a preset chore follows the unified pipeline flow.

**Acceptance Scenarios**:

1. **Given** the preset seed definitions, **When** presets are seeded into a new project, **Then** each preset's `description` field contains plain text with no YAML front matter, and no `template_path` value is stored.
2. **Given** a previously seeded preset that was stored with YAML front matter, **When** the migration runs, **Then** the preset's description is cleaned of front matter just like any other chore.

---

### User Story 6 — Cleanup Dead Code and Endpoints (Priority: P3)

All template-related backend code, API endpoints, frontend hooks, API client methods, and type definitions are removed. This includes: the `GET /{project_id}/templates` endpoint, `inline-update` and `create-with-merge` endpoints, `build_template()`, `derive_template_path()`, `update_template_in_repo()`, the `ChoreTemplate` type, `useChoreTemplates()` hook, and corresponding API client methods. The utility function `is_sparse_input()` is preserved but relocated to a shared utilities module.

**Why this priority**: Dead code removal is a cleanup task that reduces maintenance burden. It depends on all other stories being complete to ensure nothing still references the removed code.

**Independent Test**: Can be tested by searching the codebase for references to removed functions, types, and endpoints — confirming zero matches — and verifying `is_sparse_input()` is importable from its new location and behaves identically.

**Acceptance Scenarios**:

1. **Given** the cleanup is complete, **When** searching the codebase for `template_path`, `template_content`, `build_template`, `derive_template_path`, `update_template_in_repo`, `ChoreTemplate`, `useChoreTemplates`, `listTemplates`, `inlineUpdate`, `createWithMerge`, **Then** no references remain outside of migration files and version history.
2. **Given** `is_sparse_input()` was moved to a utilities module, **When** the chat flow imports and calls it, **Then** it behaves identically to the original implementation.
3. **Given** the `/templates` endpoint was removed, **When** a client requests `GET /{project_id}/templates`, **Then** the server returns a 404 or method-not-allowed response.

---

### Edge Cases

- What happens when a chore's description is empty or whitespace-only? The system should reject creation with a validation error rather than creating a blank GitHub issue.
- What happens when `execute_pipeline_launch()` fails mid-execution (e.g., GitHub API rate limit)? The chore's `current_issue_number` should not be set if the issue was never created, preventing a phantom "open instance" lock.
- What happens when the migration encounters a `template_content` value that is only YAML front matter with no body? The description should be set to an empty string, and the chore should still be queryable.
- What happens when a scheduled chore triggers while the pipeline launch flow is experiencing transient errors? The chore should remain in a triggerable state so the next evaluation cycle can retry.
- What happens when `is_sparse_input()` is imported from its new utilities location by both the chore chat flow and any future consumers? The function should be a pure utility with no service-layer dependencies.
- What happens when an existing chore has a `pr_number` or `tracking_issue_number` at migration time? These fields can be dropped or nulled since the PR workflow is being removed entirely; open PRs should be documented for manual cleanup.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST rename the chore data field from `template_content` to `description` in both the data model and database schema.
- **FR-002**: System MUST remove the `template_path` field from the chore data model and database schema.
- **FR-003**: System MUST provide a database migration that renames `template_content` → `description`, drops `template_path`, and strips YAML front matter from all existing `description` values.
- **FR-004**: System MUST rewrite `trigger_chore()` to delegate issue creation and pipeline orchestration to the existing `execute_pipeline_launch()` flow, passing the chore's `description` as issue content.
- **FR-005**: System MUST pass the chore's name as the issue title (overriding AI title derivation) when triggering through the pipeline launch flow.
- **FR-006**: System MUST append `"chore"` to the label set for every chore-triggered issue, in addition to any AI-classified labels.
- **FR-007**: System MUST preserve the 1-open-instance check in `trigger_chore()`, skipping creation when an open issue already exists for the chore.
- **FR-008**: System MUST preserve CAS (compare-and-swap) update of `current_issue_number` and `execution_count` tracking after successful trigger.
- **FR-009**: The `execute_pipeline_launch()` function MUST accept optional parameters for extra labels and issue title override so that callers can inject additional labels and a custom title without modifying the core flow.
- **FR-010**: System MUST remove the template-listing endpoint (`GET /{project_id}/templates`) from the chore API.
- **FR-011**: System MUST remove or simplify the inline-update endpoint to save directly to the database without PR creation or SHA conflict detection.
- **FR-012**: System MUST simplify the chore creation endpoint to accept `description` instead of `template_content` and stop calling template-building or path-derivation functions.
- **FR-013**: System MUST remove `build_template()`, `derive_template_path()`, and `update_template_in_repo()` from the template builder module.
- **FR-014**: System MUST relocate `is_sparse_input()` to a shared utilities module, preserving its existing behavior and ensuring all current callers are updated.
- **FR-015**: The frontend chore creation modal MUST remove the template picker UI, rename the content field label from "Template Content" to "Description", and send `description` in the creation payload.
- **FR-016**: The frontend chore card MUST remove the "Save & Create PR" button and all PR status indicators.
- **FR-017**: The frontend inline editor MUST remove SHA conflict detection and PR status display.
- **FR-018**: Frontend hooks MUST remove `useChoreTemplates()`, simplify `useCreateChoreWithAutoMerge()` to `useCreateChore()`, and update all payloads to use `description`.
- **FR-019**: The frontend API client MUST remove `listTemplates()`, `inlineUpdate()`, and `createWithMerge()` methods, and update create/update payloads to use `description`.
- **FR-020**: The frontend `ChoreTemplate` type MUST be removed, and the `Chore` type MUST be updated to use `description` instead of `template_content` and remove `template_path`.
- **FR-021**: Built-in preset files MUST be converted from YAML-front-matter templates to plain description text.
- **FR-022**: The preset seeding logic MUST store descriptions (not template-formatted content) and omit `template_path`.
- **FR-023**: System MUST validate that chore descriptions are non-empty at creation time.
- **FR-024**: All existing backend and frontend tests MUST be updated to reflect the new field names, removed endpoints, and simplified flows. Template builder and PR-related tests MUST be removed.

### Key Entities

- **Chore**: A recurring or manually-triggered task definition. Key attributes: `id`, `name`, `description` (replaces `template_content`), `schedule_type`, `schedule_value`, `status`, `current_issue_number`, `execution_count`, `ai_enhance_enabled`, `agent_pipeline_id`, `is_preset`, `preset_id`. Relationship: belongs to a Project.
- **Pipeline Launch**: The unified flow for creating a parent issue, classifying labels, deriving title, creating sub-issues, and dispatching agents. Now extended with optional `extra_labels` and `issue_title_override` parameters. Relationship: invoked by Chore trigger and Parent Issue Intake panel.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can create a chore with a plain-text description in a single step, with the chore saved to the database in under 2 seconds and no repository files or pull requests created.
- **SC-002**: Triggering a chore produces a GitHub issue via the unified pipeline flow, with the chore name as the issue title, a "chore" label present, and sub-issues created — matching the behavior of the Parent Issue Intake panel.
- **SC-003**: Inline editing a chore's description saves to the database in under 2 seconds with no PR, branch, or SHA-based conflict detection involved.
- **SC-004**: The database migration completes successfully for all existing chores, stripping YAML front matter and renaming fields, with zero data loss of user-authored content.
- **SC-005**: Zero references to `template_path`, `template_content`, `build_template`, `derive_template_path`, `update_template_in_repo`, `ChoreTemplate`, `useChoreTemplates`, `.github/ISSUE_TEMPLATE/chore-*.md` remain in the codebase outside of migration files.
- **SC-006**: All backend tests pass (`uv run pytest`), all frontend tests pass (`npm test`), and the frontend builds without errors (`npm run build`) after the changes.
- **SC-007**: The `is_sparse_input()` function remains available and functional in its new utilities location, with all existing callers updated and working.
- **SC-008**: Preset chores seeded into a fresh project contain plain description text with no YAML front matter and trigger correctly through the unified pipeline flow.
- **SC-009**: The 1-open-instance constraint continues to prevent duplicate issues — triggering a chore with an open issue returns a skip reason 100% of the time.
- **SC-010**: The chore creation and editing flows require fewer user interactions than before (no PR approval, no template picker selection, no merge waiting).

## Assumptions

- The existing `execute_pipeline_launch()` function can be extended with optional parameters without breaking its current callers (Parent Issue Intake panel and app creation flow).
- The `execute_pipeline_launch()` function may need to be extracted from the API layer into a service-layer function to avoid request-scoped dependency issues when called from the chores service. This extraction is an implementation detail to be resolved during planning.
- Existing open PRs created by the old chore template workflow will be left for manual cleanup by maintainers; the migration does not auto-close these PRs.
- The `pr_number`, `pr_url`, and `tracking_issue_number` fields on the Chore model can be safely removed since the PR workflow is being eliminated entirely (clean break, not soft deprecation).
- The three built-in presets (Security Review, Performance Review, Bug Basher) will have their content rewritten as plain descriptions during this feature's implementation; the exact wording is an implementation detail.
- The sparse input detection heuristic in `is_sparse_input()` does not need modification — only its file location changes.
- The scheduled trigger evaluation (`evaluate_triggers()`) will continue to work unchanged since it calls `trigger_chore()` internally, and that function's external contract (accepts a Chore, returns a ChoreTriggerResult) is preserved.
- The chore chat flow for sparse input refinement remains unchanged; it continues to use `is_sparse_input()` from its new location.
