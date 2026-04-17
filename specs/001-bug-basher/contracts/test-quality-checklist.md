# Test Quality Checklist (P4)

**Category**: Test Gaps & Test Quality
**Priority**: P4
**Scope**: All test files in `solune/backend/tests/` and `solune/frontend/src/__tests__/`

## Automated Scans

- [ ] Run `pytest --cov=src --cov-report=term-missing` — identify untested code paths
- [ ] Review coverage report for files below 80% coverage
- [ ] Run frontend coverage: `npm run test:coverage` — identify untested components

## Manual Audit Areas

### Tests That Pass for the Wrong Reason

- [ ] Tests that mock the code under test (instead of its dependencies)
- [ ] Tests with over-mocking that never exercise real logic
- [ ] Tests where the mock return value matches expected output coincidentally
- [ ] Tests that assert on mock call counts instead of behavior

### Mock Leaks

- [ ] `MagicMock` objects used as file paths or database paths
- [ ] Mock objects leaking into production code paths (e.g., `task_registry.create_task` mock affecting `coalesced_fetch`)
- [ ] Unscoped patches that affect other tests
- [ ] Frontend mocks that don't clean up after test completion

### Assertions That Never Fail

- [ ] `assert True` or `assert 1 == 1` (placeholder assertions)
- [ ] Assertions on always-true conditions (e.g., `assert len(result) >= 0`)
- [ ] Try/except blocks in tests that catch and ignore assertion errors
- [ ] Tests that only assert mock was called but not with correct arguments

### Missing Edge Case Coverage

- [ ] Error paths — Verify tests exist for error/exception scenarios
- [ ] Empty input — Verify tests cover empty lists, empty strings, None values
- [ ] Boundary conditions — Verify tests cover min/max values, pagination edges
- [ ] Concurrent access — Verify tests cover race condition scenarios (where applicable)

### Test Naming and Organization

- [ ] Tests named `test_something` that don't test what the name says
- [ ] Test files that don't match the source file they're testing
- [ ] Duplicate test logic that could be parameterized

## Fix Criteria

For each finding:

1. Replace weak assertions with meaningful checks that would fail on regression
2. Fix mock scoping to prevent leaks
3. Add missing edge case tests for critical code paths
4. Do NOT remove tests — fix or improve them
