# Research: Security, Privacy & Vulnerability Audit

**Feature**: 002-security-review
**Date**: 2026-03-31
**Status**: Complete

## Research Tasks

### RT-001: Session Token Delivery via Cookies (Finding #1 — Critical)

**Context**: The OAuth flow must deliver session tokens exclusively via HttpOnly cookies, never in URL parameters. Browser history, server logs, and Referer headers can all leak URL-embedded tokens.

**Decision**: Use `response.set_cookie()` on the OAuth callback response with `httponly=True`, `samesite="strict"`, and `secure=True` (auto-detected from `FRONTEND_URL` scheme). The callback redirects to the frontend with no credentials in the URL. The frontend's `useAuth.ts` reads the session from `/api/v1/auth/me` (cookie-authenticated), never from URL parameters.

**Rationale**: HTTP-only cookies are the industry standard for session delivery. They cannot be read by JavaScript (preventing XSS token theft), are automatically sent on same-origin requests (no manual header management), and `SameSite=Strict` prevents CSRF via cross-origin navigation.

**Alternatives considered**:
- **URL token with immediate redirect**: Still exposes the token briefly in history/logs. Rejected.
- **`Authorization: Bearer` header stored in localStorage**: Readable by XSS; requires manual header management. Rejected.
- **Session token in response body (JSON)**: Requires frontend to store it (localStorage/memory). Less secure than HttpOnly cookie. Rejected.

**Current status**: ✅ Implemented in `auth.py` (OAuth callback sets cookie, redirects cleanly) and `useAuth.ts` (reads session from `/api/v1/auth/me`, no URL param parsing).

---

### RT-002: Mandatory Encryption at Rest (Finding #2 — Critical)

**Context**: `ENCRYPTION_KEY` must be mandatory in production. Without it, GitHub OAuth tokens are stored in plaintext SQLite, creating a critical data-at-rest exposure.

**Decision**: `config.py` `_validate_production_secrets()` raises `ValueError` on startup if `DEBUG=false` and `ENCRYPTION_KEY` is not set. Same enforcement for `GITHUB_WEBHOOK_SECRET`. The error message includes a hint for generating a valid Fernet key. In debug mode, missing keys produce warnings (not blocking) to preserve developer ergonomics.

**Rationale**: Fail-fast startup validation is the only reliable way to prevent misconfigured deployments. Runtime warnings are insufficient because they can be missed in log streams.

**Alternatives considered**:
- **Auto-generate a key on first startup**: Creates key management complexity; operators wouldn't know the key to back up or rotate. Rejected.
- **Encrypt only if key is present (current debug behavior)**: Acceptable for development but not production. The binary gate (mandatory vs. warning) is the correct pattern.

**Migration path**: `encryption.py` detects legacy plaintext tokens by checking for known GitHub token prefixes (`gho_`, `ghp_`, `ghr_`). On decryption, if the token matches a plaintext prefix, it's returned as-is (backward compatible) and will be re-encrypted on the next write. No separate migration script needed.

**Current status**: ✅ Implemented in `config.py:_validate_production_secrets()` and `encryption.py` (Fernet with plaintext fallback detection).

---

### RT-003: Non-Root Container Execution (Finding #3 — Critical)

**Context**: The frontend Dockerfile must run nginx as a non-root user. Container escape vulnerabilities are amplified when the process runs as root.

**Decision**: The frontend Dockerfile creates a dedicated `nginx-app` user, remaps `nginx.pid` to `/tmp/nginx/`, and `chown`s all nginx directories to `nginx-app`. The backend already runs as `appuser` (non-root). Both containers use Alpine Linux for minimal attack surface.

**Rationale**: Defense-in-depth — even if a container escape occurs, the attacker gains only the privileges of an unprivileged user, not root.

**Alternatives considered**:
- **nginx `user` directive only**: Insufficient; the master process still starts as root. The Dockerfile `USER` directive ensures the entire process tree is non-root. Rejected.
- **Distroless container**: Even smaller attack surface but no shell for debugging. Overkill for a reverse proxy. Rejected.

**Current status**: ✅ Implemented in frontend Dockerfile (`USER nginx-app`) and backend Dockerfile (`USER appuser`). Both verified via `docker exec <container> id` returning non-root UID.

---

### RT-004: Project-Level Authorization (Finding #4 — High)

**Context**: Every endpoint accepting a `project_id` must verify the authenticated user has access to that project. Without this, any authenticated user can access any project by guessing its ID.

**Decision**: Centralized `verify_project_access` dependency in `dependencies.py` that calls `github_projects_service.list_user_projects()` to confirm the user owns/has access to the project. All project-scoped endpoints use this dependency (via `Depends()` or direct call). Unauthorized access raises `AuthorizationError` (403).

