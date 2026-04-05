# Feature Specification: Security, Privacy & Vulnerability Audit

**Feature Branch**: `003-security-review`  
**Created**: 2026-04-05  
**Status**: Draft  
**Input**: User description: "Security, Privacy & Vulnerability Audit — 3 Critical · 8 High · 9 Medium · 2 Low across OWASP Top 10"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Secure Authentication Flow (Priority: P1)

A user logs in via the OAuth flow. After authenticating with the identity provider, the browser is redirected back to the application. At no point do credentials or session tokens appear in the browser address bar, browser history, server logs, or HTTP Referer headers. The session is established through a secure, HTTP-only cookie that the frontend never reads directly. The user simply sees a seamless redirect to the application dashboard after login.

**Why this priority**: Session tokens in URLs are the highest-severity finding. Credential leakage through browser history and access logs represents an immediate, exploitable vulnerability that affects every authenticated user from their first interaction.

**Independent Test**: Complete a full OAuth login flow. Inspect the browser URL bar, browser history, and network requests. Confirm no credentials or tokens appear in any URL at any point. Verify the session cookie is present and marked as HttpOnly, SameSite=Strict, and Secure.

**Acceptance Scenarios**:

1. **Given** a user initiates OAuth login, **When** the identity provider redirects back to the application, **Then** no session token, access token, or credential appears in the URL
2. **Given** a successful OAuth callback, **When** the session is established, **Then** the session credential is stored in an HttpOnly cookie with SameSite=Strict and Secure attributes
3. **Given** a user is logged in, **When** the browser history is inspected, **Then** no entries contain session tokens or credentials as URL parameters
4. **Given** a developer uses the dev login endpoint, **When** they submit credentials, **Then** the credentials are sent in the request body (not as URL query parameters)

---

### User Story 2 - Mandatory Encryption and Secret Enforcement at Startup (Priority: P1)

An operations team member deploys the application to a production environment. If the required encryption key or webhook secret is missing, the application refuses to start and displays a clear error message explaining which configuration is missing. This prevents any scenario where sensitive data (such as OAuth tokens) could be stored in plaintext or where webhooks could be accepted without signature verification. In development mode, the application starts with appropriate warnings but still requires a webhook secret.

**Why this priority**: Storing OAuth tokens in plaintext and accepting unsigned webhooks are critical vulnerabilities. Enforcing configuration at startup is a gate that prevents all downstream data-at-rest and webhook integrity issues.

**Independent Test**: Attempt to start the application in production mode without the encryption key set. Verify the application exits with a clear error. Repeat for the webhook secret. Repeat for session secret keys shorter than 64 characters.

**Acceptance Scenarios**:

1. **Given** the application is started in production mode, **When** the encryption key environment variable is not set, **Then** the application refuses to start and logs an error indicating the missing key
2. **Given** the application is started in production mode, **When** the webhook secret environment variable is not set, **Then** the application refuses to start and logs an error indicating the missing secret
3. **Given** the application is started in any mode, **When** the session secret key is shorter than 64 characters, **Then** the application refuses to start and logs an error indicating insufficient key length
4. **Given** the application is started in production mode, **When** the cookie Secure flag is not enabled, **Then** the application refuses to start and logs an error indicating insecure cookie configuration
5. **Given** the application is started in debug mode, **When** the encryption key is missing, **Then** the application starts with a warning but does not store sensitive data in plaintext

---

### User Story 3 - Non-Root Container Execution (Priority: P1)

A platform engineer deploys the application using containers. All containers, including the frontend web server, run as dedicated non-root system users. If an attacker exploits a vulnerability within the container, they cannot escalate to root privileges. The engineer can verify this by inspecting the running container's user identity.

**Why this priority**: Running containers as root is a critical security misconfiguration. If the web server process is compromised, a root-level container grants the attacker unrestricted access to the container's filesystem and potentially the host system.

**Independent Test**: Build and start the frontend container. Execute a command inside the container to check the running user ID. Verify the user is not root (UID is not 0).

**Acceptance Scenarios**:

1. **Given** the frontend container is running, **When** the user identity is checked inside the container, **Then** the reported user is a non-root system user
2. **Given** all application containers are running, **When** the user identity is checked in each container, **Then** none of them run as root

---

