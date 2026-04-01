# Tasks: Librarian — Automated Documentation Refresh Process

**Input**: Design documents from `/specs/003-librarian/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/refresh-workflow.yaml
**Existing file extended by tasks**: quickstart.md (partially populated — incrementally built out by US1–US6 tasks)

**Tests**: Not included — the feature specification and constitution check explicitly state that no unit tests are required. This is a documentation workflow, not code logic. Validation is via the verification checklist (FR-014) and automated link checking (FR-011, FR-016).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Docs**: `solune/docs/` (documentation files, checklists, architectures)
- **Issue templates**: `.github/ISSUE_TEMPLATE/` (repository root)
- **Repo metadata**: `solune/docs/.last-refresh`, `solune/docs/.change-manifest.md`
- **Changelog**: `CHANGELOG.md` (repository root)
- **README**: `README.md` (repository root)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish the shared templates and structural files that multiple user stories depend on. No new backend or frontend code — all changes extend existing `solune/docs/` infrastructure.

- [x] T001 Create the doc-refresh verification checklist template at `solune/docs/checklists/doc-refresh-verification.md` with the 9 verification items defined in data-model.md Verification Checklist entity, each with pass/fail checkboxes and notes fields (FR-014)
- [x] T002 [P] Update `solune/docs/.change-manifest.md` to use the structured 6-category template format from data-model.md: add section headers for refresh window, SHA range, sources analyzed, and the six categories (new capabilities, changed behavior, removed functionality, architectural changes, UX changes, config/ops changes) plus a renames section and a verification checklist appendix section (FR-004)
- [x] T003 [P] Verify the existing `.github/ISSUE_TEMPLATE/chore-librarian.md` issue template includes all 7 phases as checklist items, references the verification checklist template from T001, and links to `specs/003-librarian/quickstart.md` for execution guidance — update if any items are missing

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Define the doc-to-source mapping reference and baseline fallback logic that ALL user stories depend on. These must be complete before any refresh phase can execute correctly.

**⚠️ CRITICAL**: The doc-to-source mapping and baseline conventions must be established before user story work begins.

- [x] T004 Add a doc-to-source mapping table to `solune/docs/OWNERS.md` listing each documentation file, its source-of-truth type, source paths, and diff method — use the 11 mappings defined in data-model.md (e.g., `docs/api-reference.md` → `routes` → `backend/src/api/*.py` → "List @router decorators → compare to doc") (FR-009)
- [x] T005 [P] Document the baseline fallback precedence in `specs/003-librarian/quickstart.md` Phase 1.1 section: (1) `.last-refresh` JSON `sha` field, (2) most recent `docs-refresh-*` git tag, (3) most recent release tag `v*`, (4) 2-week time window — include the exact git commands for each fallback level from research.md (FR-001)

**Checkpoint**: Doc-to-source mappings and baseline conventions are documented — refresh phases can now reference them.

---

## Phase 3: User Story 1 — Build a Change Manifest from Recent Activity (Priority: P1) 🎯 MVP

**Goal**: A team member initiates a documentation refresh and the system establishes a baseline, harvests changes from structured sources and code diffs, and compiles a categorized 6-category change manifest.

**Independent Test**: Run the manifest-building process against the Solune repository using the existing `.last-refresh` baseline. Verify the output `.change-manifest.md` includes all 6 categories, each change item has a description, category, source, domain, and affected docs list, and no commits since the baseline are missing from the manifest.

### Implementation for User Story 1

- [x] T006 [US1] Document Phase 1.1 (Establish the baseline) execution steps in `specs/003-librarian/quickstart.md` — read `solune/docs/.last-refresh` JSON to extract `sha` field, validate the SHA exists in git history with `git cat-file -t <sha>`, and fall back through the precedence chain if invalid (FR-001)
- [x] T007 [US1] Document Phase 1.2 (Harvest from structured sources) execution steps in `specs/003-librarian/quickstart.md` — parse `CHANGELOG.md` for Added/Changed/Removed/Fixed entries since baseline using `git diff <baseline>..HEAD -- CHANGELOG.md`, scan `specs/` and `solune/docs/decisions/` for new or modified files using `git diff --name-status <baseline>..HEAD -- specs/ solune/docs/decisions/` (FR-002)
- [x] T008 [US1] Document Phase 1.3 (Harvest from code diffs) execution steps in `specs/003-librarian/quickstart.md` — run `git diff --stat <baseline>..HEAD` and `git log --oneline <baseline>..HEAD`, flag high-signal changes using the file patterns from contracts/refresh-workflow.yaml (entry points, public modules, config schemas, dependency manifests, data models, build/deploy scripts) (FR-003)
- [x] T009 [US1] Document Phase 1.4 (Compile the manifest) execution steps in `specs/003-librarian/quickstart.md` — categorize all harvested items into the 6 manifest categories, deduplicate cross-source entries, assign domain labels, identify affected docs for each item, and write the result to `solune/docs/.change-manifest.md` using the template from T002 (FR-004)
- [x] T010 [US1] Document the edge case handling for Phase 1 in `specs/003-librarian/quickstart.md` — no baseline exists (use fallback chain per FR-001), changelog missing or non-standard (skip changelog parsing and proceed with code diffs only, noting the skip in the manifest summary), zero changes detected (report "no changes", skip all subsequent phases, preserve existing baseline per FR-017)

**Checkpoint**: Phase 1 process is fully documented and executable. A team member can build a complete change manifest from any Git repository.

---

## Phase 4: User Story 2 — Infer Focus Shifts and Prioritize Updates (Priority: P1)

**Goal**: Analyze the change manifest to measure change density by functional area, detect narrative-level shifts, and produce a prioritized update list (P0–P4) that guides which documentation to update first.

**Independent Test**: Feed the change manifest from US1 into the focus-shift analysis. Verify the output identifies the top 3 focus areas by change density, answers all 5 narrative-shift diagnostic questions, and produces a priority-ordered list mapping each affected doc to a P0–P4 priority level.

### Implementation for User Story 2

- [x] T011 [US2] Document Phase 2.1 (Measure change density by domain) execution steps in `specs/003-librarian/quickstart.md` — group manifest items by their `domain` field (e.g., pipeline, agents, auth, infra), count items per domain, rank domains by count to identify the top development focus areas (FR-005)
- [x] T012 [US2] Document Phase 2.2 (Detect narrative-level shifts) execution steps in `specs/003-librarian/quickstart.md` — answer the 5 diagnostic questions from contracts/refresh-workflow.yaml against the manifest: new top-level capability added, prominent feature reduced/removed/folded, primary value proposition shifted, primary user workflow changed, new user personas introduced (FR-006)
- [x] T013 [US2] Document Phase 2.3 (Prioritize updates) execution steps in `specs/003-librarian/quickstart.md` — assign P0–P4 priorities using the priority table from data-model.md, map each priority to specific documentation files that need updating, and produce the prioritized update list that drives Phases 3–4 (FR-007)
- [x] T014 [US2] Add the focus-shift analysis output format to `solune/docs/.change-manifest.md` template — include sections for change density by domain, narrative shift answers, and the prioritized update list with priority level, trigger, and target docs for each entry

**Checkpoint**: Phase 2 analysis process is fully documented. A team member can transform a raw change manifest into an actionable, prioritized documentation update plan.

---

## Phase 5: User Story 3 — Update the README to Reflect Current Reality (Priority: P2)

**Goal**: Update the project README based on the prioritized update list — revalidate the project description, audit the feature list, verify getting-started instructions, and update visual/structural references.

**Independent Test**: Run the README update process on the Solune project after completing US1 and US2. Verify the README description matches the current product, the feature list reflects shipped capabilities in priority order, getting-started instructions run successfully from a clean environment, and all badge URLs resolve.

### Implementation for User Story 3

- [x] T015 [US3] Document Phase 3.1 (Revalidate project description) execution steps in `specs/003-librarian/quickstart.md` — compare the current README elevator pitch against the focus-shift analysis, rewrite the description if a P0 narrative shift was detected, ensure the one-liner accurately describes what the product does today (FR-008)
- [x] T016 [US3] Document Phase 3.2 (Audit feature list) execution steps in `specs/003-librarian/quickstart.md` — cross-reference the README feature list against manifest categories: add newly shipped capabilities from "new capabilities", remove items from "removed functionality", update items from "changed behavior", and reorder by current importance based on change density (FR-008)
- [x] T017 [US3] Document Phase 3.3 (Verify getting-started instructions) execution steps in `specs/003-librarian/quickstart.md` — run the quickstart from `solune/docs/setup.md` in a clean environment, check prerequisite versions against `pyproject.toml` and `package.json`, validate that all commands produce expected output, flag failures for manual intervention — if getting-started instructions fail in a clean environment, log specific error details and flag the section as requiring manual fix (FR-008)
- [x] T018 [US3] Document Phase 3.4 (Update visual/structural references) execution steps in `specs/003-librarian/quickstart.md` — replace outdated screenshots or diagrams if UX changes were detected, update architecture-at-a-glance diagrams if topology changed, verify all badge URLs and status links resolve using `lychee README.md` (FR-008)

**Checkpoint**: Phase 3 README update process is fully documented. The README accurately reflects the current product after each refresh cycle.

---

## Phase 6: User Story 4 — Update Documentation Files Against Their Source of Truth (Priority: P2)

**Goal**: For each documentation file affected by the prioritized update list, map it to its source of truth, diff current content against that source, identify gaps (missing, stale, dead), and rewrite affected sections naturally. Regenerate structural docs from the codebase.

**Independent Test**: Select a documentation file with known drift (e.g., `solune/docs/configuration.md` after a config change). Run the update process using the doc-to-source mapping from OWNERS.md. Verify the rewritten doc matches the current codebase with no stale, missing, or dead content, and sections read naturally without patch notes.

### Implementation for User Story 4

- [x] T019 [US4] Document Phase 4.1 (Map each doc to source of truth) execution steps in `specs/003-librarian/quickstart.md` — reference the doc-to-source mapping table added to `solune/docs/OWNERS.md` in T004, explain how to use source paths and diff methods for each doc type (routes, config_schema, module_structure, dependency_manifest, feature_code, cli_definition, schema_definition, bug_fixes) (FR-009)
- [x] T020 [US4] Document Phase 4.2 (Update affected docs) execution steps in `specs/003-librarian/quickstart.md` — for each doc in priority order: read current doc, diff against its source of truth using the method from OWNERS.md, categorize gaps as missing/stale/dead, rewrite affected sections naturally (not patched with "UPDATE:" notes), adjust framing if a narrative shift was detected (FR-010)
- [x] T021 [US4] Document Phase 4.3 (Update structural docs) execution steps in `specs/003-librarian/quickstart.md` — regenerate `solune/docs/project-structure.md` module/directory map from filesystem using `tree -I 'node_modules|.git|dist|__pycache__|.venv'`, regenerate architecture diagrams using `./solune/scripts/generate-diagrams.sh`, verify all code examples in rewritten sections compile/run (FR-015)
- [x] T022 [US4] Document the edge case handling for Phase 4 in `specs/003-librarian/quickstart.md` — doc has no identifiable source of truth (flag the file for manual review, exclude from automated diffing, but still include it in link validation and terminology audit during Phase 5) (FR-009)

**Checkpoint**: Phase 4 documentation update process is fully documented. All docs in `solune/docs/` can be systematically refreshed against their source of truth.

---

## Phase 7: User Story 5 — Validate Documentation Consistency (Priority: P3)

**Goal**: After updates are applied, validate internal consistency across all documentation — check links, audit terminology for renamed concepts, verify diagram freshness, and validate embedded code samples.

**Independent Test**: Run the consistency validation suite on the Solune docs directory. Verify all internal cross-references resolve, all external URLs are reachable (with retry for transient errors), no instances of old terminology from the rename list remain, and all auto-generated diagrams match their regenerated output.

### Implementation for User Story 5

- [x] T023 [US5] Document Phase 5.1 (Link validation) execution steps in `specs/003-librarian/quickstart.md` — run `lychee solune/docs/ README.md` to check internal cross-references and external URLs, configure retry (max 3 attempts with backoff for transient errors per FR-016), verify all anchor links point to existing headings (FR-011)
- [x] T024 [P] [US5] Document Phase 5.2 (Terminology audit) execution steps in `specs/003-librarian/quickstart.md` — extract renamed concepts from the "renames" section of `.change-manifest.md`, grep all docs for old names using `grep -rn "<old_term>" solune/docs/ README.md`, replace old names with new across all files regardless of whether the specific doc was in the priority list (FR-011, Edge Case 5)
- [x] T025 [P] [US5] Document Phase 5.3 (Diagram freshness) execution steps in `specs/003-librarian/quickstart.md` — run `./solune/scripts/generate-diagrams.sh --check` to verify auto-generated Mermaid diagrams in `solune/docs/architectures/` are current, manually verify non-generated diagrams still match reality (FR-011)
- [x] T026 [P] [US5] Document Phase 5.4 (Code sample validation) execution steps in `specs/003-librarian/quickstart.md` — extract embedded code snippets from Markdown files, verify syntax validity for the detected language, note any snippets that reference removed APIs or changed function signatures from the manifest (FR-011)

**Checkpoint**: Phase 5 consistency validation process is fully documented. Documentation quality gates catch errors introduced during updates and ensure the doc set works as a coherent whole.

---

## Phase 8: User Story 6 — Stamp the Refresh and Reset the Baseline (Priority: P3)

**Goal**: After all updates and validations are complete, commit documentation changes, update the changelog, complete the verification checklist, and set a new baseline marker so the next refresh cycle starts cleanly.

**Independent Test**: Complete a full refresh cycle on the Solune project. Verify a new `.last-refresh` JSON file is written with the current SHA and date, a `docs-refresh-YYYY-MM-DD` git tag is created, the changelog includes a Documentation section, the verification checklist has pass/fail for all 9 items, and the next refresh correctly uses the new baseline.

### Implementation for User Story 6

- [x] T027 [US6] Document Phase 7.1 (Commit documentation changes) execution steps in `specs/003-librarian/quickstart.md` — commit all doc updates in a single well-described commit using conventional message format `docs: refresh documentation for <start_date> to <end_date>` (FR-012)
- [x] T028 [US6] Document Phase 7.2 (Update the changelog) execution steps in `specs/003-librarian/quickstart.md` — add a Documentation section to `CHANGELOG.md` under the current `[Unreleased]` heading, list which docs were updated and summarize key changes (FR-012)
- [x] T029 [US6] Document Phase 7.3 (Set the new baseline) execution steps in `specs/003-librarian/quickstart.md` — update `solune/docs/.last-refresh` JSON with current date (ISO 8601), commit SHA, lists of documents_updated and documents_skipped, broken_links_found count, and manual_followups list; create git tag `docs-refresh-YYYY-MM-DD` pointing to the commit (FR-012)
- [x] T030 [US6] Document the verification checklist completion process in `specs/003-librarian/quickstart.md` — fill in the `solune/docs/checklists/doc-refresh-verification.md` template from T001 with pass/fail for all 9 items, append the completed checklist to `solune/docs/.change-manifest.md` as the final section, record overall status (pass/partial/fail) (FR-014)
- [x] T031 [US6] Document the edge case handling for Phase 7 in `specs/003-librarian/quickstart.md` — zero changes detected earlier (no new baseline created, existing baseline preserved per FR-017), verification items that fail (mark as fail with notes, set overall status to partial, list in manual_followups in `.last-refresh`)

**Checkpoint**: Phase 7 stamp and baseline process is fully documented. Each refresh cycle produces an auditable record and a clean starting point for the next cycle.

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that span multiple user stories and ensure the end-to-end process is cohesive.

- [x] T032 [P] Review `specs/003-librarian/quickstart.md` end-to-end for consistency — verify all 7 phases flow sequentially with clear handoffs, cross-reference task IDs, and ensure edge cases are documented in context
- [x] T033 [P] Verify all internal cross-references between `specs/003-librarian/` documents (plan.md, spec.md, data-model.md, quickstart.md, contracts/refresh-workflow.yaml) resolve correctly and use consistent terminology
- [x] T034 Add a "Running Your First Refresh" summary section to `specs/003-librarian/quickstart.md` — a condensed single-page checklist that walks through all 7 phases with the key command for each, suitable for quick reference during execution
- [x] T035 Validate the complete Librarian process by performing a dry-run refresh against the Solune repository — execute Phases 1–2 to produce a change manifest and priority list, spot-check Phase 3–4 guidance against actual docs, run Phase 5 link validation, and confirm Phase 7 baseline output format

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational (Phase 2) — manifest process
- **User Story 2 (Phase 4)**: Depends on US1 (Phase 3) — requires manifest output to analyze
- **User Story 3 (Phase 5)**: Depends on US2 (Phase 4) — requires prioritized update list
- **User Story 4 (Phase 6)**: Depends on US2 (Phase 4) — requires prioritized update list + doc-to-source mappings
- **User Story 5 (Phase 7)**: Depends on US3 (Phase 5) and US4 (Phase 6) — validates updated docs
- **User Story 6 (Phase 8)**: Depends on US5 (Phase 7) — stamps after all updates and validation
- **Polish (Phase 9)**: Depends on all user stories being complete

### User Story Dependencies

- **US1 (P1)**: Can start after Foundational — no dependency on other stories
- **US2 (P1)**: Depends on US1 — analyzes the manifest US1 produces
- **US3 (P2)**: Depends on US2 — uses the prioritized update list. Can run in parallel with US4
- **US4 (P2)**: Depends on US2 — uses the prioritized update list. Can run in parallel with US3
- **US5 (P3)**: Depends on US3 and US4 — validates the docs they updated
- **US6 (P3)**: Depends on US5 — stamps after validation is complete

### Within Each User Story

- Documentation steps within a story are sequential (each builds on prior context)
- Edge case documentation can be written in parallel with main flow docs
- Template/structural files (T001–T003) are independent of each other

### Parallel Opportunities

- T002 and T003 can run in parallel (different files, no dependencies)
- T004 and T005 can run in parallel (different files in Foundational phase)
- T024, T025, and T026 can run in parallel within US5 (independent validation checks)
- T032 and T033 can run in parallel in Polish phase (independent review tasks)
- US3 (Phase 5) and US4 (Phase 6) can run in parallel once US2 is complete (both consume the priority list independently)

---

## Parallel Example: User Story 5 (Validate Consistency)

```text
# Launch all independent validation checks together (after T023 completes):
Task: T024 — Document Phase 5.2 (Terminology audit) in specs/003-librarian/quickstart.md
Task: T025 — Document Phase 5.3 (Diagram freshness) in specs/003-librarian/quickstart.md
Task: T026 — Document Phase 5.4 (Code sample validation) in specs/003-librarian/quickstart.md
```

## Parallel Example: Setup Phase

```text
# Launch independent setup tasks together:
Task: T002 — Update solune/docs/.change-manifest.md to structured 6-category template
Task: T003 — Verify .github/ISSUE_TEMPLATE/chore-librarian.md includes all 7 phases
```

---

## Implementation Strategy

### MVP First (User Stories 1 + 2 Only)

1. Complete Phase 1: Setup (T001–T003) — templates and structure
2. Complete Phase 2: Foundational (T004–T005) — doc-to-source mapping and baseline conventions
3. Complete Phase 3: User Story 1 (T006–T010) — change manifest process
4. Complete Phase 4: User Story 2 (T011–T014) — focus-shift analysis
5. **STOP and VALIDATE**: Build a change manifest and run focus-shift analysis against Solune
6. The team now has a structured process for understanding what changed and what to prioritize

### Incremental Delivery

1. Setup + Foundational → Infrastructure ready
2. Add US1 → Test: build a manifest → Deliverable: structured change catalog (MVP!)
3. Add US2 → Test: run focus analysis → Deliverable: prioritized update plan
4. Add US3 + US4 (parallel) → Test: update README + docs → Deliverable: refreshed documentation
5. Add US5 → Test: run consistency checks → Deliverable: validated documentation
6. Add US6 → Test: stamp baseline → Deliverable: complete auditable refresh cycle
7. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple contributors:

1. Team completes Setup + Foundational together
2. Contributor A: User Story 1 (manifest)
3. Once US1 done → Contributor A: User Story 2 (focus shifts)
4. Once US2 done:
   - Contributor A: User Story 3 (README)
   - Contributor B: User Story 4 (doc files)
5. Once US3 + US4 done → Contributor A: User Story 5 (validation)
6. Once US5 done → Contributor B: User Story 6 (stamp)

---

## Summary

- **Total tasks**: 35
- **Tasks per user story**: US1: 5, US2: 4, US3: 4, US4: 4, US5: 4, US6: 5, Setup: 3, Foundational: 2, Polish: 4
- **Parallel opportunities**: 7 (T002‖T003, T004‖T005, US3‖US4, T024‖T025‖T026, T032‖T033)
- **Independent test criteria**: Each user story has a defined independent test in its phase header
- **Suggested MVP scope**: User Stories 1 + 2 (Phases 1–4, T001–T014) — delivers the analytical foundation for documentation refresh
- **Format validation**: ✅ All 35 tasks follow checklist format (checkbox, ID, labels, file paths)
