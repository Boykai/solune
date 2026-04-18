# Quickstart: Verifying Each Workstream

**Feature**: 002-reduce-broad-except
**Audience**: implementer of the per-workstream PRs and reviewers.

This document gives copy-pasteable verification recipes for each workstream. Each recipe is the minimum sequence required to satisfy the spec's Acceptance Scenarios and Success Criteria.

All commands assume `pwd == /home/runner/work/solune/solune` (the workspace root) unless stated otherwise.

---

## Workstream A — Ban Silent Swallowers (Policy + Lint)

### Step A1 — Enable BLE001

#### Apply

Edit `solune/backend/pyproject.toml` `[tool.ruff.lint]` block to match `contracts/ruff-config-contract.md` § C1 (After Workstream A exemplar). The only change is adding `"BLE",  # flake8-blind-except` after `"B"` in the `select` list.

#### Verify

```bash
cd solune/backend

# Rule is active and reports violations
uv run ruff check src/ --select BLE001 --statistics
# Expected: ~568 violations across ~87 files

# Full lint fails (expected — triage not yet done)
uv run ruff check
# Expected: exit non-zero (BLE001 violations)
```

#### Canary (Acceptance Scenario US1.2)

```bash
cd solune/backend
cat > /tmp/canary_ble.py <<'EOF'
def risky():
    try:
        return 1 / 0
    except Exception:
        pass
EOF
uv run ruff check /tmp/canary_ble.py --select BLE001
# Expected: exit non-zero — BLE001 reported on the except line
```

---

### Step A2 — Adopt the tag convention

#### Apply

For each `except Exception` handler that is triaged as **Tagged**, add the inline suppression:

```python
except Exception as exc:  # noqa: BLE001 — reason: <justification>
```

See `contracts/tag-convention-contract.md` for the format specification, valid examples, and decision flowchart.

#### Verify

```bash
cd solune/backend

# All tags follow the convention (human-readable grep check)
grep -rn "noqa: BLE001" src/ | grep -v "reason:"
# Expected: zero output (every BLE001 suppression has a reason)

# Tag count is under the ceiling
tag_count=$(grep -rc "noqa: BLE001" src/ | awk -F: '{s+=$2} END{print s}')
echo "Tagged handler count: $tag_count (ceiling: 85)"
# Expected: $tag_count < 85 (SC-003: fewer than 15% of ~568)
```

---

### Step A3 — Triage all handlers

#### Apply

For each `except Exception` handler, resolve to one of:

| Bucket | Action | Verification |
|---|---|---|
| **Narrow** | Replace `except Exception` with specific type(s) | BLE001 no longer fires on the line |
| **Promote** | Remove the handler entirely | Error propagates to caller |
| **Tagged** | Add `# noqa: BLE001 — reason:` | BLE001 suppressed with justification |

See `data-model.md` § E3 and § E6 for triage rules and common narrowing targets.

#### Verify

```bash
cd solune/backend

# Zero unresolved BLE001 violations (SC-001)
uv run ruff check src/ --select BLE001
# Expected: exit 0

# Full lint passes
uv run ruff check
# Expected: exit 0

# Test suite passes (FR-011)
uv run pytest
# Expected: all tests pass
```

#### Canary (Acceptance Scenario US1.3)

```bash
cd solune/backend
cat > /tmp/canary_tagged.py <<'EOF'
def risky():
    try:
        return 1 / 0
    except Exception:  # noqa: BLE001 — reason: test canary with approved tag
        pass
EOF
uv run ruff check /tmp/canary_tagged.py --select BLE001
# Expected: exit 0 — tagged handler accepted
```

---

### Step A4 — Document the convention (FR-005)

#### Apply

Add a section to `solune/backend/README.md` documenting:

1. The `# noqa: BLE001 — reason:` format
2. When to use it (decision flowchart from `contracts/tag-convention-contract.md` § T3)
3. At least 3 examples of valid tagged handlers

#### Verify

```bash
# Convention is findable in README
grep -c "BLE001" solune/backend/README.md
# Expected: >= 1

# SC-005: A new contributor can find the convention within 2 minutes
# Manual review: open solune/backend/README.md, search for "BLE001" or "broad-except"
```

---

## Workstream B — Domain-Error Helper

### Step B1 — Implement `_best_effort()` helper

#### Apply

Add the `_best_effort()` method to `_ServiceMixin` in `solune/backend/src/services/github_projects/service.py` following the implementation exemplar in `contracts/best-effort-helper-contract.md` § B3.

#### Verify

```bash
cd solune/backend

# Type-check passes
uv run pyright src/services/github_projects/service.py
# Expected: exit 0

# Lint passes
uv run ruff check src/services/github_projects/service.py
# Expected: exit 0
```

---

### Step B2 — Add unit tests for `_best_effort()`

#### Apply

Create a test file at `solune/backend/tests/unit/test_best_effort.py` with the test cases specified in `contracts/best-effort-helper-contract.md` § B6.

#### Verify

```bash
cd solune/backend

# Tests pass
uv run pytest tests/unit/test_best_effort.py -v
# Expected: all 5 test cases pass
```

---

### Step B3 — Refactor GitHub-projects service handlers

#### Apply

For each simple "try → call → log → return fallback" handler in `pull_requests.py`, `projects.py`, `copilot.py`, and `issues.py`, replace the ad-hoc try/except with a `_best_effort()` call per the migration exemplar in `contracts/best-effort-helper-contract.md` § B4.

**DO NOT** migrate:

- Handlers using `_with_fallback()` (keep as-is)
- Handlers with cascading fallback logic
- Handlers with conservative assumption returns (Tag instead)
- Handlers with retry/backoff logic

#### Verify

```bash
cd solune/backend

# No except Exception handlers remain in the target files (outside _with_fallback internals)
for f in src/services/github_projects/{pull_requests,projects,copilot,issues}.py; do
    count=$(grep -c "except Exception" "$f" 2>/dev/null || echo 0)
    echo "$f: $count remaining except Exception handlers"
done
# Expected: significant reduction (zero for simple best-effort handlers)

# Lint passes
uv run ruff check src/services/github_projects/
# Expected: exit 0

# Test suite passes (SC-006: no behaviour changes)
uv run pytest
# Expected: all tests pass

# Logging behaviour preserved (spot-check)
# Manually verify that a representative refactored method logs at the same severity
# and returns the same fallback value as before
```

---

## Per-workstream Success Criteria mapping

| Workstream | Success Criteria covered |
|---|---|
| A (Step A1) | SC-002 (BLE001 active in CI, blocks new violations) |
| A (Step A2) | FR-004 (tagged handlers have justification), FR-005 (convention documented) |
| A (Step A3) | SC-001 (zero unresolved violations), SC-003 (tagged < 15%), FR-003 (all handlers triaged) |
| A (Step A4) | SC-005 (convention discoverable in < 2 minutes) |
| B (Step B1) | FR-006 (shared helper exists), FR-007 (only catches Exception) |
| B (Step B2) | FR-009 (logging preserved — validated by test) |
| B (Step B3) | SC-004 (80% reduction in duplicate handlers), SC-006 (no behaviour changes) |
| A + B | FR-010 (independent delivery), FR-011 (test suite green) |
