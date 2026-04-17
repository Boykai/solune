# Data Model: Bug Basher

**Feature**: 001-bug-basher | **Date**: 2026-04-17
**Input**: Feature specification from [spec.md](spec.md) and [research.md](research.md)

## Entities

> **Note**: The bug bash is a process-oriented feature, not a data-model-driven feature. The entities below describe the conceptual model for tracking findings and outputs, not database tables or API models.

### Bug Report Entry

An individual finding from the code review audit.

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `id` | integer | Sequential finding number | Auto-increment, starts at 1 |
| `file` | string | Relative file path from repository root | Must be a valid path to an existing file |
| `lines` | string | Line number(s) affected | Format: `N` or `N-M` for ranges |
| `category` | enum | Bug category classification | One of: Security, Runtime, Logic, Test Quality, Code Quality |
| `description` | string | Human-readable description of the bug | Must explain what the bug is and why it is a bug |
| `status` | enum | Resolution status | One of: ✅ Fixed, ⚠️ Flagged (TODO) |

**Validation Rules**:

- `file` must reference a file that exists in the repository
- `lines` must reference valid line numbers within the file
- `category` must be one of the five defined categories
- `description` must be non-empty and explain the bug clearly
- `status` must be "Fixed" only if a regression test exists and all tests pass

### Regression Test

A test case specifically written to validate a bug fix.

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `bug_id` | integer | Reference to the Bug Report Entry | Must match an existing finding with status "Fixed" |
| `test_file` | string | Path to the test file containing the regression test | Must be a valid test file path |
| `test_name` | string | Name of the test function/case | Must follow existing naming conventions |
| `description` | string | What the test validates | Must describe the regression scenario |

**Validation Rules**:

- Every Bug Report Entry with status "Fixed" must have at least one associated Regression Test
- The test must fail if the bug fix is reverted (regression prevention)
- The test must follow existing test conventions (pytest for backend, vitest for frontend)

### TODO Flag

An inline code comment marking an ambiguous issue for human review.

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `bug_id` | integer | Reference to the Bug Report Entry | Must match a finding with status "Flagged" |
| `file` | string | File containing the TODO comment | Must match the Bug Report Entry file |
| `line` | integer | Line number of the TODO comment | Must be at or near the issue location |
| `format` | string | Comment format | `# TODO(bug-bash): ...` (Python) or `// TODO(bug-bash): ...` (TypeScript) |
| `content` | string | Comment body | Must include: issue description, options, and reason for human decision |

**Validation Rules**:

- Every Bug Report Entry with status "Flagged" must have a corresponding TODO Flag in the source code
- The comment must include all three required elements: description, options, and reason
- The comment must not trigger the suppression guard (`check-suppressions.sh`)

### Summary Table

The consolidated output report of all findings.

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `entries` | list[Bug Report Entry] | All findings from the audit | Ordered by sequential ID |
| `fixed_count` | integer | Number of entries with status "Fixed" | Computed from entries |
| `flagged_count` | integer | Number of entries with status "Flagged" | Computed from entries |
| `total_count` | integer | Total number of findings | `fixed_count + flagged_count` |

**Validation Rules**:

- Files with no bugs must NOT appear in the summary
- Every entry must have either "Fixed" or "Flagged" status
- The table must include columns: #, File, Line(s), Category, Description, Status

## Relationships

```text
Summary Table
  └── contains 1..N → Bug Report Entry
                        ├── has 1..N → Regression Test    (if status = "Fixed")
                        └── has 1 → TODO Flag             (if status = "Flagged")
```

## State Transitions

### Bug Report Entry Lifecycle

```text
[Discovered] → [Analyzed] → [Fixed] (obvious bug → fix + test)
                           → [Flagged] (ambiguous → TODO comment)
```

- **Discovered**: Bug identified during audit
- **Analyzed**: Bug categorized and assessed for clarity
- **Fixed**: Obvious bug resolved with minimal code change + regression test added
- **Flagged**: Ambiguous issue marked with `TODO(bug-bash)` for human review

There is no backward transition — a finding is either Fixed or Flagged, never both.
