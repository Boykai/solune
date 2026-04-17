# Code Quality Checklist (P5)

**Category**: Code Quality Issues
**Priority**: P5 — Lowest
**Scope**: Entire codebase

## Automated Scans

- [ ] Run `ruff check src tests` with extended rules — review warnings
- [ ] Run ESLint on frontend — review warnings (not just errors)
- [ ] Search for `# type: ignore` and `# noqa` without justification comments

## Manual Audit Areas

### Dead Code

- [ ] Unused imports (should be caught by ruff/ESLint)
- [ ] Unused functions or methods not called anywhere
- [ ] Unreachable code after `return`, `raise`, `break`, or `continue`
- [ ] Commented-out code blocks that should be removed
- [ ] Frontend components that are imported but never rendered

### Duplicated Logic

- [ ] Similar validation logic repeated across multiple API endpoints
- [ ] Duplicate error handling patterns that could be extracted
- [ ] Frontend components with near-identical logic (candidates for shared hooks)
- [ ] Configuration values defined in multiple places

### Hardcoded Values

- [ ] Magic numbers without named constants
- [ ] Hardcoded URLs or paths that should be configurable
- [ ] Hardcoded timeout values that should be in configuration
- [ ] Frontend hardcoded API base URLs

### Silent Failures

- [ ] Bare `except:` or `except Exception:` without logging or re-raising
- [ ] Empty `catch` blocks in frontend code
- [ ] Functions that return `None` on error without any indication
- [ ] Missing error messages in exception handlers

### Code Clarity

- [ ] Overly complex conditionals that could be simplified
- [ ] Deeply nested code that could be flattened with early returns
- [ ] Missing type hints on public function signatures (backend)
- [ ] Missing TypeScript types (using `any` where a specific type is known)

## Fix Criteria

For each finding:

1. Dead code: Remove if safe (verify no tests break)
2. Duplication: Only consolidate if it doesn't change the public API
3. Hardcoded values: Extract to constants or configuration
4. Silent failures: Add logging or error propagation
5. If any change would require API/architecture changes: flag as `TODO(bug-bash)`
