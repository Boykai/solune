# Feature Specification: Librarian — Automated Documentation Refresh Process

**Feature Branch**: `003-librarian`
**Created**: 2026-04-01
**Status**: Draft
**Input**: User description: "Librarian — A repeatable process for keeping project documentation accurate as software evolves. Language-agnostic, structure-agnostic, applicable to any codebase. Detects what changed, infers how the product's focus shifted, and rewrites docs to match reality."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Build a Change Manifest from Recent Activity (Priority: P1)

A team member initiates a documentation refresh cycle. The system establishes a baseline (last refresh marker or fallback), harvests changes from structured sources (changelog, specs, RFCs) and code diffs since that baseline, and compiles a categorized change manifest. The manifest groups findings into new capabilities, changed behavior, removed functionality, architectural changes, UX changes, and config/ops changes. The team member reviews the manifest to understand everything that changed.

**Why this priority**: Without knowing what changed, no documentation update is possible. The change manifest is the foundation for every subsequent phase. It delivers immediate value by giving the team a clear, structured picture of all project changes since the last refresh — replacing ad-hoc guesswork with a systematic catalog.

**Independent Test**: Can be fully tested by running the manifest-building process against a repository with known recent changes and verifying the output categorizes all changes correctly. Delivers a reviewable change report as standalone value.

**Acceptance Scenarios**:

1. **Given** a repository with a previous refresh baseline marker, **When** the team member initiates a refresh cycle, **Then** the system identifies the baseline and catalogs all changes since that marker into a structured manifest with six categories (new capabilities, changed behavior, removed functionality, architectural changes, UX changes, config/ops changes).
2. **Given** a repository with no previous refresh baseline, **When** the team member initiates a refresh cycle, **Then** the system falls back to the last release tag or a reasonable time window (e.g., 2 weeks) and produces a complete manifest from that point.
3. **Given** a repository where the changelog has Added/Changed/Removed/Fixed entries since the baseline, **When** the manifest is built, **Then** all changelog entries are included in the appropriate manifest categories.
4. **Given** a repository where code diffs show new entry points, deleted modules, changed configuration schemas, updated dependency manifests, or altered data models, **When** the manifest is built, **Then** each high-signal change is flagged and categorized in the manifest.

---

### User Story 2 - Infer Focus Shifts and Prioritize Updates (Priority: P1)

After the change manifest is compiled, the system analyzes it to determine how the product's focus has shifted. It measures change density by functional area, detects narrative-level shifts (new top-level capabilities, removed features, changed value proposition, new user personas), and assigns update priorities (P0 through P4) to guide which documentation to update first.

**Why this priority**: Focus-shift detection transforms a raw list of changes into actionable documentation priorities. Without it, all changes appear equally important, and the team risks spending time on low-impact doc updates while critical narrative shifts go unaddressed. This is co-prioritized with the manifest because together they form the analytical core of the refresh process.

**Independent Test**: Can be fully tested by feeding a known manifest (with predictable domain clustering and narrative shifts) into the focus-shift analysis and verifying the output correctly identifies the top development focus areas, detects any narrative shifts, and produces a prioritized update list.

**Acceptance Scenarios**:

1. **Given** a completed change manifest, **When** focus-shift analysis runs, **Then** the system groups manifest items by functional area and identifies the areas with the highest change density as the current development focus.
2. **Given** a manifest indicating a new top-level capability was added, **When** focus-shift analysis runs, **Then** the system flags a narrative shift and assigns a P0 priority to update the top-level README and docs landing page.
3. **Given** a manifest indicating features were added or changed without altering the primary value proposition, **When** focus-shift analysis runs, **Then** the system assigns P1 priority to feature-specific docs and guides.
4. **Given** a manifest indicating only configuration or operational changes, **When** focus-shift analysis runs, **Then** the system assigns P3 priority to setup guides and config reference docs.

---

### User Story 3 - Update the README to Reflect Current Reality (Priority: P2)

Based on the prioritized update list, the team member (or automated process) updates the project README. This includes revalidating the project description, auditing the feature list (adding new, removing deprecated, reordering by importance), verifying getting-started instructions, and updating visual or structural references.

