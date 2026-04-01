# Research: Librarian — Automated Documentation Refresh Process

**Feature**: 003-librarian
**Date**: 2026-04-01
**Status**: Complete

## Research Tasks

### RT-001: Baseline Marker Format and Storage

**Context**: The spec requires establishing a baseline for each refresh cycle (FR-001). The system must retrieve the last refresh marker (tag, metadata file, or commit SHA) and fall back to the last release tag or a configurable time window (default: 2 weeks) if no baseline exists. The existing `solune/docs/.last-refresh` file already stores a JSON marker. Need to determine the canonical format and fallback strategy.

**Decision**: Use the existing `.last-refresh` JSON file as the primary baseline marker. The format is already established:

```json
{
  "date": "2026-03-14T18:41:00Z",
  "sha": "518be4cbd6ae2b9030abe4b13847e2c77f83b2b4",
  "documents_updated": [...],
  "documents_skipped": [...],
  "broken_links_found": 0,
  "manual_followups": []
}
```

Fallback order: (1) `.last-refresh` JSON `sha` field, (2) most recent `docs-refresh-*` git tag, (3) most recent release tag (`v*`), (4) `HEAD~14` (2-week equivalent as commit count).

Additionally, after each refresh, create a Git tag `docs-refresh-YYYY-MM-DD` for discoverability and as a secondary baseline source. This gives redundancy: the JSON file provides rich metadata while the tag is a simple Git-native pointer.

**Rationale**: The JSON file is already in use in the Solune project, providing a proven format with rich metadata (documents updated, skipped, broken links). Git tags provide a lightweight, version-control-native complement. The multi-level fallback ensures the process works on any repository regardless of whether previous Librarian cycles have run.

**Alternatives considered**:
- **Git tag only**: Loses the rich metadata (which docs were updated, which were skipped). Would require parsing tag messages for anything beyond the commit SHA.
- **Dedicated metadata database (SQLite, TOML)**: Over-engineered for a single metadata record. A JSON file is simpler, version-controlled, and human-readable.
- **Branch-based marker** (dedicated `docs-baseline` branch): Adds branching complexity for no clear benefit. The JSON file in the main branch is sufficient.

---

### RT-002: Change Manifest Harvesting Strategy

**Context**: The spec requires harvesting changes from structured sources (FR-002: changelog, specs, RFCs) and code diffs (FR-003: git diff, git log). Need to determine the optimal approach for each source and how to combine them into the six-category manifest (FR-004).

**Decision**: Use a three-source harvesting strategy executed sequentially:

