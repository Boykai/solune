# Feature Specification: Security, Privacy & Vulnerability Audit

**Feature Branch**: `002-security-review`
**Created**: 2026-03-31
**Status**: Draft
**Input**: User description: "Security, Privacy & Vulnerability Audit — 3 Critical · 8 High · 9 Medium · 2 Low across OWASP Top 10. Findings describe vulnerable patterns/behaviors across authentication, authorization, container hardening, transport security, data protection, and supply-chain controls."

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Secure Authentication Flow (Priority: P1)

As a user logging in via GitHub OAuth, I want my session credentials (session tokens and other long-lived secrets) to never appear in the browser URL bar, browser history, server access logs, or HTTP Referer headers, so that my session cannot be hijacked by anyone with access to those locations.

**Why this priority**: Session tokens in URLs are the highest-severity credential leak vector. Every login is affected, and exploitation requires zero privilege — anyone with log access or browser history can impersonate the user.

**Independent Test**: Complete a full OAuth login flow end-to-end and verify that no session tokens or other long-lived credentials appear in the browser address bar, navigation history, or network request URLs at any point, and that the short-lived OAuth authorization code is only present in the GitHub → backend callback URL and is never logged or forwarded to the frontend.

**Acceptance Scenarios**:

1. **Given** a user initiates GitHub OAuth login, **When** the OAuth callback completes, **Then** the backend sets an HttpOnly, SameSite=Strict, Secure cookie and redirects the browser with no session token or other long-lived credential in the URL.
2. **Given** a user has completed login, **When** the browser history is inspected, **Then** no entry contains a session token or other long-lived credential as a URL parameter.
3. **Given** the dev login endpoint is used in development mode, **When** a developer authenticates with a GitHub PAT, **Then** the PAT is accepted only from the POST request body (JSON), never from a URL query parameter.
4. **Given** the GitHub OAuth callback endpoint receives an authorization code, **When** the backend handles this callback, **Then** the OAuth authorization code is used only within the backend callback handler and is not logged, stored, or propagated to the frontend or to any subsequent URL.

---

### User Story 2 — Mandatory Encryption and Secrets at Startup (Priority: P1)

As a deployment operator, I want the application to refuse to start in production mode if critical secrets (encryption key, webhook secret, session secret) are missing or weak, so that no deployment accidentally runs with plaintext storage or trivially guessable keys.

**Why this priority**: Running without encryption at rest or with weak session secrets silently exposes all stored OAuth tokens and session data. This is a deployment-time guard that prevents entire classes of data breach.

**Independent Test**: Attempt to start the backend in non-debug mode without setting ENCRYPTION_KEY, GITHUB_WEBHOOK_SECRET, or with a SESSION_SECRET_KEY shorter than 64 characters, and verify the application exits with a clear error message.

**Acceptance Scenarios**:

1. **Given** the application starts in non-debug mode, **When** ENCRYPTION_KEY is not set, **Then** the application refuses to start and logs a clear error message.
2. **Given** the application starts in non-debug mode, **When** GITHUB_WEBHOOK_SECRET is not set, **Then** the application refuses to start and logs a clear error message.
3. **Given** the application starts in non-debug mode, **When** SESSION_SECRET_KEY is shorter than 64 characters, **Then** the application refuses to start and logs a clear error message.
4. **Given** an existing deployment has plaintext OAuth tokens in the database, **When** the operator enables ENCRYPTION_KEY for the first time, **Then** a migration path encrypts existing plaintext rows.

---

### User Story 3 — Non-Root Container Execution (Priority: P1)

As an infrastructure operator, I want all containers to run as a dedicated non-root system user, so that a container escape or vulnerability does not grant root-level host access.

**Why this priority**: Running as root inside a container is a critical misconfiguration that amplifies the impact of any container escape vulnerability to full host compromise.

**Independent Test**: Build and start the frontend container, then exec into it and verify the running user ID is non-root.

