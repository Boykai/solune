# Burn-Down Gate Contract

**Feature**: 001-backend-pyright-strict
**Owners**: `solune/scripts/pre-commit` (local), `.github/workflows/ci.yml` (CI).
**Consumers**: every backend PR.
**Activated**: Phase 4.

This contract specifies the inputs, behaviour, and exit semantics of the gate that prevents `# pyright: basic` from leaking into the strict floor and that publishes the global pragma count.

---

## G1 — Inputs

| Source | Local pre-commit | CI |
|---|---|---|
| Set of changed files | `git diff --cached --name-only --diff-filter=ACM` | `git diff origin/${{ github.base_ref }}...HEAD --name-only --diff-filter=ACM` |
| Repo working tree | current checkout | current checkout |

---

## G2 — Behaviour

The gate runs in two stages, in order. Stage 1 may exit non-zero; stage 2 always runs and is informational.

### Stage 1 — Floor violation check (blocking)

Pseudocode:

```bash
violations=$(<changed-files>
  | grep -E '^solune/backend/src/(api|models|services/agents)/[^/]+(/.*)?\.py$' \
  | xargs -r grep -lE '^# pyright: basic[[:space:]]*$' 2>/dev/null \
  || true)

if [ -n "$violations" ]; then
  echo "ERROR: # pyright: basic is not allowed inside the strict floor."
  echo "Offending files:"
  printf '  %s\n' $violations
  echo
  echo "Remove the pragma and either fix the strict-mode errors or remove"
  echo "the file from the strict floor by amending [tool.pyright] strict."
  exit 1
fi
```

### Stage 2 — Pragma count line (non-blocking)

```bash
count=$(grep -rEc '^# pyright: basic[[:space:]]*$' solune/backend/src \
        | awk -F: '{s+=$2} END{print s+0}')
echo "# pyright: basic count: $count"
```

The literal output line `# pyright: basic count: N` (no leading whitespace, no surrounding text) MUST appear in every CI build log so SC-006 can be satisfied by greppable logs.

---

## G3 — Exit semantics

| Stage | Outcome | Pre-commit exit | CI step exit |
|---|---|---|---|
| 1 | No floor violation | 0 → continue | 0 → continue |
| 1 | Floor violation found | non-zero → block commit | non-zero → fail job |
| 2 | always | 0 | 0 |

Stage 1's non-zero exit MUST occur after the existing Pyright invocation in CI so that ordering does not mask Pyright errors behind gate errors when a PR has both.

---

## G4 — Bypass policy

- `git commit --no-verify` skips stage 1 locally; CI re-runs stage 1 and fails the PR. There is no PR-side bypass.
- `git push --no-verify` is irrelevant to this gate (no pre-push hook is added).

---

## G5 — Insertion sites

### Local pre-commit (`solune/scripts/pre-commit`)

A new section `# Pyright pragma gate (Phase 4)` is appended immediately before the script's existing exit/summary block. The section guards itself with the existing `STAGED_BACKEND_CHANGES` variable so it only runs when backend files are staged.

### CI (`.github/workflows/ci.yml`)

A new YAML step is added to the `backend` job *after* the existing `Type check with pyright` step (line 50–51). Step name: `Pyright pragma gate`. Stage 2 (the count line) runs unconditionally; stage 1 runs only when `github.event_name == 'pull_request'` (so default-branch builds still print the count without re-checking the diff).

---

## G6 — Failure-message contract

A floor-violation failure message MUST contain:

1. The literal string `# pyright: basic is not allowed inside the strict floor.` (so reviewers can grep PR logs for the canonical phrase).
2. One indented line per offending file, prefixed with two spaces.
3. A pointer to the remediation: either fix strict errors or amend `[tool.pyright] strict`.

The exact format above (G2 stage 1) MUST be reproduced verbatim by both pre-commit and CI implementations to keep developer experience uniform.

---

## G7 — Acceptance test (Phase 4 verification)

After implementation, run two canary commits on a throwaway branch:

```bash
# Canary 1 — must FAIL pre-commit and CI
echo '# pyright: basic' >> solune/backend/src/api/health.py  # arbitrary floor file
echo '# reason: canary' >> solune/backend/src/api/health.py
git add -p solune/backend/src/api/health.py
git commit -m "canary: floor violation"   # pre-commit MUST exit 1

# Canary 2 — must PASS but increment count
echo '# pyright: basic' >> solune/backend/src/utils.py        # arbitrary non-floor file
echo '# reason: canary' >> solune/backend/src/utils.py
git add -p solune/backend/src/utils.py
git commit -m "canary: count bump"         # pre-commit exits 0; CI prints incremented count
```

Both canaries are reverted before the Phase 4 PR merges.
