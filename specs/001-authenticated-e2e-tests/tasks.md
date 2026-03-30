# Tasks: Add Authenticated E2E Tests for Core Application

**Input**: Design documents from `/specs/001-authenticated-e2e-tests/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/test-fixtures.md ✅, quickstart.md ✅

**Tests**: This feature IS the tests — tests are the primary deliverable. Test-first ordering applies where conftest fixtures (foundation) precede individual test files.

**Organization**: Tasks are grouped by user story (from spec.md P1–P6) to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Web app monorepo**: `solune/backend/` (Python/FastAPI), `solune/frontend/` (TypeScript/React)
- Backend tests: `solune/backend/tests/e2e/`
- Frontend E2E: `solune/frontend/e2e/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the `tests/e2e/` directory and verify project prerequisites

- [x] T001 Create the `solune/backend/tests/e2e/` directory with an empty `__init__.py` file
- [x] T002 Verify existing test suite passes before adding new tests by running `cd solune/backend && uv run pytest tests/test_api_e2e.py -v --tb=short`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Build the authenticated E2E test fixtures that ALL user stories depend on. These fixtures provide the auth_client, test database, and mocked external services.

**⚠️ CRITICAL**: No user story test file can be implemented until this phase is complete.

- [x] T003 Create the authenticated E2E conftest with all shared fixtures in `solune/backend/tests/e2e/conftest.py`:
  - `test_db` fixture (function-scoped): Creates a fresh in-memory SQLite database via `aiosqlite.connect(":memory:")`, applies all migrations using `_apply_migrations()` from `tests/conftest.py`, yields the connection, closes on teardown
  - `mock_github_projects_service` fixture: Creates a pre-configured `GitHubProjectsService` mock using `make_mock_github_service()` from `tests/conftest.py`
  - `mock_chat_agent_service` fixture: Creates an `AsyncMock` with spec `ChatAgentService` that returns mock chat responses
  - `mock_ai_agent_service` fixture: Creates an `AsyncMock` with spec `AIAgentService`
  - `mock_connection_manager` fixture: Creates an `AsyncMock` with spec `ConnectionManager`
  - `e2e_app` fixture (function-scoped): Calls `create_app()`, overrides `get_database` → `test_db`, `get_github_service` → `mock_github_projects_service`, `get_chat_agent_service` → mock, `get_ai_agent_service` → mock, `get_connection_manager` → mock; patches `github_auth_service.create_session_from_token` to return a `UserSession` with test-user data (`github_user_id="12345"`, `github_username="test-user"`, `access_token="ghp_test_access_token"`)
  - `auth_client` fixture (function-scoped): Creates `httpx.AsyncClient` with `ASGITransport(app=e2e_app)` and `base_url="http://testserver"`, calls `POST /api/v1/auth/dev-login` with `{"github_token": "ghp_test_access_token"}`, asserts 200 response and session cookie presence, yields authenticated client, closes on teardown
  - `unauthenticated_client` fixture (function-scoped): Creates `httpx.AsyncClient` with same app but no login call, yields client, closes on teardown
  - Set environment variables: `TESTING=1`, `DEBUG=true`, `DATABASE_PATH=:memory:`
- [x] T004 Validate the foundational fixtures work by running `cd solune/backend && uv run pytest tests/e2e/conftest.py --co -v` to verify fixture collection succeeds

**Checkpoint**: Foundation ready — all user story E2E test files can now be implemented in parallel.

---

## Phase 3: User Story 1 — Authenticated Session Lifecycle Verification (Priority: P1) 🎯 MVP

**Goal**: Verify the full authentication lifecycle — login, session persistence across multiple requests, and logout — through the real FastAPI app with real session store.

**Independent Test**: `cd solune/backend && uv run pytest tests/e2e/test_auth_flow.py -v`

### Implementation for User Story 1

- [x] T005 [US1] Create auth lifecycle E2E tests in `solune/backend/tests/e2e/test_auth_flow.py`:
  - `test_dev_login_sets_session_cookie_and_returns_user(auth_client)` — Verify the auth_client fixture successfully logged in: call `GET /api/v1/auth/me`, assert 200 with `github_username == "test-user"` and `github_user_id == "12345"`
  - `test_session_persists_across_multiple_requests(auth_client)` — Make 3+ sequential authenticated requests (e.g., `GET /api/v1/auth/me` three times), assert all return 200 with consistent user data, verifying cookie reuse
  - `test_logout_invalidates_session(auth_client)` — Call `POST /api/v1/auth/logout`, then call `GET /api/v1/auth/me`, assert 401 response
  - `test_unauthenticated_request_returns_401(unauthenticated_client)` — Call `GET /api/v1/auth/me` without session cookie, assert 401
  - `test_invalid_cookie_returns_401(unauthenticated_client)` — Manually set an invalid `session_id` cookie on the client, call `GET /api/v1/auth/me`, assert 401
