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

```bash
cd solune

# Read the existing baseline
BASELINE_SHA=$(cat docs/.last-refresh | python3 -c "import sys, json; print(json.load(sys.stdin)['sha'])" 2>/dev/null)

# Fallback: use most recent docs-refresh tag
if [ -z "$BASELINE_SHA" ]; then
  BASELINE_SHA=$(git tag -l 'docs-refresh-*' --sort=-creatordate | head -1)
fi

# Fallback: use most recent release tag
if [ -z "$BASELINE_SHA" ]; then
  BASELINE_SHA=$(git tag -l 'v*' --sort=-creatordate | head -1)
fi

# Fallback: use 2-week window
if [ -z "$BASELINE_SHA" ]; then
  BASELINE_SHA=$(git log --after="14 days ago" --format="%H" | tail -1)
fi

echo "Baseline: $BASELINE_SHA"
```

**Step 1.2 — Harvest from structured sources:**

```bash
# Parse changelog entries since baseline
git diff "$BASELINE_SHA"..HEAD -- CHANGELOG.md

# Scan specs and ADRs for new or changed files
git diff --name-status "$BASELINE_SHA"..HEAD -- specs/ docs/decisions/
```

**Step 1.3 — Harvest from code diffs:**

```bash
# Files with significant churn
git diff --stat "$BASELINE_SHA"..HEAD

# Commit-level summary
git log --oneline "$BASELINE_SHA"..HEAD

# High-signal changes (entry points, config, models, etc.)
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

**Step 1.4 — Compile the manifest:**

Write findings to `docs/.change-manifest.md` using the 6-category format. See [data-model.md](./data-model.md) for the category definitions.

If zero changes are detected, report "no changes detected" and stop (FR-017).

---

### Phase 2: Infer Focus Shifts

**Step 2.1 — Measure change density:**

Count manifest items per functional area. The areas with the most items are the current development focus.

**Step 2.2 — Detect narrative shifts:**

Answer these questions based on the manifest:

1. Has a new top-level capability been added that deserves prominent mention?
2. Has a previously prominent feature been reduced, removed, or folded into another?
3. Has the product's primary value proposition shifted?
4. Has the primary user workflow changed?
5. Have new user personas been introduced?

**Step 2.3 — Assign priorities:**

Based on answers, assign P0–P4 priorities to documentation updates:
- P0: Product pitch or primary workflow changed → README, docs landing page
- P1: Feature added/changed/removed → Feature docs, API reference, guides
- P2: Architecture or structure changed → Architecture docs, module maps
- P3: Config, setup, or ops changed → Setup guides, config reference
- P4: Bugs fixed or edge cases → Troubleshooting, FAQ, known issues

---

### Phase 3: Update the README

```bash
# Review current README description against manifest
head -20 ../README.md

# If narrative shift detected, rewrite the description
# Add new features to feature list
# Remove deprecated features
# Reorder by current importance

# Verify getting-started instructions
# Run setup from scratch to confirm commands work
```

---

### Phase 4: Update Documentation Files

For each doc affected by the priority list:

```bash
# Example: Check API reference against actual routes
grep -rn "@router\." backend/src/api/*.py | \
  awk -F'"' '{print $2}' | sort > /tmp/actual-routes.txt

grep -E "^(GET|POST|PUT|DELETE|PATCH)" docs/api-reference.md | \
  awk '{print $2}' | sort > /tmp/documented-routes.txt

diff /tmp/actual-routes.txt /tmp/documented-routes.txt
# Missing = new routes not documented
# Extra = documented routes that no longer exist

# Example: Check config reference against actual config keys
grep -rn "os.getenv\|os.environ\|Settings\." backend/src/config.py | sort > /tmp/actual-config.txt

# Compare to docs/configuration.md entries
```

For structural docs:

```bash
# Regenerate directory maps
tree -I 'node_modules|.git|dist|__pycache__|.venv' --dirsfirst backend/src/

# Regenerate architecture diagrams
./scripts/generate-diagrams.sh
```

---

### Phase 5: Validate Consistency

**Step 5.1 — Link validation:**

```bash
# Install lychee if not present
# cargo install lychee  OR  brew install lychee

# Run link check on all docs
lychee docs/ README.md --max-retries 3 --retry-wait-time 2 --timeout 30

# Check results — fix broken internal links, flag broken external links
```

**Step 5.2 — Terminology audit:**

```bash
# For each rename in the manifest, grep for old terms
# Example: if "WorkflowEngine" was renamed to "PipelineOrchestrator"
grep -rn "WorkflowEngine" docs/

# Replace all occurrences with the new term
```

**Step 5.3 — Diagram freshness:**

```bash
# Check if auto-generated diagrams are up to date
./scripts/generate-diagrams.sh --check

# If stale, regenerate
./scripts/generate-diagrams.sh
```

**Step 5.4 — Code sample validation:**

```bash
# Extract Python code blocks and check syntax
grep -A 50 '```python' docs/*.md | python3 -c "
import sys, ast
for block in sys.stdin.read().split('```python'):
    code = block.split('```')[0].strip()
    if code:
        try:
            ast.parse(code)
        except SyntaxError as e:
            print(f'Syntax error: {e}')
"
```

---

### Phase 6: Verify Against the Running Application

```bash
# Start the application
docker compose up -d

# Smoke-test 3-5 documented workflows
# 1. Verify dashboard page matches docs/pages/dashboard.md
# 2. Verify pipeline execution matches docs/agent-pipeline.md
# 3. Verify settings page matches docs/configuration.md
# 4. Verify activity page matches docs/pages/activity.md
# 5. Verify board page matches docs/pages/board.md

# Check config keys
grep -oP 'SOLUNE_\w+' docs/configuration.md | while read key; do
  grep -q "$key" backend/src/config.py && echo "✓ $key" || echo "✗ $key NOT IN CODE"
done
```

---

### Phase 7: Stamp and Reset Baseline

```bash
cd solune

# Stage all doc changes
git add docs/ README.md CHANGELOG.md

# Commit with conventional message
git commit -m "docs: refresh documentation for $(date -I)"

# Update the baseline marker
REFRESH_DATE=$(date -u +%Y-%m-%dT%H:%M:%SZ)
REFRESH_SHA=$(git rev-parse HEAD)
cat > docs/.last-refresh << EOF
{
  "date": "$REFRESH_DATE",
  "sha": "$REFRESH_SHA",
  "documents_updated": [],
  "documents_skipped": [],
  "broken_links_found": 0,
  "manual_followups": []
}
EOF
# Edit documents_updated and documents_skipped arrays to list actual paths

# Create the git tag
git tag "docs-refresh-$(date -I)"

# Push
git push origin main --tags
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
