# Feature Specification: Eliminate the "Dual-Init" Singleton Pattern

**Feature Branch**: `002-dual-init-singleton`
**Created**: 2026-04-18
**Status**: Draft
**Input**: User description: "Eliminate the Dual-Init Singleton Pattern — Make app.state the single source of truth for every service singleton, turn module-level globals into sentinel-holders that are None in production, and replace ad-hoc test cleanup with a @resettable_state registry enumerated by an autouse pytest fixture. Each ad-hoc patch is replaced with app.dependency_overrides so tests mock at the FastAPI boundary, not at multiple module paths."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Single Source of Truth for All Service Singletons (Priority: P1)

A backend developer needs to understand where a service singleton lives at runtime. Today, some services exist as module-level globals instantiated at import time, some are lazily initialized private variables, and two have a partial migration to `app.state` with fallback logic. After this feature, every service singleton is registered exclusively on `app.state` during the application lifespan startup. Module-level variables that previously held live instances are reduced to `None` sentinel values that are never read in production code paths.

**Why this priority**: This is the foundational change. Every other improvement — test cleanup, dependency overrides, the resettable registry — depends on `app.state` being the canonical location for all singletons. Without it, there are two (or more) places where the "real" instance might live, creating split-brain bugs and confusing onboarding.

**Independent Test**: Migrate a single service (e.g., `ChatAgentService`) to `app.state` and confirm that all existing endpoints that depend on it continue to pass tests with no `patch()` calls referencing the old module-level global path.

**Acceptance Scenarios**:

1. **Given** the application starts normally, **When** a developer inspects `app.state`, **Then** every service singleton (GitHubProjectsService, ConnectionManager, ChatAgentService, PipelineRunService, GitHubAuthService, AlertDispatcher) is accessible as a named attribute on `app.state`.
2. **Given** the application has started, **When** any module that previously held a global singleton is inspected, **Then** the former global variable is `None` (or does not exist) and is never read by production code.
3. **Given** the `dependencies.py` accessor functions (`get_github_service`, `get_connection_manager`) previously had fallback-to-global logic, **When** the migration is complete, **Then** each accessor reads exclusively from `request.app.state` with no fallback branch.
4. **Given** services that had no accessor at all (ChatAgentService, PipelineRunService, GitHubAuthService), **When** the migration is complete, **Then** each has a new FastAPI `Depends()`-compatible accessor function in `dependencies.py` that retrieves the instance from `request.app.state`.

---

### User Story 2 - Resettable State Registry for Test Isolation (Priority: P2)

A test author writes a new test that exercises a service singleton. Today, they must manually discover which module-level variables, caches, and dicts need to be cleared in `conftest.py`'s `_clear_test_caches()` fixture — and if they forget one, tests bleed state into each other. After this feature, a `@resettable_state` decorator (or equivalent registry mechanism) tracks every piece of mutable state that must be reset between tests, and an autouse pytest fixture automatically enumerates and resets all registered entries before and after each test.

**Why this priority**: Once singletons move to `app.state`, the ad-hoc cleanup in `conftest.py` becomes both incomplete (new state can be forgotten) and redundant (state is centralized). A registry-based approach ensures every new piece of resettable state is automatically cleaned up simply by registering it, eliminating an entire class of test-isolation bugs.

**Independent Test**: Register two pieces of state with the resettable mechanism. Run a test that mutates both, followed by a test that asserts they are in their initial state. Both tests pass without any manual cleanup code.

**Acceptance Scenarios**:

1. **Given** a new resettable state registry exists, **When** a developer registers a piece of mutable state (e.g., the devops tracking dictionary), **Then** the autouse pytest fixture automatically resets it to its initial value before and after every test function.
2. **Given** the registry contains all previously ad-hoc-cleared state (devops tracking, template file cache, websocket locks, bounded dicts), **When** the existing `_clear_test_caches()` fixture body is compared to the registry, **Then** every item previously cleared manually is now covered by the registry and the manual clearing code can be removed.
3. **Given** a contributor adds a new service with mutable state and registers it with `@resettable_state`, **When** they run the test suite, **Then** that state is automatically reset between tests without touching `conftest.py`.
4. **Given** the autouse fixture runs, **When** it encounters a registered entry whose reset function raises an exception, **Then** the exception is logged but does not prevent the remaining entries from being reset, and the test itself is not silently corrupted.

---

### User Story 3 - Tests Mock at the FastAPI Boundary Only (Priority: P3)

