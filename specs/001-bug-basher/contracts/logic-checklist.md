# Logic Bug Checklist (P3)

**Category**: Logic Bugs
**Priority**: P3
**Scope**: Business logic in `solune/backend/src/services/` and `solune/frontend/src/`

## Manual Audit Areas

### State Transitions

- [ ] `src/services/workflow_orchestrator/transitions.py` — Verify all state transitions are valid
- [ ] `src/services/workflow_orchestrator/orchestrator.py` — Verify orchestrator state machine
- [ ] `src/services/copilot_polling/state.py` — Verify polling state transitions
- [ ] `src/services/copilot_polling/state_validation.py` — Verify state validation logic
- [ ] Pipeline services — Verify pipeline stage transitions match preset definitions

### Off-by-One Errors

- [ ] `src/services/pagination.py` — Verify page calculations (0-indexed vs 1-indexed)
- [ ] Any loop with explicit index manipulation — Verify boundary conditions
- [ ] Frontend list rendering — Verify array index calculations

### API Call Correctness

- [ ] `src/services/github_projects/` — Verify GraphQL queries return expected fields
- [ ] `src/services/copilot_polling/` — Verify Copilot API calls use correct parameters
- [ ] Frontend API client — Verify request/response shapes match backend contracts

### Data Consistency

- [ ] `src/constants.py` — Verify constant values are consistent across usage sites
- [ ] Pipeline presets — Verify stage labels match between presets and status columns (known: "In progress" vs "In Progress" is intentional)
- [ ] Frontend state management — Verify Zustand stores stay in sync with API responses

### Control Flow

- [ ] Error recovery paths — Verify retry logic has proper backoff and termination
- [ ] `src/services/copilot_polling/recovery.py` — Verify recovery logic handles all failure modes
- [ ] `src/services/collision_resolver.py` — Verify collision detection/resolution is correct

### Return Values

- [ ] Functions returning Optional types — Verify all return paths are covered
- [ ] Boolean logic — Verify negation and compound conditions are correct
- [ ] Frontend hook return values — Verify memoization dependencies are complete

## Fix Criteria

For each finding:

1. Determine if the logic error is obvious (clearly incorrect behavior)
2. If obvious: correct logic + add boundary-case regression test
3. If ambiguous: add `TODO(bug-bash)` describing the expected vs actual behavior