- [x] T006 [US1] Run and verify auth flow tests pass: `cd solune/backend && uv run pytest tests/e2e/test_auth_flow.py -v`

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently. The auth lifecycle (login → session reuse → logout → invalidation) is verified E2E.

---

## Phase 4: User Story 2 — Authenticated Project Operations Verification (Priority: P2)

**Goal**: Verify project listing, selection (with session state update), detail retrieval, task listing, and task creation under an authenticated session with mocked GitHub API responses.

**Independent Test**: `cd solune/backend && uv run pytest tests/e2e/test_projects_flow.py -v`

### Implementation for User Story 2

- [x] T007 [P] [US2] Create project operations E2E tests in `solune/backend/tests/e2e/test_projects_flow.py`:
  - `test_list_projects(auth_client, mock_github_projects_service)` — Configure `mock_github_projects_service.list_user_projects` to return a list of mock projects (e.g., `[{"id": "PVT_test123", "title": "Test Project", "number": 1}]`), call `GET /api/v1/projects`, assert 200 with project data
  - `test_select_project_updates_session(auth_client, mock_github_projects_service)` — Configure mock to allow project access, call `POST /api/v1/projects/PVT_test123/select`, assert 200 with `selected_project_id` in response, then call `GET /api/v1/auth/me` and verify `selected_project_id` is set
  - `test_get_project_details(auth_client, mock_github_projects_service)` — Select a project first, then call `GET /api/v1/projects/PVT_test123`, assert 200 with project details
  - `test_list_project_tasks(auth_client, mock_github_projects_service)` — Select a project, configure mock to return task list, call `GET /api/v1/projects/PVT_test123/tasks`, assert 200 with task data
  - `test_create_task_in_project(auth_client, mock_github_projects_service)` — Select a project, configure mock `create_issue` return value, call task creation endpoint, assert task is created
  - `test_project_operations_require_auth(unauthenticated_client)` — Call `GET /api/v1/projects` without auth, assert 401
- [x] T008 [US2] Run and verify project flow tests pass: `cd solune/backend && uv run pytest tests/e2e/test_projects_flow.py -v`

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently. Project CRUD operations are verified E2E with session state propagation.

---

## Phase 5: User Story 3 — Authenticated Chat Flow Verification (Priority: P3)

**Goal**: Verify chat message sending, history retrieval, and project-selection validation within an authenticated session with mocked AI agent responses.

**Independent Test**: `cd solune/backend && uv run pytest tests/e2e/test_chat_flow.py -v`

### Implementation for User Story 3

- [x] T009 [P] [US3] Create chat flow E2E tests in `solune/backend/tests/e2e/test_chat_flow.py`:
  - `test_send_message_requires_selected_project(auth_client)` — Without selecting a project, call `POST /api/v1/chat/messages` with `{"content": "Hello"}`, assert error response indicating a project must be selected
  - `test_send_message_with_selected_project(auth_client, mock_github_projects_service, mock_chat_agent_service)` — Select a project first, configure mock chat agent to return a response, call `POST /api/v1/chat/messages` with `{"content": "Test message for chat flow"}`, assert 200 with message response
  - `test_get_chat_history(auth_client, mock_github_projects_service, mock_chat_agent_service)` — Select a project, send a message, then call `GET /api/v1/chat/messages`, assert 200 with history containing the sent message
  - `test_chat_requires_auth(unauthenticated_client)` — Call `POST /api/v1/chat/messages` without auth, assert 401
- [x] T010 [US3] Run and verify chat flow tests pass: `cd solune/backend && uv run pytest tests/e2e/test_chat_flow.py -v`

**Checkpoint**: Chat operations are verified E2E — project-selection enforcement, message persistence, and history retrieval all work with real session state.

---

## Phase 6: User Story 4 — Authenticated Pipeline CRUD Verification (Priority: P4)

**Goal**: Verify pipeline listing, creation, project assignment, and lifecycle operations under an authenticated session with real database persistence.

**Independent Test**: `cd solune/backend && uv run pytest tests/e2e/test_pipeline_flow.py -v`

### Implementation for User Story 4

