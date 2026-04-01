# Data Model: Bug Basher — Full Codebase Review & Fix

**Feature**: 002-bug-basher
**Created**: 2026-03-31

## Overview

The bug bash does not introduce new database entities or API models. Instead, it defines a process model for tracking findings during the code review. These entities exist as documentation artifacts (the summary table) and source code annotations (`TODO` comments), not as runtime data structures.

## Entities

### Bug Finding

Represents a single identified issue in the codebase.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | integer | Yes | Sequential finding number (1, 2, 3...) |
| `file` | string | Yes | Relative file path from repository root |
| `lines` | string | Yes | Line number or range (e.g., "42" or "42-45") |
| `category` | enum | Yes | One of: Security, Runtime, Logic, Test Quality, Code Quality |
| `description` | string | Yes | Brief description of the bug or issue |
| `status` | enum | Yes | One of: ✅ Fixed, ⚠️ Flagged (TODO) |

**Validation rules**:
- `file` must be a valid path relative to repository root
- `lines` must reference actual line numbers in the file
- `category` must match one of the five defined categories
- `description` must explain what the bug is, not how it was fixed (fix details go in commit message)
- `status` must be "Fixed" if the bug was corrected, or "Flagged" if left as a TODO

**Relationships**:
- Each Bug Finding with status "Fixed" → exactly one Regression Test
- Each Bug Finding with status "Flagged" → exactly one TODO Flag in source code

---

### Regression Test

A test added specifically to validate that a fixed bug does not reoccur.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `test_file` | string | Yes | Path to the test file containing the regression test |
| `test_name` | string | Yes | Fully qualified test function name |
| `finding_id` | integer | Yes | Reference to the Bug Finding this test validates |
| `assertion_type` | string | Yes | What the test asserts (e.g., "raises ValueError", "returns 403") |

**Validation rules**:
- `test_file` must exist and be a valid test file in the appropriate test directory
- `test_name` must follow existing naming conventions (`test_*` for pytest, `it("*")` for Vitest)
- The test must be independently runnable and produce a clear pass/fail result
- The test must fail if the bug fix is reverted (validates the fix, not just the code path)

**Relationships**:
- Each Regression Test → exactly one Bug Finding (1:1)
- Regression tests are co-located with existing tests for the same module

---

### TODO Flag

A source code comment marking an ambiguous issue for human review.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file` | string | Yes | Path to the file containing the comment |
| `line` | integer | Yes | Line number where the comment is placed |
| `finding_id` | integer | Yes | Reference to the Bug Finding this flag represents |
| `comment` | string | Yes | Full text of the `TODO(bug-bash):` comment with the file's native comment syntax |

**Format**: `TODO(bug-bash): [description of issue, options, and why it needs human decision]` with the file's native comment syntax

**Validation rules**:
- Comment must start with `# TODO(bug-bash):` (Python) or `// TODO(bug-bash):` (TypeScript)
- Comment must describe: (1) the issue, (2) available options, (3) why human judgment is needed
- The comment must be placed at the relevant code location, not at file top
- No code change accompanies a TODO flag — only the comment is added

**Relationships**:
- Each TODO Flag → exactly one Bug Finding (1:1)

---

### Summary Report

A consolidated table of all Bug Findings produced at the end of the review.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `findings` | list[Bug Finding] | Yes | All findings from the review |
| `total_fixed` | integer | Yes | Count of findings with status "Fixed" |
| `total_flagged` | integer | Yes | Count of findings with status "Flagged" |
| `total_files_audited` | integer | Yes | Count of files reviewed |
| `test_suite_status` | enum | Yes | "PASS" or "FAIL" |
| `lint_status` | enum | Yes | "PASS" or "FAIL" |

**Validation rules**:
- `findings` must include every fix and every flag — no omissions (SC-006)
- Files with no bugs are excluded from the findings list (FR-014)
- `test_suite_status` must be "PASS" before the report is finalized (FR-006)
- `lint_status` must be "PASS" before the report is finalized (FR-007)

**Output format**: Markdown table as specified in the spec:

```markdown
| # | File | Line(s) | Category | Description | Status |
|---|------|---------|----------|-------------|--------|
| 1 | `path/to/file.py` | 42-45 | Security | Description of bug | ✅ Fixed |
| 2 | `path/to/file.py` | 100 | Logic | Description of ambiguity | ⚠️ Flagged (TODO) |
```

## State Transitions

### Bug Finding Lifecycle

```
[Identified] → [Assessed]
                  ├── Clear bug → [Fixed] → regression test added → [Verified]
                  └── Ambiguous  → [Flagged] → TODO comment added → [Documented]
```

1. **Identified**: Bug discovered during file review
2. **Assessed**: Reviewer determines if fix is clear or ambiguous
3. **Fixed**: Code change applied, existing tests updated if affected
4. **Verified**: Regression test added, full suite passes
5. **Flagged**: TODO comment added, no code change
6. **Documented**: Entry added to summary report

### Review Process Lifecycle

```
[Setup] → [Category N Review] → [Fix/Flag] → [Validate] → [Next Category or Complete]
```

1. **Setup**: Establish baseline (existing tests pass, lint passes)
2. **Category N Review**: Audit files for category N bugs (N=1..5)
3. **Fix/Flag**: Apply fixes or add TODO flags for each finding
4. **Validate**: Run test suite + lint checks after each batch
5. **Complete**: Generate summary report when all categories reviewed

## Entity Relationship Diagram

```
┌─────────────────┐      1:1       ┌──────────────────┐
│   Bug Finding    │──── Fixed ────│  Regression Test  │
│                  │               │                    │
│  id              │               │  test_file         │
│  file            │               │  test_name         │
│  lines           │               │  finding_id        │
│  category        │               │  assertion_type    │
│  description     │               └──────────────────┘
│  status          │
│                  │      1:1       ┌──────────────────┐
│                  │──── Flagged ──│    TODO Flag       │
└─────────────────┘               │                    │
        │ *                        │  file              │
        │                          │  line              │
        └──────────┐               │  finding_id        │
                   │               │  comment           │
           ┌───────▼──────┐        └──────────────────┘
           │Summary Report │
           │               │
           │  findings[]   │
           │  total_fixed  │
           │  total_flagged│
           │  test_status  │
           │  lint_status  │
           └───────────────┘
```
