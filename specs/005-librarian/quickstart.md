# Quickstart: Librarian Documentation Refresh

**Feature**: Librarian | **Date**: 2026-04-13

> **Status note (2026-04-13):** This guide describes how to execute a Librarian documentation refresh cycle from start to finish. All tooling is already in the repository — no new dependencies or scripts are required.

## Prerequisites

- Git (for `git diff`, `git log`)
- Node.js ≥18 with npm (for link validation tests)
- Python 3.12+ with `uv` (for backend verification)
- Access to the repository at `solune/`

## Setup

```bash
# Navigate to the repository root
cd solune

# Ensure you have the latest main
git fetch origin main

# Read the current baseline
cat docs/.last-refresh
```

The `.last-refresh` file contains the baseline SHA and date for the previous refresh cycle.

## Execution Steps

### Step 1: Build the Change Manifest (Phase 1)

```bash
# Get the baseline SHA from .last-refresh
BASELINE_SHA=$(python3 -c "import json; print(json.load(open('docs/.last-refresh'))['sha'])")

# Harvest code diffs since last refresh
git diff --stat "$BASELINE_SHA"..HEAD
git log --oneline --since="$(python3 -c "import json; print(json.load(open('docs/.last-refresh'))['date'])")"

# Review the CHANGELOG for structured entries
cat CHANGELOG.md | head -60

# Check for new specs or ADRs
ls -la ../specs/ 2>/dev/null
ls -la docs/decisions/
```

Update `docs/.change-manifest.md` with findings categorized into:

- New capabilities
- Changed behavior
- Removed functionality
- Architectural changes
- UX changes
- Config/ops changes

### Step 2: Infer Focus Shifts (Phase 2)

Review the manifest and answer:

1. Has a new top-level capability been added?
2. Has a feature been reduced, removed, or folded into another?
3. Has the primary workflow changed?
4. Have new user personas been introduced?

Assign priorities (P0–P4) to each affected documentation file.

### Step 3: Update the README (Phase 3)

Review and update `README.md`:

1. Revalidate the project description
2. Audit the feature list (add shipped, remove deprecated)
3. Verify getting-started instructions against current dependencies
4. Check badge URLs and status links

### Step 4: Update Documentation Files (Phase 4)

For each documentation file, use the doc-to-source mapping in `docs/OWNERS.md`:

```bash
# Example: Verify API reference against actual routes
grep -rn "@router\." backend/src/api/*.py backend/src/api/**/*.py 2>/dev/null | head -50

# Example: Verify config keys against docs
grep -n "os.getenv\|os.environ" backend/src/config.py | head -30

# Example: Verify project structure
find . -maxdepth 3 -type d -not -path './.git/*' -not -path './node_modules/*' | sort
```

For each affected doc:

1. Read the current doc
2. Diff against its source of truth
3. Identify gaps: **missing**, **stale**, **dead**
4. Rewrite affected sections (don't patch — rewrite naturally)

### Step 5: Validate Consistency (Phase 5)

```bash
# 5.1 — Internal link validation
cd frontend && npm test -- --run src/docs/documentationLinks.test.ts && cd ..

# 5.2 — Regenerate diagrams
./scripts/generate-diagrams.sh

# 5.3 — Verify diagram freshness (exits non-zero if stale)
./scripts/generate-diagrams.sh --check

# 5.4 — Terminology grep (check for deprecated terms from manifest)
grep -rn "quick-access cards\|dashboard welcome hero\|standalone /chat" docs/ README.md 2>/dev/null
```

### Step 6: Verify Against Running Application (Phase 6)

If a running instance is available:

1. Smoke-test 3–5 documented user flows
2. Verify documented env vars against `backend/src/config.py`
3. Compare 3–5 documented API endpoints against FastAPI router definitions

If no running instance:

```bash
# Code-level verification of routes
grep -rn "APIRouter\|@router\." backend/src/api/ | head -30

# Code-level verification of config
grep -n "class Settings\|Field(" backend/src/config.py | head -30
```

### Step 7: Stamp & Reset Baseline (Phase 7)

```bash
# Update .last-refresh with new baseline
cat > docs/.last-refresh << 'EOF'
{
  "date": "YYYY-MM-DDTHH:MM:SSZ",
  "sha": "NEW_MAIN_HEAD_SHA",
  "documents_updated": [
    "list/of/updated/docs.md"
  ],
  "documents_skipped": [
    "list/of/skipped/docs.md"
  ],
  "broken_links_found": 0,
  "manual_followups": []
}
EOF

# Reset verification checklist
# Edit docs/checklists/doc-refresh-verification.md with new dates and re-verify all items

# Commit all changes
git add docs/ README.md CHANGELOG.md
git commit -m "docs: librarian refresh for YYYY-MM-DD"
```

## Validation Commands

```bash
# Run all validation in sequence
cd solune

# Internal links
cd frontend && npm test -- --run src/docs/documentationLinks.test.ts && cd ..

# Diagram freshness
./scripts/generate-diagrams.sh --check

# Markdown lint (via pre-commit or direct)
# markdownlint docs/**/*.md README.md
```

## Key Files Reference

### Read (inputs)

| File | Purpose |
|------|---------|
| `docs/.last-refresh` | Baseline SHA and date for previous cycle |
| `docs/.change-manifest.md` | Previous cycle's change manifest |
| `docs/OWNERS.md` | Doc-to-source mapping and ownership |
| `CHANGELOG.md` | Structured change entries |
| `docs/checklists/doc-refresh-verification.md` | Previous verification results |

### Update (outputs)

| File | Changes |
|------|---------|
| `docs/.change-manifest.md` | New manifest with current refresh window |
| `docs/.last-refresh` | New baseline SHA and date |
| `docs/checklists/doc-refresh-verification.md` | Reset and re-verified checklist |
| `README.md` | Updated feature list, description, links |
| `CHANGELOG.md` | Documentation section added to [Unreleased] |
| `docs/*.md` | Updated documentation files (per Phase 4 analysis) |

### Tooling (existing)

| Tool | Command | Purpose |
|------|---------|---------|
| `documentationLinks.test.ts` | `npm test -- --run src/docs/documentationLinks.test.ts` | Internal link validation |
| `generate-diagrams.sh` | `./scripts/generate-diagrams.sh` | Mermaid diagram regeneration |
| `generate-diagrams.sh --check` | `./scripts/generate-diagrams.sh --check` | Diagram freshness verification |
| `markdownlint` | Via pre-commit hook | Markdown style enforcement |
| `markdown-link-check` | Via pre-commit hook | External URL validation |

## Troubleshooting

### Baseline SHA not found in git history

If the SHA in `.last-refresh` isn't in your local history (shallow clone), fetch more history:

```bash
git fetch --unshallow origin
```

### Link validation test fails

Run the test directly to see which links are broken:

```bash
cd frontend && npm test -- --run --reporter=verbose src/docs/documentationLinks.test.ts
```

### Diagram generation fails

Ensure the script has execute permissions:

```bash
chmod +x scripts/generate-diagrams.sh
./scripts/generate-diagrams.sh
```
