# Feature Specification: Security, Privacy & Vulnerability Audit

**Feature Branch**: `001-security-review`  
**Created**: 2026-04-17  
**Status**: Draft  
**Input**: User description: "Security, Privacy & Vulnerability Audit — 3 Critical · 8 High · 9 Medium · 2 Low findings across OWASP Top 10"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Secure Authentication Flow (Priority: P1)

As a user logging in via OAuth, I expect my session credentials to never appear in the browser URL bar, browser history, proxy logs, or HTTP Referer headers. Instead, my session is established through a secure, HttpOnly cookie set directly by the server.

**Why this priority**: Credential leakage via URL is the most immediately exploitable vulnerability (OWASP A02 — Critical). Any party with access to browser history, proxy logs, or downstream servers receiving the Referer header can hijack sessions.

**Independent Test**: After completing an OAuth login, inspect the browser URL bar, browser history, and network requests to confirm no credentials are present. Verify the session cookie has HttpOnly, SameSite=Strict, and Secure attributes.

**Acceptance Scenarios**:

1. **Given** a user initiates OAuth login, **When** the OAuth callback completes, **Then** the browser is redirected to the frontend with no credentials in the URL and a session cookie is set with HttpOnly, SameSite=Strict, and Secure flags.
2. **Given** a user has logged in, **When** the browser history is inspected, **Then** no session tokens or credentials appear in any URL entry.
3. **Given** the frontend application, **When** any page is loaded, **Then** the frontend does not read or parse credentials from URL parameters.

---

### User Story 2 - Mandatory Encryption and Secret Enforcement (Priority: P1)

As a system operator deploying the application in production, I expect the system to refuse to start if critical security configuration is missing — specifically the encryption key for at-rest data, the webhook secret, and the session secret key. This prevents accidental deployment in an insecure state.

**Why this priority**: Running without encryption or with weak secrets in production silently exposes all stored OAuth tokens and allows unauthenticated webhook invocations. This is a Critical (OWASP A02) and High (OWASP A07) finding combined.

**Independent Test**: Attempt to start the backend in non-debug mode without ENCRYPTION_KEY, without GITHUB_WEBHOOK_SECRET, and with a SESSION_SECRET_KEY shorter than 64 characters. Confirm each scenario results in a startup failure with a clear error message.

**Acceptance Scenarios**:

1. **Given** non-debug mode and no ENCRYPTION_KEY configured, **When** the application starts, **Then** it refuses to start and displays a clear error about the missing encryption key.
2. **Given** non-debug mode and no GITHUB_WEBHOOK_SECRET configured, **When** the application starts, **Then** it refuses to start and displays a clear error about the missing webhook secret.
3. **Given** a SESSION_SECRET_KEY shorter than 64 characters, **When** the application starts, **Then** it refuses to start and displays an error about insufficient key length.
4. **Given** non-debug mode and cookies not configured as Secure, **When** the application starts, **Then** it refuses to start and displays an error about insecure cookie configuration.
5. **Given** CORS origins containing a malformed URL, **When** the application starts, **Then** it refuses to start and displays an error identifying the malformed origin.

---

### User Story 3 - Non-Root Container Execution (Priority: P1)

As a system operator, I expect all application containers to run as a dedicated non-root system user, so that a container escape or vulnerability cannot lead to root-level access on the host.

**Why this priority**: Running containers as root (OWASP A05 — Critical) is one of the most commonly exploited container misconfigurations. The backend already runs as non-root; the frontend must match.

**Independent Test**: Run `docker exec` into the frontend container and confirm the `id` command returns a non-root UID.

**Acceptance Scenarios**:

1. **Given** the frontend container is running, **When** `id` is executed inside the container, **Then** the output shows a non-root UID (not uid=0).
2. **Given** any container in the stack, **When** the container is inspected, **Then** it runs as a dedicated application user, not root.

---

### User Story 4 - Project-Level Access Control (Priority: P2)

As an authenticated user, I expect that I can only access, modify, and subscribe to projects I own. If I attempt to interact with a project I don't own — even by guessing its ID — I should be denied access.

**Why this priority**: Broken access control (OWASP A01 — High) allows any authenticated user to access or modify any other user's projects, leading to data breach and integrity violations.

**Independent Test**: Authenticate as User A, attempt to create a task in User B's project, subscribe to User B's project WebSocket, and modify User B's project settings. Confirm all attempts return 403 Forbidden.

