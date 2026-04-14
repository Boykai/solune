# Data Model: Librarian Documentation Refresh

**Feature**: Librarian | **Date**: 2026-04-13 | **Status**: Complete

## Entity: RefreshBaseline

The `.last-refresh` metadata file tracks the starting point for each documentation refresh cycle.

### Fields

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `date` | `string` (ISO 8601) | Required | Timestamp of the last completed refresh |
| `sha` | `string` (40-char hex) | Required | Git commit SHA of the baseline |
| `documents_updated` | `string[]` | Required | List of doc paths updated in the last refresh |
| `documents_skipped` | `string[]` | Required | List of doc paths verified but not changed |
| `broken_links_found` | `number` | Required, ≥ 0 | Count of broken links found during validation |
| `manual_followups` | `string[]` | Required | List of items requiring manual follow-up |

### Location

`solune/docs/.last-refresh` (JSON format)

### Current State

```json
{
  "date": "2026-04-11T22:00:00Z",
  "sha": "b183ba318e47ae2958f58aafabc299bc6b580bcc",
  "documents_updated": [
    "docs/api-reference.md",
    "docs/architecture.md",
    "docs/configuration.md",
    "docs/pages/README.md",
    "docs/pages/chat.md",
    "docs/pages/dashboard.md",
    "docs/pages/layout.md",
    "docs/project-structure.md",
    "docs/roadmap.md",
    "docs/testing.md",
    "frontend/README.md"
  ],
  "documents_skipped": [
    "docs/agent-pipeline.md",
    "docs/custom-agents-best-practices.md",
    "docs/setup.md",
    "docs/signal-integration.md",
    "docs/troubleshooting.md",
    "README.md"
  ],
  "broken_links_found": 0,
  "manual_followups": []
}
```

---

## Entity: ChangeManifest

The `.change-manifest.md` file categorizes all documentation-relevant changes since the last baseline.

### Fields

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `refresh_window` | `string` | Required | Date range of the refresh (e.g., "2026-04-11 → 2026-04-13") |
| `previous_baseline_sha` | `string` | Required | SHA from `.last-refresh` at start of cycle |
| `new_baseline_sha` | `string` | Required | SHA of `main` HEAD at time of refresh |
| `sources_analyzed` | `string` | Required | Comma-separated list of source paths scanned |
| `refresh_scopes` | `RefreshScope[]` | Required, ≥ 1 | Categorized groups of changes |
| `verified_current` | `string[]` | Optional | Docs verified as current with no changes needed |
| `verification_checklist` | `ChecklistItem[]` | Required, 9 items | End-of-manifest verification status |

### Sub-Entity: RefreshScope

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `title` | `string` | Required | Short description of the change group |
| `description` | `string` | Required | Narrative summary of what changed |
| `affected_docs` | `string[]` | Required | List of documentation files affected |

### Location

`solune/docs/.change-manifest.md` (Markdown format)

### Category Schema

The manifest categorizes findings into 6 categories (from issue #1728):

| Category | What to Look For |
|----------|-----------------|
| **New capabilities** | New user-facing features, pages, commands, integrations |
| **Changed behavior** | Altered workflows, renamed concepts, changed defaults |
| **Removed functionality** | Deleted features, deprecated APIs, removed UI |
| **Architectural changes** | New services, refactored module boundaries, changed infra |
| **UX changes** | Navigation changes, renamed screens, altered user flows |
| **Config/ops changes** | New env vars, changed deployment steps, new dependencies |

---

## Entity: DocToSourceMapping

The documentation-to-source mapping defines how each documentation file is verified against its authoritative source.

### Fields

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `doc_file` | `string` | Required | Path to the documentation file |
| `source_type` | `string` | Required | Category: Routes, Config schema, Module structure, etc. |
| `source_paths` | `string[]` | Required | Paths to authoritative source files |
| `diff_method` | `string` | Required | How to compare doc against source |

### Location

`solune/docs/OWNERS.md` (Doc-to-Source Mapping section)

### Current Mappings

| Doc File | Source Type | Source Paths |
|----------|-------------|-------------|
| `docs/api-reference.md` | Routes | `backend/src/api/*.py` |
| `docs/configuration.md` | Config schema | `backend/src/config.py`, `.env.example` |
| `docs/architecture.md` | Module structure | `backend/src/`, `docker-compose.yml` |
| `docs/setup.md` | Dependency manifest | `pyproject.toml`, `package.json`, Dockerfiles |
| `docs/pages/*.md` | Feature code | `frontend/src/pages/*.tsx` |
| `docs/agent-pipeline.md` | Feature code | `backend/src/services/workflow_orchestrator/` |
| `docs/signal-integration.md` | Feature code | `backend/src/services/signal_bridge.py` |
| `docs/testing.md` | Module structure | `tests/`, `.github/workflows/ci.yml` |
| `docs/project-structure.md` | Module structure | Repository filesystem |
| `README.md` | All types | All sources |

---

## Entity: VerificationChecklist

The verification checklist tracks completion of the 9 end-of-cycle quality gates.

### Fields

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `refresh_date` | `string` | Required | Date of the refresh cycle |
| `refresh_window` | `string` | Required | Date range covered |
| `performed_by` | `string` | Required | Agent/person who performed the refresh |
| `items` | `VerificationItem[]` | Required, 9 items | Individual verification gates |
| `overall_status` | `enum` | PASS, PARTIAL, FAIL | Aggregate result |

### Sub-Entity: VerificationItem

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `description` | `string` | Required | What is being verified |
| `passed` | `boolean` | Required | Whether the item passed |
| `tool` | `string` | Optional | Tool or command used to verify |
| `notes` | `string` | Optional | Additional context or findings |

### Location

`solune/docs/checklists/doc-refresh-verification.md` (Markdown checklist format)

### Required Verification Items

1. Change manifest accounted for all commits since last baseline
2. All internal doc links resolve
3. All documented features exist in the running application
4. All config keys in docs exist in the config schema
5. Getting-started guide runs clean from a fresh environment
6. No references to removed features remain in docs
7. README feature list matches current capabilities in priority order
8. New baseline (tag or metadata) is set for next cycle
9. Changelog updated with documentation changes

---

## Entity: UpdatePriority

Priority assignments guide the order in which documentation is updated.

### Schema

| Priority | Trigger | What to Update |
|----------|---------|----------------|
| **P0** | Product pitch or primary workflow changed | Top-level README, landing page of docs |
| **P1** | Feature added/changed/removed | Feature-specific docs, API reference, guides |
| **P2** | Architecture or structure changed | Architecture docs, directory/module maps |
| **P3** | Config, setup, or ops changed | Setup guides, config reference, deployment docs |
| **P4** | Bugs fixed or edge cases resolved | Troubleshooting, FAQ, known issues |

---

## State Transitions

### Refresh Cycle Lifecycle

```text
Idle → Phase 1 (Build Manifest)
  → Phase 2 (Infer Focus Shifts)
  → Phase 3 (Update README)
  → Phase 4 (Update Documentation Files)
  → Phase 5 (Validate Consistency)
  → Phase 6 (Verify Against Running Application)
  → Phase 7 (Stamp & Reset Baseline)
  → Idle
```

Each phase must complete before the next begins. Phase outputs are immutable once handed off. The cycle repeats bi-weekly per the cadence defined in `docs/OWNERS.md`.
