# Implementation Plan: Librarian — Automated Documentation Refresh Process

**Branch**: `003-librarian` | **Date**: 2026-04-01 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/003-librarian/spec.md`

## Summary

The Librarian is a repeatable, language-agnostic process for keeping project documentation accurate as software evolves. It operates in 7 phases: (1) build a categorized change manifest from git diffs, changelogs, and spec directories since the last baseline; (2) infer focus shifts and assign update priorities (P0–P4); (3) update the README; (4) update documentation files against their source of truth; (5) validate consistency (links, terminology, diagrams, code samples); (6) verify against the running application; (7) stamp the refresh and reset the baseline. The implementation extends the existing `solune/docs/` infrastructure — specifically the `.last-refresh` baseline marker and `.change-manifest.md` — into a structured, automatable workflow executed by AI agents (primarily the `archivist` agent) and orchestrated through a GitHub Issue template (`chore-librarian.md`).

## Technical Context

**Language/Version**: Python 3.12+ (backend scripting, git operations), Bash (shell scripts), Markdown (documentation output)
**Primary Dependencies**: Git CLI (diff, log, tag), existing `solune/docs/` structure, GitHub Issue templates, `lychee` or `markdown-link-check` (link validation)
**Storage**: JSON metadata files (`.last-refresh`), Markdown files (`.change-manifest.md`, all docs), Git tags (`docs-refresh-YYYY-MM-DD`)
**Testing**: Manual validation via verification checklist (FR-014); automated link checking via CI; shell script tests where applicable
**Target Platform**: Any Git-based repository (language-agnostic, structure-agnostic)
**Project Type**: Process/workflow — primarily documentation and scripting; no new backend API or frontend UI
**Performance Goals**: Full refresh cycle completes in under 2 hours for a medium-sized project (SC-001)
**Constraints**: Must work with any codebase regardless of language or structure (FR-013); must not break existing documentation or CI; must produce auditable verification checklist
**Scale/Scope**: ~30 documentation files in `solune/docs/`, 1 README, 6 ADRs, 11 page docs, 3 checklists; the process targets any repository with Git history

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Specification-First | ✅ PASS | `spec.md` exists with 6 prioritized user stories (P1–P3), Given-When-Then acceptance scenarios for each, 7 edge cases, and clear scope boundaries. 17 functional requirements and 10 measurable success criteria are defined. |
| II. Template-Driven | ✅ PASS | All artifacts follow canonical templates from `.specify/templates/`. This plan follows `plan-template.md`. |
| III. Agent-Orchestrated | ✅ PASS | Single-responsibility: this plan phase produces design artifacts only. Implementation deferred to `/speckit.tasks` + `/speckit.implement`. The `archivist` agent is the primary executor for the Librarian process itself. |
| IV. Test Optionality | ✅ PASS | Spec does not mandate unit tests for the process itself. Validation is via the verification checklist (FR-014) and automated link checking (FR-011, FR-016). Tests are not required per this principle since the feature is a documentation workflow, not code logic. |
| V. Simplicity and DRY | ✅ PASS | Extends existing infrastructure (`.last-refresh`, `.change-manifest.md`, `chore-librarian.md` issue template) rather than creating new systems. Each phase is a clear, sequential step. No premature automation — spec mandates manual-first with incremental automation after 2–3 cycles (Assumptions section). |

**Gate Result**: ALL PASS — proceeding to Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/003-librarian/
├── plan.md              # This file
├── research.md          # Phase 0: Research findings
├── data-model.md        # Phase 1: Entity and data model
├── quickstart.md        # Phase 1: Developer quickstart guide
├── contracts/           # Phase 1: Process contracts (workflow definitions)
│   └── refresh-workflow.yaml  # Librarian refresh workflow contract
└── tasks.md             # Phase 2 output (/speckit.tasks — NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
solune/docs/
├── .last-refresh                  # MODIFY: Structured baseline marker (JSON: date, sha, docs updated/skipped)
├── .change-manifest.md            # MODIFY: Templated change manifest output (6 categories)
├── OWNERS.md                      # EXISTING: Documentation ownership reference
├── architecture.md                # EXISTING: Target for Phase 4 structural doc updates
├── configuration.md               # EXISTING: Target for Phase 4 config reference updates
├── setup.md                       # EXISTING: Target for Phase 3 getting-started verification
├── api-reference.md               # EXISTING: Target for Phase 4 API doc updates
├── troubleshooting.md             # EXISTING: Target for Phase 4 troubleshooting updates
├── decisions/                     # EXISTING: ADR directory scanned in Phase 1.2
├── pages/                         # EXISTING: Page docs targeted in Phase 4
├── checklists/
│   ├── weekly-sweep.md            # EXISTING: References Librarian process
│   ├── monthly-review.md          # EXISTING: References Librarian process
│   ├── quarterly-audit.md         # EXISTING: References Librarian process
│   └── doc-refresh-verification.md  # NEW: Verification checklist template (FR-014)
└── architectures/                 # EXISTING: Mermaid diagrams verified in Phase 5.3

.github/ISSUE_TEMPLATE/               # Repository root (not under solune/)
└── chore-librarian.md             # EXISTING: Issue template for triggering Librarian refresh cycles

solune/README.md                   # EXISTING: Target for Phase 3 README updates
solune/CHANGELOG.md                # EXISTING: Parsed in Phase 1.2; updated in Phase 7.2
```

**Structure Decision**: Process/workflow structure. This feature is primarily a documentation process, not a code application. All changes extend existing files within `solune/docs/` and the repository root. The only new file is a verification checklist template (`doc-refresh-verification.md`). The existing `.last-refresh` JSON file and `.change-manifest.md` are the primary data artifacts. No new backend or frontend code is required — the Librarian process is executed by AI agents (archivist) guided by the issue template and this plan.

## Constitution Re-Check (Post-Design)

*Re-evaluation after Phase 1 design artifacts are complete.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Specification-First | ✅ PASS | Design artifacts (data-model, contracts, quickstart) all trace back to spec.md requirements FR-001 through FR-017. Each entity maps to at least one FR. |
| II. Template-Driven | ✅ PASS | All generated artifacts follow canonical templates. The refresh workflow contract uses a structured YAML format consistent with the spec 002 contract pattern. |
| III. Agent-Orchestrated | ✅ PASS | Plan phase complete; handoff to `/speckit.tasks` for task decomposition. The archivist agent is the designated executor for the Librarian process. |
| IV. Test Optionality | ✅ PASS | No unit tests required — this is a documentation workflow. Validation is through the verification checklist (FR-014) and CI link checks. |
| V. Simplicity and DRY | ✅ PASS | Reuses existing `.last-refresh` and `.change-manifest.md` infrastructure. Each phase is a simple sequential step. No new abstractions, services, or libraries. The verification checklist is a single Markdown template. |

**Gate Result**: ALL PASS — ready for Phase 2 (`/speckit.tasks`).

## Complexity Tracking

> No constitution violations — this section is intentionally empty.