1. **Changelog parsing**: Read `CHANGELOG.md` from baseline to HEAD. Parse entries under `### Added`, `### Changed`, `### Removed`, `### Fixed` headers following the [Keep a Changelog](https://keepachangelog.com/) format. Map to manifest categories:
   - Added → New capabilities
   - Changed → Changed behavior or UX changes (context-dependent)
   - Removed → Removed functionality
   - Fixed → Config/ops changes or Changed behavior (context-dependent)

2. **Spec/ADR scanning**: List new or modified files in `specs/`, `docs/decisions/` since baseline using `git diff --name-status <baseline>..HEAD -- specs/ docs/decisions/`. Each new spec or ADR indicates a potential new capability or architectural change.

3. **Code diff analysis**: Run `git diff --stat <baseline>..HEAD` and `git log --oneline <baseline>..HEAD`. Flag high-signal files:
   - `**/api/**`, `**/routes/**` → Entry points (new capabilities or changed behavior)
   - `**/pages/**`, `**/components/**` → Public-facing modules (UX changes)
   - `**/.env*`, `**/config*`, `**/*config*` → Configuration schemas (Config/ops changes)
   - `**/package.json`, `**/pyproject.toml`, `**/Cargo.toml` → Dependency manifests (Config/ops changes)
   - `**/migrations/**`, `**/models/**`, `**/schemas/**` → Data models (Architectural changes)
   - `**/Dockerfile`, `**/docker-compose*`, `**/*.yaml` (CI) → Build/deployment (Config/ops changes)

Consolidate findings by deduplicating entries that appear in multiple sources (e.g., a new API endpoint mentioned in both changelog and code diff). Present the manifest in the existing `.change-manifest.md` format.

**Rationale**: The three-source approach ensures comprehensive coverage: changelog captures intentional feature-level changes, spec/ADR scanning captures planned work, and code diffs catch changes that may not have been documented. The sequential execution allows earlier sources to provide context for categorizing code diff findings. The existing `.change-manifest.md` format is proven and provides a good structure.

**Alternatives considered**:
- **Code-diff only**: Misses context — a diff can show what changed but not why. The changelog provides the "why" and human-readable descriptions.
- **Changelog only**: Misses undocumented changes — developers don't always update the changelog for every change. Code diffs catch these gaps.
- **AI-powered commit message analysis**: Adds an LLM dependency for categorization. For the initial manual process, human review of structured output is more reliable and auditable. Can be added as an automation opportunity in future cycles.

---

### RT-003: Focus Shift Detection Approach

**Context**: The spec requires analyzing the change manifest to measure change density by functional area (FR-005) and detect narrative-level shifts (FR-006). Need to determine how to group changes into functional areas and detect shifts.

**Decision**: Use a two-step analysis approach:

1. **Change density measurement**: Group manifest items by functional area based on the affected files/modules. For the Solune project, the functional areas map to:
   - **Agents/AI**: `services/ai_agent.py`, `services/agent_*`, `api/agents.py`, `components/agents/`
   - **Pipelines**: `services/pipeline_*`, `api/pipelines.py`, `components/pipeline/`, `pages/Pipeline*`
   - **Activity**: `services/activity_*`, `api/activity.py`, `pages/Activity*`
   - **Settings/Config**: `api/settings.py`, `config.py`, `models/settings.py`
   - **Webhooks/Integration**: `api/webhooks.py`, `services/signal_bridge.py`
   - **Board/Projects**: `api/board.py`, `api/projects.py`, `pages/Board*`
   - **Infrastructure**: `Dockerfile`, `docker-compose*`, `.github/`, `migrations/`

   Count manifest items per area. The areas with the most items represent current development focus.

2. **Narrative shift detection**: Answer 5 questions from the manifest (per spec Phase 2.2):
   - New top-level capability? → Check for new pages, new major API routes, new service modules
   - Feature reduced/removed? → Check for deleted files, removed changelog entries
   - Value proposition shifted? → Compare development focus areas to README description
   - Primary workflow changed? → Check for changes to onboarding, main navigation, default landing page
   - New user personas? → Check for new roles, permissions, or distinct UI sections

   Each "yes" answer maps to a specific priority level (P0–P4) per the spec's priority table.

**Rationale**: File-path-based grouping is deterministic, automatable, and requires no external tooling. The functional area mapping is project-specific but the pattern (group by directory/module) is universal. The 5-question narrative check provides a structured way to elevate raw change data into strategic documentation priorities.

**Alternatives considered**:
- **LLM-based categorization**: Could provide more nuanced analysis but adds cost, latency, and non-determinism. Better suited for Phase 2 automation after manual cycles validate the process.
- **Commit message semantic analysis**: Unreliable — commit messages vary widely in quality. File paths are a more consistent signal.
- **Manual-only focus analysis**: The structured question approach provides a repeatable framework while still requiring human judgment for the answers.

---

### RT-004: Documentation-to-Source-of-Truth Mapping Strategy

**Context**: The spec requires mapping each documentation file to its source of truth and diffing the doc against that source (FR-009). Need to determine how to establish and maintain these mappings for any codebase.

**Decision**: Define explicit mappings in a structured section within each documentation file or in a central registry. For the Solune project, the mappings are:

| Doc File | Source of Truth | Diff Method |
|----------|----------------|-------------|
| `docs/api-reference.md` | `backend/src/api/*.py` route decorators | List all `@router.*` decorators → compare to documented endpoints |
| `docs/configuration.md` | `backend/src/config.py` + `.env.example` | Extract all config keys → compare to documented keys |
| `docs/architecture.md` | `backend/src/` module structure + `docker-compose.yml` | List top-level modules + services → compare to doc |
| `docs/setup.md` | `pyproject.toml` + `package.json` + `Dockerfile` | Run setup steps → note failures or version drift |
| `docs/pages/*.md` | Corresponding `frontend/src/pages/*.tsx` | Walk the page in the app → compare to doc description |
| `docs/agent-pipeline.md` | `services/workflow_orchestrator/` | Trace agent execution flow → compare to doc |
| `docs/signal-integration.md` | `services/signal_bridge.py` | Review bridge implementation → compare to doc |
| `docs/testing.md` | `tests/` directory structure + CI workflow | List test categories and commands → compare to doc |
| `docs/troubleshooting.md` | Recent closed issues + bug fixes | Review recent fixes → add new entries, prune resolved |
| `docs/project-structure.md` | Actual filesystem (`find` / `tree`) | Generate directory listing → compare to doc |
| `README.md` | All of the above + `CHANGELOG.md` | Holistic review against current capabilities |

The mapping is stored as a YAML front-matter comment in each doc file or as a central `docs/OWNERS.md` table (which already exists in the Solune project).

**Rationale**: Explicit mappings make the diffing process repeatable and auditable. Each mapping type has a clear, mechanical diff method that can eventually be automated. Storing mappings in `OWNERS.md` centralizes the reference and avoids modifying every doc file.

**Alternatives considered**:
- **Inline front-matter in each doc**: Distributes mappings across files; harder to get an overview. `OWNERS.md` already serves this role centrally.
- **Automated inference from filenames**: Brittle — not all docs have a 1:1 filename match to their source of truth. Explicit mapping is more reliable.
- **Git blame-based mapping**: Shows who last edited a doc but not what code it should reflect. Insufficient for source-of-truth alignment.

---

### RT-005: Link Validation Tooling

**Context**: The spec requires checking all internal cross-references and external URLs (FR-011, FR-016) with retry logic for transient errors. Need to select a tool that works in CI and locally.

**Decision**: Use `lychee` as the primary link validator. It is:
- Fast (Rust-based, async)
- Supports Markdown, HTML, and text files
- Has built-in retry logic with configurable backoff
- Outputs results in multiple formats (text, JSON, Markdown)
- Works in CI (GitHub Action available) and locally
- Supports excluding specific URLs or patterns (for known false positives)

Configuration:

```yaml
# .lychee.toml
max_retries: 3
retry_wait_time: 2  # seconds, with exponential backoff
timeout: 30
exclude_path: ["node_modules", ".git", "dist"]
accept: [200, 204, 301, 302, 308]
```

For the transient error retry requirement (FR-016), lychee's built-in retry with exponential backoff satisfies the "up to 3 attempts" requirement.

**Rationale**: `lychee` is the most capable and performant option available. It handles both internal and external links, supports the retry logic required by FR-016, and can be integrated into CI as a GitHub Action. The Solune project's `.last-refresh` already tracks `broken_links_found`, indicating link checking was anticipated.

**Alternatives considered**:
- **`markdown-link-check`**: JavaScript-based; slower than lychee; less configurable retry logic. Suitable but not preferred.
- **`linkinator`**: Google-maintained; good for external links but slower for large doc sets. No built-in retry configuration.
- **Custom script with `curl`**: Reinventing the wheel. Link validation is a solved problem with mature tooling.

---

### RT-006: Verification Checklist Implementation

**Context**: The spec requires a verification checklist at the end of each refresh (FR-014) confirming 9 specific items. Need to determine the format and integration approach.

**Decision**: Create a Markdown checklist template at `solune/docs/checklists/doc-refresh-verification.md` that is copied and filled in at the end of each refresh cycle. The template includes all 9 verification items from the spec, each with a pass/fail status and notes field:

```markdown
## Verification Checklist — [DATE]

- [ ] Change manifest accounted for all commits since last baseline
- [ ] All internal doc links resolve
- [ ] All documented features exist in the running application
- [ ] All config keys in docs exist in the config schema
- [ ] Getting-started guide runs clean from a fresh environment
- [ ] No references to removed features remain in docs
- [ ] README feature list matches current capabilities in priority order
- [ ] New baseline (tag or metadata) is set for next cycle
- [ ] Changelog updated with documentation changes
```

The completed checklist is appended to the `.change-manifest.md` as the final section, creating a single artifact that captures both what changed and whether the refresh was verified.

**Rationale**: A Markdown checklist is simple, version-controlled, and human-readable. Embedding it in `.change-manifest.md` keeps all refresh cycle data in one file. The template in `docs/checklists/` provides a reusable starting point that ensures no verification item is forgotten.

**Alternatives considered**:
- **Separate verification report file**: Creates file proliferation. One manifest + checklist file per cycle is cleaner.
- **GitHub Issue checklist**: Good for tracking but not version-controlled with the docs. The `.change-manifest.md` approach keeps the audit trail in the repository.
- **Automated CI gate**: Premature for the initial manual process. Can be added after 2–3 cycles validate which checks can be reliably automated.

---

### RT-007: Terminology Audit Strategy

**Context**: The spec requires auditing documentation for renamed concepts (FR-011) and ensuring consistent naming across all docs (Acceptance Scenario 5.2). Need to determine how to detect and replace renamed terms.

**Decision**: Use a two-step approach:

1. **Extract renames from the manifest**: When the change manifest identifies renamed concepts (e.g., a module renamed from `WorkflowEngine` to `PipelineOrchestrator`), add them to a `renames` section in the manifest:

   ```markdown
   ## Renames
   | Old Term | New Term | Source |
   |----------|----------|--------|
   | WorkflowEngine | PipelineOrchestrator | git log: "Rename workflow engine" |
   ```

2. **Grep docs for old terms**: For each rename, run `grep -rn "Old Term" docs/` to find all occurrences. Replace with the new term, respecting context (e.g., don't replace inside code blocks that reference historical versions).

For terminology consistency (not renames), maintain a `docs/.terminology.md` file or a section in `OWNERS.md` that lists canonical terms and their aliases. During each refresh, grep for non-canonical aliases and standardize.

**Rationale**: Simple grep-based detection is reliable, deterministic, and requires no tooling beyond standard Unix utilities. The rename table in the manifest creates a clear, auditable record of what was changed and why. This approach works for any codebase regardless of language.

**Alternatives considered**:
- **Custom linter rule**: More sophisticated but harder to maintain. For the initial manual process, grep is sufficient.
- **LLM-based semantic matching**: Could catch synonyms and near-misses but adds non-determinism. Better suited for future automation.
- **IDE find-and-replace**: Not scriptable or auditable. The grep approach can be automated and logged.

---

### RT-008: Diagram Freshness Validation

**Context**: The spec requires checking diagram freshness (FR-011, Acceptance Scenario 5.4) — regenerating auto-generated diagrams and flagging stale non-generated ones. The Solune project already has a diagram generation script (`solune/scripts/generate-diagrams.sh`).

**Decision**: Leverage the existing `generate-diagrams.sh --check` script for Mermaid diagram validation. This script already:
- Regenerates `.mmd` files from source
- Compares generated output against committed files
- Exits non-zero if any diagram is stale (used in CI)

For non-auto-generated diagrams (e.g., manually drawn architecture diagrams), flag them during the refresh for manual review. Add a `last_verified` field to diagram files or track in `.change-manifest.md`.

**Rationale**: The existing `generate-diagrams.sh` script is already integrated into CI and validated as working. Reusing it avoids duplication and ensures consistency between CI checks and the Librarian process. The `--check` flag provides exactly the freshness validation needed.

**Alternatives considered**:
- **Custom diagram diff tool**: Unnecessary — `generate-diagrams.sh` already handles this.
- **Screenshot comparison**: Brittle and requires rendering infrastructure. Text-based Mermaid comparison is more reliable.
- **Skip non-generated diagrams**: Risks stale diagrams going undetected. Flagging for manual review is a reasonable middle ground.

---

### RT-009: Code Sample Validation Approach

**Context**: The spec requires validating embedded code snippets in documentation (FR-011, Acceptance Scenario 5.3). Need to determine how to extract and verify code samples.

**Decision**: Use a three-tier approach based on code block language:

1. **Python samples**: Extract fenced code blocks tagged as `python`. For each, attempt to parse with `ast.parse()` to verify syntax validity. For import-dependent samples, verify the imported modules exist in the project.

2. **Shell/bash samples**: Extract fenced code blocks tagged as `bash` or `shell`. Verify that referenced commands exist (`which <command>`) and that referenced file paths exist in the project.

3. **TypeScript/JavaScript samples**: Extract fenced code blocks tagged as `typescript` or `javascript`. Verify syntax with `tsc --noEmit` or `node --check` where feasible.

For the initial manual process, code sample validation is a visual review during the refresh cycle. Automated extraction and validation can be added as a CI step after 2–3 cycles establish which patterns are reliable.

**Rationale**: Syntax parsing (not execution) provides a good balance between thoroughness and safety. Full execution of code samples could have side effects and requires a complete environment. Syntax validation catches the most common issues (outdated imports, renamed functions, changed APIs) without execution risk.

**Alternatives considered**:
- **Full execution in sandboxed environment**: Most thorough but complex to set up and maintain. Premature for initial cycles.
- **`doctest`-style frameworks**: Python-specific; the Librarian process is language-agnostic. Can be used for Python-specific docs as an enhancement.
- **Skip code validation**: Risks documenting broken examples. Even syntax checking catches obvious errors.