**Acceptance Scenarios**:

1. **Given** an authenticated user without access to a project, **When** they attempt to create a task in that project, **Then** the system returns 403 Forbidden.
2. **Given** an authenticated user without access to a project, **When** they attempt to connect to that project's WebSocket, **Then** the connection is rejected before any data is sent.
3. **Given** an authenticated user without access to a project, **When** they attempt to modify project settings or trigger workflows, **Then** the system returns 403 Forbidden.
4. **Given** any endpoint accepting a project identifier, **When** a request is made, **Then** the system verifies the session's access to that project through a centralized authorization check before performing any action.

---

### User Story 5 - Secure Webhook and Secret Handling (Priority: P2)

As a system integrator sending webhooks to the application, I expect all secret comparisons to use constant-time algorithms and webhook verification to be mandatory regardless of debug mode settings.

**Why this priority**: Timing attacks (OWASP A07 — High) and debug-mode bypasses (OWASP A05 — Medium) can allow unauthenticated callers to trigger workflows and extract secret information.

**Independent Test**: Code review confirms all secret/token comparisons use constant-time functions. Attempt to invoke webhooks without valid signatures in both debug and non-debug mode; confirm both are rejected.

**Acceptance Scenarios**:

1. **Given** a Signal webhook request with an invalid signature, **When** the webhook endpoint processes it, **Then** it is rejected using constant-time comparison.
2. **Given** debug mode is enabled, **When** a webhook arrives without a valid signature, **Then** it is rejected (debug mode does not bypass verification).
3. **Given** any secret comparison in the codebase, **When** reviewed, **Then** it uses a constant-time comparison function.
4. **Given** the dev login endpoint, **When** credentials are submitted, **Then** they must arrive in the POST request body (JSON), never in the URL.

---

### User Story 6 - HTTP Security Headers and Server Hardening (Priority: P2)

As a user browsing the application, I expect the server to include modern security headers that protect against common web attacks, and to not reveal its software version.

**Why this priority**: Missing security headers (OWASP A05 — High) leave users exposed to clickjacking, XSS, and man-in-the-middle attacks. Version disclosure helps attackers target known vulnerabilities.

**Independent Test**: Send a HEAD request to the frontend and verify Content-Security-Policy, Strict-Transport-Security, Referrer-Policy, and Permissions-Policy headers are present. Confirm no server version is disclosed and X-XSS-Protection is absent.

**Acceptance Scenarios**:

1. **Given** an HTTP request to the frontend, **When** response headers are inspected, **Then** Content-Security-Policy, Strict-Transport-Security, Referrer-Policy, and Permissions-Policy headers are all present.
2. **Given** an HTTP response from the frontend, **When** the Server header is inspected, **Then** it does not include the nginx version.
3. **Given** the nginx configuration, **When** it is reviewed, **Then** the deprecated X-XSS-Protection header has been removed and `server_tokens off` is set.

---

### User Story 7 - Minimal OAuth Scopes (Priority: P2)

As a user connecting my GitHub account, I expect the application to request only the minimum OAuth permissions necessary for its functionality, not broad access to all my private repositories.

**Why this priority**: Over-privileged OAuth scopes (OWASP A01 — High) grant the application access far beyond what it needs, increasing the blast radius of any token compromise.

**Independent Test**: Inspect the OAuth authorization URL and confirm it requests only the minimum necessary scopes (not the broad `repo` scope). Verify all application features still function correctly with narrower scopes.

**Acceptance Scenarios**:

1. **Given** the OAuth authorization flow, **When** the authorization URL is constructed, **Then** it requests only the minimum necessary scopes for project management functionality.
2. **Given** narrower OAuth scopes are in use, **When** all write operations are exercised, **Then** they function correctly.
3. **Given** an existing user with the old broad scope, **When** the scope changes are deployed, **Then** the user is prompted to re-authorize with the new scopes.

---

### User Story 8 - Secure Infrastructure Configuration (Priority: P2)

As a system operator, I expect Docker services to be bound to secure network interfaces and data volumes to be mounted outside the application directory with restrictive file permissions.

**Why this priority**: Services bound to all interfaces (OWASP A05 — High) and world-readable database files (OWASP A02 — Medium) expose sensitive data to anyone on the network or host system.