### User Story 4 - Project-Level Access Control (Priority: P1)

An authenticated user attempts to access a project they do not own by providing a different project identifier. The system verifies that the user has access to the requested project before performing any action. If the user does not have access, the request is denied with an appropriate error. This applies to all project-scoped operations: task creation, settings changes, workflow operations, and real-time subscriptions.

**Why this priority**: Missing authorization checks allow any authenticated user to read, modify, or subscribe to any project. This is a broken access control vulnerability that can lead to data breaches and unauthorized modifications.

**Independent Test**: Log in as User A. Attempt to create a task, modify settings, trigger a workflow, and subscribe to real-time updates for a project owned by User B. Verify all requests are denied.

**Acceptance Scenarios**:

1. **Given** User A is authenticated, **When** User A sends a request to create a task in User B's project, **Then** the request is denied with a 403 Forbidden response
2. **Given** User A is authenticated, **When** User A attempts to modify settings for User B's project, **Then** the request is denied with a 403 Forbidden response
3. **Given** User A is authenticated, **When** User A attempts to subscribe to real-time updates for User B's project, **Then** the connection is rejected before any data is sent
4. **Given** a centralized access check is implemented, **When** any endpoint receives a project identifier, **Then** the access check is invoked before any business logic executes

---

### User Story 5 - Hardened HTTP Security Headers (Priority: P2)

A security auditor scans the application's HTTP response headers. The responses include a comprehensive set of security headers: a content security policy, strict transport security, a referrer policy, and a permissions policy. The web server does not reveal its software version. Deprecated headers are removed.

**Why this priority**: Missing security headers expose users to cross-site scripting, clickjacking, and information disclosure attacks. These are straightforward to add and provide defense-in-depth against common web vulnerabilities.

**Independent Test**: Send an HTTP HEAD request to the frontend. Verify the response includes Content-Security-Policy, Strict-Transport-Security, Referrer-Policy, and Permissions-Policy headers. Verify no server version is disclosed. Verify deprecated X-XSS-Protection header is absent.

**Acceptance Scenarios**:

1. **Given** the frontend web server is running, **When** a client sends an HTTP request, **Then** the response includes Content-Security-Policy, Strict-Transport-Security, Referrer-Policy, and Permissions-Policy headers
2. **Given** the frontend web server is running, **When** a client inspects the Server response header, **Then** no software version number is disclosed
3. **Given** the frontend web server is running, **When** a client inspects response headers, **Then** the deprecated X-XSS-Protection header is not present

---

### User Story 6 - Constant-Time Secret Comparison (Priority: P2)

A webhook arrives at the application with a signature. The system validates the signature using constant-time comparison to prevent timing attacks. This applies to all secret and token comparisons across the codebase, not just a single webhook handler.

**Why this priority**: Timing attacks on secret comparisons allow attackers to reconstruct secrets character by character. While exploitability varies, the fix is simple and eliminates an entire class of vulnerability.

**Independent Test**: Code review all secret and token comparison points in the codebase. Verify each uses a constant-time comparison function. No standard string equality operators are used for secret comparisons.

**Acceptance Scenarios**:

1. **Given** a webhook with a signature arrives, **When** the system validates the signature, **Then** a constant-time comparison function is used
2. **Given** any code path compares secrets or tokens, **When** the comparison executes, **Then** it uses a constant-time comparison function regardless of the secret type

---

### User Story 7 - Minimum-Privilege OAuth Scopes (Priority: P2)

A user authorizes the application to access their identity provider account. The application requests only the minimum permissions needed for project management functionality. It does not request broad access to all repositories or resources. If the scope change affects existing users, they are prompted to re-authorize with the narrower permissions.

**Why this priority**: Requesting overly broad OAuth scopes violates the principle of least privilege. If the application's tokens are compromised, the blast radius includes all of the user's private repositories.

**Independent Test**: Initiate the OAuth authorization flow and inspect the requested scopes. Verify the scope list does not include broad permissions like full repository access. Verify all application features still function correctly with narrower scopes.

**Acceptance Scenarios**:

1. **Given** a user initiates OAuth authorization, **When** the authorization request is sent, **Then** only minimum necessary scopes are requested
2. **Given** scopes have been narrowed, **When** a user performs all standard project management operations, **Then** all operations succeed without errors
3. **Given** an existing user authorized with broader scopes, **When** the scope change is deployed, **Then** the user is prompted to re-authorize on next login

