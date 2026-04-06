# Tasks: Increase Test Coverage & Fix Discovered Bugs

**Input**: Design documents from `/home/runner/work/solune/solune/specs/001-test-coverage-bugfixes/`  
**Prerequisites**: `/home/runner/work/solune/solune/specs/001-test-coverage-bugfixes/plan.md`, `/home/runner/work/solune/solune/specs/001-test-coverage-bugfixes/spec.md`, `/home/runner/work/solune/solune/specs/001-test-coverage-bugfixes/research.md`, `/home/runner/work/solune/solune/specs/001-test-coverage-bugfixes/data-model.md`, `/home/runner/work/solune/solune/specs/001-test-coverage-bugfixes/contracts/mcp-http-auth-contract.md`, `/home/runner/work/solune/solune/specs/001-test-coverage-bugfixes/quickstart.md`

**Tests**: Tests are required for this feature by FR-005 through FR-017. Write the regression tests before or alongside the corresponding source edits and verify they fail for the target bug first.

**Organization**: Tasks are grouped by user story so each fix or coverage milestone can be implemented and validated independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no incomplete-task dependency)
- **[Story]**: User story label from `/home/runner/work/solune/solune/specs/001-test-coverage-bugfixes/spec.md`
- Every task includes the exact file path to edit, create, or validate

## Path Conventions

- **Backend**: `/home/runner/work/solune/solune/solune/backend/src/` and `/home/runner/work/solune/solune/solune/backend/tests/`
- **Frontend**: `/home/runner/work/solune/solune/solune/frontend/src/`
- **Feature docs**: `/home/runner/work/solune/solune/specs/001-test-coverage-bugfixes/`

## Phase 1: Setup (Shared Context)

**Purpose**: Lock the implementation inputs, validation commands, and file targets before source changes begin.

- [ ] T001 Review `/home/runner/work/solune/solune/specs/001-test-coverage-bugfixes/plan.md`, `/home/runner/work/solune/solune/specs/001-test-coverage-bugfixes/spec.md`, `/home/runner/work/solune/solune/specs/001-test-coverage-bugfixes/research.md`, `/home/runner/work/solune/solune/specs/001-test-coverage-bugfixes/data-model.md`, and `/home/runner/work/solune/solune/specs/001-test-coverage-bugfixes/quickstart.md` and capture the backend/frontend workstreams for execution
- [ ] T002 Review `/home/runner/work/solune/solune/specs/001-test-coverage-bugfixes/contracts/mcp-http-auth-contract.md`, `/home/runner/work/solune/solune/solune/backend/src/services/mcp_server/tools/__init__.py`, `/home/runner/work/solune/solune/solune/frontend/package.json`, and `/home/runner/work/solune/solune/solune/frontend/vitest.config.ts` before changing auth or coverage-sensitive files

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Confirm the shared patterns and harnesses that every backend or frontend story relies on.

**⚠️ CRITICAL**: Complete this phase before parallel story work so every change reuses the same auth pattern and validation flow.

- [ ] T003 [P] Verify the MCP authorization pattern in `/home/runner/work/solune/solune/solune/backend/src/services/mcp_server/tools/__init__.py` matches the resource URIs documented in `/home/runner/work/solune/solune/specs/001-test-coverage-bugfixes/contracts/mcp-http-auth-contract.md`
- [ ] T004 [P] Verify shared frontend test utilities in `/home/runner/work/solune/solune/solune/frontend/src/test/test-utils.tsx` and the coverage gates in `/home/runner/work/solune/solune/solune/frontend/vitest.config.ts` before adding modal, hook, and keyboard regression suites

**Checkpoint**: Shared auth/test conventions are fixed, so user-story work can proceed without re-deciding patterns.

---

## Phase 3: User Story 1 - Close Backend Security Gap in MCP Resource Handlers (Priority: P1) 🎯 MVP

**Goal**: Ensure every MCP resource handler enforces authenticated project access before loading or serializing data.

**Independent Test**: Call each MCP resource URI with no credentials, wrong-project credentials, and valid project credentials; only authorized requests succeed.

### Implementation for User Story 1

