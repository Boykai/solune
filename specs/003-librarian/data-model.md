# Data Model: Librarian — Automated Documentation Refresh Process

**Feature**: 003-librarian
**Date**: 2026-04-01
**Prerequisites**: [research.md](./research.md)

## Entities

### Refresh Baseline (Existing — Extended)

The baseline marker defines the starting point for each documentation refresh cycle. Stored as a JSON file at `docs/.last-refresh`. Each refresh cycle reads the previous baseline and writes a new one upon completion (FR-001, FR-012).

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `date` | `string` (ISO 8601) | Yes | Timestamp of the refresh completion |
| `sha` | `string` | Yes | Git commit SHA at which the refresh was performed |
| `documents_updated` | `string[]` | Yes | List of doc file paths that were updated during the refresh |
| `documents_skipped` | `string[]` | Yes | List of doc file paths reviewed but not requiring updates |
| `broken_links_found` | `integer` | Yes | Count of broken links detected during validation |
| `manual_followups` | `string[]` | Yes | List of items flagged for manual follow-up |

**Existing Format** (already in use in `solune/docs/.last-refresh`):

```json
{
  "date": "2026-03-14T18:41:00Z",
  "sha": "518be4cbd6ae2b9030abe4b13847e2c77f83b2b4",
  "documents_updated": [
    "docs/agent-pipeline.md",
    "docs/architecture.md"
  ],
  "documents_skipped": [
    "docs/api-reference.md",
    "docs/custom-agents-best-practices.md"
  ],
  "broken_links_found": 0,
  "manual_followups": []
}
```

**Fallback Precedence** (when `.last-refresh` is absent or invalid):

| Priority | Source | Method |
|----------|--------|--------|
| 1 | `.last-refresh` JSON | Read `sha` field directly |
| 2 | Git tag `docs-refresh-*` | `git tag -l 'docs-refresh-*' --sort=-creatordate` → take first |
| 3 | Release tag `v*` | `git tag -l 'v*' --sort=-creatordate` → take first |
| 4 | Time window (14 days) | `git log --after="14 days ago" --format="%H" \| tail -1` |

---

### Change Manifest

The categorized inventory of all project changes since the last baseline. Produced during Phase 1 and stored as `docs/.change-manifest.md` (FR-002, FR-003, FR-004).

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `refresh_window` | `string` | Yes | Date range of the refresh (e.g., "2026-03-14 → 2026-04-01") |
| `sha_range` | `string` | Yes | Git SHA range (e.g., "`518be4c..HEAD`") |
| `sources_analyzed` | `string[]` | Yes | List of sources parsed (e.g., "CHANGELOG.md, specs/ directories, git diff") |
| `categories` | `ManifestCategory[]` | Yes | Six category sections containing change items |

**Manifest Categories** (FR-004):

| Category | What to Look For | Spec Reference |
|----------|-----------------|----------------|
| **New capabilities** | New user-facing features, pages, commands, integrations | FR-002, FR-003 |
| **Changed behavior** | Altered workflows, renamed concepts, changed defaults | FR-002, FR-003 |
| **Removed functionality** | Deleted features, deprecated APIs, removed UI | FR-002, FR-003 |
| **Architectural changes** | New services, refactored module boundaries, changed infra | FR-003 |
| **UX changes** | Navigation changes, renamed screens, altered user flows | FR-003 |
| **Config / ops changes** | New env vars, changed deployment steps, new dependencies | FR-003 |

---

### Change Item

A single identified change within the manifest. Each item belongs to exactly one category (FR-004).

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `description` | `string` | Yes | Human-readable description of the change |
| `category` | `enum` | Yes | One of the six manifest categories |
| `source` | `enum` | Yes | Where the change was detected: `changelog`, `spec`, `adr`, `git-diff` |
| `source_detail` | `string` | No | Specific location within the source (e.g., "## [Unreleased] > ### Added") |
| `domain` | `string` | Yes | Functional area (e.g., "pipeline", "agents", "auth", "infra") |
| `affected_docs` | `string[]` | Yes | List of documentation files potentially affected by this change |

**Example** (from existing `.change-manifest.md`):

```markdown
1. **Pipeline Analytics dashboard** — Replaces Recent Activity section on Agents Pipelines page
   - Source: CHANGELOG
   - Source Detail: ## [Unreleased] > ### Added
   - Domain: pipeline
   - Affected Docs: docs/agent-pipeline.md, README.md
```

---

### Focus Shift Analysis