---

### User Story 8 - Rate Limiting on Sensitive Endpoints (Priority: P3)

A user or automated script sends a large volume of requests to expensive endpoints (chat, agent invocation, workflow triggers, OAuth callbacks). After exceeding a threshold, subsequent requests receive a rate limit response indicating they must wait. This prevents any single user from exhausting shared resources such as AI processing quotas or identity provider API limits.

**Why this priority**: Without rate limiting, a single user can exhaust shared AI and API quotas, causing denial of service for all users. Per-user limits are preferred to avoid penalizing users behind shared networks.

**Independent Test**: Send requests to a rate-limited endpoint at a rate exceeding the configured threshold. Verify that requests beyond the limit receive a 429 Too Many Requests response with an appropriate retry-after indicator.

**Acceptance Scenarios**:

1. **Given** a user sends requests to a chat or agent endpoint, **When** the per-user rate limit is exceeded, **Then** subsequent requests return 429 Too Many Requests
2. **Given** an IP address sends requests to the OAuth callback, **When** the per-IP rate limit is exceeded, **Then** subsequent requests return 429 Too Many Requests
3. **Given** a rate-limited user waits for the cooldown period, **When** they send a new request, **Then** the request is processed normally

---

### User Story 9 - Secure Local Data Handling (Priority: P3)

A user interacts with the chat feature. Only lightweight references (such as message identifiers) are stored locally in the browser, not full message content. When the user logs out, all locally stored data is cleared. If the browser is compromised by a cross-site scripting attack, no sensitive message content is available in local storage.

**Why this priority**: Storing full chat history in browser local storage creates a persistent data exposure risk. Local storage is accessible to any script running on the same origin, making it a prime target for XSS attacks.

**Independent Test**: Use the chat feature, then inspect browser local storage. Verify only message references are stored, not full content. Log out and verify all local data is cleared.

**Acceptance Scenarios**:

1. **Given** a user has an active chat session, **When** browser local storage is inspected, **Then** only lightweight references (message IDs) are stored, not full message content
2. **Given** a user logs out, **When** browser local storage is inspected, **Then** no chat data or message references remain
3. **Given** local references have a configured time-to-live, **When** the TTL expires, **Then** stale references are automatically removed

---

### User Story 10 - Secure Infrastructure Configuration (Priority: P3)

A platform engineer reviews the deployment configuration. Services are not exposed on all network interfaces. Database directories and files have restrictive permissions (owner-only access). Data volumes are mounted outside the application directory. The CORS origins list is validated at startup.

**Why this priority**: Infrastructure misconfigurations create attack surface even when application code is secure. Binding to all interfaces, world-readable databases, and unvalidated CORS origins are medium-severity issues that compound with other vulnerabilities.

**Independent Test**: Inspect the deployment configuration. Verify services bind to localhost only (or are behind a reverse proxy). Check database directory permissions are 0700 and file permissions are 0600. Verify CORS origins are validated at startup and malformed values cause a startup failure.

**Acceptance Scenarios**:

1. **Given** the development environment is configured, **When** services start, **Then** they bind to 127.0.0.1 only and are not accessible from external interfaces
2. **Given** the database directory is created, **When** its permissions are checked, **Then** the directory has 0700 permissions and database files have 0600 permissions
3. **Given** the CORS origins configuration contains a malformed URL, **When** the application starts, **Then** it refuses to start and logs an error identifying the invalid origin
4. **Given** the deployment uses containers, **When** data volumes are mounted, **Then** they are mounted outside the application root directory

---

### User Story 11 - Secure Debug and Documentation Controls (Priority: P3)

A developer or operator reviews the application configuration. Webhook signature verification is always enforced regardless of debug mode. API documentation availability is controlled by a dedicated toggle independent of the debug flag. Error messages returned to users are generic and do not expose internal details.

**Why this priority**: Coupling security controls to debug mode creates a risk of accidental exposure in production. Separating these concerns ensures security controls remain active even if debug mode is inadvertently enabled.

**Independent Test**: Start the application with debug mode enabled but no documentation toggle. Verify API docs are not exposed. Verify webhooks still require valid signatures. Send an invalid request and verify the error response contains no internal details.

