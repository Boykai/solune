# Research: #Harden

**Feature**: Harden Solune reliability, code quality, CI/CD, observability, DX
**Date**: 2026-04-10

## R1: Pipeline Launch Locks — Memory Leak Status

**Decision**: Bug 1.1 is already resolved. No further action required.

**Rationale**: The `_project_launch_locks` dict in `pipeline_state_store.py:40` was
refactored from a plain `dict[str, asyncio.Lock]` to
`BoundedDict[str, asyncio.Lock](maxlen=10_000)` with LRU-like refresh via
`.touch()` in `get_project_launch_lock()` (lines 65–71). The `BoundedDict`
class (defined in `utils.py:72–169`) uses an `OrderedDict` with FIFO eviction
when the capacity is reached.

**Alternatives considered**:

- Explicit TTL-based eviction (rejected — adds timer complexity; FIFO is sufficient)
- `cachetools.LRUCache` (rejected — project already has `BoundedDict`)
- Unlimited growth with periodic manual clear (rejected — non-deterministic)

---

## R2: Agent `update_agent()` Lifecycle Status

**Decision**: Bug 1.2 is already resolved in all three SQL persistence paths.

**Rationale**: `update_agent()` in `agents/service.py` sets
`lifecycle_status = AgentStatus.PENDING_PR.value` in three branches:

1. Non-repo agent UPDATE (line 1246)
2. Existing local agent UPDATE for repo-origin agents (line 1279)
3. New INSERT for repo-origin agents with no local row (line 1311)

The returned `Agent` object at line 1326 explicitly sets
`status=AgentStatus.PENDING_PR`. All three database writes and the in-memory
return object are consistent.

**Alternatives considered**: N/A — code already correct.

---

## R3: `_extract_agent_preview()` — Malformed Config Handling

**Decision**: The existing implementation already guards against `tools: "read"`
(string instead of list) via the `not isinstance(tools, list)` check at
line 1471–1472. However, the function does **not** validate individual tool
entries within the list (e.g., `tools: [123, null, {}]`). Add per-item
validation: each element must be a non-empty `str`.

**Rationale**: The specific example in the issue (`tools: "read"`) is caught by the
type guard. The residual risk is list entries that are not strings — these pass
the `isinstance(tools, list)` check and bypass Pydantic's `AgentPreview`
constructor (which accepts `list` without item-level constraints). Adding a
per-element `isinstance(item, str)` guard closes the gap and returns `None`
for any malformed-but-parseable config.

**Alternatives considered**:

- Rely solely on Pydantic model validation (rejected — `AgentPreview.tools`
  accepts `list[str]` but does not validate that individual elements are strings
  when the field type allows `list`)
- Wrap in try/except for Pydantic `ValidationError` (already done — `ValueError`
  catch at line 1484 covers Pydantic, but prevention is clearer than exception handling)

---

## R4: Module-Level Singletons (TODO 018)

**Decision**: Refactor `github_projects_service` (service.py:493) and
`agents_service_instance` (agents.py:413) to use an accessor-function pattern
that prefers `app.state` in request contexts and falls back to the module-level
instance in non-request contexts.

**Rationale**: The TODO comment (lines 479–491 in service.py) documents the
deferred refactoring with a concrete 3-step plan:

1. Audit 17+ consuming files
2. Introduce `get_github_service()` accessor
3. Update test mocks

This is a medium-risk refactor because background tasks, signal bridges, and
orchestrator loops import the singleton directly.

**Alternatives considered**:

- Full DI via `app.state` only (rejected — requires event loop propagation to
  non-request contexts, breaking background tasks)
- Keep module-level singleton permanently (rejected — violates DI principle,
  makes testing harder)
- Context-var based approach (rejected — over-engineering for this use case)

---

## R5: Pre-Release Dependency Upgrades

**Decision**: Upgrade the following packages when stable releases are available.
For pre-release packages, pin to the latest pre-release version and document
the upgrade path.

| Package | Current | Target | Risk |
|---------|---------|--------|------|
| `azure-ai-inference` | `>=1.0.0b9,<2` | Latest 1.x beta or GA | Medium — API surface may change |
| `agent-framework-core` | `>=1.0.0b1` | Latest 1.x beta | Medium — framework still maturing |
| `agent-framework-azure-ai` | `>=1.0.0b1` | Latest 1.x beta | Medium |
| `agent-framework-github-copilot` | `>=1.0.0b1` | Latest 1.x beta | Medium |
| `opentelemetry-instrumentation-fastapi` | `>=0.54b0,<1` | Latest 0.x | Low — stable API |
| `opentelemetry-instrumentation-httpx` | `>=0.54b0,<1` | Latest 0.x | Low |
| `opentelemetry-instrumentation-sqlite3` | `>=0.54b0,<1` | Latest 0.x | Low |
| `github-copilot-sdk` | `>=0.1.30,<1` | `>=1.0.17` (v2) | High — major version jump |

