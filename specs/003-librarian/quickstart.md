# Quickstart: Librarian — Automated Documentation Refresh Process

**Feature**: 003-librarian
**Date**: 2026-04-01
**Prerequisites**: [plan.md](./plan.md), [data-model.md](./data-model.md), [contracts/](./contracts/)

## Overview

The Librarian is a 7-phase documentation refresh process that detects what changed in the codebase, infers how the product's focus shifted, and rewrites docs to match reality. It extends the existing `solune/docs/` infrastructure (`.last-refresh` baseline marker and `.change-manifest.md`) into a structured, repeatable workflow.

This quickstart guides through executing each phase manually. No new backend APIs or frontend code are required — the Librarian operates on Git history, Markdown files, and shell commands.

## Existing Files (Already Present)

### 1. `solune/docs/.last-refresh` — Baseline Marker

JSON file storing the last refresh point. Read at the start of each cycle, updated at the end:

```json
{
  "date": "2026-03-14T18:41:00Z",
  "sha": "518be4cbd6ae2b9030abe4b13847e2c77f83b2b4",
  "documents_updated": [
    "docs/agent-pipeline.md",
    "docs/architecture.md",
    "docs/configuration.md",
    "docs/setup.md",
    "docs/troubleshooting.md"
  ],
  "documents_skipped": [
    "docs/api-reference.md",
    "docs/custom-agents-best-practices.md",
    "docs/project-structure.md",
    "docs/testing.md",
    "docs/signal-integration.md",
    "frontend/docs/findings-log.md",
    "README.md"
  ],
  "broken_links_found": 0,
  "manual_followups": []
}
```

### 2. `solune/docs/.change-manifest.md` — Change Manifest

Markdown file capturing all changes since the last baseline. Overwritten each cycle:

```markdown
# Change Manifest

**Refresh Window**: 2026-03-14 → 2026-04-01
**SHA Range**: `518be4c..HEAD`
**Sources Analyzed**: CHANGELOG.md, specs/ directories, git diff

---

## New Features
1. **Feature name** — Description
   - Source: CHANGELOG | spec | git-diff
   - Source Detail: specific location
   - Domain: functional area
   - Affected Docs: docs/file.md, README.md
...
```

### 3. `solune/.github/ISSUE_TEMPLATE/chore-librarian.md` — Issue Template

GitHub Issue template for triggering a Librarian refresh cycle. Already exists and contains the full 7-phase process as a checklist.

## New Files

### 1. `solune/docs/checklists/doc-refresh-verification.md` — Verification Checklist Template

Create this template for the Phase 7 verification checklist (FR-014):

```markdown
# Documentation Refresh Verification Checklist

**Refresh Date**: [DATE]
**Refresh Window**: [START] → [END]
**Performed By**: [NAME]

## Verification Items

- [ ] Change manifest accounted for all commits since last baseline
  - SHA range: `[baseline_sha]..[head_sha]`
  - Commit count: [N]
  - Notes:

- [ ] All internal doc links resolve
  - Tool: lychee
  - Broken links found: [N]
  - Notes:

- [ ] All documented features exist in the running application
  - Features smoke-tested: [list]
  - Notes:

- [ ] All config keys in docs exist in the config schema
  - Keys checked: [N]
  - Missing from code: [list or "none"]
  - Notes:

- [ ] Getting-started guide runs clean from a fresh environment
  - Environment: [container/fresh clone/CI]
  - Notes:

- [ ] No references to removed features remain in docs
  - Removed features: [list from manifest]
  - Grep results: [clean / findings]
  - Notes:

- [ ] README feature list matches current capabilities in priority order
  - Notes:

- [ ] New baseline (tag or metadata) is set for next cycle
  - Tag: docs-refresh-[DATE]
  - .last-refresh updated: yes/no
  - Notes:

- [ ] Changelog updated with documentation changes
  - Section added: yes/no
  - Notes:

## Overall Status

- [ ] **PASS** — All items verified
- [ ] **PARTIAL** — Some items require follow-up (see notes)
- [ ] **FAIL** — Critical items unresolved
```

## Phase-by-Phase Execution Guide

