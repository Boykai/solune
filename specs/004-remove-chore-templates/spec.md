# Feature Specification: Remove Issue Templates, Use DB + Parent Issue Intake Flow

**Feature Branch**: `004-remove-chore-templates`
**Created**: 2026-04-13
**Status**: Draft
**Input**: Parent issue Boykai/solune#1716 — Chores — Remove Issue Templates, Use DB + Parent Issue Intake Flow

## Summary

Remove all ISSUE_TEMPLATE integration from Chores. Chore descriptions live only in the database. When triggered, a chore's description feeds into the same `execute_pipeline_launch()` flow used by the Parent Issue Intake panel — getting transcript detection, AI label classification, title derivation, sub-issue creation, and pipeline orchestration for free.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Chore Description Stored in DB Only (Priority: P1)

A user creates a new chore by providing a name and plain-text description. The description is saved directly to the database without generating a `.github/ISSUE_TEMPLATE/*.md` file or opening a PR. No YAML front matter wrapping occurs.

**Why this priority**: This is the foundational change — every other story depends on the chore model using `description` instead of `template_content`/`template_path`.

**Independent Test**: Create a chore via the API or UI, verify the DB record has a `description` column (not `template_content`), and verify no GitHub API calls to create files or PRs were made.

**Acceptance Scenarios**:

1. **Given** a user submits a chore with name and description, **When** the chore is created, **Then** the DB record contains the description in the `description` column.
2. **Given** a chore is created, **When** the operation completes, **Then** no `.github/ISSUE_TEMPLATE/chore-*.md` file exists in the repo.
3. **Given** a chore is created, **When** the operation completes, **Then** no PR was opened for template creation.

---

### User Story 2 — Chore Trigger Uses execute_pipeline_launch() (Priority: P1)

When a chore is triggered (manually or by schedule), it calls `execute_pipeline_launch()` with the chore's description as `issue_description`, the chore name as title override, and `["chore"]` as extra labels. The chore gets the same AI label classification, sub-issue creation, and pipeline orchestration as Parent Issue Intake.

**Why this priority**: This is the core behavioral change — replacing ~200 lines of manual issue creation + pipeline launch with a single delegated call.

**Independent Test**: Trigger a chore and verify the resulting GitHub issue has the chore name as title, `["chore"]` label, AI-classified labels, and sub-issues created per the pipeline.

**Acceptance Scenarios**:

1. **Given** a chore is triggered, **When** the pipeline completes, **Then** the GitHub issue title equals the chore name.
2. **Given** a chore is triggered, **When** the issue is created, **Then** it has a `"chore"` label plus AI-classified labels.
3. **Given** a chore is triggered, **When** the pipeline launches, **Then** sub-issues are created and agents are assigned (same as Parent Issue Intake).
4. **Given** a chore has a 1-open-instance constraint, **When** a trigger fires while an issue is open, **Then** the trigger is skipped.

---

### User Story 3 — Inline Edit Saves to DB Only (Priority: P2)

When a user edits a chore's description inline, the update saves directly to the database. No PR is created, no SHA conflict detection occurs, no file is committed to the repo.

**Why this priority**: Simplifies the edit flow by removing the PR/file sync path. Depends on US1 (model change).

**Independent Test**: Edit a chore's description, verify the DB record is updated, verify no GitHub file API calls were made.

**Acceptance Scenarios**:

1. **Given** a user edits a chore description inline, **When** the edit is saved, **Then** the DB record is updated immediately.
2. **Given** a user edits a chore, **When** the save completes, **Then** no PR is created and no SHA conflict check occurs.

---

### User Story 4 — Frontend Template UI Removed (Priority: P2)

The AddChoreModal no longer shows template picker buttons or loads repo templates. The field is labeled "Description" instead of "Template Content". The ChoreCard no longer shows "Save & Create PR" — it saves directly.

**Why this priority**: Frontend cleanup depends on backend model changes (US1) and API changes (US3).

**Independent Test**: Open the AddChoreModal, verify no template picker is shown. Edit a chore card, verify the button says "Save" (not "Save & Create PR").

**Acceptance Scenarios**:

1. **Given** a user opens AddChoreModal, **When** the modal renders, **Then** no template picker buttons are visible.
2. **Given** a user opens AddChoreModal, **When** the modal renders, **Then** the text field is labeled "Description".
3. **Given** a user edits a chore inline, **When** the card renders, **Then** the save button says "Save" (not "Save & Create PR").

---

### User Story 5 — Preset Chores Use Plain Descriptions (Priority: P3)

The 3 built-in preset chores (Security Review, Performance Review, Bug Basher) store plain descriptions without YAML front matter. The `seed_presets()` function uses the `description` field.