The result of analyzing the change manifest for development focus and narrative-level shifts. Produced during Phase 2 (FR-005, FR-006, FR-007).

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `change_density` | `map[string, integer]` | Yes | Count of manifest items per functional area |
| `top_focus_areas` | `string[]` | Yes | Functional areas with the highest change density (top 3) |
| `narrative_shifts` | `NarrativeShift[]` | No | List of detected narrative-level shifts |
| `priority_assignments` | `PriorityAssignment[]` | Yes | Prioritized list of documentation updates (P0–P4) |

**Narrative Shift Detection Questions** (FR-006):

| Question | If Yes → Impact |
|----------|----------------|
| New top-level capability added? | P0: Update README pitch, docs landing page |
| Prominent feature reduced/removed/folded? | P1: Remove or consolidate affected docs |
| Primary value proposition shifted? | P0: Rewrite README description |
| Primary user workflow changed? | P0: Update getting-started, main flow docs |
| New user personas introduced? | P1: Add persona-specific docs/sections |

**Priority Assignment Table** (FR-007):

| Priority | Trigger | Docs to Update |
|----------|---------|----------------|
| P0 | Product pitch or primary workflow changed | Top-level README, docs landing page |
| P1 | Feature added/changed/removed | Feature-specific docs, API reference, guides |
| P2 | Architecture or structure changed | Architecture docs, directory/module maps |
| P3 | Config, setup, or ops changed | Setup guides, config reference, deployment docs |
| P4 | Bugs fixed or edge cases resolved | Troubleshooting, FAQ, known issues |

---

### Doc-to-Source Mapping

A relationship linking a documentation file to its source of truth in the codebase. Used in Phase 4 to detect drift (FR-009).

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `doc_path` | `string` | Yes | Path to the documentation file (relative to repo root) |
| `source_type` | `enum` | Yes | Type of source: `routes`, `config_schema`, `module_structure`, `dependency_manifest`, `feature_code`, `cli_definition`, `schema_definition`, `bug_fixes` |
| `source_paths` | `string[]` | Yes | Paths to source-of-truth files/directories |
| `diff_method` | `string` | Yes | How to compare doc against source (e.g., "List all @router decorators → compare to documented endpoints") |

**Solune Project Mappings**:

| Doc File | Source Type | Source Paths | Diff Method |
|----------|-------------|-------------|-------------|
| `docs/api-reference.md` | `routes` | `backend/src/api/*.py` | List `@router.*` decorators → compare to doc |
| `docs/configuration.md` | `config_schema` | `backend/src/config.py`, `.env.example` | Extract config keys → compare to doc |
| `docs/architecture.md` | `module_structure` | `backend/src/`, `docker-compose.yml` | List modules + services → compare to doc |
| `docs/setup.md` | `dependency_manifest` | `pyproject.toml`, `package.json`, `Dockerfile` | Run setup → note failures |
| `docs/pages/*.md` | `feature_code` | `frontend/src/pages/*.tsx` | Walk page in app → compare to doc |
| `docs/agent-pipeline.md` | `feature_code` | `services/workflow_orchestrator/` | Trace execution flow → compare to doc |
| `docs/signal-integration.md` | `feature_code` | `services/signal_bridge.py` | Review implementation → compare to doc |
| `docs/testing.md` | `module_structure` | `tests/`, `.github/workflows/ci.yml` | List test commands → compare to doc |
| `docs/troubleshooting.md` | `bug_fixes` | Recent closed issues, git log | Review fixes → update entries |
| `docs/project-structure.md` | `module_structure` | Repository filesystem | `tree` output → compare to doc |
| `README.md` | All types | All sources | Holistic review |

---

### Verification Checklist

A checklist produced at the end of each refresh cycle confirming documentation accuracy. Appended to `.change-manifest.md` as the final section (FR-014).

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `date` | `string` (ISO 8601) | Yes | Date the verification was completed |
| `items` | `VerificationItem[]` | Yes | List of 9 verification items with pass/fail status |
| `overall_status` | `enum` | Yes | `pass` (all items pass), `partial` (some items pass), `fail` (critical items fail) |

**Verification Items** (from spec):

| # | Item | Automated? | How to Verify |
|---|------|-----------|---------------|
| 1 | Change manifest covers all commits since baseline | Manual | Compare manifest SHA range to `git log` count |
| 2 | All internal doc links resolve | Automated (`lychee`) | Run `lychee docs/ README.md` |
| 3 | All documented features exist in running app | Manual | Smoke-test key features |
| 4 | All config keys in docs exist in config schema | Semi-auto | Grep config keys from docs → check `config.py` |
| 5 | Getting-started guide runs clean | Manual | Follow `docs/setup.md` from scratch |
| 6 | No references to removed features in docs | Semi-auto | Grep for removed feature names |
| 7 | README feature list matches current capabilities | Manual | Compare README to running app |
| 8 | New baseline (tag/metadata) is set | Automated | Check `.last-refresh` + git tag |
| 9 | Changelog updated with documentation changes | Manual | Check `CHANGELOG.md` for docs section |