**Why this priority**: The README is the project's storefront — the first document most users and contributors encounter. Keeping it accurate is essential for onboarding and trust. It depends on the manifest and focus-shift analysis (P1 stories) but delivers high-visibility value independently. It is slightly lower priority because it is one specific document rather than the analytical foundation.

**Independent Test**: Can be fully tested by running the README update process on a project with known feature changes and verifying that the resulting README accurately reflects the current feature set, correct getting-started instructions, and up-to-date description.

**Acceptance Scenarios**:

1. **Given** a focus-shift analysis indicating a narrative shift, **When** the README update runs, **Then** the project description (elevator pitch) is rewritten to reflect the current product identity.
2. **Given** newly shipped capabilities identified in the manifest, **When** the README feature list is audited, **Then** new features are added and the list is reordered by current importance.
3. **Given** features marked as removed or deprecated in the manifest, **When** the README feature list is audited, **Then** removed features are deleted and deprecated features are clearly marked.
4. **Given** changes to dependency manifests or build scripts, **When** the getting-started instructions are verified, **Then** prerequisite versions are updated and all quickstart commands produce expected output.

---

### User Story 4 - Update Documentation Files Against Their Source of Truth (Priority: P2)

For each documentation file affected by the prioritized update list, the system maps the doc to its source of truth, diffs the current doc against that source, identifies gaps (missing, stale, or dead content), and rewrites affected sections naturally. Structural docs (module maps, dependency graphs) are regenerated from the actual codebase.

**Why this priority**: Feature guides, configuration references, and architecture overviews are the bulk of a project's documentation surface. Updating them ensures the full documentation set — not just the README — stays accurate. This runs in parallel with README updates (also P2) because both are update actions driven by the manifest and priority list.

**Independent Test**: Can be fully tested by selecting a documentation file with known drift from its source of truth, running the update process, and verifying the rewritten doc matches the current codebase with no stale, missing, or dead content.

**Acceptance Scenarios**:

1. **Given** a documentation file and its mapped source of truth (e.g., config reference mapped to config schema definitions), **When** the doc is diffed against the source, **Then** all gaps are identified as missing (new things not documented), stale (documented things that changed), or dead (documented things that no longer exist).
2. **Given** identified gaps in a documentation file, **When** the doc is updated, **Then** affected sections are rewritten naturally (not patched with "UPDATE:" notes) so the document reads as if it was always correct.
3. **Given** a narrative shift was detected in the focus-shift analysis, **When** a feature guide is updated, **Then** the guide's framing and emphasis are adjusted to reflect the shifted product narrative.
4. **Given** the project's module structure has changed, **When** structural docs are updated, **Then** module/directory maps are regenerated from the actual filesystem and dependency graphs reflect current code.

---

### User Story 5 - Validate Documentation Consistency (Priority: P3)

After updates are applied, the system validates internal consistency across all documentation. This includes checking internal cross-references and external URLs, auditing terminology for renamed concepts, verifying diagram freshness, and validating embedded code samples.

**Why this priority**: Consistency validation catches errors introduced during the update process and ensures the documentation set works as a coherent whole. It is lower priority than the update stories because it is a quality gate — it refines work already done rather than producing new content.

**Independent Test**: Can be fully tested by running link validation, terminology audit, and code sample checks on a documentation set with known broken links, renamed terms, and outdated code snippets, then verifying all issues are detected and reported.

**Acceptance Scenarios**:

1. **Given** updated documentation files, **When** link validation runs, **Then** all broken internal cross-references, dead external URLs, and invalid anchor links are identified.
2. **Given** the change manifest includes renamed concepts, **When** the terminology audit runs, **Then** all occurrences of old names in documentation are flagged for replacement with the new names.
3. **Given** documentation contains embedded code snippets, **When** code sample validation runs, **Then** snippets that no longer compile or run against the current codebase are flagged.
4. **Given** the project uses auto-generated diagrams, **When** diagram freshness is checked, **Then** any diagrams that differ from their regenerated output are flagged as stale.

---

### User Story 6 - Stamp the Refresh and Reset the Baseline (Priority: P3)

After all updates and validations are complete, the system commits all documentation changes, updates the changelog with a documentation section, and sets a new baseline marker (tag or metadata file) so the next refresh cycle starts cleanly.

