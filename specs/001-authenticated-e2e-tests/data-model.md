# Data Model: Add Authenticated E2E Tests for Core Application

**Feature**: `001-authenticated-e2e-tests` | **Date**: 2026-03-30

## Overview

This data model describes the test entities, their relationships, and the data flows exercised by the authenticated E2E test suite. Since this feature adds tests (not production code), the "data model" captures test fixtures, mock data shapes, and the session state transitions verified by the tests.

## Test Entities

### 1. AuthenticatedTestClient

The central test entity — an `httpx.AsyncClient` instance that holds a valid session cookie obtained via the dev-login endpoint.

| Field | Type | Source | Description |
|-------|------|--------|-------------|
| `transport` | `ASGITransport` | `create_app()` | ASGI transport wrapping the full FastAPI app |
| `base_url` | `str` | Fixed | `"http://testserver"` |
| `cookies` | `CookieJar` | Dev-login response | Contains `session_id` cookie after login |

**Lifecycle**: Created fresh per test (function-scoped fixture). Login performed during fixture setup. Torn down after test completes.

### 2. TestDatabase

An in-memory SQLite database with all migrations applied, providing real data persistence within a single test.

| Field | Type | Source | Description |
|-------|------|--------|-------------|
| `connection` | `aiosqlite.Connection` | `aiosqlite.connect(":memory:")` | In-memory database |
| `tables` | Set[str] | Migration files | All tables from `src/migrations/*.sql` |

**Key Tables Used by E2E Tests**:
- `user_sessions` — Session CRUD (create, read, delete, expiry)
- `chat_messages` — Chat history persistence
- `pipeline_configs` — Pipeline CRUD
- `pipeline_runs` — Pipeline execution records
- `pipeline_assignments` — Pipeline-to-project assignments
- `global_settings` — Admin user configuration

### 3. MockUserSession

The `UserSession` returned by the mocked `create_session_from_token` method. Represents an authenticated test user.

| Field | Type | Test Value | Description |
|-------|------|------------|-------------|
| `session_id` | `UUID` | Auto-generated | Unique session identifier |
| `github_user_id` | `str` | `"12345"` | Mock GitHub user ID |
| `github_username` | `str` | `"test-user"` | Mock GitHub username |
| `github_avatar_url` | `str \| None` | `"https://avatars.githubusercontent.com/u/12345"` | Mock avatar URL |
| `access_token` | `str` | `"ghp_test_access_token"` | Mock PAT (encrypted in DB) |
| `refresh_token` | `str \| None` | `None` | PATs don't have refresh tokens |
| `token_expires_at` | `datetime \| None` | `None` | PATs don't expire |
| `selected_project_id` | `str \| None` | `None` (initially) | Set via project selection |
| `active_app_name` | `str \| None` | `None` | Set via app context |
| `created_at` | `datetime` | Auto-generated | Session creation time |
| `updated_at` | `datetime` | Auto-generated | Last activity time |

### 4. MockGitHubProject

Mock data returned by `GitHubProjectsService` methods to simulate GitHub API responses.

| Field | Type | Test Value | Description |
|-------|------|------------|-------------|
| `project_id` | `str` | `"PVT_test123"` | GitHub Project V2 ID |
| `title` | `str` | `"Test Project"` | Project name |
| `number` | `int` | `1` | Project number |
| `url` | `str` | `"https://github.com/users/test-user/projects/1"` | Project URL |

### 5. MockBoardData

Mock board data returned for board operations tests.

| Field | Type | Description |
|-------|------|-------------|
| `columns` | `list[StatusOption]` | Board column definitions (e.g., Backlog, In Progress, Done) |
| `items` | `list[BoardItem]` | Tasks/issues on the board with column assignments |

### 6. MockChatResponse

Mock response from the chat agent service for chat flow tests.

| Field | Type | Description |
|-------|------|-------------|
| `message_id` | `UUID` | Response message ID |
| `content` | `str` | AI response text |
| `action_type` | `ActionType \| None` | Optional action (task_create, status_update) |
| `action_data` | `dict \| None` | Optional action payload |

## Relationships

```text
AuthenticatedTestClient
├── holds → session cookie (from dev-login response)
├── uses → TestDatabase (via dependency override)
├── sends requests to → FastAPI App
│   ├── /api/v1/auth/* → exercises real session middleware
│   ├── /api/v1/projects/* → exercises real auth + mocked GitHub API
│   ├── /api/v1/chat/* → exercises real auth + mocked AI agent
│   ├── /api/v1/pipelines/* → exercises real auth + real DB
│   └── /api/v1/board/* → exercises real auth + mocked GitHub API
└── validates → response status, body, cookie state

TestDatabase
├── stores → UserSession (encrypted tokens)
├── stores → ChatMessage records
├── stores → PipelineConfig records
├── stores → PipelineRun records
└── stores → PipelineAssignment records

MockUserSession
├── created by → mocked create_session_from_token
├── saved to → TestDatabase (by real session_store.save_session)
├── retrieved by → real session_store.get_session
└── deleted by → real session_store.delete_session (on logout)
```

## State Transitions Verified

### Session Lifecycle (User Story 1)

```text
[No Session] → POST /auth/dev-login → [Active Session + Cookie]
[Active Session] → GET /auth/me → [Active Session] (returns user info)
[Active Session] → POST /auth/logout → [No Session] (cookie cleared)
[No Session] → GET /auth/me → [401 Unauthorized]
[Expired Session] → GET /auth/me → [401 Unauthorized] (lazy deletion)
[Invalid Cookie] → GET /auth/me → [401 Unauthorized]
```

### Project Selection (User Story 2)

```text
[Authenticated, No Project] → GET /projects → [Project List]
[Authenticated, No Project] → POST /projects/{id}/select → [Project Selected]
[Project Selected] → GET /projects/{id} → [Project Details]
[Project Selected] → GET /projects/{id}/tasks → [Task List]
```

### Chat Flow (User Story 3)

```text
[No Project Selected] → POST /chat/messages → [Error: Project Required]
[Project Selected] → POST /chat/messages → [Message Stored + AI Response]
[Project Selected] → GET /chat/messages → [Chat History]
```

### Pipeline Lifecycle (User Story 4)

```text
[Authenticated] → GET /pipelines/{project_id} → [Pipeline List]
[Authenticated] → POST /pipelines/{project_id} → [Pipeline Created]
[Pipeline Created] → PUT /pipelines/{project_id}/{id}/assignment → [Assigned]
```

### Board Operations (User Story 5)

```text
[Project Selected] → GET /board/projects → [Board Project List]
[Project Selected] → GET /board/projects/{id} → [Board Data with Columns]
[Board Data] → PATCH /board/projects/{id}/items/{item_id}/status → [Status Updated]
```

## Validation Rules

| Rule | Applies To | Validation |
|------|-----------|------------|
| Session cookie required | All authenticated endpoints | Missing cookie → 401 |
| Valid session required | All authenticated endpoints | Invalid/expired session → 401 |
| Project selection required | Chat send, board operations | No `selected_project_id` → error |
| Project access required | Project-scoped operations | User must have access → 403 if not |
| Fresh DB per test | All E2E tests | Function-scoped fixture ensures isolation |
| No shared state | All E2E tests | Each test creates its own app + DB |