### Phase 1: Build the Change Manifest

**Step 1.1 — Establish the baseline:**

The baseline is the starting point for detecting changes. The following fallback precedence is used (FR-001):

| Priority | Source | Method | When Used |
|----------|--------|--------|-----------|
| 1 | `.last-refresh` JSON | Read `sha` field from `docs/.last-refresh` | Normal operation — most recent refresh SHA |
| 2 | Git tag `docs-refresh-*` | `git tag -l 'docs-refresh-*' --sort=-creatordate \| head -1` | `.last-refresh` missing or invalid |
| 3 | Release tag `v*` | `git tag -l 'v*' --sort=-creatordate \| head -1` | No docs-refresh tags exist |
| 4 | Time window (14 days) | `git log --after="14 days ago" --format="%H" \| tail -1` | No tags of any kind exist |

```bash
cd solune

# Priority 1: Read the existing baseline from .last-refresh JSON
BASELINE_SHA=$(cat docs/.last-refresh | python3 -c "import sys, json; print(json.load(sys.stdin)['sha'])" 2>/dev/null)

# Validate the SHA exists in git history (skip empty or whitespace-only values)
if [ -n "${BASELINE_SHA// /}" ]; then
  git cat-file -t "$BASELINE_SHA" >/dev/null 2>&1 || BASELINE_SHA=""
fi

# Priority 2: Fallback to most recent docs-refresh tag
if [ -z "$BASELINE_SHA" ]; then
  BASELINE_SHA=$(git tag -l 'docs-refresh-*' --sort=-creatordate | head -1)
fi

# Priority 3: Fallback to most recent release tag
if [ -z "$BASELINE_SHA" ]; then
  BASELINE_SHA=$(git tag -l 'v*' --sort=-creatordate | head -1)
fi

# Priority 4: Fallback to 2-week time window
if [ -z "$BASELINE_SHA" ]; then
  BASELINE_SHA=$(git log --after="14 days ago" --format="%H" | tail -1)
fi

echo "Baseline: $BASELINE_SHA"
```

**Step 1.2 — Harvest from structured sources (FR-002):**

Parse the changelog for entries added since the baseline, and scan spec/ADR directories for new or modified proposals.

```bash
# Parse changelog entries since baseline — look for Added/Changed/Removed/Fixed sections
git diff "$BASELINE_SHA"..HEAD -- CHANGELOG.md

# Scan specs and ADRs for new or changed files
git diff --name-status "$BASELINE_SHA"..HEAD -- specs/ docs/decisions/
```

From the changelog diff, extract entries under these headings:

- **### Added** → candidate "New capabilities" items
- **### Changed** → candidate "Changed behavior" items
- **### Removed** or **### Deprecated** → candidate "Removed functionality" items
- **### Fixed** → candidate "Changed behavior" or "Config / ops changes" items
- **### Security** → candidate "Changed behavior" or "Config / ops changes" items

For specs and ADRs, any new file (`A` status) is a candidate for "New capabilities" or "Architectural changes". Modified files (`M` status) may indicate evolving proposals.

**Step 1.3 — Harvest from code diffs (FR-003):**

Analyze git history for high-signal changes using the file patterns from [contracts/refresh-workflow.yaml](./contracts/refresh-workflow.yaml).

```bash
# Files with significant churn
git diff --stat "$BASELINE_SHA"..HEAD

# Commit-level summary
git log --oneline "$BASELINE_SHA"..HEAD

# High-signal changes — entry points, public modules, config, deps, models, build/deploy
git diff --name-status "$BASELINE_SHA"..HEAD -- \
  'backend/src/api/' \
  'frontend/src/pages/' \
  'frontend/src/components/' \
  'backend/src/config.py' \
  'backend/src/models/' \
  'backend/src/migrations/' \
  'Dockerfile' \
  'docker-compose.yml' \
  'pyproject.toml' \
  'frontend/package.json' \
  '.github/workflows/'
```

Flag changes by signal type:

