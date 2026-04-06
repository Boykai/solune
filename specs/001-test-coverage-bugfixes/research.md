# Phase 0 Research — Increase Test Coverage & Fix Discovered Bugs

All technical-context questions for this feature are resolved from the live repository. No remaining `NEEDS CLARIFICATION` items block implementation.

## 1. MCP resource authorization pattern

- **Decision**: Update `/home/runner/work/solune/solune/solune/backend/src/services/mcp_server/resources.py` so every resource URI (`solune://projects/{project_id}/pipelines`, `/board`, `/activity`) uses the same authenticated context extraction and project-level authorization flow already used by MCP tool handlers.
- **Rationale**: `/home/runner/work/solune/solune/solune/backend/src/services/mcp_server/tools/__init__.py` already exposes `get_mcp_context()` and `verify_mcp_project_access()`, and tool modules consistently call them before returning project data. Reusing that pattern closes the current security gap with the smallest possible change and keeps resources aligned with tools.
- **Alternatives considered**:
  - Add a new decorator for resources only — rejected because shared helpers already exist and a new abstraction is unnecessary.
  - Rely on middleware-only auth — rejected because per-resource authorization still needs a project-level access check.

## 2. MCP middleware failure behavior

- **Decision**: Change `/home/runner/work/solune/solune/solune/backend/src/services/mcp_server/middleware.py` to fail closed for HTTP MCP requests: missing, malformed, empty, invalid, expired, or exception-throwing bearer token verification must return 401 before the request reaches the MCP app. Continue passing through non-HTTP scopes unchanged.
- **Rationale**: The current middleware sets a null context and still forwards the request, which defeats authentication. The spec explicitly requires 401 behavior for failed HTTP auth while preserving pass-through behavior for non-HTTP scopes.
- **Alternatives considered**:
  - Keep forwarding and let handlers fail later — rejected because it preserves the current bypass risk and weakens the security boundary.
  - Apply authentication to every scope type — rejected because the feature explicitly keeps non-HTTP scope pass-through behavior.

## 3. Token verifier cache and rate-limit bounds

- **Decision**: Keep the auth-cache and rate-limit design in `/home/runner/work/solune/solune/solune/backend/src/services/mcp_server/auth.py`, but fix cache eviction so insertion at the configured maximum evicts before the cache can exceed the bound.
- **Rationale**: The existing implementation already has the right structures (`TokenCacheEntry`, `RateLimitEntry`, TTL pruning, sliding-window cleanup). The defect is a precise off-by-one bug, so the safest plan is a precise bound fix plus regression tests for exact-size eviction, stale-rate-limit cleanup, timeouts, and API error responses.
- **Alternatives considered**:
  - Replace the cache with a new ordered-cache implementation — rejected because it is larger than the bug and increases risk.
  - Relax the maximum size assumption — rejected because the spec requires exact bounded behavior.

## 4. OpenTelemetry startup degradation

- **Decision**: Preserve the existing OTel setup path in `/home/runner/work/solune/solune/solune/backend/src/main.py` and `/home/runner/work/solune/solune/solune/backend/src/services/otel_setup.py`, but wrap startup initialization so unreachable exporters log a warning and leave the app running with no-op tracer/meter behavior.
- **Rationale**: `otel_setup.py` already exposes safe no-op accessors when `_tracer` or `_meter` is unset. The missing behavior is graceful handling around startup initialization, so a guarded initialization path is enough to satisfy the requirement without redesigning the observability stack.
- **Alternatives considered**:
  - Add retry loops/backoff at startup — rejected because the requirement is graceful degradation, not connection recovery.
  - Push fallback logic into every OTel consumer — rejected because the startup path is the single correct choke point.

## 5. Frontend lifecycle bug-fix strategy

- **Decision**: Limit frontend source edits to React-safe lifecycle fixes in the affected files: move render-time state resets into effects, hold unstable close callbacks in refs where needed, and guarantee cleanup of event listeners or animation frames on unmount.
- **Rationale**: The affected modules are narrowly scoped: `/home/runner/work/solune/solune/solune/frontend/src/components/agents/AddAgentModal.tsx`, `/home/runner/work/solune/solune/solune/frontend/src/components/chores/AddChoreModal.tsx`, `/home/runner/work/solune/solune/solune/frontend/src/components/chores/ChoreCard.tsx`, `/home/runner/work/solune/solune/solune/frontend/src/components/tools/ToolSelectorModal.tsx`, and `/home/runner/work/solune/solune/solune/frontend/src/components/command-palette/CommandPalette.tsx`. Minimal lifecycle fixes address the identified user-visible bugs without expanding scope into refactors.
- **Alternatives considered**:
  - Rebuild the modal flows around new state machines — rejected because the bug fixes are localized and do not justify architectural change.
  - Broaden the work to unrelated components — rejected by the feature scope boundaries.

## 6. Frontend test planning on the current branch

- **Decision**: Treat the current branch as already containing useful baseline tests, then add only the missing suites and expansions needed for the scoped bug fixes and coverage thresholds.
- **Rationale**: Relevant tests already exist at `/home/runner/work/solune/solune/solune/frontend/src/components/agents/__tests__/AddAgentModal.test.tsx`, `/home/runner/work/solune/solune/solune/frontend/src/components/chores/__tests__/AddChoreModal.test.tsx`, `/home/runner/work/solune/solune/solune/frontend/src/components/agents/__tests__/InstallConfirmDialog.test.tsx`, and `/home/runner/work/solune/solune/solune/frontend/src/components/chores/__tests__/ChoreScheduleConfig.test.tsx`. The missing coverage work should focus on `useCountdown`, `useFirstErrorFocus`, `ConfirmChoreModal`, `ChoresGrid`, `ToolSelectorModal`, `CommandPalette`, and any targeted expansions needed to verify the actual bug fixes.
- **Alternatives considered**:
  - Ignore existing tests and rewrite them — rejected because it duplicates working branch reality.
  - Chase coverage with unrelated files — rejected because the feature is specifically about the named bugs and their regression protection.

## 7. Validation commands and repo conventions

- **Decision**: Use the repository’s existing toolchains exactly as configured: backend via `uv`, `pytest`, `ruff`, and `pyright`; frontend via `npm`, `vitest`, `eslint`, `tsc`, and `vite`.
- **Rationale**: `/home/runner/work/solune/solune/solune/backend/pyproject.toml` and `/home/runner/work/solune/solune/solune/frontend/package.json` already encode the supported commands and coverage gates. No new tooling is required for this feature.
- **Alternatives considered**:
  - Add helper scripts just for this feature — rejected as unnecessary process churn.
  - Use ad hoc commands outside project config — rejected because the plan should stay aligned with CI behavior.