**Acceptance Scenarios**:

1. **Given** the frontend container is running, **When** `id` is executed inside the container, **Then** the output shows a non-root UID (not uid=0).
2. **Given** the nginx process inside the frontend container, **When** the process list is inspected, **Then** nginx worker processes run under a dedicated non-root user.

---

### User Story 4 — Project-Level Authorization (Priority: P2)

As an authenticated user, I want to be unable to access, modify, or subscribe to projects that I do not own, so that my project data is isolated from other users.

**Why this priority**: Without project-scoped authorization, any authenticated user can read or modify any other user's projects by guessing the project ID. This is a fundamental access control failure.

**Independent Test**: Authenticate as User A, create a project, then authenticate as User B and attempt to access User A's project by ID. Verify a 403 Forbidden response.

**Acceptance Scenarios**:

1. **Given** User A owns Project X, **When** User B sends an API request to create a task in Project X, **Then** the response is 403 Forbidden.
2. **Given** User A owns Project X, **When** User B attempts a WebSocket subscription to Project X, **Then** the connection is rejected before any data is sent.
3. **Given** User A owns Project X, **When** User B attempts to modify Project X settings or trigger a workflow, **Then** the response is 403 Forbidden.
4. **Given** a shared authorization check dependency, **When** any endpoint accepts a project identifier, **Then** the ownership check is performed by the centralized dependency before any action.

---

### User Story 5 — HTTP Security Headers and Transport Hardening (Priority: P2)

As a user accessing the application through a browser, I want proper HTTP security headers enforced on all responses, so that I am protected from cross-site scripting, clickjacking, protocol downgrade, and information leakage attacks.

**Why this priority**: Missing security headers leave users vulnerable to a wide range of browser-based attacks. These are low-effort, high-impact protections expected by any security audit.

**Independent Test**: Send a HEAD request to the frontend and verify the presence of Content-Security-Policy, Strict-Transport-Security, Referrer-Policy, Permissions-Policy, and X-Content-Type-Options headers, and the absence of the nginx version in the Server header.

**Acceptance Scenarios**:

1. **Given** a request to the frontend, **When** the response headers are inspected, **Then** Content-Security-Policy, Strict-Transport-Security, Referrer-Policy, and Permissions-Policy headers are present.
2. **Given** the nginx configuration, **When** the Server header is inspected, **Then** the nginx version is not disclosed (server_tokens off).
3. **Given** the nginx configuration, **When** headers are inspected, **Then** the deprecated X-XSS-Protection header is absent.

---

### User Story 6 — Constant-Time Secret Comparison (Priority: P2)

As a system receiving webhook callbacks, I want all secret/token comparisons to use constant-time algorithms, so that timing side-channel attacks cannot be used to guess secrets.

**Why this priority**: Timing attacks on webhook secrets allow an attacker to incrementally guess the correct secret by measuring response times. This is a well-known attack vector.

**Independent Test**: Code review confirms all secret and token comparisons throughout the codebase use `hmac.compare_digest` or equivalent constant-time functions.

**Acceptance Scenarios**:

1. **Given** the Signal webhook handler, **When** the webhook secret is verified, **Then** the comparison uses a constant-time function (e.g., `hmac.compare_digest`).
2. **Given** any code path that compares secrets or tokens, **When** reviewed, **Then** no standard equality operator (`==`, `!=`) is used for secret comparison.

---

### User Story 7 — Minimum OAuth Scopes (Priority: P2)

As a user authorizing the application via GitHub OAuth, I want the application to request only the minimum scopes necessary, so that my private repository data is not unnecessarily exposed.

**Why this priority**: The `repo` scope grants full read/write to all private repos — far broader than needed for most project-management operations. Reducing scope minimizes blast radius if tokens are compromised. However, some GitHub APIs currently require `repo` (or an equivalently broad scope) for private-repository workflows, so the product may need to request `repo` while clearly documenting this and avoiding any additional unnecessary scopes.