**Independent Test**: Inspect docker-compose.yml to confirm development services bind to 127.0.0.1. Verify database directory permissions are 0700 and file permissions are 0600. Confirm data volumes are mounted outside the application root.

**Acceptance Scenarios**:

1. **Given** the development Docker configuration, **When** services are started, **Then** backend and frontend ports are bound to 127.0.0.1 only.
2. **Given** the production Docker configuration, **When** services are deployed, **Then** backend and frontend are not directly exposed via container ports (only via reverse proxy).
3. **Given** the database is initialized, **When** directory and file permissions are checked, **Then** the directory has 0700 and the database file has 0600 permissions.
4. **Given** the Docker data volume, **When** the mount point is inspected, **Then** it is mounted outside the application root (e.g., /var/lib/solune/data).

---

### User Story 9 - Rate Limiting on Sensitive Endpoints (Priority: P3)

As a user and system operator, I expect expensive and sensitive endpoints to enforce rate limits, preventing a single user or IP from exhausting shared resources such as AI quotas and GitHub API limits.

**Why this priority**: Without rate limiting (OWASP A04 — Medium), any single user can exhaust shared quotas affecting all users, and the OAuth callback can be used for brute-force attacks.

**Independent Test**: Exceed the rate limit threshold on chat, agent invocation, workflow, and OAuth callback endpoints. Confirm each returns 429 Too Many Requests after the threshold.

**Acceptance Scenarios**:

1. **Given** a user making rapid requests to AI-powered endpoints, **When** the per-user rate limit is exceeded, **Then** subsequent requests return 429 Too Many Requests.
2. **Given** multiple requests to the OAuth callback from a single IP, **When** the per-IP rate limit is exceeded, **Then** subsequent requests return 429 Too Many Requests.
3. **Given** rate-limited endpoints, **When** limits are applied, **Then** per-user limits are preferred over per-IP to avoid penalizing users behind shared NAT or VPN.

---

### User Story 10 - Secure Client-Side Data Handling (Priority: P3)

As a user, I expect that sensitive data such as chat history is not stored indefinitely in my browser's local storage, and that all local data is cleared when I log out.

**Why this priority**: Unencrypted, indefinitely-stored chat content in localStorage (Privacy / OWASP A02 — Medium) survives logout and is readable by any XSS attack.

**Independent Test**: Log in, send messages, then log out. Verify localStorage contains no message content. Verify only lightweight references with a TTL are stored during an active session.

**Acceptance Scenarios**:

1. **Given** a logged-in user with chat history, **When** inspecting localStorage, **Then** only lightweight message references (IDs) are stored, not full message content.
2. **Given** stored message references, **When** their TTL expires, **Then** they are automatically removed from localStorage.
3. **Given** a user logs out, **When** localStorage is inspected, **Then** all application data including message references has been cleared.
4. **Given** a user needs to view chat history, **When** they open a conversation, **Then** message content is loaded on demand from the backend.

---

### User Story 11 - Safe API Documentation and Error Handling (Priority: P3)

As a developer and operator, I expect API documentation visibility to be controlled independently of debug mode, and internal error details to never be exposed to API consumers.

**Why this priority**: Debug-gated API docs (OWASP A05 — Medium) and exposed internal errors (OWASP A09 — Medium) leak system internals to potential attackers.

**Independent Test**: Enable debug mode and verify API docs are not exposed unless ENABLE_DOCS is explicitly set. Trigger a GitHub GraphQL error and verify the API response contains only a generic message while the full error is logged internally.

**Acceptance Scenarios**:

1. **Given** DEBUG=true and ENABLE_DOCS not set, **When** accessing Swagger/ReDoc URLs, **Then** they return 404 (docs are not available).
2. **Given** ENABLE_DOCS=true, **When** accessing Swagger/ReDoc URLs, **Then** the API documentation is available regardless of DEBUG setting.
3. **Given** a GitHub GraphQL API error occurs, **When** the error is returned to the API consumer, **Then** only a generic, sanitized error message is provided.
4. **Given** a GitHub GraphQL API error occurs, **When** the server logs are checked, **Then** the full error details are logged for debugging purposes.

---

### User Story 12 - Supply Chain and Injection Hardening (Priority: P4)

As a system operator and contributor, I expect GitHub Actions workflows to use minimum necessary permissions, and external user-provided content (like avatar URLs) to be validated before rendering.