A test author needs to mock the `GitHubProjectsService` for an API endpoint test. Today, they must patch the service at multiple module paths (e.g., `src.api.board.github_projects_service`, `src.api.projects.github_projects_service`, `src.services.github_projects.github_projects_service`) plus set `app.dependency_overrides[get_github_service]`. After this feature, the test sets a single `app.dependency_overrides` entry and every endpoint that uses `Depends(get_github_service)` receives the mock — no scatter-shot `patch()` calls needed.

**Why this priority**: This is the payoff story that makes daily test authoring dramatically simpler and less error-prone. It depends on Story 1 (all singletons on `app.state`) and Story 2 (automatic cleanup) to eliminate the need for patching internal module paths.

**Independent Test**: Pick an endpoint that today requires three or more `patch()` calls to mock the `GitHubProjectsService`. Rewrite the test to use only `app.dependency_overrides[get_github_service]` and confirm it passes identically.

**Acceptance Scenarios**:

1. **Given** all service singletons are accessed via `Depends()` in route handlers, **When** a test sets `app.dependency_overrides[get_service_accessor]` to a mock, **Then** every route handler that depends on that service receives the mock without additional `patch()` calls.
2. **Given** the test suite previously contained multiple `patch()` paths for the same logical service, **When** the migration is complete, **Then** the total number of distinct `patch()` target paths for service singletons is reduced to zero (all replaced by `dependency_overrides`).
3. **Given** a test uses `app.dependency_overrides` to inject a mock, **When** the test completes, **Then** the autouse fixture from Story 2 automatically clears `dependency_overrides`, preventing bleed into subsequent tests.
4. **Given** an endpoint handler accesses a service via `Depends(get_chat_agent_service)`, **When** no override is set and the app is running normally, **Then** the handler receives the real `ChatAgentService` instance from `app.state`.

---

### User Story 4 - Module-Level Caches and Mutable Dicts Centralized (Priority: P4)

A contributor is debugging a test failure caused by stale cached data. Today, the template-file cache (`_cached_files`, `_cached_warnings`) and devops tracking dict (`_devops_tracking`) are module-level variables whose lifecycle is invisible to the dependency injection system. After this feature, these mutable stores are either registered with the resettable state registry (if they must remain module-level for performance) or moved to `app.state` with proper lifecycle management during lifespan startup/shutdown.

**Why this priority**: These are lower-risk singletons that don't serve endpoint requests directly but still cause test-isolation problems. They naturally follow the same pattern established in Stories 1 and 2.

**Independent Test**: Mutate the template-file cache in one test, then assert in a following test that it has been reset to its initial empty state, without any manual cleanup in the test body.

**Acceptance Scenarios**:

1. **Given** the template-file cache variables (`_cached_files`, `_cached_warnings`) are registered with the resettable state registry, **When** a test populates the cache and completes, **Then** the next test finds both variables reset to `None`.
2. **Given** the devops tracking dict is registered with the resettable state registry, **When** a test adds entries and completes, **Then** the next test finds the dict empty.
3. **Given** the `AlertDispatcher` is stored on `app.state` with a proper accessor, **When** the module-level `set_dispatcher()` / `get_dispatcher()` functions are removed, **Then** all code that previously called them uses the `Depends()`-based accessor instead.

---

### Edge Cases