- [ ] T005 [US1] Add `get_mcp_context()` and `verify_mcp_project_access()` enforcement to every resource handler in `/home/runner/work/solune/solune/solune/backend/src/services/mcp_server/resources.py`

**Checkpoint**: MCP resources reject unauthorized callers consistently with the existing tool-handler auth flow.

---

## Phase 4: User Story 2 - Fix Backend Middleware Silent Authentication Bypass (Priority: P1)

**Goal**: Fail closed in the MCP HTTP middleware whenever bearer authentication is missing, malformed, invalid, or throws.

**Independent Test**: Send valid, missing, malformed, empty, and invalid bearer tokens through the middleware and verify only valid HTTP requests reach the downstream app; non-HTTP scopes still pass through.

### Implementation for User Story 2

- [ ] T006 [US2] Return a 401 ASGI response on failed token verification in `/home/runner/work/solune/solune/solune/backend/src/services/mcp_server/middleware.py`

**Checkpoint**: Invalid MCP HTTP auth is blocked at the middleware boundary instead of reaching handlers with a null context.

---

## Phase 5: User Story 3 - Fix Backend Auth Cache Off-by-One Error (Priority: P2)

**Goal**: Keep the token cache size bounded exactly at the configured maximum.

**Independent Test**: Fill the cache to its limit, add one more token, and verify eviction happens before insertion so the cache never exceeds the maximum.

### Implementation for User Story 3

- [ ] T007 [US3] Correct exact-bound cache eviction in `/home/runner/work/solune/solune/solune/backend/src/services/mcp_server/auth.py`

**Checkpoint**: Cache growth remains predictable and capped at the configured size.

---

## Phase 6: User Story 4 - Add Graceful Degradation for Observability Setup (Priority: P2)

**Goal**: Keep the backend starting successfully even when the OTEL exporter endpoint is unreachable.

**Independent Test**: Start the backend with an unreachable telemetry endpoint and verify startup succeeds with telemetry disabled and a warning recorded.

### Implementation for User Story 4

- [ ] T008 [US4] Add graceful OTel startup fallback in `/home/runner/work/solune/solune/solune/backend/src/services/otel_setup.py` and update `/home/runner/work/solune/solune/solune/backend/src/main.py` only if the call site needs to preserve the no-op path

**Checkpoint**: Telemetry outages no longer crash application startup.

---

## Phase 7: User Story 5 - Fix Frontend Render-Time State Mutations (Priority: P2)

**Goal**: Preserve modal and selector state across re-renders without mutating React state during render.

**Independent Test**: Re-render the affected UIs while validation errors or search text are present and verify the user-visible state persists until the user changes it.

### Implementation for User Story 5

- [ ] T009 [P] [US5] Move AddAgentModal render-time error clearing into an effect in `/home/runner/work/solune/solune/solune/frontend/src/components/agents/AddAgentModal.tsx`
- [ ] T010 [P] [US5] Move ToolSelectorModal render-time search/state initialization into an effect in `/home/runner/work/solune/solune/solune/frontend/src/components/tools/ToolSelectorModal.tsx`

**Checkpoint**: AddAgentModal and ToolSelectorModal stop resetting user-visible state during render.

---

## Phase 8: User Story 6 - Fix Frontend Event Listener and Animation Cleanup (Priority: P2)

**Goal**: Eliminate listener churn and post-unmount animation callbacks in the chore UI.

**Independent Test**: Re-render and unmount the affected components, then verify Escape handling remains reliable and no RAF callback fires after unmount.

### Implementation for User Story 6

- [ ] T011 [P] [US6] Store the close callback in a ref so the Escape listener stays stable in `/home/runner/work/solune/solune/solune/frontend/src/components/chores/AddChoreModal.tsx`
- [ ] T012 [P] [US6] Cancel pending animation frames during cleanup in `/home/runner/work/solune/solune/solune/frontend/src/components/chores/ChoreCard.tsx`

**Checkpoint**: Chore modal and card cleanup behavior is stable across re-renders and unmounts.

---

## Phase 9: User Story 7 - Fix Frontend CommandPalette Tab Focus Trap (Priority: P3)

**Goal**: Keep keyboard focus trapped inside the CommandPalette even when no focusable child elements are available.

**Independent Test**: Open the CommandPalette with an empty result set, press Tab, and verify focus does not escape; then repeat with focusable elements and verify focus cycling still works.