**Why this priority**: Overly broad workflow permissions (Supply Chain — Low) and unvalidated external URLs (OWASP A03 — Low) are lower-severity but still represent defense-in-depth gaps.

**Independent Test**: Review the GitHub Actions workflow file to confirm minimal permissions with justification comments. Render an issue card with a non-GitHub avatar URL and confirm it falls back to a placeholder.

**Acceptance Scenarios**:

1. **Given** the branch-issue-link workflow, **When** its permissions are reviewed, **Then** it has the minimum required scope with a justification comment.
2. **Given** an issue card with a GitHub avatar URL, **When** the card renders, **Then** the avatar is displayed normally.
3. **Given** an issue card with a non-HTTPS or non-GitHub-domain avatar URL, **When** the card renders, **Then** a placeholder image is displayed instead.

---

### Edge Cases

- What happens when an existing deployment has plaintext-encrypted tokens and ENCRYPTION_KEY is now mandatory? A migration path must be provided to re-encrypt existing rows.
- What happens when the OAuth scope is narrowed and existing users have tokens with the old broad scope? Users must be prompted to re-authorize.
- What happens when rate limits are hit by users behind shared NAT/VPN? Per-user limits are preferred to avoid penalizing shared-IP environments.
- What happens when the dev login endpoint is called in production? Even dev-only credential inputs must use POST body, not URL parameters.
- What happens when debug mode is accidentally enabled in production? Webhook verification must never be conditional on debug mode, and API docs must require an independent ENABLE_DOCS toggle.
- What happens when CORS origins contain trailing slashes, extra spaces, or missing schemes? Startup validation must reject malformed origins with a clear error.

## Requirements *(mandatory)*

### Functional Requirements

#### Phase 1 — Critical

- **FR-001**: System MUST establish user sessions via HttpOnly, SameSite=Strict, Secure cookies set directly on the OAuth callback response, with no credentials in the redirect URL.
- **FR-002**: Frontend MUST NOT read or parse credentials from URL parameters.
- **FR-003**: System MUST refuse to start in non-debug mode if ENCRYPTION_KEY is not configured.
- **FR-004**: System MUST refuse to start in non-debug mode if GITHUB_WEBHOOK_SECRET is not configured.
- **FR-005**: All containers MUST run as a dedicated non-root system user.

#### Phase 2 — High

- **FR-006**: Every endpoint accepting a project identifier MUST verify the authenticated user's access to that project before performing any action, through a centralized authorization check.
- **FR-007**: WebSocket connections to unowned projects MUST be rejected before any data is sent.
- **FR-008**: All secret and token comparisons MUST use constant-time comparison functions.
- **FR-009**: The frontend MUST include Content-Security-Policy, Strict-Transport-Security, Referrer-Policy, and Permissions-Policy headers in all responses.
- **FR-010**: The frontend MUST NOT include the deprecated X-XSS-Protection header and MUST set `server_tokens off`.
- **FR-011**: The dev login endpoint MUST accept credentials only in the POST request body (JSON), never in URL parameters.
- **FR-012**: The OAuth authorization flow MUST request only the minimum necessary scopes for project management functionality.
- **FR-013**: System MUST reject SESSION_SECRET_KEY values shorter than 64 characters at startup.
- **FR-014**: Development Docker services MUST bind to 127.0.0.1, not 0.0.0.0.

#### Phase 3 — Medium

- **FR-015**: AI-powered and write endpoints MUST enforce per-user rate limits, returning 429 Too Many Requests when exceeded.
- **FR-016**: The OAuth callback MUST enforce per-IP rate limits.
- **FR-017**: System MUST refuse to start in non-debug mode if cookies are not configured as Secure.
- **FR-018**: Webhook signature verification MUST NOT be conditional on debug mode. Developers MUST use a locally configured test secret.
- **FR-019**: API documentation availability MUST be gated on a dedicated ENABLE_DOCS environment variable, independent of DEBUG.
- **FR-020**: The database directory MUST be created with 0700 permissions and database files with 0600 permissions.
- **FR-021**: CORS origins MUST be validated as well-formed URLs with scheme and hostname at startup; malformed values MUST cause startup failure.
- **FR-022**: Docker data volumes MUST be mounted outside the application root directory.
- **FR-023**: Chat history in localStorage MUST store only lightweight references (message IDs) with a TTL, not full message content.
- **FR-024**: All local application data MUST be cleared on user logout.
- **FR-025**: GraphQL API errors MUST be sanitized before being returned to the API consumer; full details MUST be logged internally.

