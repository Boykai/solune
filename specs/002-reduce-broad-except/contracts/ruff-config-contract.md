# Ruff Configuration Contract

**Feature**: 002-reduce-broad-except
**Owners**: `solune/backend/pyproject.toml` (`[tool.ruff.lint]` block)
**Consumers**: `uv run ruff check` (local), `.github/workflows/ci.yml` lint step.

This contract specifies the exact post-condition state of the Ruff lint configuration after Workstream A. Implementation tasks must produce configuration that matches this exemplar verbatim (other than ordering of unrelated keys).

---

## C1 — `[tool.ruff.lint]` block in `solune/backend/pyproject.toml`

### Before Workstream A (current state)

```toml
[tool.ruff.lint]
select = [
    "E",    # pycodestyle errors
    "W",    # pycodestyle warnings
    "F",    # Pyflakes
    "I",    # isort
    "B",    # flake8-bugbear
    "C4",   # flake8-comprehensions
    "UP",   # pyupgrade
    "FURB", # refurb (more Pythonic alternatives)
    "PTH",  # pathlib (prefer pathlib over os.path)
    "PERF", # Perflint (performance anti-patterns)
    "RUF",  # Ruff-specific rules
]
ignore = [
    "E501",  # reason: line length enforced by ruff format, not lint
]
```

### After Workstream A

```toml
[tool.ruff.lint]
select = [
    "E",    # pycodestyle errors
    "W",    # pycodestyle warnings
    "F",    # Pyflakes
    "I",    # isort
    "B",    # flake8-bugbear
    "BLE",  # flake8-blind-except (ban broad except Exception handlers)
    "C4",   # flake8-comprehensions
    "UP",   # pyupgrade
    "FURB", # refurb (more Pythonic alternatives)
    "PTH",  # pathlib (prefer pathlib over os.path)
    "PERF", # Perflint (performance anti-patterns)
    "RUF",  # Ruff-specific rules
]
ignore = [
    "E501",  # reason: line length enforced by ruff format, not lint
]
```

**Delta**: One line added — `"BLE",  # flake8-blind-except (ban broad except Exception handlers)` — inserted after `"B"` in alphabetical order.

### Verification

```bash
cd solune/backend

# Rule is active
uv run ruff check src/ --select BLE001 --statistics
# Expected: ~568 violations before triage; 0 violations after triage

# Full lint still passes (after triage)
uv run ruff check
# Expected: exit 0
```

---

## C2 — No project-level ignore for BLE001

BLE001 MUST NOT appear in the `ignore` list. Suppressions are per-line only, using the `# noqa: BLE001 — reason:` format defined in `tag-convention-contract.md`.

**Forbidden configuration**:

```toml
# DO NOT DO THIS
ignore = [
    "E501",
    "BLE001",  # ← NEVER suppress globally
]
```

**Forbidden configuration (per-file)**:

```toml
# DO NOT DO THIS
[tool.ruff.lint.per-file-ignores]
"src/services/**" = ["BLE001"]  # ← NEVER suppress per-directory
```

---

## C3 — CI integration

No changes to `.github/workflows/ci.yml` are required. The existing lint step runs `uv run ruff check` which reads `pyproject.toml` at invocation time and will automatically enforce BLE001 after the `select` change.