### Implementation for User Story 7

- [ ] T013 [US7] Prevent default Tab behavior when no focusable elements are present in `/home/runner/work/solune/solune/solune/frontend/src/components/command-palette/CommandPalette.tsx`

**Checkpoint**: CommandPalette honors keyboard-trap expectations for both empty and populated states.

---

## Phase 10: User Story 8 - Achieve Backend Test Coverage Targets (Priority: P2)

**Goal**: Add regression coverage for the backend security, correctness, and resilience fixes until backend coverage reaches at least 75%.

**Independent Test**: Run the backend unit-test and coverage commands from `/home/runner/work/solune/solune/specs/001-test-coverage-bugfixes/quickstart.md` and confirm all targeted MCP/OTEL scenarios pass with overall coverage ≥ 75%.

### Tests for User Story 8 ⚠️

> **NOTE: Write these tests before or alongside the corresponding fixes and confirm they fail against the current buggy behavior first.**

- [ ] T014 [P] [US8] Add middleware auth regression coverage in `/home/runner/work/solune/solune/solune/backend/tests/unit/test_mcp_server/test_middleware.py`
- [ ] T015 [P] [US8] Add resource authorization and serialization coverage in `/home/runner/work/solune/solune/solune/backend/tests/unit/test_mcp_server/test_resources.py`
- [ ] T016 [P] [US8] Extend cache-limit, rate-limit, timeout, and GitHub API error coverage in `/home/runner/work/solune/solune/solune/backend/tests/unit/test_mcp_server/test_auth.py`
- [ ] T017 [P] [US8] Extend graceful-degradation and `RequestIDSpanProcessor` coverage in `/home/runner/work/solune/solune/solune/backend/tests/unit/test_otel_config.py`

### Implementation for User Story 8

- [ ] T018 [US8] Run `/home/runner/work/solune/solune/specs/001-test-coverage-bugfixes/quickstart.md` backend verification commands against `/home/runner/work/solune/solune/solune/backend/src` and `/home/runner/work/solune/solune/solune/backend/tests` until coverage is ≥ 75%

**Checkpoint**: Backend fixes are regression-protected and the backend coverage gate is satisfied.

---

## Phase 11: User Story 9 - Achieve Frontend Test Coverage Targets (Priority: P2)

**Goal**: Add the hook, modal, and component regression suites needed to protect the frontend fixes and clear the frontend CI coverage thresholds.

**Independent Test**: Run the frontend coverage, lint, type-check, and build commands from `/home/runner/work/solune/solune/specs/001-test-coverage-bugfixes/quickstart.md` and confirm statements ≥ 50%, branches ≥ 44%, functions ≥ 41%, and lines ≥ 50%.

### Tests for User Story 9 ⚠️

> **NOTE: Write these tests before or alongside the corresponding fixes and confirm they expose the existing bug or coverage gap first.**

- [ ] T019 [P] [US9] Add countdown decrement, reset, expiry, cleanup, and formatter coverage in `/home/runner/work/solune/solune/solune/frontend/src/hooks/useCountdown.test.ts`
- [ ] T020 [P] [US9] Add first-error focus ordering and no-op coverage in `/home/runner/work/solune/solune/solune/frontend/src/hooks/useFirstErrorFocus.test.tsx`
- [ ] T021 [P] [US9] Expand create/edit/validation/dirty-state regression coverage in `/home/runner/work/solune/solune/solune/frontend/src/components/agents/__tests__/AddAgentModal.test.tsx`
- [ ] T022 [P] [US9] Expand form, validation, Escape, and template coverage in `/home/runner/work/solune/solune/solune/frontend/src/components/chores/__tests__/AddChoreModal.test.tsx`
- [ ] T023 [P] [US9] Add unmount cleanup regression coverage in `/home/runner/work/solune/solune/solune/frontend/src/components/chores/__tests__/ChoreCard.test.tsx`
- [ ] T024 [P] [US9] Add confirmation-flow coverage in `/home/runner/work/solune/solune/solune/frontend/src/components/chores/__tests__/ConfirmChoreModal.test.tsx`
- [ ] T025 [P] [US9] Add chores grid interaction coverage in `/home/runner/work/solune/solune/solune/frontend/src/components/chores/__tests__/ChoresGrid.test.tsx`
- [ ] T026 [P] [US9] Expand schedule configuration coverage in `/home/runner/work/solune/solune/solune/frontend/src/components/chores/__tests__/ChoreScheduleConfig.test.tsx`
- [ ] T027 [P] [US9] Expand install confirmation coverage in `/home/runner/work/solune/solune/solune/frontend/src/components/agents/__tests__/InstallConfirmDialog.test.tsx`
- [ ] T028 [P] [US9] Add search persistence and selection regression coverage in `/home/runner/work/solune/solune/solune/frontend/src/components/tools/__tests__/ToolSelectorModal.test.tsx`
- [ ] T029 [P] [US9] Add focus-trap regression coverage in `/home/runner/work/solune/solune/solune/frontend/src/components/command-palette/__tests__/CommandPalette.test.tsx`