**Why this priority**: Stamping the refresh is the final bookkeeping step that closes the current cycle and enables future cycles. It is the lowest priority because it only needs to run once all other work is done and produces no user-facing content — but it is essential for the process to be repeatable.

**Independent Test**: Can be fully tested by completing a refresh cycle and verifying that a new baseline marker is set, the changelog includes a documentation section, and the next refresh cycle correctly identifies the new baseline.

**Acceptance Scenarios**:

1. **Given** all documentation updates and validations are complete, **When** the refresh is stamped, **Then** all doc changes are committed in a single, well-described commit.
2. **Given** a completed refresh, **When** the changelog is updated, **Then** a Documentation section is added noting which docs were updated and what key changes were made.
3. **Given** a completed refresh, **When** the baseline is set, **Then** a new marker (tag or metadata entry) is created with the current commit SHA and date.
4. **Given** a new baseline has been set, **When** the next refresh cycle begins, **Then** the system correctly identifies the new baseline as the starting point.

---

### Edge Cases

- What happens when the repository has no previous refresh baseline and no release tags? The system falls back to a configurable time window (default: 2 weeks of commit history) to establish an initial baseline.
- What happens when the changelog is missing or uses a non-standard format? The system proceeds with code-diff-based harvesting alone and notes that changelog parsing was skipped in the manifest summary.
- What happens when a documentation file has no identifiable source of truth? The file is flagged for manual review and excluded from automated diffing, but still included in link validation and terminology audit.
- What happens when the manifest contains zero changes since the last baseline? The system reports "no changes detected" and skips all update phases, preserving the existing baseline without creating a new one.
- What happens when a renamed concept appears in documentation that was not flagged for update? The terminology audit in the consistency validation phase catches these cross-cutting renames regardless of whether the specific doc was in the update priority list.
- What happens when getting-started instructions fail in a clean environment? The failure is logged with specific error details and the README update flags the getting-started section as requiring manual intervention.
- What happens when external URLs in documentation return temporary errors (e.g., 503)? The link validator retries transient errors (up to 3 attempts with backoff) and only flags persistent failures.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST establish a baseline for each refresh cycle by retrieving the last refresh marker (tag, metadata file, or commit SHA). If no baseline exists, the system MUST fall back to the last release tag or a configurable time window (default: 2 weeks).
- **FR-002**: System MUST harvest changes from structured sources — changelog entries (Added/Changed/Removed/Fixed) and feature spec, RFC, or ADR directories — since the established baseline.
- **FR-003**: System MUST harvest changes from code diffs, identifying files with significant churn and flagging high-signal changes: new or deleted entry points, public-facing modules, configuration schemas, dependency manifests, data models/schemas, and build/deployment scripts.
- **FR-004**: System MUST compile all harvested changes into a categorized manifest with six categories: new capabilities, changed behavior, removed functionality, architectural changes, UX changes, and config/ops changes.
- **FR-005**: System MUST analyze the change manifest to measure change density by functional area and identify the current development focus.
- **FR-006**: System MUST detect narrative-level shifts from the manifest, including new top-level capabilities, reduced or removed prominent features, shifted primary value proposition, changed primary user workflow, and new user personas.
- **FR-007**: System MUST assign update priorities (P0 through P4) based on detected shifts: P0 for product pitch or primary workflow changes, P1 for feature additions/changes/removals, P2 for architecture or structure changes, P3 for config/setup/ops changes, and P4 for bug fixes or edge case resolutions.
- **FR-008**: System MUST update the README by revalidating the project description, auditing the feature list (adding new, removing deprecated, reordering by importance), verifying getting-started instructions, and updating visual/structural references.
- **FR-009**: System MUST map each documentation file to its source of truth (e.g., config reference to config schema, API reference to route definitions) and diff the doc against that source to identify gaps categorized as missing, stale, or dead.
- **FR-010**: System MUST rewrite affected documentation sections naturally — not append patch notes — so the document reads as if it was always correct.
- **FR-011**: System MUST validate documentation consistency by checking internal cross-references, external URLs, anchor links, terminology consistency (replacing renamed concepts), diagram freshness, and embedded code sample correctness.
- **FR-012**: System MUST commit all documentation changes in a single well-described commit, update the changelog with a documentation section, and set a new baseline marker (tag or metadata) for the next cycle.
- **FR-013**: System MUST support any codebase regardless of programming language, project structure, or documentation format (language-agnostic and structure-agnostic).
- **FR-014**: System MUST produce a verification checklist at the end of each refresh confirming: manifest completeness, link resolution, feature-doc alignment, config-doc alignment, getting-started validity, no references to removed features, README accuracy, baseline reset, and changelog update.
- **FR-015**: System MUST regenerate structural documentation (module/directory maps, dependency graphs, architecture diagrams) from the actual filesystem and codebase rather than manually patching them.
- **FR-016**: System MUST retry transient errors during external URL validation (up to 3 attempts with backoff) and only flag persistent failures.
- **FR-017**: System MUST handle the case where no changes are detected since the last baseline by reporting "no changes" and preserving the existing baseline without creating a new one.