#### Phase 4 — Low

- **FR-026**: GitHub Actions workflows MUST use the minimum required permissions with justification comments.
- **FR-027**: External avatar URLs MUST be validated for HTTPS protocol and known GitHub avatar domains; invalid URLs MUST fall back to a placeholder image.

### Key Entities *(include if feature involves data)*

- **Session**: Represents an authenticated user's session. Established via HttpOnly cookie (not URL token). Associated with a specific user and their authorized projects.
- **Project Authorization**: Represents the relationship between a user and the projects they have access to. Used by the centralized authorization check for all project-scoped endpoints.
- **Rate Limit Counter**: Tracks request counts per user (for write/AI endpoints) and per IP (for OAuth callback). Enforces configurable thresholds with 429 responses when exceeded.
- **Chat Reference**: A lightweight pointer (message ID + TTL) stored in localStorage, replacing the current full-content storage. Content is loaded on demand from the backend.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: After login, no credentials appear in the browser URL bar, browser history, or server access logs — verified by inspection of 100% of OAuth login flows.
- **SC-002**: The backend refuses to start within 5 seconds when critical configuration (ENCRYPTION_KEY, GITHUB_WEBHOOK_SECRET, SESSION_SECRET_KEY, Secure cookies) is missing or invalid in non-debug mode.
- **SC-003**: All containers return a non-root UID when `id` is executed inside them.
- **SC-004**: 100% of project-scoped endpoints return 403 Forbidden when accessed by an unauthorized user, with zero data leakage.
- **SC-005**: WebSocket connections to unowned projects are rejected before any data is transmitted.
- **SC-006**: 100% of secret/token comparisons in the codebase use constant-time functions — verified by code review.
- **SC-007**: Frontend HTTP responses include all four required security headers (Content-Security-Policy, Strict-Transport-Security, Referrer-Policy, Permissions-Policy) and do not disclose the server version.
- **SC-008**: After exceeding the rate limit threshold, 100% of requests to rate-limited endpoints receive a 429 Too Many Requests response.
- **SC-009**: After logout, localStorage contains zero bytes of message content — verified in browser developer tools.
- **SC-010**: Database directory permissions are exactly 0700 and file permissions are exactly 0600 — verified by filesystem inspection.
- **SC-011**: Narrowed OAuth scopes still allow 100% of write operations to succeed in staging before production deployment.
- **SC-012**: Users can complete the OAuth login flow within the same time as before the security changes (no user-visible performance regression).

## Assumptions

- The application uses GitHub OAuth for authentication; no other OAuth providers are in scope.
- The backend is built on a Python framework (FastAPI) and the frontend uses a JavaScript/TypeScript framework with nginx as a reverse proxy.
- SQLite is the production database; the encryption enforcement applies to SQLite-stored OAuth tokens.
- The "minimum necessary scopes" for GitHub OAuth will be determined by testing all write operations with progressively narrower scopes in a staging environment.
- Rate limit thresholds will be configurable via environment variables; specific default values will be determined during planning.
- Existing deployments without an ENCRYPTION_KEY will require a one-time migration to encrypt existing plaintext tokens before the enforcement change takes effect.
- The application already uses `hmac.compare_digest` for GitHub webhook verification; the same pattern will be extended to all other secret comparisons.
- The data volume relocation from `./data` to `/var/lib/solune/data` will require a migration step for existing deployments.

## Scope Boundaries

**In Scope**:

- All 21 findings listed in the Security, Privacy & Vulnerability Audit
- Migration paths for breaking changes (encryption enforcement, OAuth scope changes, data volume relocation)
- Verification checks as defined in the audit report

**Out of Scope**:

- GitHub API security (GitHub's own infrastructure)
- MCP server internals
- Network-layer infrastructure (firewalls, load balancers, VPN configuration)
- Third-party dependency vulnerability scanning (handled by separate Dependabot/supply-chain processes)

## Dependencies

- Staging environment for testing narrowed OAuth scopes before production deployment
- Coordination with existing users for OAuth re-authorization after scope changes
- Migration tooling for re-encrypting existing plaintext OAuth tokens
