# Research: Librarian Documentation Refresh

**Feature**: Librarian | **Date**: 2026-04-13 | **Status**: Complete

## R1: Change Manifest Generation Strategy

**Decision**: Use `git diff --stat` and `git log --oneline` against the `.last-refresh` baseline SHA to build the change manifest. Parse CHANGELOG.md `[Unreleased]` section for structured Added/Changed/Fixed/Removed entries. Scan `specs/` and `docs/decisions/` for new or updated proposals.

**Rationale**: The repository already tracks a baseline SHA in `solune/docs/.last-refresh` (currently `b183ba318e47ae2958f58aafabc299bc6b580bcc`, dated 2026-04-11). The previous `.change-manifest.md` demonstrates the exact format and categorization approach. Git-based diffing provides an exhaustive, automated foundation that can be enriched with CHANGELOG parsing for semantic context.

**Alternatives considered**:

| Alternative | Why Rejected |
|-------------|-------------|
| Manual file-by-file review | Time-consuming, error-prone, misses subtle changes |
| GitHub API comparison | Requires API access; git CLI is available in all environments |
| Only parse CHANGELOG | Misses undocumented changes, dependency bumps, and structural shifts |

---

## R2: Documentation-to-Source Mapping

**Decision**: Use the existing `docs/OWNERS.md` Doc-to-Source Mapping table as the authoritative map. Each documentation file already has an explicit source type, source paths, and diff method defined.

**Rationale**: The `OWNERS.md` file at `solune/docs/OWNERS.md` already contains a comprehensive Doc-to-Source Mapping section (12 documentation files mapped to their source-of-truth paths and verification methods). This mapping was created specifically for the Librarian refresh process (referenced as "Phase 4" in the file). Reusing it avoids duplication and ensures consistency.

**Key mappings** (from OWNERS.md):

| Doc File | Source Paths | Diff Method |
|----------|-------------|-------------|
| `api-reference.md` | `backend/src/api/*.py` | List `@router.*` decorators → compare |
| `configuration.md` | `backend/src/config.py`, `.env.example` | Extract config keys → compare |
| `architecture.md` | `backend/src/`, `docker-compose.yml` | List modules + topology → compare |
| `setup.md` | `pyproject.toml`, `package.json`, Dockerfiles | Run setup steps → note drift |
| `pages/*.md` | `frontend/src/pages/*.tsx` | Walk page in running app → compare |
| `project-structure.md` | Repository filesystem | `tree` output → compare |

**Alternatives considered**:

| Alternative | Why Rejected |
|-------------|-------------|
| Build mapping from scratch | Duplicates existing OWNERS.md; risks divergence |
| Automated source detection | Over-engineered; the stable mapping in OWNERS.md is manually curated and accurate |

---

## R3: Link Validation Tooling

**Decision**: Use the existing `markdown-link-check` (configured in `.markdown-link-check.json`) for external URL validation and the frontend `documentationLinks.test.ts` for internal relative link validation. Both are already integrated into CI.

**Rationale**: The repository has comprehensive link validation infrastructure already in place:

1. **Pre-commit hook** runs `markdown-link-check` on changed markdown files
2. **CI workflow** (`ci.yml`) has a dedicated "Docs Lint" job running both `markdownlint` and `markdown-link-check`
3. **Frontend test** (`src/docs/documentationLinks.test.ts`) validates internal `.md` links and heading fragments
4. **Configuration** (`.markdown-link-check.json`) has retry/timeout settings for external URLs

No new tooling is needed — the refresh process invokes existing tools.

**Alternatives considered**:

| Alternative | Why Rejected |
|-------------|-------------|
| Install `lychee` | Redundant; `markdown-link-check` + frontend test already cover internal + external links |
| Custom link checker script | Maintenance overhead; existing tooling is battle-tested in CI |
| Skip link validation | Violates Phase 5 requirements; broken links degrade documentation quality |

---

## R4: Diagram Freshness Strategy

**Decision**: Run `solune/scripts/generate-diagrams.sh` to regenerate all Mermaid diagrams. The script has built-in change detection — it only updates files when content actually differs. Use `--check` mode to verify freshness without overwriting.

**Rationale**: The repository already has a diagram generation script that:

1. Discovers backend API modules (both `*.py` files and sub-package directories with `__init__.py`)
2. Generates 5 Mermaid diagrams: `backend-components.mmd`, `frontend-components.mmd`, `data-flow.mmd`, `deployment.mmd`, `high-level.mmd`
3. Supports `--check` flag for CI verification (exits non-zero if diagrams are stale)
4. Only updates files when content actually changes (avoids unnecessary diffs)

**Alternatives considered**:

| Alternative | Why Rejected |
|-------------|-------------|
| Manual diagram updates | Diagrams in `docs/architectures/` are auto-generated; manual edits get overwritten |
| PlantUML migration | Existing Mermaid tooling is established and renders natively in GitHub |
| Skip diagram check | Stale diagrams mislead developers; CI already enforces freshness |

---

## R5: Terminology Consistency Approach

**Decision**: Grep documentation for known renamed concepts from the change manifest. Build a simple deprecated-term → replacement mapping from the CHANGELOG and manifest, then search docs for stale terminology.

**Rationale**: The CHANGELOG `[Unreleased]` section documents concept changes (e.g., "ChatPanelManager" replacing dashboard hero, modal workflow consolidation). The `.change-manifest.md` records specific concept removals ("dashboard welcome hero", "quick-access cards", "standalone `/chat` page"). A targeted grep for these known terms is more efficient than a full NLP analysis.

**Key terms to check** (from current CHANGELOG):

- "quick-access cards" → removed
- "dashboard welcome hero" → removed
- "standalone /chat page" → replaced by ChatPanelManager workspace
- "Current Pipeline section" → removed from Pipelines page
- Any references to deleted prompt modules (`issue_generation`, `task_generation`, `transcript_analysis`)

**Alternatives considered**:

| Alternative | Why Rejected |
|-------------|-------------|
| Full NLP-based term extraction | Over-engineered for the scope; manual extraction from CHANGELOG is precise |
| Custom linter rule | Good for recurring terms but premature; start manual per the issue's "Automation Opportunities" guidance |

---

## R6: Verification Checklist Strategy

**Decision**: Use the existing `docs/checklists/doc-refresh-verification.md` template. Reset all checkboxes, update the refresh window and baseline, and re-verify each item against the current state.

**Rationale**: The checklist already exists at `solune/docs/checklists/doc-refresh-verification.md` with 8 verification items covering: change manifest completeness, link resolution, feature existence, config keys, getting-started guide, removed features, README accuracy, and baseline stamping. The previous refresh (2026-04-11) completed all items successfully. The new cycle reuses the same structure.

**Alternatives considered**:

| Alternative | Why Rejected |
|-------------|-------------|
| Create new checklist format | Existing format matches the issue's verification checklist exactly |
| Skip verification | Violates the issue's Phase 7 requirements |
| Automated verification only | Some items (feature existence, README accuracy) require human/agent judgment |