### Implementation for User Story 9

- [ ] T030 [US9] Run the frontend verification commands from `/home/runner/work/solune/solune/specs/001-test-coverage-bugfixes/quickstart.md` and `/home/runner/work/solune/solune/solune/frontend/package.json` until coverage, lint, type-check, and build all pass

**Checkpoint**: Frontend bug fixes are regression-protected and the frontend CI coverage gates are satisfied.

---

## Phase 12: Polish & Cross-Cutting Concerns

**Purpose**: Finish validation, confirm security expectations, and clean up any execution drift across stories.

- [ ] T031 [P] Re-run the backend and frontend verification checklist in `/home/runner/work/solune/solune/specs/001-test-coverage-bugfixes/quickstart.md` after all story work completes
- [ ] T032 [P] Manually review unauthorized-access assertions in `/home/runner/work/solune/solune/solune/backend/tests/unit/test_mcp_server/test_resources.py` and the frontend coverage thresholds in `/home/runner/work/solune/solune/solune/frontend/vitest.config.ts`
- [ ] T033 Update `/home/runner/work/solune/solune/specs/001-test-coverage-bugfixes/quickstart.md` or `/home/runner/work/solune/solune/specs/001-test-coverage-bugfixes/plan.md` only if the implemented validation flow or file targets changed during execution

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies; start immediately.
- **Phase 2 (Foundational)**: Depends on Phase 1; blocks all user-story execution until the shared auth and test patterns are confirmed.
- **Phases 3-9 (US1-US7 source fixes)**: Depend on Phase 2; US1 and US2 should go first because they are the security-critical fixes.
- **Phase 10 (US8 backend coverage)**: Depends on the backend fix stories (US1-US4); tests can be drafted earlier, but completion requires the backend fixes to land.
- **Phase 11 (US9 frontend coverage)**: Depends on the frontend fix stories (US5-US7); tests can be drafted earlier, but completion requires the UI fixes to land.
- **Phase 12 (Polish)**: Depends on all desired user stories being complete.

### User Story Dependencies

- **US1 (P1)**: Starts after Foundational; no dependency on other user stories.
- **US2 (P1)**: Starts after Foundational; no dependency on other user stories.
- **US3 (P2)**: Starts after Foundational; independent of US1/US2 for code changes.
- **US4 (P2)**: Starts after Foundational; independent of US1-US3 for code changes.
- **US5 (P2)**: Starts after Foundational; AddAgentModal and ToolSelectorModal can proceed in parallel.
- **US6 (P2)**: Starts after Foundational; AddChoreModal and ChoreCard can proceed in parallel.
- **US7 (P3)**: Starts after Foundational; independent keyboard fix.
- **US8 (P2)**: Complete after US1-US4; validates the backend fix set and the backend coverage target.
- **US9 (P2)**: Complete after US5-US7; validates the frontend fix set and the frontend coverage target.

### Recommended Completion Order

1. Phase 1 → Phase 2
2. US1 and US2 (ship the security fixes first)
3. US3 and US4
4. US5 and US6
5. US7
6. US8 and US9
7. Phase 12 Polish

---

## Parallel Execution Examples

### User Story 1

No safe internal parallel tasks; complete T005 before relying on US8 resource tests.

### User Story 2