**Acceptance Scenarios**:

1. **Given** debug mode is enabled, **When** a webhook arrives without a valid signature, **Then** the webhook is rejected (signature verification is never bypassed)
2. **Given** the documentation toggle is not enabled, **When** a user navigates to the API docs endpoint, **Then** the docs are not available regardless of debug mode
3. **Given** an error occurs during request processing, **When** the error response is returned to the user, **Then** it contains a generic message with no internal stack traces, query structures, or token details

---

### User Story 12 - Supply Chain and Client-Side Input Validation (Priority: P4)

A security auditor reviews the CI/CD pipeline and frontend rendering behavior. GitHub Actions workflows use minimum-necessary permissions with justification comments. External URLs rendered in the user interface are validated to ensure they use secure protocols and originate from expected domains.

**Why this priority**: These are low-severity findings that reduce attack surface incrementally. Overly broad CI permissions increase supply chain risk, and unvalidated external URLs can be used for phishing or tracking.

**Independent Test**: Review the GitHub Actions workflow file and verify permissions are scoped to minimum necessary. Render an issue card with a non-HTTPS or non-GitHub avatar URL and verify it falls back to a placeholder image.

**Acceptance Scenarios**:

1. **Given** the CI/CD workflow runs, **When** its permissions are reviewed, **Then** each permission is scoped to the minimum necessary and includes a justification comment
2. **Given** an issue card renders an avatar image, **When** the avatar URL does not use HTTPS or does not originate from a known avatar domain, **Then** a placeholder image is displayed instead

---

### Edge Cases

- What happens when the encryption key is rotated? Existing encrypted data must remain decryptable during migration, and a migration path for plaintext-to-encrypted rows must be provided.
- What happens when a user with broad OAuth scopes re-authorizes with narrower scopes? Existing operations that relied on broader scopes must fail gracefully with a clear explanation.
- What happens when the rate limiter's backing store is unavailable? The system should fail open (allow requests) rather than deny all traffic, to avoid self-inflicted denial of service.
- What happens when a webhook signature verification fails? The request is rejected, and the failure is logged for monitoring, but no details about the expected signature are revealed.
- What happens when the CORS origins configuration is empty? The application should refuse to start in production mode, as an empty CORS list likely indicates misconfiguration.
- What happens when all containers are restarted simultaneously? Session continuity depends on cookie persistence, not in-memory state. Users should not need to re-authenticate unless sessions have expired.

## Requirements *(mandatory)*

### Functional Requirements

**Phase 1 — Critical**

- **FR-001**: System MUST establish user sessions via HttpOnly, SameSite=Strict, Secure cookies — never through URL parameters
- **FR-002**: System MUST refuse to start in production mode if the encryption key is not configured
- **FR-003**: System MUST refuse to start in production mode if the webhook secret is not configured
- **FR-004**: All containers MUST run as dedicated non-root system users
- **FR-005**: System MUST refuse to start if the session secret key is shorter than 64 characters

**Phase 2 — High**

- **FR-006**: Every endpoint accepting a project identifier MUST verify the authenticated user has access to that project before executing any action
- **FR-007**: The project access check MUST be centralized as a shared dependency, not duplicated across endpoints
- **FR-008**: All secret and token comparisons MUST use constant-time comparison functions
- **FR-009**: The frontend web server MUST include Content-Security-Policy, Strict-Transport-Security, Referrer-Policy, and Permissions-Policy response headers
- **FR-010**: The frontend web server MUST NOT disclose its software version in response headers
- **FR-011**: The frontend web server MUST NOT include the deprecated X-XSS-Protection header
- **FR-012**: All credential inputs (including development-only endpoints) MUST be submitted in request bodies, never as URL parameters
- **FR-013**: OAuth authorization MUST request only the minimum scopes necessary for project management functionality
- **FR-014**: System MUST refuse to start in production mode if the cookie Secure flag is not enabled

**Phase 3 — Medium**