- [x] T011 [P] [US4] Create pipeline CRUD E2E tests in `solune/backend/tests/e2e/test_pipeline_flow.py`:
  - `test_list_pipelines(auth_client, mock_github_projects_service)` — Select a project, call `GET /api/v1/pipelines/{project_id}`, assert 200 with pipeline list (initially empty)
  - `test_create_pipeline(auth_client, mock_github_projects_service)` — Select a project, call `POST /api/v1/pipelines/{project_id}` with pipeline config data, assert 200 with created pipeline, then call list and verify it appears
  - `test_assign_pipeline_to_project(auth_client, mock_github_projects_service)` — Create a pipeline, call `PUT /api/v1/pipelines/{project_id}/{pipeline_id}/assignment` with assignment data, assert 200
  - `test_pipeline_operations_require_auth(unauthenticated_client)` — Call `GET /api/v1/pipelines/PVT_test123` without auth, assert 401
- [x] T012 [US4] Run and verify pipeline flow tests pass: `cd solune/backend && uv run pytest tests/e2e/test_pipeline_flow.py -v`

**Checkpoint**: Pipeline CRUD operations are verified E2E — create, list, assign lifecycle works with real database persistence and authenticated sessions.

---

## Phase 7: User Story 5 — Authenticated Board Operations Verification (Priority: P5)

**Goal**: Verify board column retrieval and task movement between columns under an authenticated session with mocked GitHub API responses.

**Independent Test**: `cd solune/backend && uv run pytest tests/e2e/test_board_flow.py -v`

### Implementation for User Story 5

- [x] T013 [P] [US5] Create board operations E2E tests in `solune/backend/tests/e2e/test_board_flow.py`:
  - `test_get_board_projects(auth_client, mock_github_projects_service)` — Configure mock to return board project list, call `GET /api/v1/board/projects`, assert 200 with project data
  - `test_get_board_data_with_columns(auth_client, mock_github_projects_service)` — Configure mock to return board data with columns (Backlog, In Progress, Done) and items, call `GET /api/v1/board/projects/{project_id}`, assert 200 with column and item data
  - `test_move_task_between_columns(auth_client, mock_github_projects_service)` — Configure mock for status update, call `PATCH /api/v1/board/projects/{project_id}/items/{item_id}/status` with `{"status": "In Progress"}`, assert 200 with updated status
  - `test_board_operations_require_auth(unauthenticated_client)` — Call `GET /api/v1/board/projects` without auth, assert 401
- [x] T014 [US5] Run and verify board flow tests pass: `cd solune/backend && uv run pytest tests/e2e/test_board_flow.py -v`

**Checkpoint**: Board operations are verified E2E — column retrieval and task movement work with real auth and session context.

---

## Phase 8: User Story 6 — Frontend Authenticated E2E Flows (Priority: P6)

**Goal**: Extend the existing frontend Playwright E2E fixtures to return authenticated user data and realistic API responses, then verify authenticated UI flows (dashboard, project selector, kanban board, navigation).

**Independent Test**: `cd solune/frontend && npx playwright test e2e/authenticated-flows.spec.ts`

### Implementation for User Story 6

- [x] T015 [P] [US6] Create authenticated Playwright fixtures in `solune/frontend/e2e/authenticated-fixtures.ts`:
  - Extend the existing `fixtures.ts` pattern using `test.extend()`
  - Route `/api/v1/auth/me` → 200 with mock user (`{ github_username: "test-user", github_user_id: "12345", github_avatar_url: "https://avatars.githubusercontent.com/u/12345", selected_project_id: "PVT_test123" }`)
  - Route `/api/v1/projects` → 200 with mock project list
  - Route `/api/v1/board/projects` → 200 with mock board project list
  - Route `/api/v1/board/projects/{id}` → 200 with mock board data (columns + items)
  - Route `/api/v1/chat/messages` GET → 200 with mock chat history
  - Route `/api/v1/health` → 200 with `{ status: "healthy" }`
  - All other `/api/**` routes → 404 fallback
- [x] T016 [US6] Create authenticated UI flow tests in `solune/frontend/e2e/authenticated-flows.spec.ts`:
  - `test('dashboard renders with authenticated user data')` — Navigate to `/`, verify user info displays, project list renders
  - `test('project selector works with authenticated data')` — Verify project selector shows projects, selecting one updates the UI
  - `test('kanban board shows tasks in columns')` — Navigate to board page, verify columns (Backlog, In Progress, Done) and task items render
  - `test('navigation between pages works')` — Navigate between dashboard, board, and other pages, verify content renders correctly
- [x] T017 [US6] Run and verify frontend E2E tests pass: `cd solune/frontend && npx playwright test e2e/authenticated-flows.spec.ts`

