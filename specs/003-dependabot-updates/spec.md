# Feature Specification: Apply All Safe Dependabot Updates

**Feature Branch**: `003-dependabot-updates`
**Created**: 2026-04-19
**Status**: Draft
**Input**: User description: "Apply All Safe Dependabot Updates — Review all open Dependabot pull requests in this repository and apply every dependency update that does not break the application."

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Discover and Prioritize Open Dependabot PRs (Priority: P1)

A maintainer wants to see every open Dependabot pull request in the repository, grouped by ecosystem and ranked by risk level (patch → minor → major). This gives the team a clear picture of the pending dependency updates and the order in which they should be evaluated.

**Why this priority**: Discovery is the prerequisite for every subsequent step. Without a complete, prioritized inventory of open Dependabot PRs, the team cannot safely decide what to apply. This story delivers value on its own by surfacing the full scope of pending updates.

**Independent Test**: Can be fully tested by listing all open Dependabot PRs, confirming they are grouped by ecosystem, and verifying the sort order is patch → minor → major. Delivers value by providing an actionable inventory.

**Acceptance Scenarios**:

1. **Given** the repository has open pull requests authored by `dependabot[bot]`, **When** the discovery step runs, **Then** every open Dependabot PR is identified and listed with its package name, ecosystem, current version, and target version.
2. **Given** the discovered PRs span multiple ecosystems (e.g., npm, pip, GitHub Actions), **When** the inventory is produced, **Then** PRs are grouped by ecosystem.
3. **Given** a mix of patch, minor, and major version bumps, **When** the inventory is prioritized, **Then** patch bumps appear first, followed by minor, then major.
4. **Given** two Dependabot PRs that update the same transitive dependency or have overlapping version constraints, **When** the inventory is produced, **Then** those PRs are flagged as overlapping so they can be handled carefully.

---

### User Story 2 — Apply and Verify Each Safe Update (Priority: P1)

A maintainer applies each Dependabot dependency update one at a time, in priority order, and verifies that the build and test suite pass. Updates that pass are kept; updates that fail are recorded and skipped. After each successful update, the dependency state is consistent before starting the next.

**Why this priority**: This is the core value of the feature — actually applying safe updates and rejecting unsafe ones. Without this story, the inventory from Story 1 is informational only. This story is also P1 because it directly reduces the security and maintenance burden of outdated dependencies.

**Independent Test**: Can be tested by applying a single Dependabot update, running the build and test suite, and confirming the update is accepted (if passing) or rejected (if failing). Each update is independently verifiable.

**Acceptance Scenarios**:

1. **Given** a prioritized list of Dependabot PRs, **When** each update is applied in priority order, **Then** the dependency version change is applied to the appropriate manifest and lock files.
2. **Given** an update has been applied to the manifest and lock files, **When** the build and test suite run, **Then** both complete without errors for a safe update.
3. **Given** a dependency update where the build or test suite fails, **When** the failure is detected, **Then** the update is not kept, and the package name, target version, and a one-line failure summary are recorded.
4. **Given** a successful update has been applied, **When** the next update is started, **Then** the dependency state reflects all previously applied successful updates so that version resolution remains consistent.
5. **Given** a repository that uses a lock file, **When** a dependency version is changed in the manifest, **Then** the lock file is regenerated (not manually edited) to reflect the new dependency graph.

---

### User Story 3 — Combine Successful Updates into a Single PR (Priority: P2)

A maintainer produces a single pull request that contains all successfully applied updates, along with a clear description of what was updated and what was skipped. The corresponding Dependabot PRs and branches are cleaned up.

**Why this priority**: Combining updates into one PR keeps the commit history clean and reduces review overhead. It depends on Story 2 (the updates must be applied and verified first) but delivers significant value by making the batch update reviewable as a single unit.

**Independent Test**: Can be tested by verifying that the resulting PR contains all successful updates, the PR description lists every applied update with old → new versions, skipped updates with reasons are documented, and the corresponding Dependabot PR branches are cleaned up.

**Acceptance Scenarios**:

