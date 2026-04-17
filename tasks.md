# Tasks: Security, Privacy & Vulnerability Audit

**Input**: Design documents from `/specs/001-security-review/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Not explicitly requested in the feature specification. Verification is behavior-based per the audit verification checklist.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story. All 21 audit findings are mapped to their respective user stories.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Web app**: `solune/backend/src/`, `solune/frontend/src/`
- **Infrastructure**: `solune/docker-compose.yml`, `solune/frontend/Dockerfile`, `solune/backend/Dockerfile`
- **CI/CD**: `.github/workflows/`

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish secure development environment and validate tooling prerequisites

- [ ] T001 Review current codebase state against all 21 audit findings in specs/001-security-review/plan.md
- [ ] T002 [P] Verify Python 3.11+ with FastAPI, slowapi, and cryptography (Fernet) dependencies in solune/backend/pyproject.toml
- [ ] T003 [P] Verify Node.js 20+ with React 19 and Vite dependencies in solune/frontend/package.json
- [ ] T004 [P] Verify Docker and Docker Compose configuration supports non-root containers in solune/docker-compose.yml

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core security infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T005 Implement startup configuration validation framework in solune/backend/src/config.py with `_validate_production_settings()` that enforces mandatory secrets and secure defaults in non-debug mode
- [ ] T006 [P] Implement centralized project access verification dependency `verify_project_access()` in solune/backend/src/dependencies.py using FastAPI dependency injection
- [ ] T007 [P] Integrate slowapi rate limiting middleware into FastAPI application in solune/backend/src/main.py with Limiter instance and SlowAPIMiddleware
- [ ] T008 [P] Configure Fernet at-rest encryption service in solune/backend/src/services/encryption.py with legacy plaintext token detection via GitHub token prefix pattern

**Checkpoint**: Foundation ready — user story implementation can now begin in parallel

---

## Phase 3: User Story 1 — Secure Authentication Flow (Priority: P1) 🎯 MVP

**Goal**: Ensure OAuth session credentials never appear in URLs, browser history, proxy logs, or HTTP Referer headers. Sessions established exclusively through secure HttpOnly cookies.

**Independent Test**: After OAuth login, inspect browser URL bar, history, and network requests — no credentials present. Session cookie has HttpOnly, SameSite=Strict, and Secure attributes.

**Findings**: #1 (Critical — OWASP A02)

### Implementation for User Story 1

- [ ] T009 [US1] Implement `_set_session_cookie()` helper in solune/backend/src/api/auth.py that sets HttpOnly, SameSite=Strict, Secure cookie on the response
- [ ] T010 [US1] Modify OAuth callback handler in solune/backend/src/api/auth.py to redirect to frontend with no credentials in the URL, using `_set_session_cookie()` to deliver the session
- [ ] T011 [P] [US1] Ensure frontend `useAuth` hook in solune/frontend/src/hooks/useAuth.ts does not read or parse credentials from URL parameters
- [ ] T012 [US1] Verify cookie attributes (HttpOnly, SameSite=Strict, Secure) are correctly set by inspecting OAuth callback response headers

**Checkpoint**: User Story 1 complete — OAuth login produces no URL-visible credentials; session cookie is secure

---

## Phase 4: User Story 2 — Mandatory Encryption and Secret Enforcement (Priority: P1)

**Goal**: Application refuses to start in non-debug mode if critical security configuration is missing: ENCRYPTION_KEY, GITHUB_WEBHOOK_SECRET, SESSION_SECRET_KEY (≥64 chars), Secure cookies, and valid CORS origins.

**Independent Test**: Start backend in non-debug mode without each required secret — each scenario produces startup failure with clear error message.

**Findings**: #2 (Critical — OWASP A02), #9 (High — OWASP A07), #12 (Medium — OWASP A02), #16 (Medium — OWASP A05)

### Implementation for User Story 2

- [ ] T013 [US2] Enforce mandatory ENCRYPTION_KEY at startup in non-debug mode in solune/backend/src/config.py — refuse to start if missing
- [ ] T014 [P] [US2] Enforce mandatory GITHUB_WEBHOOK_SECRET at startup in non-debug mode in solune/backend/src/config.py — refuse to start if missing
- [ ] T015 [P] [US2] Enforce SESSION_SECRET_KEY minimum length of 64 characters at startup in solune/backend/src/config.py — refuse to start if shorter
- [ ] T016 [P] [US2] Enforce Secure cookie flag in non-debug mode in solune/backend/src/config.py via `effective_cookie_secure` property — refuse to start if not Secure
- [ ] T017 [P] [US2] Validate CORS origins as well-formed URLs with scheme and hostname in `cors_origins_list` property in solune/backend/src/config.py — refuse to start on malformed values
- [ ] T018 [US2] Ensure encryption service in solune/backend/src/services/encryption.py handles legacy plaintext token detection (GitHub token prefix matching) for migration path
- [ ] T019 [US2] Verify debug mode logs warnings instead of failing for missing configuration in solune/backend/src/config.py

**Checkpoint**: User Story 2 complete — production deployments cannot start without proper security configuration

---

## Phase 5: User Story 3 — Non-Root Container Execution (Priority: P1)

**Goal**: All application containers run as dedicated non-root system users, limiting blast radius of container compromise.

**Independent Test**: `docker exec <container> id` returns non-root UID for both frontend and backend containers.

**Findings**: #3 (Critical — OWASP A05)

### Implementation for User Story 3

- [ ] T020 [P] [US3] Configure frontend Dockerfile in solune/frontend/Dockerfile to create `nginx-app` non-root user with `addgroup -S` and `adduser -S`, set `USER nginx-app`, and use unprivileged port 8080
- [ ] T021 [P] [US3] Verify backend Dockerfile in solune/backend/Dockerfile creates and uses `appuser` non-root user
- [ ] T022 [US3] Update nginx configuration in solune/frontend/nginx.conf to listen on unprivileged port 8080 compatible with non-root execution

**Checkpoint**: User Story 3 complete — all containers run as non-root users

---

## Phase 6: User Story 4 — Project-Level Access Control (Priority: P2)

**Goal**: Every project-scoped endpoint verifies authenticated user ownership before any action. Unauthorized access returns 403 Forbidden with no data leakage.

**Independent Test**: Authenticate as User A, attempt operations on User B's project — all return 403 Forbidden.

**Findings**: #4 (High — OWASP A01)

### Implementation for User Story 4

- [ ] T023 [US4] Implement `verify_project_access()` dependency in solune/backend/src/dependencies.py with in-memory cache, GitHub API fallback, and 403 Forbidden response for unauthorized access
- [ ] T024 [P] [US4] Apply `verify_project_access()` to task endpoints in solune/backend/src/api/tasks.py via FastAPI Depends()
- [ ] T025 [P] [US4] Apply `verify_project_access()` to project endpoints in solune/backend/src/api/projects.py via FastAPI Depends()
- [ ] T026 [P] [US4] Apply `verify_project_access()` to settings endpoints in solune/backend/src/api/settings.py via FastAPI Depends()
- [ ] T027 [P] [US4] Apply `verify_project_access()` to workflow endpoints in solune/backend/src/api/workflow.py via FastAPI Depends()
- [ ] T028 [US4] Ensure WebSocket connections in project-scoped endpoints verify access before upgrade — reject unauthorized connections before any data is sent

**Checkpoint**: User Story 4 complete — all project-scoped endpoints enforce centralized access control

---

## Phase 7: User Story 5 — Secure Webhook and Secret Handling (Priority: P2)

**Goal**: All secret comparisons use constant-time algorithms. Webhook verification is mandatory regardless of debug mode. Dev login credentials arrive via POST body only.

**Independent Test**: Code review confirms `hmac.compare_digest()` usage. Webhooks without valid signatures rejected in both debug and non-debug mode.

**Findings**: #5 (High — OWASP A07), #7 (High — OWASP A02), #13 (Medium — OWASP A05)

### Implementation for User Story 5

- [ ] T029 [US5] Implement constant-time secret comparison using `hmac.compare_digest()` for Signal webhook verification in solune/backend/src/api/signal.py
- [ ] T030 [P] [US5] Verify GitHub webhook handler in solune/backend/src/api/webhooks.py uses `hmac.compare_digest()` for HMAC-SHA256 signature verification unconditionally (no debug bypass)
- [ ] T031 [P] [US5] Remove any debug-mode conditional bypass of webhook signature verification in solune/backend/src/api/webhooks.py — verification must always execute
- [ ] T032 [US5] Modify dev login endpoint in solune/backend/src/api/auth.py to accept credentials exclusively via POST request body (JSON), not URL parameters

**Checkpoint**: User Story 5 complete — all secret comparisons are constant-time; webhook verification is unconditional

---

## Phase 8: User Story 6 — HTTP Security Headers and Server Hardening (Priority: P2)

**Goal**: Frontend nginx responses include all modern security headers. No server version disclosure. Deprecated X-XSS-Protection removed.

**Independent Test**: `curl -I <frontend>` returns CSP, HSTS, Referrer-Policy, Permissions-Policy. No nginx version in Server header. X-XSS-Protection absent.

**Findings**: #6 (High — OWASP A05)

### Implementation for User Story 6

- [ ] T033 [US6] Add Content-Security-Policy header to solune/frontend/nginx.conf restricting default-src, script-src, style-src, img-src (self + avatars.githubusercontent.com), connect-src (self + ws/wss), frame-ancestors none
- [ ] T034 [P] [US6] Add Strict-Transport-Security header with max-age=31536000 and includeSubDomains to solune/frontend/nginx.conf
- [ ] T035 [P] [US6] Add Referrer-Policy (strict-origin-when-cross-origin) header to solune/frontend/nginx.conf
- [ ] T036 [P] [US6] Add Permissions-Policy (camera=(), microphone=(), geolocation=()) header to solune/frontend/nginx.conf
- [ ] T037 [P] [US6] Remove deprecated X-XSS-Protection header from solune/frontend/nginx.conf
- [ ] T038 [US6] Set `server_tokens off` directive in solune/frontend/nginx.conf to prevent nginx version disclosure

**Checkpoint**: User Story 6 complete — all security headers present; no version disclosure

---

## Phase 9: User Story 7 — Minimal OAuth Scopes (Priority: P2)

**Goal**: OAuth authorization requests only minimum necessary scopes. `repo` scope retained with documented rationale per research.md decision R7.

**Independent Test**: Inspect OAuth authorization URL for scope list. Verify all write operations function with current scopes.

**Findings**: #8 (High — OWASP A01)

### Implementation for User Story 7

- [ ] T039 [US7] Configure OAuth scopes to `read:user read:org project repo` in solune/backend/src/services/github_auth.py with inline documentation explaining rationale for `repo` scope retention
- [ ] T040 [US7] Verify all write operations (issue creation, label management, project board mutations) function correctly with configured scopes in staging

**Checkpoint**: User Story 7 complete — OAuth scopes documented and minimized within functional constraints

---

## Phase 10: User Story 8 — Secure Infrastructure Configuration (Priority: P2)

**Goal**: Docker services bind to 127.0.0.1 in development. Data volumes mounted at /var/lib/solune/data (outside application root). Database files created with restrictive permissions.

**Independent Test**: Inspect docker-compose.yml for 127.0.0.1 bindings. Verify database directory is 0700 and files are 0600. Confirm volume mount is outside app root.

**Findings**: #10 (High — OWASP A05), #15 (Medium — OWASP A02), #17 (Medium — OWASP A05)

### Implementation for User Story 8

- [ ] T041 [US8] Bind backend service port to `127.0.0.1:8000` in solune/docker-compose.yml instead of `0.0.0.0`
- [ ] T042 [P] [US8] Bind frontend service port to `127.0.0.1:5173` in solune/docker-compose.yml instead of `0.0.0.0`
- [ ] T043 [P] [US8] Mount data volume at `/var/lib/solune/data` using named volume `solune-data` in solune/docker-compose.yml (outside application root)
- [ ] T044 [US8] Create database directory with 0o700 permissions in solune/backend/src/database.py using `os.makedirs()` with explicit mode
- [ ] T045 [P] [US8] Set database file permissions to 0o600 in solune/backend/src/database.py using `os.chmod()` after file creation

**Checkpoint**: User Story 8 complete — infrastructure hardened with restrictive bindings, volumes, and permissions

---

## Phase 11: User Story 9 — Rate Limiting on Sensitive Endpoints (Priority: P3)

**Goal**: Per-user rate limits on write/AI endpoints and per-IP rate limit on OAuth callback. Returns 429 Too Many Requests when exceeded.

**Independent Test**: Exceed rate limit threshold on chat, agent, workflow, and OAuth callback endpoints — each returns 429.

**Findings**: #11 (Medium — OWASP A04)

### Implementation for User Story 9

- [ ] T046 [US9] Configure slowapi Limiter instance with in-memory storage in solune/backend/src/main.py and register SlowAPIMiddleware and SlowAPIASGIMiddleware
- [ ] T047 [P] [US9] Apply per-IP rate limit (20/minute) to OAuth callback endpoint in solune/backend/src/api/auth.py using slowapi @limiter.limit decorator
- [ ] T048 [P] [US9] Apply per-user rate limit (10/minute) to chat endpoints in solune/backend/src/api/chat.py using slowapi @limiter.limit decorator
- [ ] T049 [P] [US9] Apply per-user rate limit (5/minute) to agent invocation endpoints in solune/backend/src/api/agents.py using slowapi @limiter.limit decorator
- [ ] T050 [US9] Verify rate-limited endpoints return proper 429 response with Retry-After header when threshold is exceeded

**Checkpoint**: User Story 9 complete — all expensive/sensitive endpoints enforce rate limits

---

## Phase 12: User Story 10 — Secure Client-Side Data Handling (Priority: P3)

**Goal**: Chat history stored in-memory only (React state). No message content persisted to localStorage. Legacy localStorage data cleaned up on initialization. All local data cleared on logout.

**Independent Test**: After logout, localStorage contains no message content. Legacy `chat-message-history` key removed.

**Findings**: #18 (Medium — Privacy / OWASP A02)

### Implementation for User Story 10

- [ ] T051 [US10] Implement in-memory-only chat history in solune/frontend/src/hooks/useChatHistory.ts — messages stored as React state, never persisted to localStorage or sessionStorage
- [ ] T052 [P] [US10] Add `clearLegacyStorage('chat-message-history')` call on hook initialization in solune/frontend/src/hooks/useChatHistory.ts to remove pre-v2 localStorage data
- [ ] T053 [US10] Implement localStorage cleanup on logout in solune/frontend/src/hooks/useAuth.ts — clear all application data including any legacy storage keys

**Checkpoint**: User Story 10 complete — no sensitive data persists in browser storage after logout

---

## Phase 13: User Story 11 — Safe API Documentation and Error Handling (Priority: P3)

**Goal**: API docs gated on dedicated ENABLE_DOCS variable independent of DEBUG. GraphQL errors sanitized before API response — full details logged internally.

**Independent Test**: DEBUG=true without ENABLE_DOCS — docs return 404. Trigger GraphQL error — API returns generic message, full error in server logs.

**Findings**: #14 (Medium — OWASP A05), #19 (Medium — OWASP A09)

### Implementation for User Story 11

- [ ] T054 [P] [US11] Add `enable_docs: bool = False` configuration field in solune/backend/src/config.py gated on ENABLE_DOCS environment variable, independent of DEBUG
- [ ] T055 [US11] Gate Swagger/ReDoc endpoint availability on `settings.enable_docs` in solune/backend/src/main.py instead of DEBUG flag
- [ ] T056 [P] [US11] Sanitize GraphQL error responses in solune/backend/src/services/github_projects/service.py — log full error with `logger.error()`, raise generic `ValueError("GitHub API request failed")` to API consumers

**Checkpoint**: User Story 11 complete — API docs independently controlled; no internal error details exposed

---

## Phase 14: User Story 12 — Supply Chain and Injection Hardening (Priority: P4)

**Goal**: GitHub Actions workflows use minimum permissions with justification comments. Avatar URLs validated for HTTPS and known GitHub domains with placeholder fallback.

**Independent Test**: Review workflow permissions. Render issue card with non-GitHub avatar URL — placeholder displayed.

**Findings**: #20 (Low — Supply Chain), #21 (Low — OWASP A03)

### Implementation for User Story 12

- [ ] T057 [P] [US12] Set default `permissions: {}` at workflow level and grant only `issues: write` and `contents: read` at job level with justification comments in .github/workflows/branch-issue-link.yml
- [ ] T058 [P] [US12] Implement avatar URL validation in solune/frontend/src/components/board/IssueCard.tsx with `ALLOWED_AVATAR_HOSTS` allowlist (avatars.githubusercontent.com), HTTPS protocol check, and SVG placeholder fallback for invalid URLs

**Checkpoint**: User Story 12 complete — minimal workflow permissions; external URLs validated

---

## Phase 15: Polish & Cross-Cutting Concerns

**Purpose**: Final verification across all user stories and cross-cutting improvements

- [ ] T059 [P] Run behavior-based verification checklist from specs/001-security-review/quickstart.md against all 10 verification checks
- [ ] T060 [P] Verify all security behavioral contracts in specs/001-security-review/contracts/ are satisfied (security-headers.yaml, startup-validation.yaml, access-control.yaml, rate-limiting.yaml)
- [ ] T061 Run full backend test suite from solune/backend with `uv run pytest --cov=src --cov-report=term-missing` to confirm no regressions
- [ ] T062 [P] Run full frontend test suite from solune/frontend with `npm run test` and `npm run type-check` to confirm no regressions
- [ ] T063 [P] Run backend linting and security scanning with `uv run ruff check src tests` and `uv run bandit -r src/ -ll -ii` from solune/backend
- [ ] T064 Validate Docker build succeeds for both frontend and backend containers with `docker compose build` from solune/
- [ ] T065 Run quickstart.md verification steps: security headers check, container user check, database permissions check, port binding check

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Stories (Phases 3–14)**: All depend on Foundational phase completion
  - P1 stories (US1, US2, US3) can proceed in parallel
  - P2 stories (US4, US5, US6, US7, US8) can proceed in parallel after P1
  - P3 stories (US9, US10, US11) can proceed in parallel after P2
  - P4 stories (US12) can proceed after P3
  - Or all stories can run sequentially in priority order
- **Polish (Phase 15)**: Depends on all desired user stories being complete

### User Story Dependencies

- **US1 (P1)**: Depends on T005 (config validation) — no cross-story dependencies
- **US2 (P1)**: Depends on T005, T008 (config + encryption) — no cross-story dependencies
- **US3 (P1)**: No dependencies on other stories — standalone container configuration
- **US4 (P2)**: Depends on T006 (access control dependency) — no cross-story dependencies
- **US5 (P2)**: No dependencies on other stories — standalone webhook/secret changes
- **US6 (P2)**: No dependencies on other stories — standalone nginx configuration
- **US7 (P2)**: No dependencies on other stories — standalone OAuth scope configuration
- **US8 (P2)**: No dependencies on other stories — standalone infrastructure configuration
- **US9 (P3)**: Depends on T007 (rate limiting middleware) — no cross-story dependencies
- **US10 (P3)**: No dependencies on other stories — standalone frontend changes
- **US11 (P3)**: Depends on T005 (config for ENABLE_DOCS) — no cross-story dependencies
- **US12 (P4)**: No dependencies on other stories — standalone CI/frontend changes

### Within Each User Story

- Configuration/infrastructure before application code
- Backend changes before frontend changes (where both apply)
- Core implementation before integration verification
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel (T002, T003, T004)
- All Foundational tasks marked [P] can run in parallel (T006, T007, T008)
- P1 stories (US1, US2, US3) can all run in parallel — different files, no dependencies
- P2 stories (US4, US5, US6, US7, US8) can all run in parallel — different files, no dependencies
- P3 stories (US9, US10, US11) can all run in parallel — different files, no dependencies
- Within US4: endpoint tasks T024–T027 can all run in parallel (different API files)
- Within US6: header tasks T034–T037 can all run in parallel (additive changes to same config)
- Within US9: rate limit tasks T047–T049 can all run in parallel (different API files)
- Polish tasks T059, T060, T062, T063 can run in parallel

---

## Parallel Example: User Story 4 (Access Control)

```bash
# Launch all endpoint tasks in parallel (different files):
Task: "Apply verify_project_access() to task endpoints in solune/backend/src/api/tasks.py"
Task: "Apply verify_project_access() to project endpoints in solune/backend/src/api/projects.py"
Task: "Apply verify_project_access() to settings endpoints in solune/backend/src/api/settings.py"
Task: "Apply verify_project_access() to workflow endpoints in solune/backend/src/api/workflow.py"
```

## Parallel Example: P1 Stories (Critical)

```bash
# Launch all P1 stories in parallel (independent files and concerns):
Story US1: "Secure authentication flow — solune/backend/src/api/auth.py, solune/frontend/src/hooks/useAuth.ts"
Story US2: "Encryption enforcement — solune/backend/src/config.py, solune/backend/src/services/encryption.py"
Story US3: "Non-root containers — solune/frontend/Dockerfile, solune/backend/Dockerfile"
```

---

## Implementation Strategy

### MVP First (P1 Critical Stories Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: US1 — Secure Authentication Flow
4. Complete Phase 4: US2 — Mandatory Encryption Enforcement
5. Complete Phase 5: US3 — Non-Root Containers
6. **STOP and VALIDATE**: Run verification checks 1, 2, 3 from quickstart.md
7. Deploy/demo if ready — Critical findings resolved

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add P1 stories (US1, US2, US3) → Validate → Deploy (MVP — all Critical findings)
3. Add P2 stories (US4–US8) → Validate → Deploy (all High findings)
4. Add P3 stories (US9–US11) → Validate → Deploy (all Medium findings)
5. Add P4 story (US12) → Validate → Deploy (all Low findings)
6. Each priority tier adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: US1 (auth flow) + US5 (webhooks) — related auth/secret concerns
   - Developer B: US2 (config enforcement) + US11 (API docs/errors) — related config concerns
   - Developer C: US3 (containers) + US8 (infrastructure) — related Docker/infra concerns
   - Developer D: US4 (access control) + US9 (rate limiting) — related API middleware
   - Developer E: US6 (headers) + US7 (OAuth scopes) — related HTTP/auth concerns
   - Developer F: US10 (client storage) + US12 (supply chain) — related frontend/CI
3. Stories complete and integrate independently

---

## Summary

| Metric | Value |
|--------|-------|
| Total tasks | 65 |
| Setup tasks | 4 (T001–T004) |
| Foundational tasks | 4 (T005–T008) |
| US1 tasks (P1 — Auth Flow) | 4 (T009–T012) |
| US2 tasks (P1 — Encryption) | 7 (T013–T019) |
| US3 tasks (P1 — Containers) | 3 (T020–T022) |
| US4 tasks (P2 — Access Control) | 6 (T023–T028) |
| US5 tasks (P2 — Webhooks) | 4 (T029–T032) |
| US6 tasks (P2 — Headers) | 6 (T033–T038) |
| US7 tasks (P2 — OAuth Scopes) | 2 (T039–T040) |
| US8 tasks (P2 — Infrastructure) | 5 (T041–T045) |
| US9 tasks (P3 — Rate Limiting) | 5 (T046–T050) |
| US10 tasks (P3 — Client Storage) | 3 (T051–T053) |
| US11 tasks (P3 — Docs/Errors) | 3 (T054–T056) |
| US12 tasks (P4 — Supply Chain) | 2 (T057–T058) |
| Polish tasks | 7 (T059–T065) |
| Parallel opportunities | 36 tasks marked [P] |
| Independent stories | All 12 stories independently testable |
| Suggested MVP scope | US1 + US2 + US3 (P1 Critical — 14 tasks) |

---

## Notes

- [P] tasks = different files, no dependencies — safe to execute in parallel
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Plan notes all 21 findings already implemented — tasks serve as verification and implementation reference
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
