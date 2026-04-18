# Implementation Plan: Tighten Backend Pyright (Standard → Strict, Gradually)

**Branch**: `001-tighten-backend-pyright` | **Date**: 2026-04-18 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-tighten-backend-pyright/spec.md`

## Summary

Gradually raise backend Pyright type-checking from `standard` to `strict` in four
phased increments. Phase 1 adds safety-net diagnostic rules without changing the
global mode. Phase 2 declares a strict floor on the three cleanest package trees
(`src/api`, `src/models`, `src/services/agents`). Phase 3 flips the global default
to `strict` and adds explicit `# pyright: basic` pragmas to legacy modules that
cannot yet pass. Phase 4 installs a CI gate preventing new pragmas in the strict
floor and tracks the remaining downgrade count per build. Each phase lands as one
or a few small PRs so diffs stay reviewable and regressions stay isolated.

## Technical Context

**Language/Version**: Python 3.13 (pyright `pythonVersion = "3.13"`)
**Primary Dependencies**: FastAPI, githubkit, aiosqlite, agent-framework-github-copilot SDK
**Storage**: aiosqlite (SQLite via async wrapper)
**Testing**: pytest (pyright tests config stays `typeCheckingMode = "off"`)
**Target Platform**: Linux server (GitHub Actions CI runner)
**Project Type**: Web application (backend only; frontend is out of scope)
**Performance Goals**: N/A — tooling/config change, no runtime impact
**Constraints**: Zero new pyright errors after each phase lands; no mega-PR
**Scale/Scope**: ~183 Python source files in `src/`; 23 in `src/api`, 29 in `src/models`, 4 in `src/services/agents`; ~13 in `src/services/github_projects`, ~12 in `src/services/copilot_polling`

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| I. Specification-First | ✅ Pass | `spec.md` contains three prioritized user stories (P1–P3) with Given-When-Then acceptance scenarios |
| II. Template-Driven | ✅ Pass | All artifacts follow canonical `.specify/templates/` structure |
| III. Agent-Orchestrated | ✅ Pass | Single-responsibility agent (`speckit.plan`) producing well-defined outputs |
| IV. Test Optionality | ✅ Pass | Spec does not mandate new tests; canary verification tests are lightweight CI assertions, not unit tests. Test pyright config stays `off` |
| V. Simplicity / DRY | ✅ Pass | No new abstractions; config changes in `pyproject.toml` and file-level pragmas only. Grep gate preferred over new tooling |
| VI. Phase-Based Execution | ✅ Pass | Four explicit phases map directly to user stories P1–P3 plus burn-down |
| VII. Independent Stories | ✅ Pass | Each user story (US-1 baseline, US-2 strict floor, US-3 audit/visibility) is independently implementable and testable |
| Constitution Supremacy | ✅ Pass | No conflicts between constitution and this plan |

**Gate result**: PASS — no violations; Complexity Tracking section is empty.

## Project Structure

### Documentation (this feature)

```text
specs/001-tighten-backend-pyright/
├── plan.md              # This file
├── research.md          # Phase 0 output — decisions and rationale
├── data-model.md        # Phase 1 output — entity descriptions (config-centric)
├── quickstart.md        # Phase 1 output — developer quick-start for each phase
├── contracts/           # Phase 1 output — contract definitions
│   └── pyright-policy.md
└── tasks.md             # Phase 2 output (/speckit.tasks — NOT created here)
```

### Source Code (repository root)

```text
solune/backend/
├── pyproject.toml                   # [tool.pyright] — single source of truth
├── pyrightconfig.tests.json         # Tests-only pyright config (mode stays off)
├── src/
│   ├── api/                         # Protected strict floor (Phase 2)
│   ├── models/                      # Protected strict floor (Phase 2)
│   ├── services/
│   │   ├── agents/                  # Protected strict floor (Phase 2)
│   │   ├── github_projects/         # Expected legacy opt-out (Phase 3)
│   │   ├── copilot_polling/         # Expected legacy opt-out (Phase 3)
│   │   ├── chat_agent.py            # Expected legacy opt-out (Phase 3)
│   │   ├── agent_provider.py        # Has existing type: ignore (re-verify)
│   │   └── plan_agent_provider.py   # Has existing type: ignore (re-verify)
│   ├── main.py                      # Expected legacy opt-out (Phase 3)
│   └── typestubs/                   # May need augmentation (Phase 2)
│       ├── githubkit/
│       ├── copilot/
│       └── agent_framework_github_copilot/
├── docs/decisions/                  # ADR for Phase 3 debt record
└── tests/                           # Excluded from strict (mode = off)
```