1. **Given** multiple dependency updates have been successfully applied and verified, **When** the batch PR is created, **Then** it contains all successful updates in a single branch targeting the default branch.
2. **Given** the batch PR is created, **When** a reviewer opens the PR description, **Then** it includes a checklist of every applied update (package name, old version → new version) and a section listing skipped updates with the reason for each.
3. **Given** a Dependabot PR whose update was successfully applied to the batch PR, **When** the batch PR is created, **Then** the corresponding Dependabot PR is closed and its remote branch is deleted.
4. **Given** a Dependabot PR whose update was skipped (failed verification), **When** the batch PR is created, **Then** the Dependabot PR remains open and its branch is not deleted.

---

### User Story 4 — Respect Repository Constraints (Priority: P2)

A maintainer can trust that the batch update process does not introduce unintended changes — no application code, test code, or configuration is modified beyond what is strictly required by the dependency upgrade. Major version bumps that require code changes are identified and skipped with clear documentation of what migration steps would be needed.

**Why this priority**: This story protects the integrity of the codebase during the update process. It is P2 because it acts as a guardrail for Stories 2 and 3, ensuring the updates are truly "safe" and do not introduce scope creep.

**Independent Test**: Can be tested by reviewing the diff of the batch PR and confirming that only dependency manifest and lock files are changed. Any skipped major updates should include migration notes.

**Acceptance Scenarios**:

1. **Given** the batch update process is running, **When** updates are applied, **Then** only dependency manifest files and lock files are modified — no application code, test code, or non-dependency configuration is changed.
2. **Given** a major version bump that requires code changes to pass the test suite, **When** the update is attempted and tests fail, **Then** the update is skipped and the failure record includes a note about what migration steps are needed.
3. **Given** the batch update process is running, **When** branch operations occur, **Then** only Dependabot-authored branches are closed or deleted — no other branches are force-pushed or removed.

---

### Edge Cases

- What happens when there are no open Dependabot PRs? The process completes immediately with a message indicating no updates are pending and no PR is created.
- What happens when all Dependabot updates fail verification? No batch PR is created; instead, a report is produced listing every skipped update and the reason for failure.
- What happens when two Dependabot PRs update the same transitive dependency to different versions? The overlapping PRs are flagged during discovery. The higher-priority (lower-risk) update is attempted first; if it succeeds, the overlapping PR is re-evaluated against the updated dependency graph.
- What happens when a lock file regeneration changes transitive dependencies beyond the direct update? This is expected behaviour — the lock file reflects the full dependency graph. The build and test suite verification ensures the resulting state is safe.
- What happens when the build or test command cannot be determined? The process looks for scripts in `package.json`, `pyproject.toml`, `Makefile`, `Taskfile`, or CI workflow files. If no obvious command is found, the update is skipped with a note explaining that no test command could be identified.
- What happens when a Dependabot PR branch has merge conflicts with the default branch? The update is skipped with a note indicating a merge conflict, and the Dependabot PR remains open for manual resolution.
- What happens when network or rate-limit errors occur while closing Dependabot PRs? The batch PR is still created with all successful updates; cleanup of Dependabot PRs is retried or documented as incomplete for manual follow-up.

## Requirements *(mandatory)*

### Functional Requirements

#### Discovery

- **FR-001**: The process MUST list every open pull request authored by `dependabot[bot]` in the repository.
- **FR-002**: The process MUST group discovered PRs by ecosystem (e.g., npm, pip, GitHub Actions, Maven) and record the current version and target version for each dependency.
- **FR-003**: The process MUST identify PRs that update the same transitive dependency or have overlapping version constraints and flag them for careful handling.

#### Prioritization

- **FR-004**: The process MUST apply updates in risk order: patch version bumps first, then minor version bumps, then major version bumps.
- **FR-005**: Within each risk tier, the process MUST apply updates with no overlap to other PRs before those with overlapping dependencies.
- **FR-006**: For major version bumps, the process MUST inspect changelogs or migration guides (where available) before attempting the update.

#### Apply & Verify