**Checkpoint**: Frontend authenticated flows are verified — the UI correctly renders authenticated user data and handles realistic API responses.

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Final validation, regression check, and documentation

- [x] T018 Run the full backend test suite to verify zero regressions: `cd solune/backend && uv run pytest tests/ -v`
- [x] T019 [P] Verify each E2E test completes within 5 seconds (SC-004): `cd solune/backend && uv run pytest tests/e2e/ -v --durations=0`
- [x] T020 [P] Verify test isolation — no shared state between tests: Review all fixtures use function scope, each test gets a fresh app and database
- [x] T021 Run quickstart.md validation: Execute all commands in `specs/001-authenticated-e2e-tests/quickstart.md` and verify they succeed

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Stories (Phase 3–8)**: All depend on Foundational phase completion
  - User Stories 1–5 (backend) can proceed in parallel (different test files, no shared state)
  - User Story 6 (frontend) can proceed in parallel with backend stories (separate codebase)
  - Or sequentially in priority order (P1 → P2 → P3 → P4 → P5 → P6)
- **Polish (Phase 9)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) — No dependencies on other stories. MVP deliverable.
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) — Independent of US1; exercises project endpoints
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) — Independent of US1/US2; exercises chat endpoints. Note: internally requires project selection (handled within each test)
- **User Story 4 (P4)**: Can start after Foundational (Phase 2) — Independent of US1–US3; exercises pipeline endpoints
- **User Story 5 (P5)**: Can start after Foundational (Phase 2) — Independent of US1–US4; exercises board endpoints
- **User Story 6 (P6)**: Can start after Foundational (Phase 2) — Independent of US1–US5; extends frontend fixtures (separate codebase)

### Within Each User Story

- Models/fixtures configured before making test requests
- Each test function is independent — no ordering dependency between tests in the same file
- Mock configuration happens within each test function or via fixtures

### Parallel Opportunities

- After Phase 2, all 6 user stories (Phases 3–8) can start simultaneously
- Within each story, test functions are independent and can be written in parallel
- Backend (US1–US5) and frontend (US6) work on completely separate codebases
- All tasks marked [P] can run in parallel with any other [P] task in the same phase

---

## Parallel Example: All Backend Stories

```bash
# After Phase 2 (Foundational) is complete, launch all backend stories in parallel:
Task: T005 [US1] — Auth lifecycle tests in tests/e2e/test_auth_flow.py
Task: T007 [US2] — Project operations tests in tests/e2e/test_projects_flow.py
Task: T009 [US3] — Chat flow tests in tests/e2e/test_chat_flow.py
Task: T011 [US4] — Pipeline CRUD tests in tests/e2e/test_pipeline_flow.py
Task: T013 [US5] — Board operations tests in tests/e2e/test_board_flow.py

# Frontend story can also run in parallel with all backend stories:
Task: T015 [US6] — Authenticated fixtures in frontend/e2e/authenticated-fixtures.ts
Task: T016 [US6] — Authenticated flow tests in frontend/e2e/authenticated-flows.spec.ts
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T002)
2. Complete Phase 2: Foundational (T003–T004) — CRITICAL, blocks all stories
3. Complete Phase 3: User Story 1 — Auth Lifecycle (T005–T006)
4. **STOP and VALIDATE**: `cd solune/backend && uv run pytest tests/e2e/test_auth_flow.py -v`
5. Auth lifecycle is verified E2E — the core foundation works

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 (Auth) → Validate → **MVP delivered!**
3. Add User Story 2 (Projects) → Validate → Project CRUD verified
4. Add User Story 3 (Chat) → Validate → Chat flows verified
5. Add User Story 4 (Pipelines) → Validate → Pipeline CRUD verified
6. Add User Story 5 (Board) → Validate → Board operations verified
7. Add User Story 6 (Frontend) → Validate → Frontend flows verified
8. Each story adds E2E coverage without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together (T001–T004)
2. Once Foundational is done:
   - Developer A: User Story 1 (Auth) + User Story 2 (Projects)
   - Developer B: User Story 3 (Chat) + User Story 4 (Pipelines)
   - Developer C: User Story 5 (Board) + User Story 6 (Frontend)
3. Stories complete and integrate independently — all write to separate files

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Phase 8 (frontend, US6) is optional per spec — backend stories are the priority deliverable
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
- **Total tasks**: 21
- **Tasks per user story**: US1: 2, US2: 2, US3: 2, US4: 2, US5: 2, US6: 3
- **Setup/Foundational tasks**: 4
- **Polish tasks**: 4
- **Parallel opportunities**: After Phase 2, all 6 user stories can proceed simultaneously; 5 tasks marked [P] within story phases
