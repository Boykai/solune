# Quickstart: Verifying Each Phase

**Feature**: 001-backend-pyright-strict
**Audience**: implementer of the per-phase PRs and reviewers.

This document gives copy-pasteable verification recipes for each of the four phases. Each recipe is the minimum sequence required to satisfy the spec's Acceptance Scenarios and Success Criteria for that phase.

All commands assume `pwd == /root/repos/solune` (the workspace root) unless stated otherwise.

---

## Phase 1 — Safety-net settings

### Apply

Edit `solune/backend/pyproject.toml` `[tool.pyright]` block to match `contracts/pyright-config-contract.md` § C1 (Phase 1 exemplar). Edit `solune/backend/pyrightconfig.tests.json` to match § C2 (Phase 1 exemplar).

### Verify

```bash
cd solune/backend
uv run pyright                                # MUST exit 0 (FR-003)
uv run pyright -p pyrightconfig.tests.json    # MUST exit 0
uv run pyright --outputjson \
  | jq -e '[.generalDiagnostics[] | select(.severity == "error")] | length == 0'
```

If the first command surfaces ≤ ~20 new findings, fix them inline in the same PR and re-run. Anticipated findings: untyped private helper parameters, `lambda x:` defaulted callbacks, possibly redundant `# type: ignore` comments.

### Canary (Acceptance Scenario US1.1 / US1.2)

```bash
git checkout -b canary/phase-1
cat > solune/backend/src/canary.py <<'EOF'
def helper(x):
    pass
EOF
cd solune/backend && uv run pyright src/canary.py     # MUST exit non-zero
                                                       # error: reportMissingParameterType
git checkout - && git branch -D canary/phase-1
```

---

## Phase 2 — Strict floor

### Baseline measurement (do NOT commit this step)

```bash
cd solune/backend
# Temporarily prepend strict = [...] to pyproject.toml
python - <<'PY'
import pathlib, re
p = pathlib.Path("pyproject.toml")
text = p.read_text()
text = text.replace(
    '[tool.pyright]',
    '[tool.pyright]\nstrict = ["src/api", "src/models", "src/services/agents"]'
)
p.write_text(text)
PY
uv run pyright --outputjson \
  | jq '[.generalDiagnostics[] | select(.severity == "error") |
         .file] | group_by(. | sub("^.*/src/"; "src/") |
         split("/")[0:3] | join("/")) |
         map({tree: .[0] | sub("^.*/src/"; "src/") |
              split("/")[0:3] | join("/"), count: length})'
git checkout -- pyproject.toml   # discard the temporary edit
```

Record per-tree error counts in the PR description. Order tree-by-tree PRs cheapest-first (Phase 0 research R5).

### Apply (per tree, then once green for all three)

For each tree (`src/models` → `src/api` → `src/services/agents`, ordered by Phase 2 baseline):

1. Fix the strict-mode errors. Hotspots from Phase 0 R5: `Depends()` return types in `src/api/chat.py`, WebSocket payloads in `src/api/projects.py`, `aiosqlite.Row` access in `src/services/agents/.../service.py:71`.
2. If a third-party stub gap is the cause, augment `solune/backend/src/typestubs/` (R6); do *not* add `# type: ignore` inside the floor.
3. Re-run `uv run pyright` until clean.

When all three trees are green, add to `[tool.pyright]`:

```toml
strict = ["src/api", "src/models", "src/services/agents"]
```

### Verify

```bash
cd solune/backend
uv run pyright                                # MUST exit 0
uv run pyright --outputjson \
  | jq -e '[.generalDiagnostics[] | select(.severity == "error")] | length == 0'

# Floor exclusivity (no per-file pragma in floor — FR-005)
! grep -rE '^# pyright:\s*(basic|off)\b' \
    solune/backend/src/api solune/backend/src/models solune/backend/src/services/agents
```

### Canary (Acceptance Scenario US2.2)

```bash
git checkout -b canary/phase-2
echo "def regress(x): pass" >> solune/backend/src/api/health.py
cd solune/backend && uv run pyright src/api/health.py   # MUST exit non-zero
git checkout - && git branch -D canary/phase-2
```

---

## Phase 3 — Global strict + legacy opt-out

### Step 1 — Re-verify existing `# type: ignore` (FR-012)