- **FR-007**: For each update, the process MUST start from a clean state based on the default branch with all previously successful updates applied.
- **FR-008**: The process MUST apply the dependency version change to the appropriate manifest files (e.g., `package.json`, `pyproject.toml`, `requirements.txt`).
- **FR-009**: If the repository uses a lock file (`package-lock.json`, `pnpm-lock.yaml`, `yarn.lock`, `poetry.lock`, etc.), the process MUST regenerate it after each manifest change — the lock file MUST NOT be edited manually.
- **FR-010**: The process MUST run the full build after applying each update.
- **FR-011**: The process MUST run the repository's existing test suite after a successful build. If no obvious test command exists, the process MUST search for scripts in `package.json`, `pyproject.toml`, `Makefile`, `Taskfile`, or CI workflow files.
- **FR-012**: If the build and tests pass, the update MUST be committed and retained for the batch PR.
- **FR-013**: If the build or tests fail, the update MUST NOT be applied. The process MUST record the package name, target version, and a one-line failure summary, then continue to the next update.

#### Batch PR

- **FR-014**: All successful updates MUST be combined into a single pull request targeting the default branch, titled `chore(deps): apply Dependabot batch update`.
- **FR-015**: The PR description MUST include a checklist of every applied update (package name, old version → new version).
- **FR-016**: The PR description MUST include a section listing any skipped updates with the reason for each.
- **FR-017**: For each successfully applied update, the corresponding Dependabot PR MUST be closed and its remote branch MUST be deleted.
- **FR-018**: Dependabot PRs whose updates were skipped MUST remain open with their branches intact.

#### Constraints

- **FR-019**: The process MUST NOT change application code, test code, or configuration beyond what is required by the dependency upgrade.
- **FR-020**: If a major version bump requires code changes to pass tests, the update MUST be skipped and the failure record MUST note what migration steps are needed.
- **FR-021**: The process MUST NOT force-push or delete branches that are not Dependabot branches.

### Key Entities

- **Dependabot PR**: An open pull request authored by `dependabot[bot]` that proposes a single dependency version change. Key attributes: package name, ecosystem, current version, target version, version bump type (patch/minor/major), overlap status.
- **Update Result**: The outcome of attempting to apply a single Dependabot PR. Key attributes: package name, old version, new version, status (applied/skipped), failure summary (if skipped).
- **Batch PR**: The single combined pull request containing all successfully applied updates. Key attributes: title, applied updates checklist, skipped updates list, target branch.
- **Dependency Manifest**: A file declaring direct dependencies (e.g., `package.json`, `pyproject.toml`). Modified during each update.
- **Lock File**: A file pinning the full resolved dependency graph (e.g., `package-lock.json`, `poetry.lock`). Regenerated (never manually edited) after each manifest change.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of open Dependabot PRs are evaluated — every PR is either applied successfully or skipped with a documented reason; no PR is silently ignored.
- **SC-002**: All applied dependency updates pass the full build and test suite before being included in the batch PR — zero regressions are introduced.
- **SC-003**: The batch PR contains a complete inventory: every applied update lists the package name, old version, and new version; every skipped update lists the package name, target version, and failure reason.
- **SC-004**: No application code, test code, or non-dependency configuration is modified in the batch PR — the diff is limited to dependency manifests and lock files.
- **SC-005**: All Dependabot PRs corresponding to successfully applied updates are closed and their remote branches deleted, reducing the open PR count by the number of successful updates.
- **SC-006**: The entire batch update process (discovery through PR creation) completes within a single working session — no manual intervention is required for updates that pass verification.

## Assumptions

- The repository has open Dependabot PRs at the time this process runs; if none exist, the process exits cleanly with no action taken.
- The repository has a working build and test suite that can be invoked via standard commands found in `package.json`, `pyproject.toml`, `Makefile`, `Taskfile`, or CI workflow files.
- Dependabot PRs each propose a single dependency version change (Dependabot's default behaviour); grouped PRs are not expected but would be handled as a single unit if encountered.
- The default branch is the merge target for the batch PR and is the baseline for all update attempts.
- Lock file regeneration is performed using the ecosystem's standard tooling (e.g., `npm install`, `poetry lock`, `pip-compile`) rather than manual edits.
- Network access to package registries is available during dependency installation and lock file regeneration.
- The process operator has sufficient repository permissions to close PRs, delete branches, and create new PRs.