**Independent Test**: Initiate an OAuth flow and verify that the requested scopes exactly match the documented minimum required scopes for this application. If `repo` is requested, verify that (a) it is explicitly documented as required due to GitHub API limitations, and (b) no broader or additional scopes beyond this documented set are requested. Verify all application write operations still function with this documented minimum scope set.

**Acceptance Scenarios**:

1. **Given** a user initiates GitHub OAuth, **When** the authorization URL is generated, **Then** the requested scopes are limited to the documented minimum set required for the application's features; any broad scopes (such as `repo`) are included only if explicitly documented as required due to GitHub API limitations.
2. **Given** the documented minimum scopes are requested, **When** the application performs its required GitHub operations, **Then** all operations succeed without errors.
3. **Given** existing users authorized with a broader scope set than the current documented minimum (for example, previously including `repo` when it is no longer required), **When** the scope set is narrowed, **Then** affected users are prompted to re-authorize.

---

### User Story 8 — Network Binding and Service Isolation (Priority: P2)

As a deployment operator, I want Docker services to bind only to localhost in development and to be accessible only via reverse proxy in production, so that backend and frontend ports are not exposed on all network interfaces.

**Why this priority**: Binding to 0.0.0.0 exposes services on all network interfaces, making them accessible from the public internet if firewall rules are misconfigured.

**Independent Test**: Inspect the Docker Compose configuration and verify port bindings use 127.0.0.1 in the development profile. Verify production configuration exposes services only behind a reverse proxy.

**Acceptance Scenarios**:

1. **Given** the development Docker Compose configuration, **When** service ports are inspected, **Then** all bindings use 127.0.0.1 instead of 0.0.0.0.
2. **Given** the production Docker Compose configuration, **When** service ports are inspected, **Then** backend and frontend services are not directly exposed; only the reverse proxy is externally accessible.

---

### User Story 9 — Rate Limiting on Sensitive Endpoints (Priority: P3)

As a platform operator, I want per-user rate limits on expensive or sensitive endpoints (chat, agent invocation, workflow, OAuth callback), so that a single user or attacker cannot exhaust shared AI/GitHub quotas or cause denial of service.

**Why this priority**: Without rate limits, any authenticated user can exhaust shared resources. Per-user limits are preferred over per-IP to avoid penalizing shared NAT/VPN users.

**Independent Test**: Authenticate and rapidly send requests to a rate-limited endpoint beyond the threshold, then verify the endpoint returns 429 Too Many Requests.

**Acceptance Scenarios**:

1. **Given** an authenticated user, **When** they exceed the per-user rate limit on a chat or agent endpoint, **Then** subsequent requests return 429 Too Many Requests.
2. **Given** an unauthenticated caller, **When** they exceed the per-IP rate limit on the OAuth callback endpoint, **Then** subsequent requests return 429 Too Many Requests.
3. **Given** rate limits are active, **When** the limit window expires, **Then** the user can resume making requests normally.

---

### User Story 10 — Secure Cookie Configuration (Priority: P3)

As a deployment operator, I want the application to enforce the Secure flag on cookies in production, so that session cookies are never transmitted over unencrypted connections.

**Why this priority**: Without the Secure flag, cookies can be intercepted over HTTP. Relying on URL-prefix detection is fragile and can silently misconfigure.

**Independent Test**: Start the application in non-debug mode without Secure cookie configuration and verify the application refuses to start.

**Acceptance Scenarios**:

1. **Given** the application starts in non-debug mode, **When** cookies are not configured as Secure, **Then** the application refuses to start with a clear error.

---

### User Story 11 — Unconditional Webhook Signature Verification (Priority: P3)

As a system receiving webhooks, I want signature verification to never be bypassed based on debug mode, so that an accidental debug-mode deployment in production cannot allow unauthenticated webhook triggers.

**Why this priority**: Debug-conditional verification creates a silent bypass if debug mode is left on in production. Developers should use a locally configured test secret instead.