| Signal Type | File Patterns | Manifest Category |
|-------------|---------------|-------------------|
| Entry points | `backend/src/api/`, CLI commands, event handlers | New capabilities / Changed behavior |
| Public modules | `frontend/src/pages/`, `frontend/src/components/` | UX changes / New capabilities |
| Config schemas | `backend/src/config.py`, `.env*`, feature flags | Config / ops changes |
| Dependency manifests | `pyproject.toml`, `package.json`, `Cargo.toml` | Config / ops changes |
| Data models / migrations | `backend/src/migrations/`, `backend/src/models/` | Architectural changes |
| Build / deploy scripts | `Dockerfile`, `docker-compose.yml`, `.github/workflows/` | Architectural changes / Config / ops changes |

**Step 1.4 — Compile the manifest (FR-004):**

Categorize all harvested items into the 6 manifest categories and write to `docs/.change-manifest.md`:

| Category | What to Look For |
|----------|------------------|
| **New capabilities** | New user-facing features, pages, commands, integrations |
| **Changed behavior** | Altered workflows, renamed concepts, changed defaults |
| **Removed functionality** | Deleted features, deprecated APIs, removed UI |
| **Architectural changes** | New services, refactored module boundaries, changed infra |
| **UX changes** | Navigation changes, renamed screens, altered user flows |
| **Config / ops changes** | New env vars, changed deployment steps, new dependencies |

For each item, record:

- **Description**: Human-readable summary of the change
- **Source**: Where detected (`changelog`, `spec`, `adr`, `git-diff`)
- **Source Detail**: Specific location (e.g., "## [Unreleased] > ### Added")
- **Domain**: Functional area (e.g., "pipeline", "agents", "auth", "infra")
- **Affected Docs**: Documentation files potentially impacted

Deduplicate cross-source entries (e.g., a feature mentioned in both the changelog and git diff should appear once, noting both sources).

If zero changes are detected, report "no changes detected" and stop — skip all subsequent phases and preserve the existing baseline (FR-017).

**Edge cases (Phase 1):**

| Condition | Handling |
|-----------|----------|
| No baseline exists | Use the fallback chain from Step 1.1 (tag → release → 2 weeks) per FR-001 |
| Changelog missing or non-standard format | Skip changelog parsing entirely; proceed with code diffs only. Note the skip in the manifest summary: "CHANGELOG.md: skipped (not found or non-standard format)" |
| Zero changes detected since baseline | Report "no changes detected since [baseline_sha]". Skip Phases 2–7. Preserve the existing `.last-refresh` baseline unchanged (FR-017) |

---

### Phase 2: Infer Focus Shifts

**Step 2.1 — Measure change density by domain (FR-005):**

Group manifest items by their `domain` field and count items per domain. The domains with the most entries represent the current development focus.

```text
Example output:
| Domain       | Change Count | Focus Level |
|-------------|-------------|-------------|
| pipeline     | 12          | 🔴 High     |
| agents       | 8           | 🔴 High     |
| infra        | 8           | 🔴 High     |
| tools        | 5           | 🟡 Medium   |
| projects     | 4           | 🟡 Medium   |
| auth         | 3           | 🟢 Low      |
```

Rank domains by count to identify the top 3 development focus areas.

**Step 2.2 — Detect narrative shifts (FR-006):**

Answer these 5 diagnostic questions from [contracts/refresh-workflow.yaml](./contracts/refresh-workflow.yaml) based on the manifest:

| # | Question | If Yes → Impact |
|---|----------|-----------------|
| 1 | Has a new top-level capability been added that deserves prominent mention? | P0: Update README pitch, docs landing page |
| 2 | Has a previously prominent feature been reduced, removed, or folded into another? | P1: Remove or consolidate affected docs |
| 3 | Has the product's primary value proposition shifted? | P0: Rewrite README description |
| 4 | Has the primary user workflow changed? (different starting point, different happy path) | P0: Update getting-started, main flow docs |
| 5 | Have new user personas been introduced? (e.g., admin panel added → admin persona) | P1: Add persona-specific docs/sections |

Record each answer with supporting evidence from the manifest items.

**Step 2.3 — Assign priorities (FR-007):**

Based on the narrative shift answers, assign P0–P4 priorities to documentation updates using the priority table from [data-model.md](./data-model.md):