- **FR-015**: Expensive and sensitive endpoints (chat, agent invocation, workflow, OAuth callback) MUST enforce rate limits
- **FR-016**: Rate limits on authenticated endpoints MUST be per-user; rate limits on unauthenticated endpoints MUST be per-IP
- **FR-017**: Webhook signature verification MUST NOT be conditional on debug mode
- **FR-018**: API documentation availability MUST be controlled by a dedicated environment variable, independent of the debug flag
- **FR-019**: The database directory MUST be created with 0700 permissions; database files MUST have 0600 permissions
- **FR-020**: CORS origins configuration MUST be validated at startup; malformed URLs MUST cause a startup failure
- **FR-021**: Data volumes MUST be mounted outside the application root directory
- **FR-022**: Browser local storage MUST store only lightweight references (message IDs) with a time-to-live, not full message content
- **FR-023**: All locally stored data MUST be cleared on user logout
- **FR-024**: Error messages returned to users MUST be generic and MUST NOT expose internal details such as query structures, stack traces, or token scope information
- **FR-025**: Development services MUST bind to 127.0.0.1 only; production services MUST be accessible only via a reverse proxy

**Phase 4 — Low**

- **FR-026**: CI/CD workflow permissions MUST be scoped to the minimum necessary and include justification comments
- **FR-027**: External avatar URLs MUST be validated to use HTTPS and originate from a known domain; invalid URLs MUST fall back to a placeholder image

### Key Entities

- **Session**: Represents an authenticated user's active session; attributes include user identifier, creation timestamp, and expiration. Established via secure cookie, never via URL parameter.
- **Project Access Grant**: Represents the relationship between a user and a project they are authorized to access. Used by the centralized access check to verify ownership or membership.
- **Rate Limit Bucket**: Tracks request counts for a user or IP address within a sliding time window. Attributes include identifier (user ID or IP), endpoint group, request count, and window expiration.
- **Local Storage Reference**: A lightweight pointer to a server-side message, stored in the browser. Attributes include message identifier and time-to-live. Does not contain message content.

### Assumptions

- The application uses an OAuth-based authentication flow with a third-party identity provider (GitHub).
- The backend is a Python-based web application; the frontend is a JavaScript/TypeScript single-page application served by nginx.
- Deployment uses Docker containers orchestrated by Docker Compose.
- SQLite is the primary database engine.
- The application distinguishes between debug and production modes via an environment variable.
- Existing users with broad OAuth scopes will need to re-authorize after scope narrowing; a migration path for encrypted data will be provided alongside encryption enforcement.
- Rate limiting will use per-user bucketing for authenticated endpoints to avoid penalizing users behind shared NAT or VPN connections.
- GitHub avatars are the primary external image source requiring domain validation.

### Out of Scope

- GitHub API internal security (outside the application's control)
- MCP server internals
- Network-layer infrastructure (load balancers, firewalls, DNS)
- Penetration testing or red team exercises
- Compliance certifications (SOC 2, ISO 27001) — may be addressed in a future audit

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: After login, no credentials or session tokens appear in the browser URL bar, browser history, or server access logs — verified across 100% of authentication flows
- **SC-002**: Application refuses to start in production mode within 5 seconds when required secrets (encryption key, webhook secret, session key) are missing or insufficient
- **SC-003**: All containers report a non-root user identity when inspected at runtime
- **SC-004**: 100% of requests to project-scoped endpoints with an unauthorized project ID return a 403 Forbidden response, not a success response
- **SC-005**: Real-time connections to unauthorized projects are rejected before any data is transmitted
- **SC-006**: 100% of secret and token comparisons in the codebase use constant-time functions (verified by code review)
- **SC-007**: HTTP response headers from the frontend include Content-Security-Policy, Strict-Transport-Security, Referrer-Policy, and Permissions-Policy; no server version is disclosed
- **SC-008**: Requests exceeding the rate limit threshold receive a 429 Too Many Requests response within 1 second
- **SC-009**: After logout, browser local storage contains zero chat message content items
- **SC-010**: Database directory permissions are 0700 and database file permissions are 0600 — verified in all deployment configurations
- **SC-011**: Webhook signature verification succeeds or fails identically regardless of debug mode setting
- **SC-012**: OAuth authorization requests include only scopes necessary for project management; all standard operations succeed with narrowed scopes
- **SC-013**: Error responses contain no internal details (stack traces, query structures, token scopes) — verified by inspecting responses to deliberately malformed requests
- **SC-014**: 100% of CORS origin entries pass URL format validation at startup; any malformed entry causes startup failure
