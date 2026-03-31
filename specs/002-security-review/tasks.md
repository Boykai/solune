# Tasks: Security, Privacy & Vulnerability Audit

**Input**: Design documents from `/specs/002-security-review/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Not explicitly requested. Verification is behavior-based per the 10-check verification checklist in quickstart.md.

**Organization**: Tasks are grouped by user story to enable independent verification and sign-off. All 21 security findings have been remediated — tasks focus on verification, documentation, and edge-case hardening.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Web app**: `solune/backend/src/`, `solune/frontend/src/`
- **Infrastructure**: `docker-compose.yml`, `solune/frontend/Dockerfile`, `solune/frontend/nginx.conf`
- **CI**: `.github/workflows/`

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish the verification framework and baseline for security audit sign-off

- [ ] T001 Create verification script skeleton at solune/scripts/verify-security.sh that orchestrates all 10 behavior-based checks from quickstart.md
- [ ] T002 [P] Document the security audit scope and findings summary in specs/002-security-review/tasks.md (this file)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Verify foundational security controls that ALL user stories depend on — startup validation gates, encryption infrastructure, and centralized authorization

**⚠️ CRITICAL**: No user story verification can be considered valid until these foundational controls are confirmed

- [ ] T003 Verify production startup validation rejects missing ENCRYPTION_KEY in solune/backend/src/config.py (lines 173–178)
- [ ] T004 [P] Verify production startup validation rejects missing GITHUB_WEBHOOK_SECRET in solune/backend/src/config.py (lines 173–178)
- [ ] T005 [P] Verify SESSION_SECRET_KEY minimum length check (64 chars) enforced in all modes in solune/backend/src/config.py (lines 184–189)
- [ ] T006 [P] Verify Fernet encryption service initializes correctly with valid ENCRYPTION_KEY in solune/backend/src/services/encryption.py (lines 18–110)
- [ ] T007 [P] Verify centralized verify_project_access dependency exists and is applied to all project-accepting endpoints in solune/backend/src/dependencies.py (lines 206–231)
- [ ] T008 Verify effective_cookie_secure production gate rejects insecure cookies in solune/backend/src/config.py (lines 190–194)
- [ ] T009 [P] Verify CORS origins validation rejects malformed origins at startup in solune/backend/src/config.py (lines 256–274)

**Checkpoint**: Foundation verified — all startup gates and shared dependencies confirmed operational

---

## Phase 3: User Story 1 — Secure Authentication Flow (Priority: P1) 🎯 MVP

**Goal**: Verify session credentials never appear in browser URL bar, history, server logs, or Referer headers

**Independent Test**: Complete a full OAuth login flow and confirm no credentials appear in the browser address bar, navigation history, or network request URLs

### Implementation for User Story 1

- [ ] T010 [US1] Verify OAuth callback sets HttpOnly, SameSite=Strict, Secure cookie and redirects with no credentials in URL in solune/backend/src/api/auth.py (lines 132–138)
- [ ] T011 [P] [US1] Verify frontend reads auth state from cookie-authenticated API calls, not URL params, in solune/frontend/src/hooks/useAuth.ts (lines 32–39)
- [ ] T012 [P] [US1] Verify dev login endpoint accepts credentials only via POST body (JSON) in solune/backend/src/api/auth.py (lines 184–206)
- [ ] T013 [US1] Verify dev login endpoint returns 404 in production mode (debug=false) in solune/backend/src/api/auth.py

**Checkpoint**: User Story 1 verified — OAuth flow is credential-safe

---

## Phase 4: User Story 2 — Mandatory Encryption and Secrets at Startup (Priority: P1)

**Goal**: Verify the application refuses to start in production without required secrets and provides plaintext token migration

**Independent Test**: Attempt to start the backend in non-debug mode without ENCRYPTION_KEY, GITHUB_WEBHOOK_SECRET, or with a short SESSION_SECRET_KEY — verify startup failure with clear error

### Implementation for User Story 2

- [ ] T014 [US2] Verify startup error message includes generation instructions for ENCRYPTION_KEY in solune/backend/src/config.py
- [ ] T015 [P] [US2] Verify legacy plaintext token detection (gho_, ghp_, ghr_, ghu_, ghs_, github_pat_ prefixes) in solune/backend/src/services/encryption.py (lines 18–110)
- [ ] T016 [US2] Verify transparent encryption-on-access migration for existing plaintext tokens in solune/backend/src/services/encryption.py

**Checkpoint**: User Story 2 verified — production deployments cannot run with missing secrets

---

## Phase 5: User Story 3 — Non-Root Container Execution (Priority: P1)

**Goal**: Verify all containers run as dedicated non-root system users

**Independent Test**: Build the frontend container and run `id` inside — verify non-root UID

### Implementation for User Story 3

- [ ] T017 [US3] Verify frontend Dockerfile creates nginx-app user and sets USER directive in solune/frontend/Dockerfile (lines 27–32, 41, 44)
- [ ] T018 [P] [US3] Verify nginx PID file moved to non-privileged path /tmp/nginx/nginx.pid in solune/frontend/Dockerfile
- [ ] T019 [US3] Verify frontend container exposes port 8080 (non-privileged) instead of 80 in solune/frontend/Dockerfile (line 44)

**Checkpoint**: User Story 3 verified — no container runs as root

---

## Phase 6: User Story 4 — Project-Level Authorization (Priority: P2)

**Goal**: Verify every project-accepting endpoint enforces ownership checks via centralized dependency

**Independent Test**: Authenticate as User A, then attempt to access User B's project by ID — verify 403 Forbidden

### Implementation for User Story 4

- [ ] T020 [US4] Verify verify_project_access is applied to tasks endpoints in solune/backend/src/api/tasks.py
- [ ] T021 [P] [US4] Verify verify_project_access is applied to projects endpoints in solune/backend/src/api/projects.py
- [ ] T022 [P] [US4] Verify verify_project_access is applied to settings endpoints in solune/backend/src/api/settings.py
- [ ] T023 [P] [US4] Verify verify_project_access is applied to workflow endpoints in solune/backend/src/api/workflow.py
- [ ] T024 [P] [US4] Verify verify_project_access is applied to agents endpoints in solune/backend/src/api/agents.py
- [ ] T025 [P] [US4] Verify verify_project_access is applied to activity and pipelines endpoints in solune/backend/src/api/activity.py and solune/backend/src/api/pipelines.py
- [ ] T026 [US4] Verify WebSocket connections validate project access before data transmission in solune/backend/src/api/projects.py

**Checkpoint**: User Story 4 verified — no cross-user project access is possible

---

## Phase 7: User Story 5 — HTTP Security Headers and Transport Hardening (Priority: P2)

**Goal**: Verify all required security headers are present and nginx version is hidden

**Independent Test**: `curl -I` the frontend and verify Content-Security-Policy, Strict-Transport-Security, Referrer-Policy, Permissions-Policy headers present; no nginx version in Server header

### Implementation for User Story 5

- [ ] T027 [US5] Verify Content-Security-Policy header restricts sources to 'self' with GitHub avatar allowance in solune/frontend/nginx.conf (lines 52–58)
- [ ] T028 [P] [US5] Verify Strict-Transport-Security header set to 1 year with includeSubDomains in solune/frontend/nginx.conf
- [ ] T029 [P] [US5] Verify Referrer-Policy set to strict-origin-when-cross-origin in solune/frontend/nginx.conf
- [ ] T030 [P] [US5] Verify Permissions-Policy disables camera, microphone, geolocation in solune/frontend/nginx.conf
- [ ] T031 [P] [US5] Verify server_tokens off hides nginx version in solune/frontend/nginx.conf (line 1)
- [ ] T032 [US5] Verify deprecated X-XSS-Protection header is absent from solune/frontend/nginx.conf

**Checkpoint**: User Story 5 verified — all security headers correct

---

## Phase 8: User Story 6 — Constant-Time Secret Comparison (Priority: P2)

**Goal**: Verify all secret/token comparisons use hmac.compare_digest

**Independent Test**: Code review confirms no `==` or `!=` operators on secrets

### Implementation for User Story 6

- [ ] T033 [US6] Verify Signal webhook uses hmac.compare_digest for secret comparison in solune/backend/src/api/signal.py (lines 9, 287–289)
- [ ] T034 [P] [US6] Verify GitHub webhook uses hmac.compare_digest in solune/backend/src/api/webhooks.py
- [ ] T035 [US6] Audit entire backend codebase for any remaining non-constant-time secret comparisons via grep for == or != adjacent to secret/token/key variables

**Checkpoint**: User Story 6 verified — no timing leaks in secret comparisons

---

## Phase 9: User Story 7 — Minimum OAuth Scopes (Priority: P2)

**Goal**: Verify OAuth scope rationale is documented and the intentional trade-off for retaining repo scope is justified

**Independent Test**: Review the OAuth authorization URL generation and verify scope documentation

### Implementation for User Story 7

- [ ] T036 [US7] Verify OAuth scope is documented with justification for retaining repo in solune/backend/src/services/github_auth.py (line 74)
- [ ] T037 [US7] Verify research.md documents the GitHub API limitation requiring repo scope in specs/002-security-review/research.md (RT-008)

**Checkpoint**: User Story 7 verified — scope trade-off documented and justified

---

## Phase 10: User Story 8 — Network Binding and Service Isolation (Priority: P2)

**Goal**: Verify Docker services bind to localhost only in development

**Independent Test**: Inspect docker-compose.yml and confirm 127.0.0.1 bindings

### Implementation for User Story 8

- [ ] T038 [US8] Verify backend port binding is 127.0.0.1:8000:8000 in docker-compose.yml (line 11)
- [ ] T039 [P] [US8] Verify frontend port binding is 127.0.0.1:5173:8080 in docker-compose.yml (line 68)
- [ ] T040 [US8] Verify internal services use expose instead of ports in docker-compose.yml

**Checkpoint**: User Story 8 verified — no services exposed on all interfaces

---

## Phase 11: User Story 9 — Rate Limiting on Sensitive Endpoints (Priority: P3)

**Goal**: Verify per-user and per-IP rate limits are enforced on expensive endpoints

**Independent Test**: Exceed rate limit threshold and confirm 429 Too Many Requests response

### Implementation for User Story 9

- [ ] T041 [US9] Verify slowapi rate limiting middleware is configured in solune/backend/src/middleware/rate_limit.py (lines 10–108)
- [ ] T042 [P] [US9] Verify per-IP rate limit on OAuth callback (20/minute) in solune/backend/src/api/auth.py (line 107)
- [ ] T043 [P] [US9] Verify per-user rate limits on chat endpoints in solune/backend/src/api/chat.py
- [ ] T044 [P] [US9] Verify per-user rate limits on agent endpoints in solune/backend/src/api/agents.py
- [ ] T045 [P] [US9] Verify per-user rate limits on workflow endpoints in solune/backend/src/api/workflow.py
- [ ] T046 [US9] Verify rate limit key resolution order: github_user_id → session cookie → IP address in solune/backend/src/middleware/rate_limit.py

**Checkpoint**: User Story 9 verified — rate limiting operational on all sensitive endpoints

---

## Phase 12: User Story 10 — Secure Cookie Configuration (Priority: P3)

**Goal**: Verify production startup rejects insecure cookie configuration

**Independent Test**: Start in non-debug mode without Secure cookie config — verify startup failure

### Implementation for User Story 10

- [ ] T047 [US10] Verify effective_cookie_secure auto-detects HTTPS from frontend_url in solune/backend/src/config.py (lines 301–308)
- [ ] T048 [US10] Verify production gate rejects cookies without Secure flag in solune/backend/src/config.py (lines 190–194)

**Checkpoint**: User Story 10 verified — cookies always Secure in production

---

## Phase 13: User Story 11 — Unconditional Webhook Signature Verification (Priority: P3)

**Goal**: Verify webhook verification is never bypassed by debug mode

**Independent Test**: Enable DEBUG without webhook secret — verify webhook requests are rejected

### Implementation for User Story 11

- [ ] T049 [US11] Verify webhook signature verification is unconditional in solune/backend/src/api/webhooks.py (lines 232–240)
- [ ] T050 [US11] Verify inline comment documents that developers must use a local test secret in solune/backend/src/api/webhooks.py

**Checkpoint**: User Story 11 verified — no debug bypass for webhooks

---

## Phase 14: User Story 12 — Independent API Docs Toggle (Priority: P3)

**Goal**: Verify API docs are gated on ENABLE_DOCS, not DEBUG

**Independent Test**: Set DEBUG=true, ENABLE_DOCS=false — verify /docs returns 404

### Implementation for User Story 12

- [ ] T051 [US12] Verify enable_docs environment variable exists with default False in solune/backend/src/config.py (line 95)
- [ ] T052 [US12] Verify FastAPI docs_url and redoc_url gated on enable_docs in solune/backend/src/main.py (lines 591–592)

**Checkpoint**: User Story 12 verified — docs visibility independent of debug mode

---

## Phase 15: User Story 13 — Secure Database File Permissions (Priority: P3)

**Goal**: Verify database directory is 0700 and database file is 0600

**Independent Test**: Start the application and inspect file permissions

### Implementation for User Story 13

- [ ] T053 [US13] Verify database directory created with 0o700 permissions in solune/backend/src/services/database.py (lines 32–42)
- [ ] T054 [P] [US13] Verify database file permissions set to 0o600 after creation in solune/backend/src/services/database.py (lines 50–56)
- [ ] T055 [US13] Verify error handling logs warning if permission changes fail in solune/backend/src/services/database.py

**Checkpoint**: User Story 13 verified — database files have restricted permissions

---

## Phase 16: User Story 14 — CORS Origins Validation (Priority: P3)

**Goal**: Verify CORS origins are validated at startup for scheme and hostname

**Independent Test**: Set a malformed CORS origin — verify startup failure

### Implementation for User Story 14

- [ ] T056 [US14] Verify cors_origins_list property validates each origin with urlparse in solune/backend/src/config.py (lines 256–274)
- [ ] T057 [US14] Verify malformed origins raise ValueError with descriptive message in solune/backend/src/config.py

**Checkpoint**: User Story 14 verified — no malformed CORS origins pass silently

---

## Phase 17: User Story 15 — Data Volume Isolation (Priority: P3)

**Goal**: Verify data volume is mounted outside application root

**Independent Test**: Inspect docker-compose.yml volume mount path

### Implementation for User Story 15

- [ ] T058 [US15] Verify data volume mounts at /var/lib/solune/data in docker-compose.yml (lines 46–47)
- [ ] T059 [US15] Verify DATABASE_PATH environment variable defaults to /var/lib/solune/data/settings.db in docker-compose.yml (line 37)

**Checkpoint**: User Story 15 verified — data isolated from application code

---

## Phase 18: User Story 16 — Secure Client-Side Chat Storage (Priority: P3)

**Goal**: Verify chat history uses memory-only storage and is cleared on logout

**Independent Test**: Send messages, log out, inspect localStorage — no message content remains

### Implementation for User Story 16

- [ ] T060 [US16] Verify useChatHistory stores messages in React state only (no localStorage) in solune/frontend/src/hooks/useChatHistory.ts (lines 63–79)
- [ ] T061 [P] [US16] Verify clearLegacyStorage removes pre-existing localStorage entries in solune/frontend/src/hooks/useChatHistory.ts (lines 41–55)
- [ ] T062 [US16] Verify clearChatHistory export is called on logout in solune/frontend/src/hooks/useChatHistory.ts

**Checkpoint**: User Story 16 verified — no chat content persists in browser storage

---

## Phase 19: User Story 17 — Sanitized Error Messages (Priority: P3)

**Goal**: Verify GraphQL errors are logged internally but only generic messages reach the API response

**Independent Test**: Trigger a GitHub GraphQL error and verify the response contains only a generic message

### Implementation for User Story 17

- [ ] T063 [US17] Verify GraphQL errors logged at ERROR level with full details in solune/backend/src/services/github_projects/service.py (lines 446–451)
- [ ] T064 [US17] Verify API responses contain only generic "GitHub API request failed" message in solune/backend/src/services/github_projects/service.py

**Checkpoint**: User Story 17 verified — no internal error details leak to clients

---

## Phase 20: User Story 18 — Minimum GitHub Actions Permissions (Priority: P4)

**Goal**: Verify workflow declares minimum permissions with justification comments

**Independent Test**: Review workflow YAML for scoped permissions

### Implementation for User Story 18

- [ ] T065 [US18] Verify top-level permissions: {} (empty) in .github/workflows/branch-issue-link.yml (lines 7–8)
- [ ] T066 [P] [US18] Verify job-level issues: write and contents: read with justification comments in .github/workflows/branch-issue-link.yml (lines 18–22)

**Checkpoint**: User Story 18 verified — minimal workflow permissions

---

## Phase 21: User Story 19 — Avatar URL Domain Validation (Priority: P4)

**Goal**: Verify avatar URLs are validated for HTTPS and known GitHub domains

**Independent Test**: Render an issue card with a non-GitHub avatar URL — verify placeholder displayed

### Implementation for User Story 19

- [ ] T067 [US19] Verify validateAvatarUrl checks https protocol and allowed hosts in solune/frontend/src/components/board/IssueCard.tsx (lines 15–35)
- [ ] T068 [P] [US19] Verify fallback to inline SVG placeholder on validation failure in solune/frontend/src/components/board/IssueCard.tsx (line 370)
- [ ] T069 [US19] Verify label color validation regex prevents CSS injection in solune/frontend/src/components/board/IssueCard.tsx

**Checkpoint**: User Story 19 verified — no unvalidated external image URLs

---

## Phase 22: Polish & Cross-Cutting Concerns

**Purpose**: Final verification sweep and documentation updates

- [ ] T070 Run the complete 10-check verification checklist from specs/002-security-review/quickstart.md
- [ ] T071 [P] Verify all 30 functional requirements (FR-001 through FR-030) from spec.md are traceable to implemented remediations
- [ ] T072 [P] Verify all 12 success criteria (SC-001 through SC-012) from spec.md are satisfied
- [ ] T073 Run solune/scripts/verify-security.sh to execute all automated verification checks
- [ ] T074 Document the OAuth repo scope trade-off decision in a visible location for future audits

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Stories (Phase 3–21)**: All depend on Foundational phase completion
  - P1 stories (US1–US3) should be verified first as the MVP
  - P2 stories (US4–US8) can proceed after P1 verification
  - P3 stories (US9–US17) can proceed after P2 verification
  - P4 stories (US18–US19) can proceed any time after Foundational
- **Polish (Phase 22)**: Depends on all user stories being verified

### User Story Dependencies

- **US1 (P1)**: Independent — verifies auth flow in isolation
- **US2 (P1)**: Independent — verifies startup validation gates
- **US3 (P1)**: Independent — verifies container configuration
- **US4 (P2)**: Depends on US1 (auth must work to test authorization)
- **US5 (P2)**: Independent — verifies nginx config only
- **US6 (P2)**: Independent — code review task
- **US7 (P2)**: Independent — documentation verification
- **US8 (P2)**: Independent — verifies docker-compose config
- **US9 (P3)**: Depends on US1 (auth required for per-user rate limits)
- **US10 (P3)**: Depends on US2 (part of startup validation)
- **US11 (P3)**: Independent — verifies webhook handler
- **US12 (P3)**: Independent — verifies docs toggle
- **US13 (P3)**: Independent — verifies file permissions
- **US14 (P3)**: Depends on US2 (part of startup validation)
- **US15 (P3)**: Independent — verifies docker-compose config
- **US16 (P3)**: Independent — verifies frontend hook
- **US17 (P3)**: Independent — verifies error handling
- **US18 (P4)**: Independent — verifies CI workflow
- **US19 (P4)**: Independent — verifies frontend component

### Within Each User Story

- Verify shared infrastructure first (dependencies.py, config.py)
- Verify backend implementation before frontend
- Verify individual files before cross-file integration
- Complete verification before marking story as done

### Parallel Opportunities

- All Foundational tasks marked [P] can run in parallel (T004–T009)
- Within US4: All endpoint checks (T021–T025) can run in parallel
- Within US5: All header checks (T028–T031) can run in parallel
- Within US9: All endpoint rate limit checks (T043–T045) can run in parallel
- Independent stories can be verified in parallel by different reviewers
- P4 stories (US18, US19) can start immediately after Foundational

---

## Parallel Example: User Story 4

```bash
# Launch all endpoint authorization checks together:
Task: "Verify verify_project_access in projects endpoints — solune/backend/src/api/projects.py"
Task: "Verify verify_project_access in settings endpoints — solune/backend/src/api/settings.py"
Task: "Verify verify_project_access in workflow endpoints — solune/backend/src/api/workflow.py"
Task: "Verify verify_project_access in agents endpoints — solune/backend/src/api/agents.py"
Task: "Verify verify_project_access in activity/pipelines — solune/backend/src/api/activity.py"
```

## Parallel Example: User Story 5

```bash
# Launch all security header checks together:
Task: "Verify Strict-Transport-Security in nginx.conf"
Task: "Verify Referrer-Policy in nginx.conf"
Task: "Verify Permissions-Policy in nginx.conf"
Task: "Verify server_tokens off in nginx.conf"
```

---

## Implementation Strategy

### MVP First (P1 Stories Only)

1. Complete Phase 1: Setup (verification framework)
2. Complete Phase 2: Foundational (startup gates confirmed)
3. Complete Phases 3–5: User Stories 1–3 (auth flow, encryption, non-root containers)
4. **STOP and VALIDATE**: Run quickstart.md checks 1–3
5. Sign off P1 — Critical findings verified

### Incremental Delivery

1. Complete Setup + Foundational → Verification baseline established
2. Verify US1–US3 (P1) → Critical findings confirmed → MVP sign-off
3. Verify US4–US8 (P2) → High findings confirmed → Run checks 4–7
4. Verify US9–US17 (P3) → Medium findings confirmed → Run checks 8–10
5. Verify US18–US19 (P4) → Low findings confirmed → Full audit sign-off

### Parallel Team Strategy

With multiple reviewers:

1. Team confirms Foundational phase together
2. Once Foundational is done:
   - Reviewer A: US1 (auth flow) + US2 (startup validation) + US3 (containers)
   - Reviewer B: US4 (authorization) + US5 (headers) + US6 (timing)
   - Reviewer C: US7 (scopes) + US8 (network) + US9 (rate limits)
   - Reviewer D: US10–US17 (remaining medium findings)
   - Reviewer E: US18–US19 (low findings)
3. All reviewers sign off independently per story

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- All 21 findings already remediated — tasks verify existing remediations
- OAuth `repo` scope intentionally retained (GitHub API limitation) — see research.md RT-008
- Verification is behavior-based: use quickstart.md checks for end-to-end validation
- Commit verification evidence after each story checkpoint
- Stop at any checkpoint to validate story independently