| Priority | Trigger | Docs to Update |
|----------|---------|----------------|
| **P0** | Product pitch or primary workflow changed | Top-level README, docs landing page |
| **P1** | Feature added/changed/removed | Feature-specific docs, API reference, guides |
| **P2** | Architecture or structure changed | Architecture docs, directory/module maps |
| **P3** | Config, setup, or ops changed | Setup guides, config reference, deployment docs |
| **P4** | Bugs fixed or edge cases resolved | Troubleshooting, FAQ, known issues |

Produce a prioritized update list mapping each affected doc to its priority level, trigger reason, and source of truth (from the [doc-to-source mapping in OWNERS.md](../../solune/docs/OWNERS.md#doc-to-source-mapping)). This list drives Phases 3–4.

Write the focus-shift analysis output to `docs/.change-manifest.md` after the Summary section, including:

- **Domain Classification** table with change counts and focus levels
- **Narrative Shift Analysis** with answers to all 5 diagnostic questions
- **Priority Assignments** table mapping each document to its priority, trigger, and source of truth

---

### Phase 3: Update the README

**Step 3.1 — Revalidate project description (FR-008):**

Compare the current README elevator pitch against the focus-shift analysis from Phase 2.

```bash
# Review current README description
head -20 ../README.md
```

- If a **P0 narrative shift** was detected (primary value proposition or workflow changed), rewrite the project description to match reality
- If no P0 shift, verify the one-liner still accurately describes what the product does today
- The description should reflect the current product, not planned features

**Step 3.2 — Audit feature list (FR-008):**

Cross-reference the README feature list against the manifest categories:

- **Add** newly shipped capabilities from the "New capabilities" section
- **Remove** items listed in "Removed functionality"
- **Update** items from "Changed behavior" to reflect current state
- **Reorder** by current importance — use the change density ranking from Phase 2 to determine which features are most active/important

**Step 3.3 — Verify getting-started instructions (FR-008):**

Run the quickstart from `docs/setup.md` in a clean environment:

```bash
# Check prerequisite versions against current dependency manifests
python3 --version  # Compare to pyproject.toml requires-python
node --version     # Compare to package.json engines (if specified)

# Run setup steps and verify each command succeeds
# Follow docs/setup.md instructions step by step
```

- Check prerequisite versions against `pyproject.toml` and `package.json`
- Validate that all commands produce expected output
- **Edge case**: If getting-started instructions fail in a clean environment, log the specific error details and flag the section as requiring manual fix — do not silently skip failures

**Step 3.4 — Update visual/structural references (FR-008):**

```bash
# If UX changes were detected, check for outdated screenshots or diagrams
# Replace any visuals that no longer match the current UI

# Verify architecture-at-a-glance diagrams if topology changed
# Update if new services, pages, or modules were added

# Verify all badge URLs and status links resolve
lychee README.md --max-retries 3 --retry-wait-time 2 --timeout 30
```

---

### Phase 4: Update Documentation Files

**Step 4.1 — Map each doc to its source of truth (FR-009):**

Reference the [doc-to-source mapping table in OWNERS.md](../../solune/docs/OWNERS.md#doc-to-source-mapping) to identify the source of truth for each documentation file. The mapping defines:

- **Source type**: What kind of source (routes, config_schema, module_structure, dependency_manifest, feature_code, cli_definition, schema_definition, bug_fixes)
- **Source paths**: Where to find the authoritative code/config
- **Diff method**: How to compare the doc against its source

**Step 4.2 — Update affected docs (FR-010):**

For each doc in the prioritized update list (from Phase 2), follow this process:

1. **Read** the current documentation file
2. **Diff** against its source of truth using the method from OWNERS.md
3. **Categorize gaps**:
   - **Missing**: New things in code not yet documented
   - **Stale**: Documented things that have changed in code
   - **Dead**: Documented things that no longer exist in code
4. **Rewrite** affected sections naturally — do not patch with "UPDATE:" notes
5. **Adjust framing** if a narrative shift was detected in Phase 2

```bash
# Example: Check API reference against actual routes
grep -rn "@router\." backend/src/api/*.py | \
  awk -F'"' '{print $2}' | sort > /tmp/actual-routes.txt

grep -E "^(GET|POST|PUT|DELETE|PATCH)" docs/api-reference.md | \
  awk '{print $2}' | sort > /tmp/documented-routes.txt

diff /tmp/actual-routes.txt /tmp/documented-routes.txt
# Missing in doc = new routes not documented (gap: missing)
# Extra in doc = documented routes no longer exist (gap: dead)

# Example: Check config reference against actual config keys
grep -rn "os.getenv\|os.environ\|Settings\." backend/src/config.py | sort > /tmp/actual-config.txt
# Compare to docs/configuration.md entries
```

**Step 4.3 — Update structural docs (FR-015):**

```bash
# Regenerate directory maps for docs/project-structure.md
tree -I 'node_modules|.git|dist|__pycache__|.venv' --dirsfirst backend/src/

# Regenerate architecture diagrams
./solune/scripts/generate-diagrams.sh

# Verify all code examples in rewritten sections compile/run
```

**Edge case (Phase 4):**

| Condition | Handling |
|-----------|----------|
| Doc has no identifiable source of truth | Flag the file for manual review. Exclude from automated diffing, but still include it in link validation (Phase 5.1) and terminology audit (Phase 5.2). Note in the manifest: "docs/[file].md: no source mapping — manual review required" |

---

### Phase 5: Validate Consistency

**Step 5.1 — Link validation (FR-011, FR-016):**

Check all internal cross-references and external URLs across documentation files.

```bash
# Install lychee if not present
# cargo install lychee  OR  brew install lychee

# Run link check on all docs with retry for transient errors (FR-016)
lychee solune/docs/ README.md --max-retries 3 --retry-wait-time 2 --timeout 30

# Check results — fix broken internal links, flag persistent broken external links
```

- Fix all broken **internal** links immediately (cross-references between doc files)
- For **external** URLs, lychee retries up to 3 times with backoff — only flag persistent failures (FR-016)
- Verify all **anchor links** point to existing headings

**Step 5.2 — Terminology audit (FR-011):**

Extract renamed concepts from the "Renames" section of `docs/.change-manifest.md` and grep all docs for old terminology — regardless of whether the specific doc was in the priority list (catches cross-cutting renames per Edge Case 5).

```bash
# For each rename in the manifest, grep for old terms across ALL docs
# Example: if "WorkflowEngine" was renamed to "PipelineOrchestrator"
grep -rn "WorkflowEngine" solune/docs/ README.md

# Replace all occurrences with the new term
# Use sed or manual editing depending on context sensitivity
# sed -i 's/WorkflowEngine/PipelineOrchestrator/g' solune/docs/*.md
```

Ensure consistent naming across README and all doc files — a concept should use the same name everywhere unless the difference is intentional and documented.

**Step 5.3 — Diagram freshness (FR-011):**

Verify auto-generated Mermaid diagrams in `solune/docs/architectures/` are current.

```bash
# Check if auto-generated diagrams are up to date
./solune/scripts/generate-diagrams.sh --check

# If stale, regenerate
./solune/scripts/generate-diagrams.sh
```

For non-generated diagrams, manually verify they still match reality by comparing against the current codebase structure.

**Step 5.4 — Code sample validation (FR-011):**

Extract embedded code snippets from Markdown files and verify syntax validity for the detected language.

```bash
# Extract Python code blocks and check syntax
grep -A 50 '```python' solune/docs/*.md | python3 -c "
import sys, ast
for block in sys.stdin.read().split('python'):
    code = block.split('---')[0].strip()
    if code and not code.startswith('#'):
        try:
            ast.parse(code)
        except SyntaxError as e:
            print(f'Syntax error: {e}')
"
```

Note any snippets that reference removed APIs or changed function signatures from the manifest.

---

### Phase 6: Verify Against the Running Application

**Step 6.1 — Smoke-test documented workflows:**

Pick 3–5 key user flows described in docs and walk each in the running application.

```bash
# Start the application
docker compose up -d

# Smoke-test documented workflows:
# 1. Verify dashboard page matches docs/pages/dashboard.md
# 2. Verify pipeline execution matches docs/agent-pipeline.md
# 3. Verify settings page matches docs/configuration.md
# 4. Verify activity page matches docs/pages/activity.md
# 5. Verify board page matches docs/pages/board.md
```

For each flow, verify: screen names, navigation paths, button labels, terminology, and expected outcomes all match the documentation.

**Step 6.2 — Verify config and setup docs:**

```bash
# Confirm all documented config keys exist in the config schema
grep -oP 'SOLUNE_\w+' solune/docs/configuration.md | while read key; do
  grep -q "$key" solune/backend/src/config.py && echo "✓ $key" || echo "✗ $key NOT IN CODE"
done

# Confirm documented default values match actual defaults
```

**Step 6.3 — Verify API docs (if applicable):**

Compare 3–5 documented endpoints against actual request/response shapes, or compare against an auto-generated OpenAPI/Swagger spec if available.

---

### Phase 7: Stamp & Reset Baseline

**Step 7.1 — Commit documentation changes (FR-012):**

Commit all doc updates in a single, well-described commit using conventional commit format.

```bash
cd solune

# Stage all doc changes
git add docs/ README.md CHANGELOG.md

# Commit with conventional message including the refresh date range (YYYY-MM-DD format)
git commit -m "docs: refresh documentation for 2026-03-14 to 2026-04-01"
```

**Step 7.2 — Update the changelog (FR-012):**

Add a Documentation section to `CHANGELOG.md` under the current `[Unreleased]` heading:

```markdown
### Documentation

- Refreshed `docs/api-reference.md` — added N new endpoints, removed M deprecated
- Refreshed `docs/architecture.md` — updated service diagram for new modules
- ...list each updated doc with a brief summary of key changes
```

**Step 7.3 — Set the new baseline (FR-012):**

Update `docs/.last-refresh` JSON with current refresh metadata and create the git tag.

```bash
# Update the baseline marker
REFRESH_DATE=$(date -u +%Y-%m-%dT%H:%M:%SZ)
REFRESH_SHA=$(git rev-parse HEAD)
cat > docs/.last-refresh << EOF
{
  "date": "$REFRESH_DATE",
  "sha": "$REFRESH_SHA",
  "documents_updated": [
    "docs/api-reference.md",
    "docs/architecture.md"
  ],
  "documents_skipped": [
    "docs/signal-integration.md"
  ],
  "broken_links_found": 0,
  "manual_followups": []
}
EOF
# Edit documents_updated and documents_skipped arrays to list actual paths

# Commit the baseline update
git add docs/.last-refresh
git commit --amend --no-edit

# Create the git tag
git tag "docs-refresh-$(date -I)"

# Push
git push origin main --tags
```

**Step 7.4 — Complete the verification checklist (FR-014):**

Fill in the [`doc-refresh-verification.md`](../../solune/docs/checklists/doc-refresh-verification.md) template with pass/fail for all 9 verification items. Append the completed checklist to `docs/.change-manifest.md` as the final "Verification Checklist" section. Record overall status:

- **PASS**: All 9 items verified successfully
- **PARTIAL**: Some items require follow-up — list failed items in `manual_followups` in `.last-refresh`
- **FAIL**: Critical items (items 1, 2, or 8) unresolved

**Edge cases (Phase 7):**

| Condition | Handling |
|-----------|----------|
| Zero changes detected in Phase 1 | No new baseline created. Existing `.last-refresh` is preserved unchanged. No git tag is created. The next cycle will re-use the same baseline (FR-017) |
| Verification items that fail | Mark the item as fail with notes explaining the failure. Set overall status to PARTIAL. Add the failed items to the `manual_followups` array in `.last-refresh` so they are tracked for the next cycle |

## Running Your First Refresh

A condensed single-page checklist for quick reference during execution. Each step links to the detailed section above.

### Checklist

```text
Phase 1: Build the Change Manifest
  □ 1.1  Read docs/.last-refresh → extract baseline SHA (or use fallback chain)
  □ 1.2  git diff <baseline>..HEAD -- CHANGELOG.md specs/ docs/decisions/
  □ 1.3  git diff --stat <baseline>..HEAD  +  git log --oneline <baseline>..HEAD
  □ 1.4  Categorize findings into 6 categories → write docs/.change-manifest.md
         ⚠ If zero changes: STOP here, preserve baseline

Phase 2: Infer Focus Shifts
  □ 2.1  Group manifest items by domain → rank by count
  □ 2.2  Answer 5 narrative-shift questions
  □ 2.3  Assign P0–P4 priorities → produce prioritized update list

Phase 3: Update the README
  □ 3.1  Compare README pitch to manifest → rewrite if P0 shift detected
  □ 3.2  Add/remove/reorder features in README feature list
  □ 3.3  Run getting-started instructions from scratch → fix any failures
  □ 3.4  Verify badges, links, diagrams → update outdated visuals

Phase 4: Update Documentation Files
  □ 4.1  Reference OWNERS.md doc-to-source mapping for each affected doc
  □ 4.2  For each doc: read → diff against source → identify gaps → rewrite
  □ 4.3  Regenerate project-structure.md + architecture diagrams

Phase 5: Validate Consistency
  □ 5.1  lychee solune/docs/ README.md → fix broken links
  □ 5.2  Grep all docs for renamed concepts from manifest → replace old names
  □ 5.3  ./solune/scripts/generate-diagrams.sh --check → regenerate if stale
  □ 5.4  Extract code snippets → verify syntax validity

Phase 6: Verify Against Running App
  □ 6.1  Smoke-test 3–5 documented workflows in the running application
  □ 6.2  Verify all documented config keys exist in backend/src/config.py
  □ 6.3  Verify 3–5 documented API endpoints match actual responses

Phase 7: Stamp & Reset Baseline
  □ 7.1  git add + git commit -m "docs: refresh documentation for <period>"
  □ 7.2  Add Documentation section to CHANGELOG.md
  □ 7.3  Update docs/.last-refresh JSON + create docs-refresh-YYYY-MM-DD tag
  □ 7.4  Fill doc-refresh-verification.md → append to .change-manifest.md
```

## Implementation Order

1. **Create verification checklist template** at `docs/checklists/doc-refresh-verification.md`
2. **Execute Phase 1** — Build change manifest from baseline
3. **Execute Phase 2** — Analyze manifest for focus shifts and priorities
4. **Execute Phase 3** — Update README based on priorities
5. **Execute Phase 4** — Update affected documentation files
6. **Execute Phase 5** — Validate consistency (links, terms, diagrams, code samples)
7. **Execute Phase 6** — Smoke-test against running application
8. **Execute Phase 7** — Commit, update changelog, set new baseline

## Verification

After completing a full refresh cycle, run through the verification checklist:

```bash
# Verify baseline is set
cat docs/.last-refresh | python3 -m json.tool

# Verify git tag exists
git tag -l 'docs-refresh-*' --sort=-creatordate | head -1

# Verify no broken links
lychee docs/ README.md --max-retries 3

# Verify changelog has documentation section
grep -A 5 "### Documentation" CHANGELOG.md | head -10

# Verify all docs are reachable from README or docs index
# (Manual check — ensure no orphan docs)
```

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| No new backend/frontend code | Librarian is a process, not a service. Uses Git CLI + Markdown + shell commands. |
| Extend existing `.last-refresh` and `.change-manifest.md` | Proven format already in use; avoids creating parallel infrastructure. |
| JSON baseline + Git tag redundancy | JSON provides rich metadata; tag provides Git-native discoverability. Both are cheap. |
| Manual-first with incremental automation | Per spec assumptions: validate the process manually for 2–3 cycles before automating. |
| `lychee` for link validation | Fast (Rust), built-in retry logic matching FR-016, CI-ready, multi-format support. |
| 6-category manifest | Matches spec exactly (FR-004); provides clear buckets for prioritization. |
| Verification checklist in `.change-manifest.md` | Single artifact per cycle; keeps manifest and verification together for auditability. |
| Archivist agent as primary executor | Leverages existing agent infrastructure; the archivist agent is already designed for doc updates. |