**Independent Test**: Enable DEBUG mode without a webhook secret and send a webhook request. Verify that signature verification is still enforced (request rejected).

**Acceptance Scenarios**:

1. **Given** DEBUG mode is enabled, **When** a webhook is received without a valid signature, **Then** the request is rejected (not bypassed).
2. **Given** a developer environment, **When** a developer needs to test webhooks, **Then** they configure a local test secret rather than disabling verification.

---

### User Story 12 — Independent API Docs Toggle (Priority: P3)

As a deployment operator, I want API documentation exposure to be controlled by a separate ENABLE_DOCS environment variable rather than the DEBUG flag, so that debug mode in production does not accidentally expose the full API schema.

**Why this priority**: Coupling docs visibility to DEBUG creates an information disclosure risk if debug mode is accidentally enabled in production.

**Independent Test**: Set DEBUG=true and ENABLE_DOCS=false, then verify Swagger/ReDoc endpoints return 404.

**Acceptance Scenarios**:

1. **Given** ENABLE_DOCS is set to false, **When** a user accesses the Swagger or ReDoc endpoint, **Then** the endpoint returns 404 regardless of DEBUG setting.
2. **Given** ENABLE_DOCS is set to true, **When** a user accesses the docs endpoint, **Then** the documentation is served normally.

---

### User Story 13 — Secure Database File Permissions (Priority: P3)

As an infrastructure operator, I want the SQLite database directory to have restricted permissions (0700) and the database file to have restricted permissions (0600), so that other processes on the container cannot read the database.

**Why this priority**: World-readable database files allow any compromised process in the container to exfiltrate all stored data.

**Independent Test**: Start the application and verify the database directory has 0700 permissions and the database file has 0600 permissions.

**Acceptance Scenarios**:

1. **Given** the application creates the database directory, **When** directory permissions are inspected, **Then** they are 0700.
2. **Given** the application creates the database file, **When** file permissions are inspected, **Then** they are 0600.

---

### User Story 14 — CORS Origins Validation (Priority: P3)

As a deployment operator, I want the CORS origins configuration to be validated at startup, so that typos or malformed origins are caught before the application serves traffic.

**Why this priority**: Unvalidated CORS origins can silently misconfigure the application, either blocking legitimate requests or allowing unauthorized origins.

**Independent Test**: Set a malformed CORS origin (e.g., missing scheme) and verify the application refuses to start.

**Acceptance Scenarios**:

1. **Given** a CORS origin without a URL scheme, **When** the application starts, **Then** it refuses to start and reports the malformed origin.
2. **Given** all CORS origins are well-formed URLs with scheme and hostname, **When** the application starts, **Then** startup succeeds normally.

---

### User Story 15 — Data Volume Isolation (Priority: P3)

As an infrastructure operator, I want the SQLite data volume to be mounted outside the application root directory, so that runtime data does not commingle with application code.

**Why this priority**: Commingling data and code in the same directory increases the risk of accidental data exposure through static file serving or code deployment.

**Independent Test**: Inspect the Docker Compose configuration and verify the data volume is mounted at a path outside the application root (e.g., /var/lib/solune/data).

**Acceptance Scenarios**:

1. **Given** the Docker Compose configuration, **When** the data volume mount path is inspected, **Then** it is outside the application root directory.

---

### User Story 16 — Secure Client-Side Chat Storage (Priority: P3)

As a user, I want my chat history to not persist full message content in localStorage indefinitely, so that my conversation data is not vulnerable to XSS-based exfiltration and is cleared when I log out.

**Why this priority**: Full chat content in localStorage survives logout, has no expiration, and is readable by any XSS attack on the domain.

**Independent Test**: Send chat messages, log out, then inspect localStorage and verify no message content remains.

**Acceptance Scenarios**:

1. **Given** a user has an active chat session, **When** they log out, **Then** all chat-related data is cleared from localStorage.
2. **Given** chat history is needed for display, **When** the user opens a previous chat, **Then** chat messages are fetched from the backend and are not read from or stored in localStorage.
3. **Given** a future implementation that stores lightweight chat references (for example, message IDs) in localStorage, **When** a configured TTL expires, **Then** those references are automatically removed from localStorage.

---

### User Story 17 — Sanitized Error Messages (Priority: P3)

As a user, I want API error responses to contain only generic, safe messages, so that internal implementation details (GraphQL query structure, token scopes, stack traces) are never leaked to the client.

**Why this priority**: Leaking internal error details helps attackers understand the system architecture and find further vulnerabilities.

**Independent Test**: Trigger a GitHub GraphQL API error and verify the API response contains only a generic error message while the full error is logged server-side.

**Acceptance Scenarios**:

1. **Given** a GitHub GraphQL API call fails, **When** the error is returned to the client, **Then** the response contains only a generic sanitized message (e.g., "An internal error occurred").
2. **Given** a GitHub GraphQL API call fails, **When** the error is logged server-side, **Then** the full error details are captured for debugging.

---

### User Story 18 — Minimum GitHub Actions Permissions (Priority: P4)

As a repository maintainer, I want GitHub Actions workflows to request only the minimum permissions needed, so that a compromised workflow has limited blast radius.

**Why this priority**: Broad `issues: write` permission is more than needed and increases supply-chain risk.

**Independent Test**: Review the workflow YAML and verify permissions are scoped to the minimum required, with justification comments.

**Acceptance Scenarios**:

1. **Given** the branch-issue-link workflow, **When** its permissions are reviewed, **Then** only the minimum necessary permissions are declared with a justification comment.

---

### User Story 19 — Avatar URL Domain Validation (Priority: P4)

As a user viewing issue cards, I want avatar images to only load from validated HTTPS GitHub domains, so that a compromised or spoofed avatar URL cannot be used for content injection.

**Why this priority**: Unvalidated external image URLs can be used for tracking, phishing, or mixed-content attacks. Low severity since GitHub controls the avatar URLs, but defense-in-depth matters.

**Independent Test**: Render an issue card with a non-GitHub or HTTP avatar URL and verify a placeholder image is displayed instead.

**Acceptance Scenarios**:

1. **Given** an issue card with a valid GitHub avatar URL (https://avatars.githubusercontent.com/...), **When** the card renders, **Then** the avatar image loads normally.
2. **Given** an issue card with a non-GitHub or non-HTTPS avatar URL, **When** the card renders, **Then** a placeholder image is displayed instead.

---

### Edge Cases

- What happens when an existing deployment upgrades and has plaintext OAuth tokens that need to be encrypted? A migration path must encrypt existing rows on first startup with ENCRYPTION_KEY set.
- For the current release, GitHub OAuth continues to require the broad `repo` scope, and existing tokens authorized with this scope remain valid without re-authorization. In a future iteration where scopes can be narrowed, we must design a migration path (e.g., prompting re-authorization) for users whose tokens were granted the older, broader scope.
- What happens when DEBUG is accidentally set to true in a production deployment? Webhook verification must still be enforced, and API docs must not be exposed unless ENABLE_DOCS is separately set.
- What happens when a WebSocket connection is attempted to an unowned project? The connection must be rejected before any data is transmitted.
- What happens when the CORS origins environment variable contains a mix of valid and invalid URLs? The application must refuse to start and report all malformed origins.
- What happens when rate limiting is triggered during a legitimate burst of user activity? Rate limit responses must include appropriate Retry-After headers.

## Requirements *(mandatory)*

### Functional Requirements

**Phase 1 — Critical**

- **FR-001**: System MUST set session credentials via HttpOnly, SameSite=Strict, Secure cookies on the OAuth callback response and MUST NOT include any credentials in redirect URLs.
- **FR-002**: Frontend MUST NOT read authentication credentials from URL parameters.
- **FR-003**: System MUST refuse to start in non-debug mode if ENCRYPTION_KEY environment variable is not set.
- **FR-004**: System MUST refuse to start in non-debug mode if GITHUB_WEBHOOK_SECRET environment variable is not set.
- **FR-005**: System MUST provide a migration path to encrypt existing plaintext OAuth tokens when ENCRYPTION_KEY is first configured.
- **FR-006**: All containers (frontend and backend) MUST run as a dedicated non-root system user.

**Phase 2 — High**

- **FR-007**: Every API endpoint accepting a project identifier MUST verify the authenticated user has access to that project before performing any action.
- **FR-008**: Project ownership verification MUST be implemented as a centralized shared dependency used by all relevant endpoints.
- **FR-009**: WebSocket connections to an unowned project MUST be rejected before any data is transmitted.
- **FR-010**: All secret and token comparisons throughout the codebase MUST use constant-time comparison functions.
- **FR-011**: The frontend reverse proxy MUST include Content-Security-Policy, Strict-Transport-Security, Referrer-Policy, and Permissions-Policy HTTP security headers on all responses.
- **FR-012**: The frontend reverse proxy MUST NOT disclose the server software version (server_tokens off) and MUST remove the deprecated X-XSS-Protection header.
- **FR-013**: The dev login endpoint MUST accept credentials only from the POST request body (JSON), not from URL query parameters.
- **FR-014**: The OAuth authorization flow MUST request only the minimum necessary GitHub scopes. The broad `repo` scope is temporarily retained due to a current GitHub API limitation and MUST be revisited and narrowed or removed once a viable alternative exists.
- **FR-015**: System MUST refuse to start in non-debug mode if SESSION_SECRET_KEY is shorter than 64 characters.
- **FR-016**: In the development configuration, Docker services MUST bind to 127.0.0.1 only. In production, services MUST be accessible only via a reverse proxy.

**Phase 3 — Medium**

- **FR-017**: Per-user rate limits MUST be enforced on chat, agent invocation, and workflow endpoints.
- **FR-018**: Per-IP rate limits MUST be enforced on the OAuth callback endpoint.
- **FR-019**: Rate-limited responses MUST return HTTP 429 Too Many Requests.
- **FR-020**: System MUST refuse to start in non-debug mode if cookies are not configured with the Secure flag.
- **FR-021**: Webhook signature verification MUST NOT be conditional on debug mode. Verification MUST always be enforced.
- **FR-022**: API documentation (Swagger/ReDoc) visibility MUST be controlled by a dedicated ENABLE_DOCS environment variable, independent of the DEBUG flag.
- **FR-023**: The database directory MUST be created with 0700 permissions and database files with 0600 permissions.
- **FR-024**: The CORS origins configuration MUST validate that each origin is a well-formed URL with scheme and hostname. Malformed values MUST cause startup failure.
- **FR-025**: The SQLite data volume MUST be mounted outside the application root directory (e.g., /var/lib/solune/data).
- **FR-026**: Client-side chat storage MUST store only lightweight references (message IDs) with a TTL, not full message content. Full content MUST be loaded from the backend on demand.
- **FR-027**: All local chat data MUST be cleared from the browser on user logout.
- **FR-028**: GraphQL API error responses MUST contain only generic, sanitized messages. Full error details MUST be logged server-side only.

**Phase 4 — Low**

- **FR-029**: GitHub Actions workflows MUST declare only the minimum necessary permissions with a justification comment.
- **FR-030**: Avatar URLs MUST be validated to use HTTPS and originate from known GitHub avatar domains. Invalid URLs MUST fall back to a placeholder image.

### Key Entities

- **Session**: Represents an authenticated user session. Key attributes: session token (stored in cookie, not URL), expiry, associated user ID. Relationship: belongs to one User.
- **User**: An authenticated GitHub user. Key attributes: user ID, GitHub username, authorized OAuth scopes. Relationship: owns zero or more Projects.
- **Project**: A user-owned project workspace. Key attributes: project ID, owner user ID. Relationship: belongs to one User; contains Tasks, Settings, Workflows.
- **OAuth Token**: An encrypted-at-rest token for GitHub API access. Key attributes: encrypted token value, associated user ID, authorized scopes. Relationship: belongs to one User.
- **Webhook Secret**: A server-side secret used for webhook signature verification. Key attributes: secret value (constant-time compared). Relationship: system-level configuration.
- **Chat Message**: A message in a conversation. Key attributes: message ID, content (stored server-side only), timestamp. Relationship: belongs to a chat session; only message ID stored client-side.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: After login, no credentials appear in the browser URL bar, browser history, or server access logs — verified by end-to-end authentication flow testing.
- **SC-002**: The application refuses to start in production mode when any required secret (ENCRYPTION_KEY, GITHUB_WEBHOOK_SECRET, SESSION_SECRET_KEY with 64+ characters) is missing or inadequate — verified by startup failure tests.
- **SC-003**: Running `id` inside the frontend container returns a non-root UID — verified by container inspection.
- **SC-004**: An authenticated request targeting an unowned project returns 403 Forbidden, not a success response — verified across all project-accepting endpoints.
- **SC-005**: A WebSocket connection to an unowned project is rejected before any data is sent — verified by WebSocket connection testing.
- **SC-006**: 100% of secret/token comparisons in the codebase use constant-time functions — verified by code review.
- **SC-007**: HTTP response from the frontend includes Content-Security-Policy, Strict-Transport-Security, Referrer-Policy, and Permissions-Policy headers, with no nginx version in the Server header — verified by response header inspection.
- **SC-008**: After exceeding the rate limit threshold, expensive endpoints return 429 Too Many Requests — verified by rapid-fire request testing.
- **SC-009**: After logout, localStorage contains no chat message content — verified by browser devtools inspection.
- **SC-010**: Database directory permissions are 0700 and database file permissions are 0600 — verified by filesystem inspection.
- **SC-011**: All OAuth authorization requests use minimum necessary scopes (no `repo` scope) — verified by inspecting the OAuth authorization URL.
- **SC-012**: The dev login endpoint rejects credentials sent as URL query parameters — verified by sending a GET request with credentials in the URL.

## Assumptions

- The backend is built with Python (FastAPI) and the frontend uses a React-based stack with nginx as the static file server and reverse proxy.
- The current authentication flow uses GitHub OAuth and stores session tokens; the fix changes the transport mechanism (cookie vs URL) but not the authentication provider.
- The recommended rate-limiting approach is compatible with the backend framework; the specific library choice will be finalized during planning.
- The OAuth scope change (removing `repo`) may require existing users to re-authorize; this is an acceptable trade-off for security.
- The encryption key migration (plaintext to encrypted OAuth tokens) will be a one-time operation performed on application startup.
- The application runs in Docker containers in both development and production environments.
- Per-user rate limits are preferred over per-IP to avoid false positives for users behind shared NAT/VPN.
- GitHub API security, MCP server internals, and network-layer infrastructure are out of scope for this audit.

## Dependencies

- The encryption migration (FR-005) must be implemented alongside the mandatory encryption enforcement (FR-003) to avoid breaking existing deployments.
- The OAuth scope change (FR-014) must be tested in a staging environment before production deployment to verify all write operations still function.
- Rate limiting (FR-017, FR-018) depends on selecting and integrating a rate-limiting library compatible with the backend framework.
- The data volume path change (FR-025) requires coordination with any existing deployment scripts or infrastructure configuration.

## Out of Scope

- GitHub API security (GitHub's own infrastructure and API hardening).
- MCP server internals (internal MCP protocol and server implementation details).
- Network-layer infrastructure (firewall rules, load balancer configuration, DNS security).
- Penetration testing or active exploitation verification.
- Third-party dependency vulnerability scanning (covered by separate Dependabot/supply-chain tooling).