---

## Relationships

```text
Refresh Baseline (.last-refresh)
    │
    ├── Read by: Phase 1.1 (Establish baseline)
    │   └── Provides: sha, date → used as diff starting point
    │
    ├── Written by: Phase 7.3 (Set new baseline)
    │   └── Updates: date, sha, documents_updated/skipped, broken_links, followups
    │
    └── Complemented by: Git tag (docs-refresh-YYYY-MM-DD)
        └── Created in: Phase 7.3

Change Manifest (.change-manifest.md)
    │
    ├── Built by: Phase 1 (Build the Change Manifest)
    │   ├── Phase 1.2: Harvest from changelog + specs/ADRs → Change Items
    │   ├── Phase 1.3: Harvest from code diffs → Change Items
    │   └── Phase 1.4: Categorize into 6 categories
    │
    ├── Analyzed by: Phase 2 (Infer Focus Shifts)
    │   ├── Phase 2.1: Group by domain → change_density
    │   ├── Phase 2.2: Detect narrative shifts → narrative_shifts
    │   └── Phase 2.3: Assign priorities → priority_assignments
    │
    ├── Consumed by: Phase 3 (Update README)
    │   └── Uses: priority_assignments to determine what to update
    │
    ├── Consumed by: Phase 4 (Update Documentation Files)
    │   └── Uses: priority_assignments + doc-to-source mappings
    │
    └── Appended to by: Phase 5/7 (Verification Checklist)

Doc-to-Source Mapping (OWNERS.md or inline)
    │
    ├── Used by: Phase 4.1 (Map each doc to source of truth)
    │   └── Provides: source paths + diff methods for each doc
    │
    └── Updated by: Phase 4.3 (Structural docs)
        └── When new docs or sources are added

Verification Checklist (appended to .change-manifest.md)
    │
    ├── Populated by: Phase 5 (Validate Consistency)
    │   ├── Item 2: Link validation (lychee)
    │   ├── Item 4: Config key check
    │   └── Item 6: Removed feature check
    │
    ├── Populated by: Phase 6 (Verify Against Running App)
    │   ├── Item 3: Feature existence
    │   └── Item 5: Getting-started guide
    │
    └── Finalized by: Phase 7 (Stamp & Reset)
        ├── Item 1: Manifest completeness
        ├── Item 7: README accuracy
        ├── Item 8: Baseline set
        └── Item 9: Changelog updated
```

## State Transitions

The Librarian process is a linear, phase-based workflow. Each phase produces output that feeds into subsequent phases. The overall state machine:

```text
[No Baseline / First Run]
    │
    └── Phase 1: Build Change Manifest
        │ Input:  .last-refresh (or fallback)
        │ Output: .change-manifest.md (6 categories)
        │
        ├── Zero changes detected? → Report "no changes", STOP (FR-017)
        │
        └── Phase 2: Infer Focus Shifts
            │ Input:  .change-manifest.md
            │ Output: Focus analysis (density, shifts, priorities P0–P4)
            │
            └── Phase 3: Update README
                │ Input:  Priority assignments (P0 items)
                │ Output: Updated README.md
                │
                └── Phase 4: Update Documentation Files
                    │ Input:  Priority assignments + doc-to-source mappings
                    │ Output: Updated docs/*.md files
                    │
                    └── Phase 5: Validate Consistency
                        │ Input:  All updated docs
                        │ Output: Link check results, terminology audit, diagram status
                        │
                        └── Phase 6: Verify Against Running App
                            │ Input:  Updated docs
                            │ Output: Smoke test results, config verification
                            │
                            └── Phase 7: Stamp & Reset Baseline
                                │ Input:  All phase outputs
                                │ Output: Git commit, changelog entry, new .last-refresh, git tag
                                │
                                └── [Cycle Complete → New Baseline Set]
```

**Edge Case Transitions**:

| Condition | Behavior | Spec Reference |
|-----------|----------|----------------|
| No baseline exists | Use fallback precedence (tag → release → 2 weeks) | FR-001 |
| Changelog missing or non-standard | Skip changelog parsing; proceed with code diffs only | Edge Case 2 |
| Doc has no source of truth | Flag for manual review; include in link/term validation only | Edge Case 3 |
| Zero changes since baseline | Report "no changes"; skip Phases 2–7; preserve existing baseline | FR-017 |
| Renamed concept found in non-flagged doc | Terminology audit catches it in Phase 5 regardless of priority list | Edge Case 5 |
| Getting-started instructions fail | Log failure; flag section for manual intervention | Edge Case 6 |
| External URL returns transient error | Retry up to 3 times with backoff; flag only persistent failures | FR-016 |
