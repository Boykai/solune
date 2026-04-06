# Quickstart — Increase Test Coverage & Fix Discovered Bugs

Use this sequence after implementation work to verify the feature end to end from the live repository.

## 1. Backend security and resilience checks

```bash
cd /home/runner/work/solune/solune/solune/backend
uv run pytest tests/unit/test_mcp_server -q
uv run pytest tests/unit -q
uv run ruff check src tests
uv run pyright
```

Recommended focused reruns while implementing:

```bash
cd /home/runner/work/solune/solune/solune/backend
uv run pytest tests/unit/test_mcp_server/test_middleware.py -q
uv run pytest tests/unit/test_mcp_server/test_resources.py -q
uv run pytest tests/unit/test_mcp_server/test_auth.py -q
```

Expected outcomes:

- MCP HTTP requests without a valid bearer token fail with 401 before handlers run.
- MCP resources for `solune://projects/{project_id}/pipelines`, `/board`, and `/activity` reject unauthorized callers and allow authorized callers.
- Token-cache size never exceeds the configured maximum.
- App startup does not fail when the OTel exporter endpoint is unreachable.

## 2. Frontend bug-fix and coverage checks

```bash
cd /home/runner/work/solune/solune/solune/frontend
npm run test -- src/components/agents/__tests__/AddAgentModal.test.tsx src/components/chores/__tests__/AddChoreModal.test.tsx src/components/agents/__tests__/InstallConfirmDialog.test.tsx src/components/chores/__tests__/ChoreScheduleConfig.test.tsx
npm run test:coverage
npm run lint
npm run type-check
npm run build
```

Recommended focused reruns while implementing:

```bash
cd /home/runner/work/solune/solune/solune/frontend
npm run test -- src/hooks/useCountdown.test.ts src/hooks/useFirstErrorFocus.test.tsx src/components/tools/__tests__/ToolSelectorModal.test.tsx src/components/command-palette/__tests__/CommandPalette.test.tsx
```

Expected outcomes:

- `AddAgentModal` preserves validation errors across re-renders until the user fixes the issue.
- `AddChoreModal` closes reliably on Escape after repeated re-renders.
- `ChoreCard` cancels pending animation work on unmount.
- `ToolSelectorModal` preserves search input/results across re-renders.
- `CommandPalette` traps Tab even when no focusable child exists.
- Frontend coverage reaches at least 50% statements, 44% branches, 41% functions, and 50% lines.

## 3. Ordered implementation checklist

1. Add/expand backend regression tests for middleware and resource authorization.
2. Apply backend security fixes, then add auth-cache and OTel resilience tests/fixes.
3. Expand existing frontend tests on this branch before touching source where possible.
4. Apply the five scoped frontend bug fixes.
5. Add the missing hook/component coverage tests needed to cross the frontend thresholds.