**Structure Decision**: Web application layout. Only the `solune/backend/` subtree
is affected. All config changes are in `pyproject.toml` `[tool.pyright]` and
`pyrightconfig.tests.json`. No new directories created except `docs/decisions/`
for the Phase 3 ADR.

## Complexity Tracking

> No constitution violations to justify. Table is intentionally empty.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| *(none)*  | —          | —                                   |

---

## Phase 0: Research & Decisions

*See [research.md](./research.md) for full details.*

### Key Decisions

1. **Phased rollout** over single mega-PR — lower review burden, isolated regressions.
2. **`reportUnknownMemberType = "warning"`** (not `"error"`) in Phase 1 — githubkit and aiosqlite stubs are incomplete; promote to error in Phase 4 once backlog is clear.
3. **`strict = [...]` as floor contract** — survives the Phase 3 global flip; makes protected scope explicit and auditable.
4. **`# pyright: basic` pragmas** (not `# pyright: off`) for legacy opt-outs — preserves baseline checking on legacy files and follows the repo's suppression-with-reason convention.
5. **Tests stay `typeCheckingMode = "off"`** — heavy mocking creates low-value noise under strict; only `reportUnnecessaryTypeIgnoreComment` is mirrored.
6. **Grep CI gate** for pragma control — no new tooling; `grep -R "pyright: basic" src/ | wc -l` per build tracks count; adding a pragma inside the strict floor fails CI.

## Phase 1: Safety-Net Settings (maps to User Story 1)

### 1.1 Config Changes

**`pyproject.toml` `[tool.pyright]`** — add these lines after existing settings:

```toml
reportUnnecessaryTypeIgnoreComment = "error"
reportMissingParameterType = "error"
reportUnknownParameterType = "error"
reportUnknownMemberType = "warning"
```

**`pyrightconfig.tests.json`** — add:

```json
"reportUnnecessaryTypeIgnoreComment": "error"
```

### 1.2 Fix Inline Findings

- Run `cd solune/backend && uv run pyright src` — expect ≤~20 new diagnostics.
- Fix findings inline (add type annotations, remove redundant suppressions).
- Re-verify the two existing `type: ignore` comments:
  - `agent_provider.py:501` — `reportGeneralTypeIssues` for SDK preview field
  - `plan_agent_provider.py:207` — `reportGeneralTypeIssues` for SDK preview field
  - `reportUnnecessaryTypeIgnoreComment = "error"` will flag them if redundant.

### 1.3 Acceptance Gate

- `uv run pyright src` exits 0 with no errors.
- `uv run pyright -p pyrightconfig.tests.json` exits 0.
- Canary: a redundant `# type: ignore` on a clean line must fail CI.

## Phase 2: Strict Floor (maps to User Story 2)

### 2.1 Baseline Error Count

For each protected tree, run pyright with a temporary local `strict` override
and count errors:

```bash
# Temporary local test (not committed)
cd solune/backend
uv run pyright --typeCheckingMode strict src/api 2>&1 | tail -1
uv run pyright --typeCheckingMode strict src/models 2>&1 | tail -1
uv run pyright --typeCheckingMode strict src/services/agents 2>&1 | tail -1
```

### 2.2 Fix Errors Per Tree

Anticipated hotspots from the issue:

| File | Expected Issue | Fix Approach |
|------|---------------|--------------|
| `src/api/chat.py` | `Depends()` return types | Add explicit return-type annotations to dependency functions |
| `src/api/projects.py` | WebSocket payload types | Type WebSocket `receive_json()` payloads via TypedDict or Pydantic model |
| `src/services/agents/service.py:71` | `aiosqlite.Row` → typed access | Cast or wrap `Row` results with typed accessor / TypedDict |
| `src/typestubs/` | Incomplete stubs for githubkit/copilot | Augment stubs as needed for strict compatibility |

### 2.3 Declare Strict Floor

