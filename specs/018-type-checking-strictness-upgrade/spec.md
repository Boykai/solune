# Feature Specification: Type Checking Strictness Upgrade

**Feature Branch**: `018-type-checking-strictness-upgrade`  
**Created**: 2026-04-06  
**Status**: Draft  
**Input**: User description: "Remove all type suppression comments across the monorepo and resolve the underlying issues. Tighten strictness settings where feasible."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Backend Source Code Achieves Full Type Safety (Priority: P1)

A developer working on the Solune backend can run the type checker and get meaningful, accurate feedback on every source file. No real type issues are hidden behind suppression comments. When a developer introduces a type error — such as passing the wrong argument type, accessing a nonexistent attribute, or missing a required method — the type checker catches it immediately rather than silently allowing it.

**Why this priority**: Backend source code is the highest-risk area. Type suppressions in production code mask latent bugs (e.g., a missing `add()` method on `_NoOpInstrument` means counter instrumentation silently fails). Fixing these first prevents real runtime issues from reaching users.

**Independent Test**: Can be fully validated by running the backend type checker (`pyright src`) with zero errors and confirming all `# type: ignore` and `# pyright:` directives have been removed from `src/` files. Delivers value by catching genuine type mismatches in production code paths.

**Acceptance Scenarios**:

1. **Given** the backend source directory contains type suppression comments, **When** all suppressions are replaced with proper type annotations, protocol inheritance, type stubs, and typed alternatives, **Then** the type checker passes with zero errors and zero suppression comments remain in source files.
2. **Given** a developer introduces a type error in a file that previously had a suppression, **When** they run the type checker, **Then** the error is reported immediately instead of being silently suppressed.
3. **Given** classes implement third-party protocols (OpenTelemetry, githubkit), **When** a required protocol method is missing, **Then** the type checker reports the missing method as an error.

---

### User Story 2 - Backend Tests Are Type-Checked (Priority: P2)

A developer writing or modifying backend tests gets the same quality of type-checking feedback as they do for production code. Test code is checked under a standard strictness mode, catching type errors in test setup, mocking patterns, and assertions before they cause confusing test failures at runtime.

**Why this priority**: Tests are the safety net for the codebase. Unchecked test code can contain latent type errors that lead to false-passing tests or cryptic runtime failures. This story depends on Story 1 (backend source fixes must be in place first), making it the natural next priority.

**Independent Test**: Can be validated by running the test type checker (`pyright -p pyrightconfig.tests.json`) under standard mode with zero errors and confirming all `# type: ignore` comments have been removed from test files. Delivers value by ensuring tests accurately exercise the types they claim to test.

**Acceptance Scenarios**:

1. **Given** the test type checker configuration uses `typeCheckingMode: "off"`, **When** it is changed to `typeCheckingMode: "standard"` and all test suppressions are resolved, **Then** the test type checker passes with zero errors.
2. **Given** a test mutates a frozen dataclass field directly, **When** the mutation is replaced with a type-safe alternative (`object.__setattr__` or `dataclasses.replace`), **Then** the type checker accepts the code and the test still passes.
3. **Given** a test file uses `Settings()` with no arguments, **When** it is replaced with the typed `Settings.model_validate({})` alternative, **Then** the type checker accepts the code and the test still passes.

---

### User Story 3 - Frontend Source Code Achieves Full Type Safety (Priority: P2)

A developer working on the Solune frontend can run the TypeScript compiler and get accurate type feedback on every source file. No type assertions (`as any`, `as unknown as`, `@ts-expect-error`) hide genuine type gaps in production-facing code. Browser API usage, lazy loading, and event streaming are all properly typed.

**Why this priority**: Frontend source suppressions are fewer in number (7 total) but affect user-facing code paths including voice input, lazy component loading, and server-sent event parsing. These are equal priority with Story 2 because they are independent workstreams.

**Independent Test**: Can be validated by running the TypeScript compiler (`tsc --noEmit`) and ESLint with zero errors, confirming all `as any`, `@ts-expect-error`, and `eslint-disable` directives have been removed from `src/` files (excluding test files). Delivers value by catching type mismatches in browser API integration and component loading.

**Acceptance Scenarios**:

1. **Given** `useVoiceInput.ts` casts `window as any` to access speech recognition APIs, **When** a typed `SpeechRecognitionWindow` interface is used instead, **Then** the TypeScript compiler validates the access pattern and the voice input feature still works in supported browsers.
2. **Given** `lazyWithRetry.ts` uses `ComponentType<any>`, **When** it is replaced with a properly constrained generic, **Then** the TypeScript compiler validates component type compatibility.
3. **Given** `api.ts` uses `as unknown as ThinkingEvent`, **When** it is replaced with a type guard, **Then** the TypeScript compiler validates the narrowing logic and runtime safety is improved.

---

### User Story 4 - Frontend Test Type Casts Are Eliminated (Priority: P3)

A developer writing frontend tests uses properly-typed mock factories instead of `as unknown as` casts. When API response types change, test mocks produce compile-time errors rather than silently passing with outdated shapes.

**Why this priority**: The 55 `as unknown as` casts in frontend tests are the largest group of suppressions by count. While they don't affect production code directly, they weaken the test safety net. This is P3 because the casts are a consistent, low-risk pattern and the value is primarily in long-term maintainability.

**Independent Test**: Can be validated by running the test TypeScript compiler (`tsc` on test files) with zero `as unknown as` casts remaining and all tests still passing. Delivers value by ensuring test mocks stay in sync with actual API types.