### Key Entities

- **Refresh Baseline**: The starting point for a documentation refresh cycle. Key attributes: identifier (tag name, commit SHA, or metadata reference), timestamp, and type (tag, metadata file, or commit).
- **Change Manifest**: A categorized inventory of all project changes since the last baseline. Key attributes: baseline reference, six change categories (new capabilities, changed behavior, removed functionality, architectural changes, UX changes, config/ops changes), and list of individual change items with source references.
- **Change Item**: A single identified change within the manifest. Key attributes: description, category, source (changelog entry, code diff, or spec file), and affected files or modules.
- **Focus Shift Analysis**: The result of analyzing the change manifest for narrative-level shifts. Key attributes: change density by functional area, detected narrative shifts, and prioritized update list (P0–P4).
- **Doc-to-Source Mapping**: A relationship linking a documentation file to its source of truth in the codebase. Key attributes: documentation file path, source of truth type (routes, config schema, module structure, etc.), and diffing method.
- **Verification Checklist**: A checklist produced at the end of each refresh cycle confirming documentation accuracy. Key attributes: list of verification items, pass/fail status for each, and notes on any items requiring manual follow-up.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A team member can complete a full documentation refresh cycle (from initiating the manifest to stamping the baseline) in under 2 hours for a medium-sized project, compared to the current ad-hoc approach.
- **SC-002**: 100% of changes committed since the last baseline are represented in the change manifest, with zero undiscovered changes after manual spot-check.
- **SC-003**: After a refresh cycle, zero documentation pages contain references to features, configuration keys, or workflows that no longer exist in the codebase.
- **SC-004**: After a refresh cycle, all internal documentation cross-references resolve correctly, with zero broken links detected by automated link validation.
- **SC-005**: After a refresh cycle, the README feature list matches the current product capabilities in priority order, with newly shipped features included and removed features absent.
- **SC-006**: Getting-started instructions run successfully from a clean environment after each refresh, with zero failures caused by outdated prerequisites or commands.
- **SC-007**: The process is applicable to any codebase regardless of programming language or project structure, validated by successfully running on at least 2 projects with different technology stacks.
- **SC-008**: Each refresh cycle produces a completed verification checklist with pass/fail status for every verification item, providing an auditable record of documentation accuracy.
- **SC-009**: Renamed concepts identified in the change manifest are updated across 100% of documentation files, with zero instances of old terminology remaining after the terminology audit.
- **SC-010**: The bi-weekly refresh cadence reduces documentation-related support questions or contributor confusion by at least 30% within 3 months of adoption.

## Assumptions

- The project uses Git for version control, and commit history is available for diff-based change harvesting.
- A changelog file or equivalent structured change record exists (though the process gracefully handles its absence by relying on code diffs alone).
- Documentation files are stored as text-based formats (e.g., Markdown, reStructuredText, AsciiDoc) within the repository or an accessible documentation system.
- The team has access to run the project's getting-started instructions in a clean environment (container, fresh clone, or CI) for verification purposes.
- The initial implementation of this process is manual, with automation added incrementally after 2–3 successful manual cycles validate the workflow.
- Link validation tooling (e.g., lychee, markdown-link-check, or equivalent) is available or can be installed in the project environment.
- The refresh cycle is owned by a rotating team member on a bi-weekly cadence, with per-PR doc updates handled by PR authors and per-release audits by the release manager.