**Rationale**: Centralized authorization prevents the "forgot to add the check" failure mode. A shared `Depends()` function is the idiomatic FastAPI pattern for cross-cutting concerns.

**Alternatives considered**:
- **Per-endpoint inline checks**: Error-prone; easy to forget on new endpoints. Rejected.
- **Database-level row security**: SQLite doesn't support row-level security policies. Not applicable.
- **Middleware-based check**: Would need to parse request bodies/paths to extract project_id. Too fragile. Rejected.

**Current status**: ✅ Implemented in `dependencies.py:verify_project_access()`. Applied to all project-accepting endpoints: tasks.py, projects.py, workflow.py, agents.py, chat.py, activity.py, board.py, pipelines.py.

---

### RT-005: Constant-Time Secret Comparison (Finding #5 — High)

**Context**: Secret comparisons using `==` or `!=` operators leak timing information that attackers can exploit to incrementally guess the correct secret byte-by-byte.

**Decision**: All secret/token comparisons use `hmac.compare_digest()` throughout the codebase. The GitHub webhook handler already used this pattern; the Signal webhook handler has been updated to match.

**Rationale**: `hmac.compare_digest()` is the standard library's constant-time comparison function, designed specifically to prevent timing side-channel attacks.

**Alternatives considered**:
- **Custom constant-time comparison**: Reinventing the wheel; `hmac.compare_digest` is battle-tested. Rejected.
- **Hashing both values and comparing hashes**: Adds unnecessary complexity; `compare_digest` already solves the problem. Rejected.

**Current status**: ✅ Implemented in `signal.py` (webhook secret comparison uses `hmac.compare_digest`), `webhooks.py` (GitHub webhook verification uses `hmac.compare_digest`).

---

### RT-006: HTTP Security Headers (Finding #6 — High)

**Context**: The nginx reverse proxy must include Content-Security-Policy, Strict-Transport-Security, Referrer-Policy, Permissions-Policy, and X-Content-Type-Options headers. The deprecated X-XSS-Protection must be removed. `server_tokens off` must hide the nginx version.

**Decision**: nginx.conf includes all five security headers with strict policies. CSP middleware in the backend (`middleware/csp.py`) adds headers to API responses. `server_tokens off` is set at the http level. X-XSS-Protection is not included (deprecated).

**Rationale**: Defense-in-depth — security headers protect against a wide range of browser-based attacks (XSS, clickjacking, protocol downgrade, MIME sniffing) with minimal performance impact.

**Alternatives considered**:
- **Backend-only headers (no nginx)**: Would miss static file responses. Both layers must set headers. Rejected as insufficient.
- **Permissive CSP (unsafe-inline, unsafe-eval)**: Defeats the purpose of CSP. Strict policy is preferred. Rejected.

**Current status**: ✅ Implemented in nginx.conf (all headers present, server_tokens off, no X-XSS-Protection) and backend CSP middleware.

---

### RT-007: Dev Login Endpoint (Finding #7 — High)

**Context**: The dev login endpoint must accept GitHub PAT from the POST body, not URL query parameters. URL parameters are logged by proxies and servers.

**Decision**: The `/api/v1/auth/dev-login` endpoint accepts credentials only via POST body (JSON). The endpoint returns 404 in non-debug mode. No GET parameter variant exists.

**Rationale**: Even in development, good security habits prevent credential leaks in logs and browser history. POST body is the standard for credential submission.

**Current status**: ✅ Implemented in `auth.py` (POST-only, JSON body for PAT).

---

### RT-008: OAuth Scope Minimization (Finding #8 — High)

**Context**: The app requests the `repo` scope which grants full read/write access to all private repositories. Only project management access is needed.

**Decision**: The OAuth authorization URL requests scopes: `read:user read:org project repo`. The `repo` scope is retained because GitHub's Projects V2 GraphQL API requires `repo` scope to read/write project items that reference repository issues and pull requests. Removing `repo` would break core functionality (creating issues, reading PR status, managing project items linked to repos).

**Rationale**: While `repo` is broader than ideal, it is the minimum scope required by GitHub's API for the operations Solune performs. GitHub does not offer a narrower scope that grants project item CRUD with repository issue/PR linkage.

**Alternatives considered**:
- **Remove `repo` scope entirely**: Breaks issue creation, PR status reads, and project item management. Tested and confirmed non-functional. Rejected.
- **Use `public_repo` only**: Limits functionality to public repos only. Not acceptable for users with private repos. Rejected.
- **GitHub fine-grained PATs**: Not applicable to OAuth App flow; only available for GitHub App installations. Future consideration.

**Key decision**: `repo` scope retained due to GitHub API limitation. Documented as an accepted risk with mitigation (tokens encrypted at rest, short-lived sessions).