Add to `pyproject.toml` `[tool.pyright]`:

```toml
strict = ["src/api", "src/models", "src/services/agents"]
```

**Invariant**: No file inside the strict floor may use `# pyright: basic` or any
file-level downgrade. The Phase 4 CI gate enforces this.

### 2.4 Acceptance Gate

- `uv run pyright src` exits 0 (strict floor files now checked at strict level).
- Canary: `def foo(x):` added inside `src/api/` must fail CI.

## Phase 3: Global Strict + Legacy Opt-Out (maps to User Story 3)

### 3.1 Flip Global Default

In `pyproject.toml` `[tool.pyright]`:

```toml
typeCheckingMode = "strict"
```

### 3.2 Add Legacy Pragmas

For each file that fails under strict, add at line 1:

```python
# pyright: basic  — reason: <short justification>
```

Expected candidates (~4–5 modules):

- `src/services/github_projects/**` (13 files) — deep githubkit integration, incomplete stubs
- `src/services/copilot_polling/**` (12 files) — copilot SDK partial typing
- `src/main.py` — FastAPI app assembly, dynamic imports
- `src/services/chat_agent.py` — complex agent orchestration

### 3.3 Create ADR

Create `solune/backend/docs/decisions/001-pyright-strict-legacy-opt-outs.md`:

- Title, date, status (Accepted)
- Context: why strict was adopted
- Decision: `# pyright: basic` pragmas as documented escape hatch
- Table of downgraded modules with owner and reason
- Consequences: debt is visible, each removal is a small PR

### 3.4 Re-verify Existing Suppressions

- `agent_provider.py:501` and `plan_agent_provider.py:207` — if
  `reportUnnecessaryTypeIgnoreComment` flags them as redundant under strict,
  remove the `# type: ignore` comments.

### 3.5 Acceptance Gate

- `uv run pyright src` exits 0.
- 100% of source files run under strict unless they carry `# pyright: basic`.
- Every `# pyright: basic` file is listed in the ADR.

## Phase 4: Burn-Down (maps to ongoing maintenance)

### 4.1 CI Pragma Gate

Add a step in CI (after pyright passes):

```bash
# Fail if any file inside strict floor has a downgrade pragma
if grep -rn "pyright: basic" src/api/ src/models/ src/services/agents/; then
  echo "ERROR: pyright: basic pragma found inside strict floor"
  exit 1
fi
```

### 4.2 Downgrade Count Reporting

Add a step in CI:

```bash
echo "Pyright downgrades remaining: $(grep -rn 'pyright: basic' src/ | wc -l)"
```

### 4.3 Future Promotion

- Once all `# pyright: basic` pragmas in `src/services/github_projects/` and
  `src/services/copilot_polling/` are removed, promote
  `reportUnknownMemberType` from `"warning"` to `"error"`.

### 4.4 Acceptance Gate

- No new `# pyright: basic` inside strict floor merges.
- Downgrade count trends downward over time.

---

## Dependency Order

```text
Phase 1 (US-1)  →  Phase 2 (US-2)  →  Phase 3 (US-3)  →  Phase 4 (ongoing)
     │                    │                    │                    │
     │                    │                    │                    └─ CI gate + count
     │                    │                    └─ Global strict + ADR
     │                    └─ Strict floor on api/models/agents
     └─ Safety-net rules + inline fixes
```

Each phase is a prerequisite for the next. Within Phase 2, trees can be fixed
independently (one PR per tree: `src/api`, `src/models`, `src/services/agents`).

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| githubkit stubs generate excessive unknowns | High | Medium | `reportUnknownMemberType = "warning"` (not error) in Phase 1; augment typestubs in Phase 2 |
| Existing `type: ignore` comments become redundant | Medium | Low | `reportUnnecessaryTypeIgnoreComment = "error"` catches them automatically |
| Phase 3 legacy list is larger than expected | Low | Medium | Each file gets `# pyright: basic` with reason; ADR tracks them; burn-down is explicit |
| Strict floor breaks on FastAPI `Depends()` patterns | Medium | Medium | Add explicit return-type annotations to DI functions; well-known FastAPI pattern |
| Third-party SDK updates change stub completeness | Low | Low | Re-run pyright after dependency bumps; stubs in `src/typestubs/` are repo-controlled |
