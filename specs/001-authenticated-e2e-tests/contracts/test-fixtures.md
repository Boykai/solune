# Test Fixture Contracts: Authenticated E2E Tests

**Feature**: `001-authenticated-e2e-tests` | **Date**: 2026-03-30

## Overview

This document defines the contracts for the test fixtures used by the authenticated E2E test suite. These contracts specify the interface, behavior, and guarantees of each fixture so that test authors can rely on them consistently.

## Fixture Contracts

### 1. `auth_client` — Authenticated HTTP Client

**Type**: `httpx.AsyncClient`  
**Scope**: Function (fresh per test)  
**Location**: `tests/e2e/conftest.py`

**Guarantees**:
- Client holds a valid `session_id` cookie obtained via `POST /api/v1/auth/dev-login`
- All requests sent through this client are authenticated
- The underlying FastAPI app is a full `create_app()` instance with all middleware active
- External services (GitHub API, AI agents, WebSocket) are mocked
- Internal services (session store, database, auth middleware) are real
- The database is a fresh in-memory SQLite with all migrations applied

**Pre-conditions**:
- `TESTING=1` environment variable is set (disables rate limiting)
- `DEBUG=true` environment variable is set (enables dev-login endpoint)
- `DATABASE_PATH=:memory:` environment variable is set

**Post-conditions**:
- Client is closed after the test
- Database connection is closed after the test
- All dependency overrides are cleared

**Mock User Properties**:
| Field | Value |
|-------|-------|
| `github_user_id` | `"12345"` |
| `github_username` | `"test-user"` |
| `github_avatar_url` | `"https://avatars.githubusercontent.com/u/12345"` |
| `access_token` | `"ghp_test_access_token"` |
| `selected_project_id` | `None` (initially) |

### 2. `unauthenticated_client` — Unauthenticated HTTP Client

**Type**: `httpx.AsyncClient`  
**Scope**: Function (fresh per test)  
**Location**: `tests/e2e/conftest.py`

**Guarantees**:
- Client has no session cookie set
- Requests to authenticated endpoints return 401
- Same app and database configuration as `auth_client`

### 3. `test_db` — Test Database Connection

**Type**: `aiosqlite.Connection`  
**Scope**: Function (fresh per test)  
**Location**: `tests/e2e/conftest.py`

**Guarantees**:
- In-memory SQLite database
- All migrations from `src/migrations/*.sql` applied in sorted order
- Shared with the `auth_client` fixture (same database instance)
- Can be queried directly for assertion purposes

### 4. `mock_github_projects_service` — Mocked GitHub API

**Type**: `AsyncMock` (spec: `GitHubProjectsService`)  
**Scope**: Function  
**Location**: `tests/e2e/conftest.py`

**Guarantees**:
- All methods return `AsyncMock` instances by default
- Common methods pre-configured with sensible defaults (via `make_mock_github_service()`)
- Can be customized per-test by setting `.return_value` on individual methods

**Pre-configured Returns**:
| Method | Default Return |
|--------|---------------|
| `list_user_projects` | Empty list `[]` |
| `get_project_repository` | `("owner", "repo")` |
| `create_issue` | `{"id": 300042, "number": 42, ...}` |

### 5. `mock_chat_agent_service` — Mocked AI Agent

**Type**: `AsyncMock` (spec: `ChatAgentService`)  
**Scope**: Function  
**Location**: `tests/e2e/conftest.py`

**Guarantees**:
- `run()` method returns a mock `ChatMessage` by default
- `run_stream()` method returns an async generator by default
- No external AI API calls are made

## Endpoint Contracts Exercised

### Authentication Endpoints

| Method | Path | Auth Required | Request Body | Success Response | Error Response |
|--------|------|--------------|--------------|-----------------|----------------|
| POST | `/api/v1/auth/dev-login` | No | `{"github_token": "..."}` | 200 + `UserResponse` + session cookie | 404 (prod mode) |
| GET | `/api/v1/auth/me` | Yes | — | 200 + `UserResponse` | 401 |
| POST | `/api/v1/auth/logout` | Optional | — | 200 + `{"message": "..."}` | — |

### Project Endpoints

| Method | Path | Auth Required | Request Body | Success Response | Error Response |
|--------|------|--------------|--------------|-----------------|----------------|
| GET | `/api/v1/projects` | Yes | — | 200 + project list | 401 |
| GET | `/api/v1/projects/{id}` | Yes | — | 200 + project details | 401, 403 |
| GET | `/api/v1/projects/{id}/tasks` | Yes | — | 200 + task list | 401, 403 |
| POST | `/api/v1/projects/{id}/select` | Yes | — | 200 + `UserResponse` | 401, 403 |

### Chat Endpoints

| Method | Path | Auth Required | Project Required | Request Body | Success Response |
|--------|------|--------------|-----------------|--------------|-----------------|
| POST | `/api/v1/chat/messages` | Yes | Yes | `{"content": "..."}` | 200 + `ChatMessage` |
| GET | `/api/v1/chat/messages` | Yes | No | — | 200 + `ChatMessagesResponse` |

### Pipeline Endpoints

| Method | Path | Auth Required | Request Body | Success Response |
|--------|------|--------------|--------------|-----------------|
| GET | `/api/v1/pipelines/{project_id}` | Yes | — | 200 + pipeline list |
| POST | `/api/v1/pipelines/{project_id}` | Yes | `PipelineConfigCreate` | 200 + `PipelineConfig` |
| PUT | `/api/v1/pipelines/{project_id}/{id}/assignment` | Yes | `ProjectPipelineAssignment` | 200 |

### Board Endpoints

| Method | Path | Auth Required | Request Body | Success Response |
|--------|------|--------------|--------------|-----------------|
| GET | `/api/v1/board/projects` | Yes | — | 200 + board project list |
| GET | `/api/v1/board/projects/{id}` | Yes | — | 200 + `BoardDataResponse` |
| PATCH | `/api/v1/board/projects/{id}/items/{item_id}/status` | Yes | `{"status": "..."}` | 200 + `StatusUpdateResponse` |

## Test Data Conventions

### Naming Convention

| Entity | Convention | Example |
|--------|-----------|---------|
| GitHub user ID | `"12345"` | Fixed across all tests |
| GitHub username | `"test-user"` | Fixed across all tests |
| Project ID | `"PVT_test{N}"` | `"PVT_test123"`, `"PVT_test456"` |
| Pipeline name | `"Test Pipeline {N}"` | `"Test Pipeline 1"` |
| Chat message | `"Test message {context}"` | `"Test message for chat flow"` |

### Session Cookie Name

The session cookie name is defined in `src/api/auth.py` as `SESSION_COOKIE_NAME`. Tests should import this constant rather than hardcoding it.
