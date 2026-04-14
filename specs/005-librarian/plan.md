# Implementation Plan: Librarian Documentation Refresh

**Branch**: `copilot/add-implementation-plan` | **Date**: 2026-04-13 | **Spec**: [GitHub Issue #1728](https://github.com/Boykai/solune/issues/1728)
**Input**: Parent issue Boykai/solune#1728 — Librarian

## Summary

Execute a full Librarian documentation refresh cycle: build a change manifest from the last baseline (`b183ba31`, 2026-04-11) through the current `main` HEAD, infer focus shifts from recent development activity, update the README and all documentation files to match the current codebase reality, validate consistency (links, terminology, diagrams), and stamp a new baseline for the next cycle. This is a process-execution feature — no new application code is written; only documentation and metadata files are created or updated.

## Technical Context

**Language/Version**: Markdown (documentation); Bash (existing scripts); Python 3.12+ / TypeScript (codebase under documentation)
**Primary Dependencies**: `markdownlint` (markdown style), `markdown-link-check` (link validation), `generate-diagrams.sh` (Mermaid diagram generation), `documentationLinks.test.ts` (internal link verification)
**Storage**: N/A — file-based documentation; `.last-refresh` JSON metadata file
**Testing**: `cd solune/frontend && npm test -- --run src/docs/documentationLinks.test.ts` (link validation); `markdownlint` (style); `generate-diagrams.sh --check` (diagram freshness)
**Target Platform**: GitHub-rendered Markdown; developer workstations
**Project Type**: Documentation refresh (no application code changes)
**Performance Goals**: N/A — documentation-only
**Constraints**: Zero broken links post-refresh; all documented features must match the running application; all config keys in docs must exist in code; no references to removed features
**Scale/Scope**: ~43 markdown files in `solune/docs/`, 5 Mermaid diagrams, 1 root README, 1 frontend README, 1 CHANGELOG, 7 ADRs, 15 page guides, 4 verification checklists

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Specification-First Development**: PASS — The parent issue (#1728) provides a structured specification with 7 phased requirements, explicit principles, verification checklist, and cadence guidelines. This plan follows the issue as the authoritative spec.
- **II. Template-Driven Workflow**: PASS — This plan and all Phase 0/1 artifacts reside in `specs/005-librarian/` using the canonical Speckit artifact set. The documentation refresh itself uses existing templates (`.change-manifest.md`, `doc-refresh-verification.md`, `OWNERS.md` doc-to-source mapping).
- **III. Agent-Orchestrated Execution**: PASS — The plan decomposes into 7 sequential phases suitable for single-responsibility agent execution. The `archivist` agent handles Phases 1–7 content work; the `linter` agent handles Phase 5 validation. Each phase has clear inputs, outputs, and handoff criteria.
- **IV. Test Optionality with Clarity**: PASS — No new tests are mandated. Existing validation tools (`documentationLinks.test.ts`, `markdownlint`, `markdown-link-check`, `generate-diagrams.sh --check`) serve as quality gates. The verification checklist in Phase 7 provides the manual validation layer.
- **V. Simplicity and DRY**: PASS — The plan reuses 100% of existing tooling and file formats. No new scripts, frameworks, or abstractions are introduced. The refresh follows the exact process described in the issue and already demonstrated in the previous cycle (2026-04-11).

**Post-Phase-1 Re-check**: PASS — No constitution violations introduced by the design. All phases operate on existing documentation infrastructure. No complexity justifications required.

## Project Structure

### Documentation (this feature)

```text
specs/005-librarian/
├── plan.md              # This file
├── research.md          # Phase 0 output — tooling and strategy research
├── data-model.md        # Phase 1 output — change manifest and document model
├── quickstart.md        # Phase 1 output — execution guide for each phase
├── contracts/           # Phase 1 output — refresh-cycle-contract.yaml
└── tasks.md             # Phase 2 output (NOT created by /speckit.plan)
```

### Source Files (documentation under refresh)

```text
solune/
├── README.md                               # Phase 3: revalidate project description + features
├── CHANGELOG.md                            # Phase 1: parse for change harvest; Phase 7: update
├── docs/
│   ├── .last-refresh                       # Phase 1: read baseline; Phase 7: stamp new baseline
│   ├── .change-manifest.md                 # Phase 1: compile new manifest
│   ├── OWNERS.md                           # Phase 4: doc-to-source mapping reference
│   ├── api-reference.md                    # Phase 4: diff against backend/src/api/
│   ├── architecture.md                     # Phase 4: diff against module structure
│   ├── configuration.md                    # Phase 4: diff against backend/src/config.py
│   ├── project-structure.md                # Phase 4: diff against filesystem
│   ├── setup.md                            # Phase 4: verify setup steps
│   ├── testing.md                          # Phase 4: diff against test structure
│   ├── agent-pipeline.md                   # Phase 4: diff against orchestrator
│   ├── signal-integration.md               # Phase 4: diff against signal bridge
│   ├── custom-agents-best-practices.md     # Phase 4: review for accuracy
│   ├── roadmap.md                          # Phase 4: shipped vs. aspirational
│   ├── architectures/                      # Phase 5: regenerate diagrams
│   │   ├── backend-components.mmd
│   │   ├── data-flow.mmd
│   │   ├── deployment.mmd
│   │   ├── frontend-components.mmd
│   │   └── high-level.mmd
│   ├── checklists/
│   │   ├── doc-refresh-verification.md     # Phase 7: reset and re-verify
│   │   ├── weekly-sweep.md
│   │   ├── monthly-review.md
│   │   └── quarterly-audit.md
│   ├── decisions/                          # Phase 4: check for new ADRs
│   │   ├── 001-githubkit-sdk.md
│   │   ├── 002-sqlite-wal-auto-migrations.md
│   │   ├── 003-copilot-default-ai-provider.md
│   │   ├── 004-pluggable-completion-provider.md
│   │   ├── 005-sub-issue-per-agent-pipeline.md
│   │   └── 006-signal-sidecar.md
│   └── pages/                              # Phase 4: diff against frontend pages
│       ├── README.md
│       ├── activity.md, agents.md, apps.md, chat.md, chores.md
│       ├── dashboard.md, help.md, layout.md, login.md
│       ├── not-found.md, pipeline.md, projects.md
│       ├── settings.md, tools.md
├── frontend/
│   ├── README.md                           # Phase 4: diff against frontend structure
│   └── docs/findings-log.md               # Phase 4: review for staleness
├── scripts/
│   └── generate-diagrams.sh               # Phase 5: diagram regeneration tool
└── .pre-commit-config.yaml                 # Phase 5: existing validation hooks
```

**Structure Decision**: No new directories or files are introduced to the source tree. The refresh operates entirely on the existing documentation structure under `solune/docs/`, `solune/README.md`, and `solune/frontend/README.md`. The only new files are in `specs/005-librarian/` (plan artifacts) and updates to existing documentation/metadata files.

## Phase Execution Plan

### Phase 1 — Build the Change Manifest

**Goal**: Catalog everything that changed since the last refresh (2026-04-11, baseline `b183ba31`).

| Step | Action | Details |
|------|--------|---------|
| 1.1 | Read baseline from `.last-refresh` | Parse JSON: `date`, `sha`, `documents_updated`, `documents_skipped` |
| 1.2 | Harvest from CHANGELOG | Parse `[Unreleased]` section of `solune/CHANGELOG.md` for Added/Changed/Fixed entries since 2026-04-11 |
| 1.3 | Harvest from code diffs | `git diff --stat b183ba31..HEAD` and `git log --oneline --since=2026-04-11` on `main` |
| 1.4 | Scan for new specs/ADRs | Check `specs/` for new feature directories; check `docs/decisions/` for new ADR files |
| 1.5 | Flag high-signal changes | New/deleted entry points, public modules, config schema changes, dependency bumps, data model changes, build/deploy script changes |
| 1.6 | Compile manifest | Categorize findings into 6 categories: New capabilities, Changed behavior, Removed functionality, Architectural changes, UX changes, Config/ops changes |
| 1.7 | Write `.change-manifest.md` | Update `solune/docs/.change-manifest.md` with new refresh window, baseline SHAs, categorized findings, and source analysis paths |

**Output**: Updated `solune/docs/.change-manifest.md`

### Phase 2 — Infer Focus Shifts

**Goal**: Understand how the product has evolved since last refresh.

| Step | Action | Details |
|------|--------|---------|
| 2.1 | Measure change density | Group manifest items by functional area (chat, agents, pipeline, tools, chores, admin, infra) |
| 2.2 | Detect narrative shifts | Answer: new top-level capability? Feature reduced/removed? Value proposition shifted? Primary workflow changed? New user personas? |
| 2.3 | Prioritize updates | Assign P0–P4 to each doc based on triggers: P0 (pitch/workflow changed), P1 (feature add/change/remove), P2 (architecture/structure), P3 (config/setup/ops), P4 (bug fixes/edge cases) |

**Output**: Priority-annotated manifest entries guiding Phase 3–4 work order

### Phase 3 — Update the README

**Goal**: Ensure `solune/README.md` reflects the current product accurately.

| Step | Action | Details |
|------|--------|---------|
| 3.1 | Revalidate project description | Does the elevator pitch still describe what Solune does today? |
| 3.2 | Audit feature list | Add newly shipped capabilities; remove/mark deprecated features; reorder by importance |
| 3.3 | Verify getting-started instructions | Cross-check prerequisites against `pyproject.toml`, `package.json`, and Dockerfiles |
| 3.4 | Update visual/structural references | Verify badge URLs, status links, and architecture-at-a-glance references |

**Verification**: README accurately describes current capabilities. All links resolve.

### Phase 4 — Update Documentation Files

**Goal**: Each doc page is accurate to the current codebase.

| Step | Action | Files | Source of Truth |
|------|--------|-------|----------------|
| 4.1 | Diff API reference | `docs/api-reference.md` | `backend/src/api/*.py` — list all `@router.*` decorators |
| 4.2 | Diff configuration reference | `docs/configuration.md` | `backend/src/config.py` — extract all config keys |
| 4.3 | Diff architecture overview | `docs/architecture.md` | `backend/src/`, `docker-compose.yml` — list modules + topology |
| 4.4 | Verify setup guide | `docs/setup.md` | `pyproject.toml`, `package.json`, Dockerfiles |
| 4.5 | Diff project structure | `docs/project-structure.md` | Repository filesystem — `find`/`tree` output |
| 4.6 | Diff testing reference | `docs/testing.md` | `tests/`, `.github/workflows/ci.yml` |
| 4.7 | Diff page guides | `docs/pages/*.md` | `frontend/src/pages/*.tsx` |
| 4.8 | Diff agent pipeline docs | `docs/agent-pipeline.md` | `backend/src/services/workflow_orchestrator/` |
| 4.9 | Diff signal integration | `docs/signal-integration.md` | `backend/src/services/signal_bridge.py` |
| 4.10 | Review custom agents guide | `docs/custom-agents-best-practices.md` | Agent authoring patterns in code |
| 4.11 | Update roadmap | `docs/roadmap.md` | CHANGELOG shipped items vs. aspirational items |
| 4.12 | Check for new ADRs | `docs/decisions/` | Any new architectural decisions since last refresh |
| 4.13 | Update frontend README | `frontend/README.md` | Frontend source structure |
| 4.14 | Review findings log | `frontend/docs/findings-log.md` | Staleness check |

**Rewrite rule**: For each affected doc — identify gaps (missing, stale, dead), rewrite sections naturally (don't patch with "UPDATE:" notes).

**Verification**: All docs match their source of truth per OWNERS.md mapping.

### Phase 5 — Validate Consistency

**Goal**: Docs are internally consistent and all references resolve.

| Step | Action | Tool/Command |
|------|--------|-------------|
| 5.1 | Validate internal links | `cd solune/frontend && npm test -- --run src/docs/documentationLinks.test.ts` |
| 5.2 | Validate external URLs | `markdown-link-check` via pre-commit or manual run |
| 5.3 | Terminology audit | Grep docs for deprecated terms from change manifest (see research.md R5) |
| 5.4 | Regenerate diagrams | `cd solune && ./scripts/generate-diagrams.sh` |
| 5.5 | Verify diagram freshness | `cd solune && ./scripts/generate-diagrams.sh --check` |
| 5.6 | Markdown style validation | `markdownlint` via pre-commit or manual run |

**Verification**: 0 broken links; 0 stale terms; diagrams up-to-date; markdown lint clean.

### Phase 6 — Verify Against Running Application

**Goal**: Docs match the actual user experience.

| Step | Action | Details |
|------|--------|---------|
| 6.1 | Smoke-test documented workflows | Pick 3–5 key user flows from docs and verify against running app or code wiring |
| 6.2 | Verify config/setup docs | Confirm documented env vars exist in `backend/src/config.py`; confirm defaults match |
| 6.3 | Verify API docs | Compare 3–5 documented endpoints against actual FastAPI router definitions |

**Note**: Full running-application verification depends on environment access. Code-level verification (routing wiring, config schema comparison) is always possible and is the minimum bar.

### Phase 7 — Stamp & Reset Baseline

**Goal**: Record the refresh so the next cycle starts clean.

| Step | Action | Details |
|------|--------|---------|
| 7.1 | Update `.last-refresh` | New JSON: `date` (current), `sha` (main HEAD), `documents_updated`, `documents_skipped`, `broken_links_found`, `manual_followups` |
| 7.2 | Reset verification checklist | Update `docs/checklists/doc-refresh-verification.md`: new dates, new SHA range, re-verify all 8 items |
| 7.3 | Update CHANGELOG | Add Documentation section to `[Unreleased]` noting which docs were updated |
| 7.4 | Commit all changes | Single commit: `docs: librarian refresh for YYYY-MM-DD` |

**Verification**: `.last-refresh` updated; verification checklist all-PASS; CHANGELOG updated.

## Verification Matrix

| Check | Command | After Phase |
|-------|---------|-------------|
| Internal links | `cd solune/frontend && npm test -- --run src/docs/documentationLinks.test.ts` | 4, 5 |
| Markdown lint | `markdownlint solune/docs/**/*.md solune/README.md` | 3, 4, 5 |
| External links | `markdown-link-check` on changed files | 5 |
| Diagram freshness | `cd solune && ./scripts/generate-diagrams.sh --check` | 5 |
| Config key completeness | Grep `backend/src/config.py` for all env vars → diff against `docs/configuration.md` | 4 |
| API endpoint completeness | Grep `backend/src/api/*.py` for `@router.*` → diff against `docs/api-reference.md` | 4 |
| Stale terminology | Grep docs for deprecated terms from manifest | 5 |

## Decisions

| Decision | Rationale |
|----------|-----------|
| **Reuse existing tooling** | All link validation, diagram generation, and markdown linting tools are already in the repository and CI. No new tools needed. |
| **Reuse OWNERS.md doc-to-source mapping** | The mapping is comprehensive, manually curated, and specifically designed for the Librarian refresh process. |
| **Reuse `.change-manifest.md` format** | Previous cycle established the format; consistency between cycles aids comparison. |
| **Code-level verification over running-app** | Phase 6 can be satisfied by comparing code wiring (routes, config schema, component structure) when a running instance is unavailable. |
| **No new ADRs** | This feature introduces no architectural decisions; it executes an existing process. |

## Complexity Tracking

> No constitution violations found. No complexity justifications required.