**Current status**: ✅ Scopes configured in `github_auth.py`. `repo` retained with documented justification.

---

### RT-009: Session Secret Key Entropy (Finding #9 — High)

**Context**: `SESSION_SECRET_KEY` must have a minimum length of 64 characters to prevent brute-force attacks on session signing.

**Decision**: `config.py:_validate_production_secrets()` validates `len(SESSION_SECRET_KEY) >= 64` on startup. Fails with `ValueError` and a generation hint if shorter.

**Rationale**: 64 characters of random data provides at least 384 bits of entropy (assuming base64), far exceeding the 128-bit minimum for session signing keys.

**Current status**: ✅ Implemented in `config.py:_validate_production_secrets()`.

---

### RT-010: Docker Service Network Binding (Finding #10 — High)

**Context**: Docker services bound to `0.0.0.0` expose them on all network interfaces, making them accessible from the public internet if firewall rules are misconfigured.

**Decision**: docker-compose.yml binds all services to `127.0.0.1` only. In production, services are accessed only through the nginx reverse proxy (which handles TLS termination). The frontend nginx container listens on 8080 internally, mapped to `127.0.0.1:5173` externally.

**Rationale**: Binding to localhost ensures services are only accessible from the host machine, requiring an explicit reverse proxy for external access.

**Current status**: ✅ Implemented in docker-compose.yml (`127.0.0.1:8000`, `127.0.0.1:5173`).

---

### RT-011: Rate Limiting (Finding #11 — Medium)

**Context**: Chat, agent invocation, workflow, and OAuth callback endpoints need per-user and per-IP rate limits to prevent resource exhaustion.

**Decision**: Use `slowapi` (FastAPI-compatible, built on `limits` library). Per-user key resolution via `RateLimitKeyMiddleware` that pre-resolves `github_user_id` from the session store. Fallback to IP-based limiting for unauthenticated requests. OAuth callback limited to 20/minute per IP.

**Rationale**: Per-user limits avoid penalizing shared NAT/VPN users. slowapi integrates natively with FastAPI's exception handling and middleware stack.

**Alternatives considered**:
- **Custom middleware**: Reinventing rate limiting is error-prone. slowapi is battle-tested. Rejected.
- **Per-IP only**: Penalizes shared NAT/VPN users; unfair for legitimate users on corporate networks. Rejected.
- **External rate limiter (nginx)**: Would require duplicating user identity resolution in nginx config. Backend rate limiting is more precise. Rejected.

**Current status**: ✅ Implemented via `middleware/rate_limit.py` (RateLimitKeyMiddleware) + `slowapi` decorators on sensitive endpoints.

---

### RT-012: Cookie Secure Flag Enforcement (Finding #12 — Medium)

**Context**: The `Secure` cookie flag must be enforced in production to prevent session cookies from being transmitted over unencrypted HTTP connections.

**Decision**: `config.py:_validate_production_secrets()` checks that `cookie_secure=True` OR `FRONTEND_URL` starts with `https://` (which auto-enables Secure). Startup fails if neither condition is met in non-debug mode.

**Rationale**: Failing fast on misconfiguration prevents silent security downgrades where cookies are sent over HTTP.

**Current status**: ✅ Implemented in `config.py:_validate_production_secrets()`.

---

### RT-013: Unconditional Webhook Verification (Finding #13 — Medium)

**Context**: Webhook signature verification must not be conditional on debug mode. If debug mode is accidentally enabled in production, unauthenticated callers could trigger workflows.

**Decision**: `webhooks.py` always verifies webhook signatures. The `GITHUB_WEBHOOK_SECRET` is mandatory in production (enforced by config validation). In debug mode, if no secret is configured, the webhook endpoint returns a clear error rather than silently skipping verification. Developers use a locally configured test secret.

**Rationale**: Unconditional verification eliminates an entire class of misconfiguration-based attacks.

**Current status**: ✅ Implemented in `webhooks.py` (always verifies signature) and `config.py` (webhook secret mandatory in production).

---

### RT-014: Independent API Docs Toggle (Finding #14 — Medium)

**Context**: API documentation (Swagger/ReDoc) must be controlled by `ENABLE_DOCS`, not `DEBUG`.

**Decision**: `main.py` uses `settings.enable_docs` (backed by `ENABLE_DOCS` env var, default `false`) to control docs URL exposure. `docs_url` and `redoc_url` are set to `None` when disabled. Independent of `DEBUG`.

**Rationale**: Decoupling docs visibility from debug mode prevents information disclosure if debug mode is accidentally enabled in production.

**Current status**: ✅ Implemented in `main.py` (`docs_url="/api/docs" if settings.enable_docs else None`).

---

