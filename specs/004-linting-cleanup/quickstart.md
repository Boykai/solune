# Quickstart: Linting Clean Up

**Feature**: 004-linting-cleanup | **Date**: 2026-04-02
**Purpose**: Step-by-step guide for contributors implementing the linting cleanup.

## Prerequisites

- Python 3.13+ with `uv` package manager
- Node.js 20+ with `npm`
- Backend virtual environment: `cd solune/backend && uv sync --locked --extra dev`
- Frontend dependencies: `cd solune/frontend && npm ci`

## Phase Execution Order

> **Critical**: Execute phases in order. Each phase depends on the previous.

### Phase 1: Test Type-Check Gate Expansion (P1)

**Goal**: Make test type errors visible in CI and pre-commit.

1. **Create frontend test type-check config**:

   ```bash
   # Create solune/frontend/tsconfig.test.json extending the main config
   # Include all src files (remove test exclusions)
   # Add vitest/globals types
   ```

2. **Add frontend test type-check npm script**:

   ```bash
   cd solune/frontend
   # Add to package.json scripts:
   #   "type-check:test": "tsc --noEmit -p tsconfig.test.json"
   ```

3. **Add backend test type-check CI step**:

   ```yaml
   # In .github/workflows/ci.yml, Backend job:
   - name: Type Check Backend Tests
     run: uv run pyright tests
     working-directory: solune/backend
   ```

4. **Add frontend test type-check CI step**:

   ```yaml
   # In .github/workflows/ci.yml, Frontend job:
   - name: Type Check Frontend Tests
     run: npm run type-check:test
     working-directory: solune/frontend
   ```

5. **Update pre-commit hooks** in `solune/.pre-commit-config.yaml`:

   ```yaml
   - id: backend-pyright-tests
     name: Type Check Backend Tests (pyright)
     entry: bash -c 'cd solune/backend && pyright tests'
     language: system
     files: ^solune/backend/.*\.py$
     pass_filenames: false

   - id: frontend-typecheck-tests
     name: Type Check Frontend Tests (TypeScript)
     entry: bash -c 'cd solune/frontend && npx tsc --noEmit -p tsconfig.test.json'
     language: system
     files: ^solune/frontend/.*\.(ts|tsx)$
     pass_filenames: false
   ```

6. **Update `solune/scripts/pre-commit`** — add test type-check steps.

7. **Verify**: Run both new commands locally and confirm they report current errors.

### Phase 2: Backend Source Cleanup (P2)

**Goal**: Remove all 55 `# type: ignore` and `# pyright:` suppressions from `solune/backend/src/`.

**Order** (shared patterns first, then one-offs):

1. **Async task typing** (7 files): Add `[None]` or `[T]` type parameters to bare `asyncio.Task`.
2. **Cache generics** (8 files): Use `typing.cast()` or make cache classes generic.
3. **OTel stubs** (7 in `otel_setup.py`): Add return type annotations and proper base classes.
4. **Optional imports** (5 files): Use `TYPE_CHECKING` guards with conditional runtime imports.
5. **pyright directives** (8 files in `github_projects/`): Remove file-level; narrow to per-line if needed.
6. **Config/dynamic** (5 files): Add protocols, factory methods, or explicit types.
7. **Remaining one-offs** (6 files): Fix individually.

**Verify after each file group**:

```bash
cd solune/backend
uv run pyright src
uv run ruff check src
uv run pytest tests/unit/ -q --tb=short
```

### Phase 3: Backend Test Cleanup (P3)

**Goal**: Remove all 28 `# type: ignore` from `solune/backend/tests/`.

1. Create typed test helpers (e.g., `FakeL1Cache`, `RequestIdLogRecord` protocol).
2. Replace `Settings()` calls with `model_construct()` or explicit kwargs.
3. Use `unittest.mock.patch.object()` instead of direct method assignment.
4. Use `object.__setattr__()` for frozen model field mutations.

**Verify**:

```bash
cd solune/backend
uv run pyright tests
uv run pytest tests/ -q --tb=short
```

### Phase 4: Frontend Source Cleanup (P4)

**Goal**: Remove all 18 production suppressions from `solune/frontend/src/`.

1. Replace `as unknown as` casts with type guards or proper interfaces.
2. Replace `@typescript-eslint/no-explicit-any` with actual types.
3. Review and resolve `react-hooks/exhaustive-deps` suppressions.
4. Keep `jsx-a11y` suppressions but ensure they have descriptive reason comments.

**Verify**:

```bash
cd solune/frontend
npm run type-check
npm run lint
npm test
```

### Phase 5: Frontend Test Cleanup (P5)

**Goal**: Remove all 51 test suppressions.

1. Extend `createMockApi()` in `src/test/setup.ts` to cover all API namespaces.
2. Migrate hook tests from `as unknown as` to the mock factory.
3. Create typed WebSocket/MediaDevices/HTMLElement mock helpers.
4. Fix `@ts-expect-error` in test setup with proper global type declarations.

**Verify**:

```bash
cd solune/frontend
npm run type-check:test
npm test
```

### Phase 6: Guardrails & Documentation

**Goal**: Prevent regression and update contributor guidance.

1. **Tighten ESLint** in `solune/frontend/eslint.config.js`:
   - `@typescript-eslint/ban-ts-comment`: error, allow `ts-expect-error` with description only
   - Verify `@typescript-eslint/no-explicit-any`: error

2. **Update `solune/docs/testing.md`**:
   - Document `npm run type-check:test` command
   - Document `uv run pyright tests` command
   - Add typed mock foundation usage guidance
   - Document ESLint suppression policy

3. **Full validation**:

   ```bash
   # Backend
   cd solune/backend
   uv run ruff check src tests
   uv run ruff format --check src tests
   uv run pyright src
   uv run pyright tests
   uv run pytest tests/ -q --tb=short

   # Frontend
   cd solune/frontend
   npm run lint
   npm run type-check
   npm run type-check:test
   npm test
   npm run build

   # Contracts
   cd /path/to/repo
   bash solune/scripts/validate-contracts.sh
   ```

## Suppression Audit Command

To verify zero suppressions remain in authored code:

```bash
# Backend
grep -rn "# type: ignore" solune/backend/src/ --include="*.py" | grep -v __pycache__
grep -rn "# type: ignore" solune/backend/tests/ --include="*.py" | grep -v __pycache__
grep -rn "# pyright:" solune/backend/src/ --include="*.py" | grep -v __pycache__

# Frontend (excluding node_modules, dist, generated)
grep -rn "@ts-expect-error\|@ts-ignore" solune/frontend/src/ --include="*.ts" --include="*.tsx"
grep -rn "as unknown as" solune/frontend/src/ --include="*.ts" --include="*.tsx"
```

Any remaining suppressions must have:
1. A specific error code (not bare `# type: ignore`)
2. A comment explaining why removal is not possible
3. A link to an upstream issue if applicable