**Rationale**: The `pyproject.toml` line 16 comment explicitly notes the v2
upgrade path: `copilot-sdk>=1.0.17`. Each upgrade should be an isolated
commit with full CI validation.

**Alternatives considered**:

- Upgrade all at once (rejected — risk too high; serial upgrades with CI gates
  are safer)
- Defer indefinitely (rejected — pre-release versions accumulate breaking changes)

---

## R6: Stryker Config Consolidation

**Decision**: Merge the 4 specialized Stryker configs into a single
`stryker.config.mjs` with configurable target selection via CLI flags or
environment variables.

**Rationale**: Five config files exist:

1. `stryker.config.mjs` — base (all hooks + lib)
2. `stryker-hooks-board.config.mjs` — board hooks subset
3. `stryker-hooks-data.config.mjs` — data hooks subset
4. `stryker-hooks-general.config.mjs` — general hooks subset
5. `stryker-lib.config.mjs` — lib utilities

Each shares the same runner, reporters, and thresholds. Only `mutate` globs
differ. A unified config with a `STRYKER_TARGET` environment variable can
select the appropriate `mutate` pattern while reducing maintenance.

**Alternatives considered**:

- Keep separate configs (rejected — 80% duplication, maintenance overhead)
- Use Stryker `--mutate` CLI flag only (rejected — complex glob patterns are
  easier to maintain in config)

---

## R7: Plan-Mode Orphaned Chat History

**Decision**: Bug 3.4 is already resolved for the plan-mode endpoints.

**Rationale**: Both plan-mode endpoints (`/messages/plan` at line 1974 and
`/messages/plan/stream` at line 2049) now persist user messages **after**
`get_chat_agent_service()` succeeds:

- Lines 2010–2016: Service availability check with 503 early return
- Lines 2018–2024: User message creation only after success
- Lines 2083–2097: Same pattern for streaming endpoint

The comment at line 2018 explicitly documents this ordering:
*"Create user message only after plan mode is confirmed available."*

However, the regular chat endpoint at line 1050–1055 persists the user message
after verifying at least one AI service is available (line 1039 guard), so
this is consistent.

**Alternatives considered**: N/A — code already correct.

---

## R8: Test Coverage — Backend Strategy

**Decision**: Target ~30 untested modules with focused unit tests. Raise
`fail_under` from 75 to 80 in `pyproject.toml`.

**Rationale**: Current backend has 185 source files, 235 test files. Untested
modules concentrated in:

- `prompts/` (6 template modules)
- Copilot polling internals (4 modules)
- MCP server tools (8 modules)
- Chores service internals (4 modules)
- `middleware/request_id.py` (1 module)

Each module needs 2–5 tests targeting core logic paths. Property-based tests
(currently 7 files in `tests/property/`) should expand with round-trip
serialization and migration idempotency tests.

---

## R9: Test Coverage — Frontend Strategy

**Decision**: Target ~61 untested components. Raise thresholds from
50/44/41/50 → 60/52/50/60 (statements/branches/functions/lines).

**Rationale**: Current frontend has 275 source files, 232 test files. Untested
components concentrated in:

- Chores (13 components)
- Agents (10 components)
- Tools (9 components)
- UI primitives (7 components)
- Settings (4 components)
- Pipeline (4 components)
- Chat (4 components)

Hooks (98%) and pages (100%) are well-covered. Property-based tests (currently
6 files) should expand with additional round-trip and edge-case tests.

---

## R10: Axe-Core Playwright Integration

**Decision**: Expand `@axe-core/playwright` usage from 2 spec files
(ui.spec.ts, protected-routes.spec.ts) to auth, board, chat, and settings
E2E flows.

**Rationale**: `@axe-core/playwright` is installed (`^4.10.1` in
`package.json:61`) and imported in 2 of 19 E2E spec files. The integration
pattern is established — `AxeBuilder` is used with Playwright's `page` object.
Extending to the remaining flows requires adding `AxeBuilder` assertions
after page navigation in each spec file.

**Alternatives considered**:

- Custom a11y assertions (rejected — axe-core is the industry standard)
- Lighthouse CI (rejected — heavier than needed; axe is already installed)