**Acceptance Scenarios**:

1. **Given** test files use `as unknown as SomeType` to create mock API responses, **When** typed mock factory helpers are provided, **Then** tests use the factories and the TypeScript compiler validates mock shapes against actual types.
2. **Given** an API response type adds a new required field, **When** a test creates a mock without that field, **Then** the TypeScript compiler reports the missing field as an error.

---

### Edge Cases

- What happens when a third-party library (copilot SDK, githubkit) releases updated types that conflict with locally authored stubs? Locally authored stubs should be minimal and updated or removed when the library ships its own types.
- How does the system handle the `test_human_delay.py` case where `int(raw_delay)` may receive a non-numeric value? This is a potential latent runtime bug that should be investigated and fixed with proper input validation or a type guard.
- What happens when pyright or TypeScript compiler versions are upgraded in the future? The fixes should use standard typing patterns (protocol inheritance, TypedDict extension, type guards) that are stable across tool versions.
- What if a future developer needs to add a new `# type: ignore` or `as any`? The absence of existing suppressions establishes a zero-tolerance baseline, making any new suppression visible in code review.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST pass the backend type checker on all source files with zero errors and zero type suppression comments (`# type: ignore`, `# pyright:` directives).
- **FR-002**: The system MUST pass the backend type checker on all test files under standard strictness mode with zero errors and zero type suppression comments.
- **FR-003**: The system MUST pass the frontend TypeScript compiler on all source files with zero errors and zero type assertion workarounds (`as any`, `as unknown as`, `@ts-expect-error`, `eslint-disable` for type-related rules) in production code.
- **FR-004**: The system MUST pass the frontend TypeScript compiler on all test files with zero `as unknown as` casts, using typed mock factories or equivalent patterns instead.
- **FR-005**: The system MUST provide type stub declarations for third-party libraries that do not ship their own type definitions (copilot SDK, githubkit), covering all symbols actually imported by the codebase.
- **FR-006**: The system MUST add explicit protocol base classes to OpenTelemetry no-op implementations so that missing protocol methods are caught by the type checker.
- **FR-007**: The system MUST use fully-typed alternatives for Pydantic Settings construction (replacing untyped no-arg constructor calls) across both source and test code.
- **FR-008**: The system MUST declare proper TypeScript interfaces for browser vendor APIs (Web Speech API) instead of using untyped casts.
- **FR-009**: The system MUST provide typed mock factory helpers or equivalent patterns for frontend tests to replace unsafe type casts.
- **FR-010**: All existing unit, integration, and end-to-end tests MUST continue to pass after every change with no regressions in test outcomes.
- **FR-011**: The system MUST resolve any latent bugs discovered during suppression removal (e.g., missing protocol methods, unsafe type conversions) rather than re-suppressing them.

### Key Entities

- **Type Suppression**: A comment or directive (`# type: ignore`, `# pyright:`, `@ts-expect-error`, `as any`, `as unknown as`, `eslint-disable`) that instructs the type checker to skip validation of a specific line or file. Each suppression masks a potential type issue.
- **Type Stub**: A `.pyi` file that provides type declarations for a library that does not include its own. Stubs enable the type checker to validate usage of third-party code without modifying the library itself.
- **Protocol Conformance**: The relationship between a class and the interface (protocol) it implements. Explicit protocol inheritance allows the type checker to verify that all required methods are present.
- **Typed Mock Factory**: A shared test utility that produces properly-typed mock objects for testing, replacing unsafe `as unknown as` casts. Ensures mock shapes stay synchronized with actual types.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Zero type suppression comments remain in backend source files (currently 15 `# type: ignore` + 9 `# pyright:` directives = 24 total).
- **SC-002**: Zero type suppression comments remain in backend test files (currently 19 `# type: ignore` comments).
- **SC-003**: Zero type assertion workarounds remain in frontend source files (currently 2 `@ts-expect-error` + 1 `as any` + 2 `eslint-disable` + 1 `as unknown as` = 6 total).
- **SC-004**: Zero unsafe type casts remain in frontend test files (currently 55 `as unknown as` casts).
- **SC-005**: Backend test type checker operates under standard strictness mode instead of being disabled.
- **SC-006**: All existing tests pass with zero regressions after the upgrade — same pass count and coverage levels are maintained.
- **SC-007**: At least one latent bug is identified and fixed through suppression removal (e.g., missing protocol method on a no-op instrumentation class).
- **SC-008**: Type checker execution completes within the same time budget as before the upgrade (no measurable increase in developer feedback loop duration).

### Assumptions

- Both pyright (backend) and tsc (frontend) currently pass with zero errors — all suppressions are masking gaps, not preventing build failures.
- The copilot SDK (`github-copilot-sdk`) does not ship `py.typed` or type stubs; locally authored stubs are the appropriate solution.
- The githubkit library uses dynamic attribute access patterns that require stub-level type declarations to validate.
- The `reasoning_effort` key is a valid runtime option for copilot requests but is not yet declared in the SDK's TypedDict.
- Standard strictness mode for backend test type checking is appropriate once existing test suppressions are resolved.
- The 55 frontend test `as unknown as` casts follow a consistent pattern that can be addressed with shared mock factory utilities.
- No runtime behavior changes are required — all fixes are type-annotation-level changes that do not alter program logic, with the exception of fixing discovered latent bugs.
