# Pragma Contract

**Feature**: 001-backend-pyright-strict
**Owners**: every Python module under `solune/backend/src/` that is downgraded in Phase 3.
**Consumers**: Pyright (parses the pragma); the burn-down gate (greps for it); the Phase 3 ADR (enumerates files carrying it).

---

## P1 — Permitted pragma forms

Exactly one form is permitted as a per-file downgrade:

```python
# pyright: basic
# reason: <single-line justification>
```

The two lines MUST be consecutive. The `reason:` line MAY be `# reason: <text>` *or* `# reason: <text> — owner: <github-handle>` (the optional owner suffix mirrors the Phase 3 ADR ownership column).

---

## P2 — Forbidden pragma forms

The following are explicitly rejected; the burn-down gate (`burn-down-gate-contract.md`) and reviewer policy reject them:

- `# pyright: off` — too aggressive; disables all analysis on the file.
- `# pyright: basic — reason: …` (single line, em-dash): rejected per Phase 0 research R1 (Pyright parser may not tolerate trailing same-line text). The burn-down gate's regex `^# pyright: basic\s*$` rejects this form.
- `# pyright: basic` *without* a following `# reason:` line: silent downgrades are not allowed; the gate flags missing reason as a `WARNING:` line in CI (does not fail the build, but is visible in review).
- `# type: ignore` (whole-file, hand-rolled equivalent): does not satisfy the contract; only individual-line `# type: ignore[<rule>]` is permitted, and only with a `— reason: …` suffix matching the existing repo style (E4).

---

## P3 — Placement rules

The pragma MUST be the first non-blank, non-shebang, non-encoding, non-docstring line of the file. Concretely:

```python
#!/usr/bin/env python                  # optional shebang (rare in this repo)
# -*- coding: utf-8 -*-                # optional encoding (rare; default is UTF-8)
"""Module docstring, if present."""    # optional, single-line or triple-quoted

# pyright: basic                       # ← pragma here
# reason: <text>

from __future__ import annotations     # imports follow
…
```

If the docstring is multi-line, the pragma goes on the line immediately after the closing `"""`.

---

## P4 — Floor exclusivity

The pragma MUST NOT appear in any file matching the glob:

```text
solune/backend/src/api/**/*.py
solune/backend/src/models/**/*.py
solune/backend/src/services/agents/**/*.py
```

This is the strict floor. The burn-down gate enforces this in pre-commit and CI (`burn-down-gate-contract.md`).

---

## P5 — Lifecycle

A pragma's lifecycle is:

1. **Add** (Phase 3 PR or follow-up legacy-debt PR): file fails strict; pragma + reason added; ADR row added.
2. **Track** (every CI build): the burn-down count line records the file as part of `N`.
3. **Remove** (refactor PR): file made strict-clean; pragma + reason both removed in one commit; ADR row removed in the same PR.

A pragma MUST NOT be added without a corresponding ADR row in the same PR. The reviewer rejects PRs that drift the two.

---

## P6 — Re-verification of pre-existing `# type: ignore` (FR-012)

Before Phase 3 lands its pragmas, run:

```bash
cd solune/backend && uv run pyright 2>&1 | grep reportUnnecessaryTypeIgnoreComment
```

For each match at the two known sites (`agent_provider.py:501`, `plan_agent_provider.py:207`):

- If the comment is flagged, remove it in the Phase 3 PR.
- If it is not flagged, leave it untouched.

The pragmas added by Phase 3 do not affect this check; the check runs against the *strict* analysis state, which is the Phase 3 PR's pre-pragma intermediate state.
