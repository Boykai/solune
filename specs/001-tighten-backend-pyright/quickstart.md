# Quick Start: Tighten Backend Pyright

**Feature**: 001-tighten-backend-pyright | **Date**: 2026-04-18

## Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) package manager
- Backend dependencies installed: `cd solune/backend && uv sync`

## Verify Current State

```bash
cd solune/backend

# Check current pyright config
grep -A 10 '\[tool.pyright\]' pyproject.toml

# Run pyright (should pass at standard mode)
uv run pyright src

# Run pyright on tests (should pass at off mode)
uv run pyright -p pyrightconfig.tests.json

# Count existing type: ignore comments
grep -rn "type: ignore" src/ | wc -l

# Count existing pyright pragmas (should be 0 before Phase 3)
grep -rn "pyright: basic" src/ | wc -l
```

## Phase 1: Apply Safety-Net Settings

### Step 1 — Update config

Add to `pyproject.toml` `[tool.pyright]`:

```toml
reportUnnecessaryTypeIgnoreComment = "error"
reportMissingParameterType = "error"
reportUnknownParameterType = "error"
reportUnknownMemberType = "warning"
```

Add to `pyrightconfig.tests.json`:

```json
"reportUnnecessaryTypeIgnoreComment": "error"
```

### Step 2 — Fix findings

```bash
uv run pyright src 2>&1 | head -50   # See new diagnostics
# Fix each finding inline (add types, remove redundant ignores)
```

### Step 3 — Verify

```bash
uv run pyright src                           # Must exit 0
uv run pyright -p pyrightconfig.tests.json   # Must exit 0
```

## Phase 2: Establish Strict Floor

### Step 1 — Baseline error count

```bash
# Check errors per protected tree (informational, not committed)
uv run pyright --typeCheckingMode strict src/api 2>&1 | tail -5
uv run pyright --typeCheckingMode strict src/models 2>&1 | tail -5
uv run pyright --typeCheckingMode strict src/services/agents 2>&1 | tail -5
```

### Step 2 — Fix errors

Common patterns:

- **Missing return types on `Depends()` functions**: Add `-> ReturnType` annotations
- **Untyped WebSocket payloads**: Use `TypedDict` or Pydantic model for `receive_json()`
- **`aiosqlite.Row` access**: Cast or wrap with typed accessor
- **Incomplete stubs**: Augment `src/typestubs/` as needed

### Step 3 — Declare strict floor

Add to `pyproject.toml` `[tool.pyright]`:

```toml
strict = ["src/api", "src/models", "src/services/agents"]
```

### Step 4 — Verify

```bash
uv run pyright src   # Must exit 0 with strict floor active
```

## Phase 3: Flip to Global Strict

### Step 1 — Change global mode

In `pyproject.toml`:

```toml
typeCheckingMode = "strict"
```

### Step 2 — Add legacy pragmas

For each file that fails, add at line 1:

```python
# pyright: basic  — reason: <short justification>
```

### Step 3 — Create ADR

Create `solune/backend/docs/decisions/001-pyright-strict-legacy-opt-outs.md`
listing every downgraded file with owner and reason.

### Step 4 — Verify

```bash
uv run pyright src   # Must exit 0
# Every # pyright: basic file must be in the ADR
```

## Phase 4: Ongoing Burn-Down

### Monitor downgrade count

```bash
grep -rn "pyright: basic" src/ | wc -l   # Track this number
```

### Verify strict floor integrity

```bash
# Must return empty (no pragmas in protected packages)
grep -rn "pyright: basic" src/api/ src/models/ src/services/agents/
```

### Remove a legacy pragma

1. Fix all strict errors in the target file
2. Remove the `# pyright: basic` pragma
3. Remove the file from the ADR table
4. Run `uv run pyright src` — must still exit 0

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `reportUnknownMemberType` noise on githubkit | Incomplete stubs | Augment `src/typestubs/githubkit/`; setting is `"warning"` so non-blocking |
| `reportUnnecessaryTypeIgnoreComment` error | `# type: ignore` is now redundant | Remove the comment; the underlying issue was fixed |
| Strict-floor file fails in CI | Missing type annotation | Add the annotation; no pragma allowed in strict floor |
| New file in `src/api/` missing types | Strict floor enforces full typing | Annotate all parameters and return types |