- What happens when a service singleton's constructor fails during lifespan startup? The application must fail fast with a clear error message rather than silently serving requests with a `None` service.
- What happens when a test forgets to register new mutable state with the resettable registry? The registry should be the documented convention, but unregistered state will not be automatically cleaned up — this is an acceptable trade-off since the pattern is opt-in.
- How does the system handle circular imports if `dependencies.py` accessor functions import from service modules that themselves import from `dependencies.py`? Accessor functions must use lazy imports (inside the function body) to break any cycles.
- What happens if two tests run concurrently and both modify `app.dependency_overrides`? The existing pytest-asyncio configuration runs tests sequentially within a single event loop, so this is not a concern under the current test runner. If parallel test execution is adopted in the future, overrides must be scoped per-test.
- What happens to the `AlertDispatcher` dual-registration path (both `app.state` and `set_dispatcher()`)? The module-level setter must be removed, and all code paths must read exclusively from `app.state` via a `Depends()` accessor.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST register every service singleton (GitHubProjectsService, ConnectionManager, ChatAgentService, PipelineRunService, GitHubAuthService, AlertDispatcher) as a named attribute on `app.state` during the application lifespan startup.
- **FR-002**: System MUST provide a `Depends()`-compatible accessor function in `dependencies.py` for every service singleton that reads exclusively from `request.app.state` with no module-level global fallback.
- **FR-003**: System MUST reduce former module-level global variables for service singletons to `None` sentinel values (or remove them entirely) so that no production code path reads from them.
- **FR-004**: System MUST provide a resettable state registry mechanism (e.g., `@resettable_state` decorator) that allows any piece of mutable state to register itself for automatic reset between tests.
- **FR-005**: System MUST provide an autouse pytest fixture that enumerates all entries in the resettable state registry and resets each one before and after every test function.
- **FR-006**: System MUST handle exceptions raised during state reset gracefully — logging the error and continuing to reset remaining entries rather than aborting.
- **FR-007**: System MUST eliminate all multi-path `patch()` calls for service singletons in the test suite, replacing them with single `app.dependency_overrides` entries.
- **FR-008**: System MUST clear `app.dependency_overrides` automatically after each test via the autouse fixture, preventing override bleed between tests.
- **FR-009**: System MUST register the template-file cache (`_cached_files`, `_cached_warnings`), devops tracking dict (`_devops_tracking`), and other previously ad-hoc-cleared mutable state with the resettable state registry.
- **FR-010**: System MUST fail fast during lifespan startup if any service singleton constructor raises an exception, providing a clear error message identifying which service failed.
- **FR-011**: System MUST use lazy imports inside `dependencies.py` accessor function bodies to prevent circular import errors.
- **FR-012**: System MUST maintain full backward compatibility for all existing API endpoints — no endpoint behavior changes, only internal wiring changes.

### Key Entities

- **Service Singleton**: A long-lived object instantiated once and shared across the application (e.g., `GitHubProjectsService`, `ConnectionManager`). After migration, each is registered on `app.state` with a unique attribute name and accessed via a `Depends()` accessor.
- **Resettable State Entry**: A registered piece of mutable state (singleton reference, cache, dictionary) with an associated reset function. The registry tracks all entries and the autouse fixture invokes each reset function between tests.
- **Dependency Accessor**: A function in `dependencies.py` with signature `def get_X(request: Request) -> ServiceType` that retrieves a service from `request.app.state`. Used as `Depends(get_X)` in route handler signatures.
- **Dependency Override**: A FastAPI mechanism (`app.dependency_overrides[get_X] = lambda: mock`) that replaces the real accessor's return value with a test double for the duration of a test.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every service singleton is accessible from exactly one location (`app.state`), reducing the number of distinct "source of truth" locations from 8+ module-level globals to 1 centralized registry.
- **SC-002**: The total number of distinct `patch()` target paths for service singletons in the test suite is reduced to zero — all replaced by `app.dependency_overrides` entries.
- **SC-003**: The manual state-cleanup code in `conftest.py`'s `_clear_test_caches()` fixture is reduced by at least 80%, replaced by automatic registry-based resets.
- **SC-004**: A new contributor can mock any service singleton in a test by writing a single `app.dependency_overrides` line, without needing to discover which module paths to patch.
- **SC-005**: The full backend test suite passes with zero test-isolation failures (no state bleed between tests) after the migration.
- **SC-006**: Adding a new service singleton to the application requires registering it in exactly one place (lifespan startup + registry), not updating multiple `conftest.py` cleanup blocks.
- **SC-007**: Application startup time is not degraded — service initialization remains sequential during lifespan startup with no additional overhead from the registry mechanism.

### Assumptions

- The application uses FastAPI's lifespan context manager for startup/shutdown, which is the existing pattern in `main.py`.
- Tests run sequentially within a single event loop (pytest-asyncio default), so `app.dependency_overrides` does not require per-test scoping for concurrency.
- The `@resettable_state` registry is a test-time utility; it has no runtime overhead in production because the registry is only enumerated by the pytest fixture.
- Lazy imports inside accessor function bodies are an acceptable trade-off for avoiding circular dependencies, as these functions are called per-request and Python caches module imports after the first load.
- The existing `conftest.py` autouse fixture pattern is the correct extension point for the registry-based cleanup, not a custom pytest plugin.

### Out of Scope

- Refactoring service constructors or changing how services are configured (e.g., database connections, API keys). This feature only changes where instances are stored and how they are accessed.
- Introducing a full dependency injection container or framework (e.g., `dependency-injector`). The solution uses FastAPI's built-in `Depends()` mechanism exclusively.
- Migrating background tasks, scheduled jobs, or CLI entry points that may also access singletons outside the request lifecycle. These are tracked separately.
- Performance optimization of service initialization order or parallelizing startup. Services continue to initialize sequentially.
