# Implementation Plan: Harden Phase 1 — Critical Bug Fixes

**Branch**: `copilot/fix-critical-bug-issues` | **Date**: 2026-04-10 | **Spec**: [#1227](https://github.com/Boykai/solune/issues/1227)
**Input**: Parent issue #1227 — Harden Phase 1: Fix critical bugs in pipeline state store, agent lifecycle management, and agent preview extraction.

## Summary

Harden Solune's reliability by fixing three critical bugs in the backend. No new features — only correctness fixes, regression tests, and validation hardening for existing code paths.

| Bug | File | Root Cause | Fix |
|-----|------|-----------|-----|
| 1.1 | `pipeline_state_store.py` | `_project_launch_locks` was an unbounded `dict[str, asyncio.Lock]` that grows indefinitely | Replace with `BoundedDict(maxlen=10_000)` with LRU touch |
| 1.2 | `agents/service.py` | `update_agent()` did not set `lifecycle_status = pending_pr` for updated local agents | Set `PENDING_PR` in all 3 SQL persistence paths |
| 1.3 | `agents/service.py` | `_extract_agent_preview()` did not validate `tools` field type (e.g. `tools: "read"` passed through) | Add `isinstance(tools, list)` guard returning `None`; harden element validation |

## Technical Context

**Language/Version**: Python >=3.12 (pyright targets 3.13)
**Primary Dependencies**: FastAPI, aiosqlite, Pydantic v2
**Storage**: SQLite via aiosqlite (agent configs), in-memory `BoundedDict` caches (pipeline state)
**Testing**: pytest with `asyncio_mode=auto`, coverage threshold 75%
**Target Platform**: Linux server (containerized)
**Project Type**: Web application (Python backend + TypeScript frontend)
**Performance Goals**: No regressions; bounded memory in long-running instances
**Constraints**: All fixes must be backward-compatible; no schema migrations required
**Scale/Scope**: 3 targeted bug fixes across 2 source files, with regression tests

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Specification-First | ✅ PASS | Bugs are specified in parent issue #1227 with clear descriptions |
| II. Template-Driven Workflow | ✅ PASS | This plan follows `plan-template.md` structure |
| III. Agent-Orchestrated Execution | ✅ PASS | Plan agent produces plan; implement agent will execute |
| IV. Test Optionality | ✅ PASS | Regression tests are warranted for bug fixes to prevent recurrence |
| V. Simplicity and DRY | ✅ PASS | Fixes use existing `BoundedDict` utility; no new abstractions |

**Gate Result**: PASS — no violations. Proceed to Phase 0.

## Project Structure

### Documentation (this feature)

```text
plan.md                  # This file (speckit.plan output)
```

### Source Code (repository root)

```text
solune/backend/
├── src/
│   ├── utils.py                           # BoundedDict utility (existing, no changes needed)
│   └── services/
│       ├── pipeline_state_store.py         # Bug 1.1: _project_launch_locks fix
│       └── agents/
│           └── service.py                  # Bug 1.2: update_agent() lifecycle + Bug 1.3: _extract_agent_preview()
└── tests/
    └── unit/
        ├── test_pipeline_state_store.py    # Bug 1.1 regression tests
        └── test_agents_service.py          # Bug 1.2 + 1.3 regression tests
```

**Structure Decision**: Existing web application structure. All changes target `solune/backend/` — no frontend or infrastructure changes.

## Complexity Tracking

> No Constitution Check violations — this section is intentionally empty.

---

## Phase 0: Research

### R1: BoundedDict Suitability for Lock Cache

**Decision**: Use `BoundedDict` from `src.utils` as the bounded LRU container for `_project_launch_locks`.

**Rationale**: `BoundedDict` is already used throughout `pipeline_state_store.py` for other caches (`_pipeline_states`, `_issue_main_branches`, `_issue_sub_issue_map`, `_agent_trigger_inflight`). It wraps `OrderedDict` with a configurable `maxlen`, supports `touch()` for LRU-style refresh, and evicts the oldest entry when capacity is exceeded. Using it for locks provides consistent behavior with the other caches.

**Alternatives considered**:

- `functools.lru_cache`: Not suitable — LRU cache wraps function calls, not dict-like access patterns; harder to test and introspect.
- `cachetools.LRUCache`: External dependency; unnecessary when `BoundedDict` already exists.
- Manual `OrderedDict` with size cap: Duplicates `BoundedDict` logic; violates DRY.

### R2: Agent Lifecycle Status in update_agent()

**Decision**: Set `lifecycle_status = AgentStatus.PENDING_PR.value` in all three SQL persistence branches within `update_agent()`.

**Rationale**: The `update_agent()` method has three distinct persistence paths depending on agent state:

1. **Non-repo agent** (line 1230): `UPDATE` existing `agent_configs` row → must set `lifecycle_status`
2. **Repo agent with existing local row** (line 1259): `UPDATE` with additional fields → must set `lifecycle_status`
3. **Repo agent without local row** (line 1286): `INSERT` new `agent_configs` row → must set `lifecycle_status`

All three paths must set `lifecycle_status = 'pending_pr'` because in every case a PR has been opened (or will be opened). The returned `Agent` object (line 1326) correctly sets `status=AgentStatus.PENDING_PR`, but if the database rows are not also updated, subsequent reads from the database will return stale status.

**Alternatives considered**:

- Setting status only on the returned `Agent` object: Insufficient — database reads bypass the in-memory object and would show stale `active` status.
- Adding a post-commit hook: Over-engineered for a simple field assignment.

### R3: _extract_agent_preview() Input Validation

**Decision**: Add `isinstance(tools, list)` guard in `_extract_agent_preview()` and validate individual tool elements are non-empty strings.

**Rationale**: The method parses AI-generated JSON from chat responses. Malformed but JSON-valid configs like `tools: "read"` (string instead of list) or `tools: [123, null, {}]` (list with non-string elements) bypass the previous validation and create `AgentPreview` objects with invalid `tools` fields. These break downstream Pydantic serialization and chat refinement flows.

**Alternatives considered**:

- Pydantic model validation at the `AgentPreview` level: Would work but pushes validation further from the parsing boundary; `_extract_agent_preview` is the explicit gatekeeper.
- Coercing invalid tools (e.g. wrapping a string in a list): Masks AI model errors; better to reject and re-prompt.
- Filtering invalid elements silently: Partial configs are confusing to users in chat flow; returning `None` triggers a re-prompt.

---

## Phase 1: Design & Contracts

### Bug 1.1 — Fix `_project_launch_locks` Memory Leak

**File**: `solune/backend/src/services/pipeline_state_store.py`

**Current state (ALREADY RESOLVED)**: The code at line 40 already uses:

```python
_project_launch_locks: BoundedDict[str, asyncio.Lock] = BoundedDict(maxlen=10_000)
```

The `get_project_launch_lock()` function (lines 54–71) already implements LRU-like behavior via `touch()` for existing keys and automatic eviction via `BoundedDict.__setitem__` for new keys.

**Regression tests (ALREADY EXIST)**: `TestProjectLaunchLocksBounded` class in `test_pipeline_state_store.py` (lines 795–840) covers:

- `test_lock_dict_is_bounded` — confirms `BoundedDict` type
- `test_returns_same_lock_for_same_project` — identity check
- `test_returns_different_locks_for_different_projects` — isolation check
- `test_lock_count_stays_bounded` — capacity enforcement
- `test_eviction_does_not_corrupt_remaining_locks` — eviction safety

**Remaining work**: None — bug is fully resolved with regression tests.

### Bug 1.2 — Fix `update_agent()` Lifecycle Status

**File**: `solune/backend/src/services/agents/service.py`

**Current state (ALREADY RESOLVED)**: All three SQL persistence paths in `update_agent()` set `lifecycle_status`:

1. Line 1246: `AgentStatus.PENDING_PR.value` in `UPDATE` for non-repo agents
2. Line 1279: `AgentStatus.PENDING_PR.value` in `UPDATE` for repo agents with existing local row
3. Line 1311: `AgentStatus.PENDING_PR.value` in `INSERT` for repo agents without local row

The returned `Agent` object at line 1326 also sets `status=AgentStatus.PENDING_PR`.

**Regression tests (ALREADY EXIST)**: `test_agents_service.py` includes:

- `test_update_agent_allows_repo_only_agent_and_persists_pending_row` (line 433) — verifies INSERT path
- `test_update_agent_marks_existing_local_agent_pending_pr` (line 522) — verifies UPDATE path for existing local agents

**Remaining work**: None — bug is fully resolved with regression tests.

### Bug 1.3 — Fix `_extract_agent_preview()` Validation

**File**: `solune/backend/src/services/agents/service.py`

**Current state (PARTIALLY RESOLVED)**: The `isinstance(tools, list)` guard at line 1472 catches the primary case (`tools: "read"`). However, a residual validation gap exists: the code does not validate that individual list elements are non-empty strings. Malformed configs like `tools: [123, null, {}]` pass the list check and create invalid `AgentPreview` objects.

**Current code** (lines 1471–1473):

```python
tools = config.get("tools", [])
if not isinstance(tools, list):
    return None
```

**Required fix**: Add element-level validation after the list type check:

```python
tools = config.get("tools", [])
if not isinstance(tools, list):
    return None
if not all(isinstance(t, str) and bool(t.strip()) for t in tools):
    return None
```

This ensures every tool element is a non-empty string. The `isinstance` check short-circuits before `strip()` for non-string elements, and `bool(t.strip())` rejects empty or whitespace-only strings.

**Regression tests (PARTIALLY EXIST)**: `TestExtractAgentPreview` class (lines 1538–1580) covers:

- `test_non_list_tools_returns_none` — catches `tools: "read"` ✅
- Missing: test for `tools: [123, null, {}]` (non-string list elements)
- Missing: test for `tools: ["read", ""]` (empty string elements)
- Missing: test for `tools: ["read", 123]` (mixed valid/invalid elements)

**Required test additions**:

```python
def test_non_string_tool_elements_returns_none(self):
    """Regression: tools=[123, null, {}] (non-string elements) → None."""
    text = '```agent-config\n{"name": "Bot", "tools": [123, null, {}]}\n```'
    assert AgentsService._extract_agent_preview(text) is None

def test_empty_string_tool_element_returns_none(self):
    """Regression: tools=["read", ""] (empty string) → None."""
    text = '```agent-config\n{"name": "Bot", "tools": ["read", ""]}\n```'
    assert AgentsService._extract_agent_preview(text) is None

def test_mixed_valid_invalid_tool_elements_returns_none(self):
    """Regression: mixed valid/invalid elements → None."""
    text = '```agent-config\n{"name": "Bot", "tools": ["read", 123]}\n```'
    assert AgentsService._extract_agent_preview(text) is None
```

---

## Execution Phases

### Step 1 — Bug 1.3 Fix: Harden `_extract_agent_preview()` Element Validation

| Task | File | Action |
|------|------|--------|
| 1.1 | `solune/backend/src/services/agents/service.py` | Add element-level validation for `tools` list: every element must be a non-empty string |
| 1.2 | `solune/backend/tests/unit/test_agents_service.py` | Add 3 regression tests for non-string elements, empty strings, and mixed invalid elements |

**Acceptance**: `_extract_agent_preview()` returns `None` for any config where `tools` contains non-string or empty-string elements. All existing tests continue to pass.

### Step 2 — Verification: Bugs 1.1 and 1.2

| Task | File | Action |
|------|------|--------|
| 2.1 | `solune/backend/src/services/pipeline_state_store.py` | Verify `BoundedDict` usage — no code change needed |
| 2.2 | `solune/backend/src/services/agents/service.py` | Verify all 3 SQL paths set `PENDING_PR` — no code change needed |
| 2.3 | `solune/backend/tests/unit/test_pipeline_state_store.py` | Run existing `TestProjectLaunchLocksBounded` tests — must pass |
| 2.4 | `solune/backend/tests/unit/test_agents_service.py` | Run existing update_agent lifecycle tests — must pass |

**Acceptance**: All existing regression tests pass. No changes needed for bugs 1.1 and 1.2.

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Element validation rejects valid AI output | Low | Medium | Only rejects non-string / empty elements; standard AI outputs are `["read", "search_code"]` |
| BoundedDict eviction drops active lock | Very Low | Low | `maxlen=10_000` is 100× typical concurrent projects; LRU touch keeps active locks |
| Update lifecycle change breaks UI flow | None | N/A | Already resolved; no change needed |

## Dependencies

```text
Bug 1.1 ──→ (none — already resolved)
Bug 1.2 ──→ (none — already resolved)
Bug 1.3 ──→ Step 1.1 (code fix) → Step 1.2 (regression tests)
```

All three bugs are independent of each other with no cross-dependencies.

## Quickstart

### Running the fix

```bash
# No code changes needed for bugs 1.1 and 1.2 — already resolved.

# Bug 1.3: Apply element validation in _extract_agent_preview()
# File: solune/backend/src/services/agents/service.py, lines 1471-1473
# Add after the isinstance(tools, list) check:
#   if not all(isinstance(t, str) and t.strip() for t in tools):
#       return None
```

### Running the tests

```bash
cd solune/backend

# Run Bug 1.1 regression tests
python -m pytest tests/unit/test_pipeline_state_store.py::TestProjectLaunchLocksBounded -v

# Run Bug 1.2 lifecycle tests
python -m pytest tests/unit/test_agents_service.py -k "update_agent" -v

# Run Bug 1.3 preview extraction tests
python -m pytest tests/unit/test_agents_service.py::TestExtractAgentPreview -v

# Run all backend unit tests
python -m pytest tests/unit/ -v
```