No safe internal parallel tasks; complete T006 before relying on US8 middleware tests.

### User Story 3

No safe internal parallel tasks; complete T007 before finalizing the US8 auth-edge test run.

### User Story 4

No safe internal parallel tasks; complete T008 before finalizing the US8 OTel test run.

### User Story 5

```text
T009 /home/runner/work/solune/solune/solune/frontend/src/components/agents/AddAgentModal.tsx
T010 /home/runner/work/solune/solune/solune/frontend/src/components/tools/ToolSelectorModal.tsx
```

### User Story 6

```text
T011 /home/runner/work/solune/solune/solune/frontend/src/components/chores/AddChoreModal.tsx
T012 /home/runner/work/solune/solune/solune/frontend/src/components/chores/ChoreCard.tsx
```

### User Story 7

No safe internal parallel tasks; complete T013 sequentially.

### User Story 8

```text
T014 /home/runner/work/solune/solune/solune/backend/tests/unit/test_mcp_server/test_middleware.py
T015 /home/runner/work/solune/solune/solune/backend/tests/unit/test_mcp_server/test_resources.py
T016 /home/runner/work/solune/solune/solune/backend/tests/unit/test_mcp_server/test_auth.py
T017 /home/runner/work/solune/solune/solune/backend/tests/unit/test_otel_config.py
```

### User Story 9

```text
T019 /home/runner/work/solune/solune/solune/frontend/src/hooks/useCountdown.test.ts
T020 /home/runner/work/solune/solune/solune/frontend/src/hooks/useFirstErrorFocus.test.tsx
T021 /home/runner/work/solune/solune/solune/frontend/src/components/agents/__tests__/AddAgentModal.test.tsx
T022 /home/runner/work/solune/solune/solune/frontend/src/components/chores/__tests__/AddChoreModal.test.tsx
T023 /home/runner/work/solune/solune/solune/frontend/src/components/chores/__tests__/ChoreCard.test.tsx
T024 /home/runner/work/solune/solune/solune/frontend/src/components/chores/__tests__/ConfirmChoreModal.test.tsx
T025 /home/runner/work/solune/solune/solune/frontend/src/components/chores/__tests__/ChoresGrid.test.tsx
T026 /home/runner/work/solune/solune/solune/frontend/src/components/chores/__tests__/ChoreScheduleConfig.test.tsx
T027 /home/runner/work/solune/solune/solune/frontend/src/components/agents/__tests__/InstallConfirmDialog.test.tsx
T028 /home/runner/work/solune/solune/solune/frontend/src/components/tools/__tests__/ToolSelectorModal.test.tsx
T029 /home/runner/work/solune/solune/solune/frontend/src/components/command-palette/__tests__/CommandPalette.test.tsx
```

---

## Implementation Strategy

### MVP First

1. Complete Phase 1 and Phase 2.
2. Complete **US1** in `/home/runner/work/solune/solune/solune/backend/src/services/mcp_server/resources.py`.
3. Validate the unauthorized-resource behavior independently.
4. If a single-story MVP is acceptable, stop here; otherwise ship **US2** immediately after because it is also security-critical.

### Incremental Delivery

1. Finish the shared setup/foundational review work.
2. Deliver backend security fixes (US1-US2), then backend correctness/resilience fixes (US3-US4).
3. Deliver frontend lifecycle fixes (US5-US7).
4. Add backend coverage suites (US8) and clear backend verification.
5. Add frontend coverage suites (US9) and clear frontend verification.
6. Finish with Phase 12 cross-cutting validation.

### Parallel Team Strategy

1. One engineer completes Phase 1 and Phase 2.
2. Then split by workstream:
   - Engineer A: US1-US4 backend source fixes
   - Engineer B: US5-US7 frontend source fixes
   - Engineer C: US8 backend tests once backend fixes stabilize
   - Engineer D: US9 frontend tests once frontend fixes stabilize
3. Rejoin for Phase 12 final validation.

---

## Notes

- [P] tasks touch different files and can be assigned in parallel safely.
- US8 and US9 are the regression/coverage stories that make the earlier bug-fix stories release-ready.
- Keep source edits minimal and scoped to the files named in each task.
- Verify each regression test exposes the targeted bug before relying on it as acceptance coverage.
