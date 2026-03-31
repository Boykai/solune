# Data Model: Bug Basher — Full Codebase Review & Fix

**Feature**: 002-bug-basher
**Date**: 2026-03-31
**Prerequisites**: [research.md](./research.md)

## Entities

### BugFinding (Core Entity)

Represents a single identified issue in the codebase. This is the primary unit of work for the review process.

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `id` | `int` | Yes | Sequential, starting at 1 | Unique finding number for the summary report |
| `file` | `str` | Yes | Relative path from repo root | File path where the bug was found |
| `lines` | `str` | Yes | Single line or range (e.g., `42` or `42-45`) | Line number(s) where the bug occurs |
| `category` | `BugCategory` | Yes | One of 5 defined categories | Classification of the bug type |
| `description` | `str` | Yes | Clear, concise explanation | What the bug is and why it's a problem |
| `status` | `FindingStatus` | Yes | `Fixed` or `Flagged` | Whether the bug was fixed or flagged for human review |
| `commit_sha` | `str` | If Fixed | 40-char hex SHA | Commit that contains the fix |
| `regression_test` | `str` | If Fixed | Test file path + test name | Test that guards against recurrence |
| `todo_comment` | `str` | If Flagged | `# TODO(bug-bash): ...` text | The TODO comment added to the source |

**Validation Rules**:
- Every finding with `status = Fixed` MUST have a non-empty `regression_test`
- Every finding with `status = Flagged` MUST have a non-empty `todo_comment`
- `category` must match the most severe applicable category if multiple apply
- `file` must reference an existing file in the repository

---

### BugCategory (Enumeration)

Priority-ordered classification for findings.

| Value | Priority | Description |
|-------|----------|-------------|
| `Security` | P1 | Auth bypasses, injection risks, exposed secrets, insecure defaults, improper input validation |
| `Runtime` | P2 | Unhandled exceptions, race conditions, null references, missing imports, type errors, resource leaks |
| `Logic` | P3 | Incorrect state transitions, wrong API calls, off-by-one errors, data inconsistencies, broken control flow |
| `Test Quality` | P4 | Untested code paths, tests passing for wrong reasons, mock leaks, assertions that never fail |
| `Code Quality` | P5 | Dead code, unreachable branches, duplicated logic, hardcoded values, missing error messages, silent failures |

**Priority Rule**: When a single bug spans multiple categories (edge case from spec), it is tagged with the highest-priority (lowest number) applicable category.

---

### FindingStatus (Enumeration)

| Value | Symbol | Meaning |
|-------|--------|---------|
| `Fixed` | ✅ | Bug resolved, tests added, all passing |
| `Flagged` | ⚠️ | Ambiguous issue left as `TODO(bug-bash)` comment for human review |

---

### RegressionTest (Associated Entity)

A test added specifically to validate that a fixed bug does not recur.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `test_file` | `str` | Yes | Path to the test file (relative to repo root) |
| `test_name` | `str` | Yes | Fully qualified test function/method name |
| `finding_id` | `int` | Yes | References the BugFinding this test guards |
| `description` | `str` | Yes | What the test verifies (docstring content) |

**Validation Rules**:
- Each RegressionTest is associated with exactly one BugFinding
- Each Fixed BugFinding has at least one RegressionTest
- The test must be independently runnable via `pytest <test_file>::<test_name>` (backend) or `npx vitest <test_file>` (frontend)
- The test must produce a clear pass/fail result

---

### TodoFlag (Associated Entity)

A source code comment marking an ambiguous issue for human review.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file` | `str` | Yes | File where the TODO comment is placed |
| `line` | `int` | Yes | Line number of the TODO comment |
| `finding_id` | `int` | Yes | References the BugFinding this flag documents |
| `comment_text` | `str` | Yes | Full TODO comment text including options and rationale |

**Format**: `# TODO(bug-bash): [description of issue, options considered, why human decision needed]`

**Validation Rules**:
- Each TodoFlag is associated with exactly one BugFinding
- Each Flagged BugFinding has exactly one TodoFlag
- The comment must appear at or near the referenced line in the source file
- The comment must explain: the issue, available options, and why it needs human judgment

---

### SummaryReport (Aggregate Entity)

A consolidated table of all BugFindings produced at the end of the review.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `findings` | `list[BugFinding]` | Yes | All findings, ordered by ID |
| `total_files_audited` | `int` | Yes | Total files reviewed (SC-001) |
| `total_fixed` | `int` | Yes | Count of Fixed findings |
| `total_flagged` | `int` | Yes | Count of Flagged findings |

**Validation Rules**:
- Every entry marked Fixed has a corresponding passing regression test (SC-002)
- Every entry marked Flagged has a corresponding TODO comment in source (SC-005)
- Files with no findings are excluded from the report (FR-014)
- The report covers 100% of files in the repository (SC-001)

---

## Relationships

```text
SummaryReport
    │
    └── contains: BugFinding[] (ordered by id)
                    │
                    ├── has_one: BugCategory (priority enum)
                    ├── has_one: FindingStatus (Fixed or Flagged)
                    │
                    ├── if Fixed → has_many: RegressionTest[]
                    │                 └── test_file + test_name
                    │
                    └── if Flagged → has_one: TodoFlag
                                      └── file + line + comment_text
```

## State Transitions

This feature does not introduce new stateful entities to the application. The BugFinding lifecycle is a review process artifact:

```text
[Module Under Review]
        │
        ├── Bug Identified → [Categorize by Priority]
        │                          │
        │                          ├── Clear Fix → [Fix Code] → [Add Regression Test] → [Verify Pass]
        │                          │                                                          │
        │                          │                                           status = Fixed ──┘
        │                          │
        │                          └── Ambiguous → [Add TODO Comment] → status = Flagged
        │
        └── No Bug Found → (skip, not in report)
```

**Terminal States**: Fixed and Flagged are both terminal. A Flagged finding may become Fixed in a future review cycle (outside the scope of this bug bash).