### RT-015: Secure Database Permissions (Finding #15 — Medium)

**Context**: The SQLite database directory must have 0700 permissions and database files must have 0600 permissions.

**Decision**: `database.py` creates the database directory with `os.makedirs(mode=0o700)` and sets file permissions with `os.chmod(path, 0o600)` after database creation.

**Rationale**: Restrictive permissions prevent other processes in the container from reading the database, limiting the blast radius of a container compromise.

**Current status**: ✅ Implemented in `database.py` (directory 0o700, file 0o600).

---

### RT-016: CORS Origins Validation (Finding #16 — Medium)

**Context**: The CORS origins configuration must validate each origin is a well-formed URL with scheme and hostname.

**Decision**: `config.py` provides a `cors_origins_list` property that parses the comma-separated `cors_origins` string. Each origin is validated via `urllib.parse.urlparse()` — must have a scheme (http/https) and hostname. Malformed origins raise `ValueError` on access.

**Rationale**: Catching typos at startup prevents silent CORS misconfiguration that could either block legitimate requests or allow unauthorized origins.

**Current status**: ✅ Implemented in `config.py:cors_origins_list` property.

---

### RT-017: Data Volume Isolation (Finding #17 — Medium)

**Context**: The SQLite data volume must be mounted outside the application root directory to prevent commingling runtime data with application code.

**Decision**: docker-compose.yml mounts the SQLite volume at `/var/lib/solune/data` (a standard Linux data path outside the application root `/app`). The `DATABASE_PATH` default in config.py points to `/var/lib/solune/data/settings.db`.

**Rationale**: Separating data from code prevents accidental data exposure through static file serving or code deployment.

**Current status**: ✅ Implemented in docker-compose.yml (`solune-data:/var/lib/solune/data`) and config.py (default `DATABASE_PATH`).

---

### RT-018: Secure Client-Side Chat Storage (Finding #18 — Medium)

**Context**: Full chat message content must not persist in localStorage. Only lightweight references should be stored locally with a TTL.

**Decision**: `useChatHistory.ts` stores chat history in React state (memory only), never in localStorage or sessionStorage. A `clearLegacyStorage()` function removes any pre-v2 localStorage data (`chat-message-history` key) on logout. The `useAuth.ts` logout mutation calls `clearChatHistory()` to ensure all local data is cleared.

**Rationale**: In-memory-only storage ensures chat content doesn't survive page reloads or logout, and is not accessible to XSS attacks via storage APIs.

**Current status**: ✅ Implemented in `useChatHistory.ts` (memory-only) and `useAuth.ts` (logout clears all local state).

---

### RT-019: Sanitized GraphQL Error Messages (Finding #19 — Medium)

**Context**: Raw error messages from the GitHub GraphQL API must not be surfaced to clients. Only generic messages should be returned.

**Decision**: The GitHub Projects service (`graphql.py`) catches all GitHub API exceptions, logs the full error details server-side, and raises sanitized `GitHubAPIError` exceptions with generic messages (e.g., "Failed to fetch project data"). The exception hierarchy in `exceptions.py` ensures only the sanitized message reaches the API response.

**Rationale**: Leaking internal error details (query structure, token scopes, stack traces) helps attackers understand the system architecture.

**Current status**: ✅ Implemented in `graphql.py` (catches and sanitizes) and `exceptions.py` (structured error responses).

---

### RT-020: GitHub Actions Minimum Permissions (Finding #20 — Low)

**Context**: The `branch-issue-link.yml` workflow should declare only minimum necessary permissions with justification comments.

**Decision**: The workflow sets `permissions: {}` at the workflow level (deny-all default) and grants `issues: write` + `contents: read` at the job level. These are the minimum permissions needed: `issues: write` for posting branch-link comments on issues, `contents: read` for reading repository metadata to resolve branch names.

**Rationale**: Least-privilege principle limits the blast radius of a compromised workflow token.

**Current status**: ✅ Implemented in `branch-issue-link.yml` (minimum permissions with scoped grants).

---

### RT-021: Avatar URL Domain Validation (Finding #21 — Low)

**Context**: External avatar URLs from the GitHub API must be validated to use HTTPS and originate from known GitHub avatar domains.

**Decision**: `IssueCard.tsx` includes a `validateAvatarUrl()` function that checks: (1) URL is non-null, (2) protocol is `https:`, (3) hostname is in the allowed list (`avatars.githubusercontent.com`). Invalid URLs fall back to a placeholder SVG data URI.

**Rationale**: Defense-in-depth against compromised or spoofed avatar URLs. Low severity since GitHub controls the avatar CDN, but validates the principle.

**Current status**: ✅ Implemented in `IssueCard.tsx` (whitelist validation + placeholder fallback).