```bash
cd solune/backend
# Pre-pragma intermediate state: flip mode to strict in a worktree-only edit
sed -i.bak 's/typeCheckingMode = "standard"/typeCheckingMode = "strict"/' pyproject.toml
uv run pyright 2>&1 | grep -E 'agent_provider\.py:501|plan_agent_provider\.py:207'
mv pyproject.toml.bak pyproject.toml
```

If either site is flagged with `reportUnnecessaryTypeIgnoreComment`, queue the deletion as part of the Phase 3 PR. Otherwise leave both untouched.

### Step 2 — Enumerate failing modules

```bash
cd solune/backend
sed -i.bak 's/typeCheckingMode = "standard"/typeCheckingMode = "strict"/' pyproject.toml
uv run pyright --outputjson \
  | jq -r '.generalDiagnostics[] | select(.severity == "error") | .file' \
  | sort -u > /tmp/phase3-failing-files.txt
mv pyproject.toml.bak pyproject.toml
cat /tmp/phase3-failing-files.txt
```

This list is the canonical set of files that need `# pyright: basic` in Phase 3.

### Step 3 — Add pragmas + ADR

For each file in `/tmp/phase3-failing-files.txt`, add the pragma per `contracts/pragma-contract.md` § P1 + P3:

```python
# pyright: basic
# reason: <one-line justification>
```

Create `solune/docs/decisions/007-backend-pyright-strict-downgrades.md` per `data-model.md` § E5 with one row per file. Then commit `typeCheckingMode = "strict"` in `pyproject.toml`.

### Verify

```bash
cd solune/backend
uv run pyright                                # MUST exit 0

# ADR consistency (data-model.md cross-entity invariant 2)
adr_files=$(awk -F'|' '/solune\/backend\/src/{gsub(/^[ \t]+|[ \t]+$/,"",$2); print $2}' \
  ../docs/decisions/007-backend-pyright-strict-downgrades.md | sort -u)
fs_files=$(grep -rl '^# pyright: basic$' src/ | sort -u)
diff <(echo "$adr_files") <(echo "$fs_files")  # MUST be empty
```

### Canary (Acceptance Scenario US3.2)

```bash
# Removing the pragma surfaces strict errors in just that module.
git checkout -b canary/phase-3
target=$(head -n1 /tmp/phase3-failing-files.txt)
sed -i '/^# pyright: basic$/d; /^# reason:/d' "$target"
cd solune/backend && uv run pyright "$target"  # MUST exit non-zero
git checkout - && git branch -D canary/phase-3
```

---

## Phase 4 — Burn-down gate

### Apply

1. Append the gate block from `contracts/burn-down-gate-contract.md` § G2 to `solune/scripts/pre-commit` at the insertion site described in § G5.
2. Add the `Pyright pragma gate` step to `.github/workflows/ci.yml` after the existing `Type check with pyright` step (line 51), per § G5.
3. Re-run `solune/scripts/setup-hooks.sh` locally so the new pre-commit content is mirrored into `.git/hooks/`.

### Verify

```bash
# Stage 2 output (count line) appears
solune/scripts/pre-commit 2>&1 | grep -E '^# pyright: basic count: [0-9]+$'

# Run the canary script from contracts/burn-down-gate-contract.md § G7
# Canary 1 MUST fail; Canary 2 MUST pass and increment N.
```

### Optional follow-up — reportUnknownMemberType promotion

When the legacy backlog is empty (`# pyright: basic count: 0`):

```toml
# in [tool.pyright]
reportUnknownMemberType = "error"   # was "warning"
```

```bash
cd solune/backend && uv run pyright   # MUST still exit 0 (SC-007)
```

---

## Per-phase Success Criteria mapping

| Phase | Success Criteria covered |
|---|---|
| 1 | SC-001 (new untyped params/redundant ignores blocked), SC-004 (zero error-severity diagnostics post-phase) |
| 2 | SC-002 (strict floor 100 % strict, zero per-file downgrades inside it), SC-004 |
| 3 | SC-003 (global strict + ADR enumerates pragmas), SC-004 |
| 4 | SC-006 (count line + monotonic non-increase), SC-007 (post-promotion strict still green) |
| 1 → 3 cumulative | SC-005 (≤ 25 % feedback-loop wall-clock regression — measured per Phase 0 R9) |