**Why this priority**: Cleanup task — presets must conform to the new model but are not user-facing until seeded.

**Independent Test**: Seed presets, verify the DB records have plain descriptions without `---` YAML front matter delimiters.

**Acceptance Scenarios**:

1. **Given** presets are seeded, **When** the DB records are inspected, **Then** the `description` column contains plain text without YAML front matter.
2. **Given** preset files exist on disk, **When** they are read, **Then** they contain plain markdown without `---` delimiters at the top.

---

### Edge Cases

- What happens if a chore has an existing `template_content` with YAML front matter during migration? The migration strips YAML front matter from existing rows using the `_strip_front_matter()` logic.
- What happens if `execute_pipeline_launch()` requires HTTP-scoped dependencies that aren't available from the chores service? The core logic must be extracted into a service-layer function or the chores service must construct a compatible session context.
- What happens if a preset file has no YAML front matter? The stripping logic is a no-op for plain text.
- What happens when a chore has `template_path` set in existing DB rows? The migration drops the column entirely; existing values are discarded.
- What happens to existing PRs opened by chores before the migration? They remain as-is in GitHub but are no longer tracked or referenced by the app.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The Chore model MUST use `description` (not `template_content`) to store chore body text.
- **FR-002**: The Chore model MUST NOT have a `template_path` field.
- **FR-003**: The `trigger_chore()` method MUST delegate to `execute_pipeline_launch()` for issue creation and pipeline orchestration.
- **FR-004**: The `trigger_chore()` method MUST pass the chore name as the issue title (not derived from description).
- **FR-005**: The `trigger_chore()` method MUST pass `["chore"]` as extra labels on the created issue.
- **FR-006**: The `trigger_chore()` method MUST preserve the 1-open-instance check and CAS update with issue_number tracking.
- **FR-007**: The `execute_pipeline_launch()` function MUST accept `extra_labels` and `issue_title_override` parameters.
- **FR-008**: Inline chore edits MUST save directly to the database without creating PRs or checking file SHAs.
- **FR-009**: The AddChoreModal MUST NOT display template picker buttons.
- **FR-010**: The AddChoreModal MUST label the content field as "Description".
- **FR-011**: The ChoreCard MUST NOT display "Save & Create PR" — only "Save".
- **FR-012**: The `template_builder.py` functions `build_template()`, `derive_template_path()`, `update_template_in_repo()` MUST be removed.
- **FR-013**: The `is_sparse_input()` function MUST be preserved and relocated to a utils module.
- **FR-014**: The API endpoints `GET /{project_id}/templates`, `PUT /.../inline-update`, `POST /.../create-with-merge` MUST be removed or simplified.
- **FR-015**: The DB migration MUST rename `template_content` → `description`, drop `template_path`, and strip YAML front matter from existing rows.
- **FR-016**: Preset files MUST be rewritten as plain descriptions without YAML front matter.
- **FR-017**: The `seed_presets()` function MUST use the `description` field.
- **FR-018**: All existing automated tests MUST pass after migration (updated where needed).

### Key Entities

- **Chore**: Recurring maintenance task with a DB-stored description (formerly template_content).
- **execute_pipeline_launch()**: Core pipeline orchestration function in `pipelines.py` — creates issues, classifies labels, creates sub-issues, starts agents.
- **Preset Chore**: Built-in chore (Security Review, Performance Review, Bug Basher) seeded from files.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Zero references to `.github/ISSUE_TEMPLATE/chore-*.md` remain in the codebase.
- **SC-002**: Creating a chore makes zero GitHub file/PR API calls.
- **SC-003**: Triggering a chore produces identical pipeline behavior to Parent Issue Intake (label classification, sub-issues, agent dispatch).
- **SC-004**: Chore trigger issues have `["chore"]` label and chore name as title.
- **SC-005**: `uv run pytest`, `npm test`, `npm run build` all pass.
- **SC-006**: Frontend shows "Description" (not "Template Content") in AddChoreModal.
- **SC-007**: Frontend ChoreCard save button says "Save" (not "Save & Create PR").

## Assumptions

- The `execute_pipeline_launch()` function's HTTP-scoped `UserSession` dependency can be satisfied by constructing a session object from the chores service context (access_token, github_user_id).
- Existing chores with YAML front matter in `template_content` will be correctly stripped during migration.
- The 3 preset files can be rewritten in-place without breaking backwards compatibility.
- No external systems depend on the `template_path` field or the template file API endpoints.
- The `is_sparse_input()` function's only non-template-builder consumer is the chat flow, confirming it should be preserved.
