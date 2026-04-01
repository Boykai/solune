# Research: Security, Privacy & Vulnerability Audit

**Feature**: 002-security-review
**Date**: 2026-03-31
**Status**: Complete

## Research Tasks

### RT-001: Session Token Transport (Finding #1 — Critical)

**Context**: The audit found session tokens passed in URL query parameters during OAuth callback. Tokens in URLs are recorded in browser history, server/proxy/CDN access logs, and HTTP Referer headers.

**Decision**: The OAuth callback (`auth.py`) already delivers session tokens exclusively via HttpOnly, SameSite=Strict, Secure cookies. The redirect URL (`/auth/callback`) contains no credentials. The frontend (`useAuth.ts`) reads authentication state from API calls (cookie-authenticated), not from URL parameters, and performs URL cleanup on the `/auth/callback` route.

**Rationale**: Cookie-based session transport is the industry standard for web applications. The current implementation sets `httponly=True`, `samesite="strict"`, and `secure=settings.effective_cookie_secure` on the session cookie, preventing XSS access, CSRF, and cleartext transmission respectively.

**Alternatives considered**:
- **Authorization header with Bearer token**: Requires JavaScript token storage (vulnerable to XSS); cookies with HttpOnly are more secure for browser-based apps.
- **Fragment-based token (`#token=...`)**: Not sent to servers but still visible in browser history and accessible to JavaScript on the page.

**Current status**: ✅ Remediated — `auth.py` lines 132–138, `useAuth.ts` lines 32–39.

---

### RT-002: At-Rest Encryption Enforcement (Finding #2 — Critical)

**Context**: The audit found ENCRYPTION_KEY was optional; when absent, OAuth tokens stored in plaintext SQLite.

**Decision**: Production startup validation in `config.py` now requires `ENCRYPTION_KEY` (Fernet key) and `GITHUB_WEBHOOK_SECRET` in non-debug mode. Missing either causes a startup error with a clear message including generation instructions. The `EncryptionService` (`encryption.py`) provides Fernet encryption and includes legacy plaintext token detection for migration — tokens with known GitHub prefixes (`gho_`, `ghp_`, `ghr_`, `ghu_`, `ghs_`, `github_pat_`) are identified as unencrypted and can be transparently encrypted on access.

**Rationale**: Fail-fast on missing secrets prevents silent plaintext storage in production. The Fernet algorithm (AES-128-CBC with HMAC-SHA256) provides both confidentiality and integrity. Legacy token detection enables seamless migration without a separate migration script.

**Alternatives considered**:
- **AES-256-GCM (manual)**: More control but requires nonce management; Fernet handles this automatically with less room for implementation error.
- **Database-level encryption (SQLCipher)**: Encrypts entire database; heavier dependency and more complex key management for the same protection level on specific fields.
- **Warning-only on missing key**: Unacceptable — any production deployment without encryption is a data breach waiting to happen.

**Current status**: ✅ Remediated — `config.py` lines 173–178, `encryption.py` lines 18–110.

---

### RT-003: Frontend Container Non-Root Execution (Finding #3 — Critical)

**Context**: The audit found the frontend Dockerfile had no USER directive; nginx ran as root (uid=0).

**Decision**: The frontend Dockerfile now creates a dedicated `nginx-app` user/group, sets all necessary directory permissions (`/var/cache/nginx`, `/var/run`, `/tmp/nginx`), moves the PID file to `/tmp/nginx/nginx.pid`, switches to `USER nginx-app`, and exposes port 8080 (non-privileged). Assets are copied with `--chown=nginx-app:nginx-app`.

**Rationale**: Non-root container execution is a defense-in-depth measure that limits the blast radius of container escape vulnerabilities. Port 8080 (>1024) does not require root privileges. The backend already ran non-root, so this aligns the frontend.

**Alternatives considered**:
- **nginx unprivileged official image**: Available but less control over base image updates and hardening.
- **rootless Docker/Podman**: Addresses the problem at the runtime level but doesn't protect in rootful Docker deployments.

**Current status**: ✅ Remediated — `Dockerfile` lines 27–32 (user creation), line 41 (`USER nginx-app`), line 44 (`EXPOSE 8080`).

---

### RT-004: Project-Level Authorization (Finding #4 — High)

**Context**: Endpoints accepting project_id did not verify the authenticated user owned that project. Any authenticated user could access any project by guessing its ID.

**Decision**: A centralized `verify_project_access` dependency in `dependencies.py` fetches the user's project list via the GitHub Projects API and confirms the target project_id is included. It raises HTTP 403 if access is denied. This dependency is applied to all project-accepting endpoints: `tasks.py`, `projects.py`, `settings.py`, `workflow.py`, `agents.py`, `activity.py`, `pipelines.py`, and `tools.py`. WebSocket connections also validate project access before data transmission.

**Rationale**: Centralized authorization avoids duplicated checks across endpoints and ensures consistency. Using FastAPI's `Depends()` mechanism integrates naturally with the existing dependency injection pattern. Fetching the user's project list (rather than querying project ownership) aligns with GitHub's permission model where access can be granted through organization membership.

**Alternatives considered**:
- **Database-level ownership table**: Would require maintaining a local permission cache separate from GitHub's authoritative source; adds complexity and staleness risk.
- **Per-endpoint inline checks**: Works but violates DRY; a missed endpoint creates an authorization bypass.
- **Middleware-based path matching**: Fragile — route changes could silently disable authorization.

**Current status**: ✅ Remediated — `dependencies.py` lines 206–231, applied across 8+ API modules.

---

### RT-005: Timing Attack on Signal Webhook (Finding #5 — High)

**Context**: Signal webhook secret comparison used standard string equality (`!=`), leaking timing information.

**Decision**: The Signal webhook handler (`signal.py`) now uses `hmac.compare_digest()` for secret comparison, matching the pattern already used by the GitHub webhook handler. All secret/token comparisons throughout the codebase use constant-time functions.

**Rationale**: `hmac.compare_digest()` is Python's standard library constant-time comparison function. It prevents timing side-channel attacks by ensuring comparison time is independent of how many bytes match.

**Alternatives considered**:
- **Custom constant-time comparison**: Unnecessary when the standard library provides a well-tested implementation.
- **HMAC-based signature verification**: Overkill for a simple shared-secret comparison; `compare_digest` is sufficient for direct secret matching.

**Current status**: ✅ Remediated — `signal.py` lines 9, 287–289.

---

### RT-006: HTTP Security Headers in nginx (Finding #6 — High)

**Context**: Missing Content-Security-Policy, Strict-Transport-Security, Referrer-Policy, Permissions-Policy headers. X-XSS-Protection was deprecated.

**Decision**: The nginx configuration now includes all required security headers: `Content-Security-Policy` (restricting sources to 'self' with specific allowances for GitHub avatars and WebSocket connections), `Strict-Transport-Security` (1 year with includeSubDomains), `Referrer-Policy` (strict-origin-when-cross-origin), `Permissions-Policy` (camera, microphone, geolocation disabled), `X-Frame-Options` (SAMEORIGIN), and `X-Content-Type-Options` (nosniff). `server_tokens off` hides the nginx version. The deprecated `X-XSS-Protection` header is absent.

**Rationale**: These headers provide defense-in-depth against XSS, clickjacking, protocol downgrade, and information leakage. The CSP policy uses `'unsafe-inline'` only for styles (required by the build tooling) while restricting all other sources to 'self'.

**Alternatives considered**:
- **CSP with nonce-based style loading**: More secure but requires server-side nonce generation and injection into HTML, adding complexity to the static file serving architecture.
- **Report-Only CSP**: Useful for gradual rollout but delays actual protection; direct enforcement chosen since the application is new.

**Current status**: ✅ Remediated — `nginx.conf` line 1 (`server_tokens off`), lines 52–58 (security headers).

---

### RT-007: Dev Endpoint PAT in URL (Finding #7 — High)

**Context**: The dev login endpoint received a GitHub Personal Access Token as a URL query parameter.

**Decision**: The dev login endpoint is now `POST /dev-login` accepting credentials exclusively in the JSON request body via a `DevLoginRequest` Pydantic model (`github_token: str`). The endpoint is guarded by `settings.debug` and returns 404 in production mode.

**Rationale**: POST body data is not logged in server access logs, browser history, or HTTP Referer headers. Pydantic validation ensures the token field is present and non-empty.

**Alternatives considered**:
- **Authorization header**: Valid but inconsistent with the endpoint's purpose as a dev convenience; POST body is simpler and more explicit.
- **Removing the endpoint entirely**: Would impair development workflow; keeping it behind the debug guard is an acceptable trade-off.

**Current status**: ✅ Remediated — `auth.py` lines 184–206.

---

### RT-008: OAuth Scope Reduction (Finding #8 — High)

**Context**: The application requests the `repo` scope, granting full read/write access to all private repositories.

**Decision**: The OAuth scope is retained as `"read:user read:org project repo"` based on testing that confirmed GitHub's API returns misleading 404 errors for project write operations (e.g., creating issues, moving cards) when the token has only `project` scope without `repo`. The `repo` scope is documented as a known GitHub API limitation that prevents narrower scoping.

**Rationale**: GitHub's Projects V2 API requires `repo` scope for write operations on project items linked to repository issues, even though the application only performs project management actions. This is a documented GitHub limitation, not an application design choice. Removing `repo` breaks core workflow functionality (issue creation, label assignment, project card management).

**Alternatives considered**:
- **`project` scope only**: Tested and confirmed to cause 404 errors on write operations. GitHub's scoping model does not granularly separate project writes from repository writes.
- **Fine-grained personal access tokens**: Not available for OAuth Apps (only GitHub Apps); migrating to GitHub App authentication is a separate initiative.
- **GitHub App installation**: Would allow granular repository permissions but requires significant OAuth flow changes and user experience considerations.

**Current status**: ⚠️ Intentionally deferred — `github_auth.py` line 74, with inline comment documenting the justification.

---

### RT-009: Session Secret Key Entropy (Finding #9 — High)

**Context**: SESSION_SECRET_KEY was accepted at any length with no validation.

**Decision**: Startup validation in `config.py` enforces a minimum length of 64 characters for SESSION_SECRET_KEY when `debug` is `False` (production-like mode), rejecting shorter keys with a clear error message including generation instructions (`openssl rand -hex 32`). When `debug` is `True`, the same condition triggers a warning log but does not block startup.

**Rationale**: 64 characters of hex output from `openssl rand -hex 32` provides 256 bits of entropy, exceeding the minimum recommended for HMAC-SHA256 session signing. Enforcing this check when `debug` is `False` prevents weak keys in production deployments, while debug-mode warning behavior reflects the current implementation.

**Alternatives considered**:
- **Entropy analysis**: More precise but complex to implement; length is a sufficient proxy for keys generated with cryptographic random generators.
- **All-modes strict check (including debug)**: Stronger — developers would also use strong keys in local/test environments, reducing the risk of habit-forming with weak keys. Not currently implemented; would require a follow-up code change.

**Current status**: ✅ Remediated — `config.py` lines 184–189 (strict enforcement when `debug` is `False`, warning-only when `debug` is `True`).

---

### RT-010: Docker Service Network Binding (Finding #10 — High)

**Context**: Backend and frontend ports were bound to 0.0.0.0, exposing them on all network interfaces.

**Decision**: The `docker-compose.yml` binds all service ports to `127.0.0.1` (loopback only): backend on `127.0.0.1:8000:8000`, frontend on `127.0.0.1:5173:8080`. Internal services (Signal API) use `expose` instead of `ports`, making them accessible only within the Docker network. Production deployments use a reverse proxy (nginx) as the single external entry point.

**Rationale**: Loopback binding prevents direct access from external networks, even if host firewall rules are misconfigured. The Docker bridge network (`solune-network`) provides service-to-service communication without host exposure.

**Alternatives considered**:
- **Docker network-only (no port mapping)**: More secure but prevents host-level development access (e.g., accessing the API from a host IDE or browser).
- **Separate dev/prod compose files**: Adds maintenance burden; loopback binding is secure enough for development.

**Current status**: ✅ Remediated — `docker-compose.yml` lines 11, 68.

---

### RT-011: Rate Limiting (Finding #11 — Medium)

**Context**: No rate limiting on expensive/sensitive endpoints. A single user could exhaust shared AI/GitHub quotas.

**Decision**: The `slowapi` library provides per-user and per-IP rate limiting via `RateLimitKeyMiddleware`. The middleware resolves rate limit keys in order: GitHub user ID → session cookie → IP address, preferring per-user limits. The OAuth callback uses per-IP limiting (20/minute). AI-intensive endpoints (chat, agents, workflow) use per-user limits. Rate-limited responses return HTTP 429 with appropriate headers.

**Rationale**: Per-user limits are preferred over per-IP to avoid penalizing shared NAT/VPN users (per the spec). `slowapi` is FastAPI-compatible and wraps `limits` library, supporting in-memory and Redis-backed stores.

**Alternatives considered**:
- **Custom middleware**: More control but reinvents well-tested rate limiting logic.
- **API gateway rate limiting (nginx)**: Per-IP only at the nginx layer; per-user requires application-level awareness.
- **Redis-backed limits**: Better for multi-instance deployments but adds infrastructure complexity; in-memory sufficient for single-instance.

**Current status**: ✅ Remediated — `middleware/rate_limit.py` lines 10–108, `auth.py` line 107.

---

### RT-012: Cookie Secure Flag Enforcement (Finding #12 — Medium)

**Context**: `cookie_secure` defaulted to False and relied on indirect URL-prefix detection.

**Decision**: The `effective_cookie_secure` property in `config.py` auto-detects HTTPS from `frontend_url` or honors explicit `COOKIE_SECURE=true`. Production startup validation requires `effective_cookie_secure` to be true, failing with a clear error message if cookies would be transmitted insecurely.

**Rationale**: Auto-detection from the frontend URL provides a sensible default that works for both development (`http://localhost`) and production (`https://app.example.com`) without requiring explicit configuration in most cases. The production gate catches misconfigurations.

**Alternatives considered**:
- **Always require explicit COOKIE_SECURE**: Adds configuration burden for straightforward HTTPS deployments.
- **Derive from request scheme at runtime**: Race condition — the first request determines the flag; unreliable behind proxies.

**Current status**: ✅ Remediated — `config.py` lines 88, 190–194, 301–308.

---

### RT-013: Unconditional Webhook Verification (Finding #13 — Medium)

**Context**: Debug mode bypassed webhook signature verification when no secret was set.

**Decision**: Webhook verification in `webhooks.py` is unconditional — it always requires a valid signature regardless of debug mode. When `GITHUB_WEBHOOK_SECRET` is not configured, the webhook is rejected (not bypassed). The inline comment explicitly states: "Verify signature — always required regardless of debug mode. Developers must configure a local test secret."

**Rationale**: Debug-conditional security bypasses create a class of vulnerabilities where production misconfiguration (accidentally enabling debug) silently disables security controls. Developers can configure a local test secret for webhook testing.

**Alternatives considered**:
- **Skip verification in test harness only**: Still creates a bypass path; better to require secrets everywhere.
- **Mock webhook signature in development**: Adds complexity; a simple local secret is sufficient.

**Current status**: ✅ Remediated — `webhooks.py` lines 232–240.

---

### RT-014: Independent API Docs Toggle (Finding #14 — Medium)

**Context**: Swagger/ReDoc availability was gated on DEBUG, not a dedicated toggle.

**Decision**: API docs are controlled by the `enable_docs` environment variable (default: `False`), independent of `DEBUG`. The FastAPI app sets `docs_url` and `redoc_url` to `None` when `enable_docs` is false.

**Rationale**: Decoupling docs from debug mode prevents accidental API schema exposure. Operators can enable docs in staging environments without debug mode, or disable them in debug environments.

**Alternatives considered**:
- **IP-based access control for docs**: More complex; the toggle approach is simpler and works with reverse proxy ACLs for production.
- **Authentication-gated docs**: Adds complexity for a convenience feature; the toggle is sufficient.

**Current status**: ✅ Remediated — `config.py` line 95, `main.py` lines 591–592.

---

### RT-015: Database File Permissions (Finding #15 — Medium)

**Context**: Database directory created with default 0755 permissions; any process could read the DB.

**Decision**: The `database.py` module creates the database directory with `0o700` and sets the database file to `0o600` after creation. Both operations include error handling with warning-level logging if permission changes fail (e.g., on unsupported filesystems).

**Rationale**: `0o700` (rwx------) restricts directory access to the application user. `0o600` (rw-------) restricts file access to the application user. These are the minimum permissions needed for SQLite operation.

**Alternatives considered**:
- **umask-based approach**: Process-wide; could affect other file operations unintentionally.
- **Encrypted filesystem**: Overkill for container deployments where the volume is already isolated.

**Current status**: ✅ Remediated — `database.py` lines 32–42 (directory), lines 50–56 (file).

---

### RT-016: CORS Origins Validation (Finding #16 — Medium)

**Context**: CORS origins parsed with no URL format validation; typos silently passed.

**Decision**: The `cors_origins_list` property in `config.py` validates each comma-separated origin using `urlparse`. Each origin must have a scheme (`http` or `https`) and a hostname. Malformed origins raise `ValueError` with a descriptive message identifying the invalid origin.

**Rationale**: Startup validation catches configuration errors early, before the application serves traffic. Valid CORS origins consist of scheme and hostname, with an optional port; any path component is not part of the origin and should be rejected or stripped during configuration validation.

**Alternatives considered**:
- **Regex validation**: More fragile and harder to maintain than URL parsing.
- **Runtime validation on first request**: Too late — a misconfigured CORS policy could block legitimate requests or allow unauthorized origins.

**Current status**: ✅ Remediated — `config.py` lines 256–274.

---

### RT-017: Data Volume Mount Path (Finding #17 — Medium)

**Context**: SQLite volume mounted at `data` inside the application directory.

**Decision**: The `docker-compose.yml` mounts the data volume at `/var/lib/solune/data`, outside the application root. The `DATABASE_PATH` environment variable defaults to `/var/lib/solune/data/settings.db`.

**Rationale**: Separating data from application code prevents accidental exposure through static file serving, simplifies deployment rollbacks (data survives code replacements), and follows the Linux Filesystem Hierarchy Standard.

**Alternatives considered**:
- **Bind mount to host directory**: Less portable; Docker-managed volumes are recommended for container deployments.
- **In-container path like `/data`**: Works but `/var/lib/solune/data` follows FHS conventions and is more discoverable.

**Current status**: ✅ Remediated — `docker-compose.yml` lines 46–47, environment variable on line 37.

---

### RT-018: Client-Side Chat Storage (Finding #18 — Medium)

**Context**: Full chat message content persisted to localStorage indefinitely, surviving logout.

**Decision**: The `useChatHistory.ts` hook stores message history exclusively in React state (memory). No localStorage persistence for message content. A `clearLegacyStorage()` function removes any pre-existing localStorage entries from earlier versions. The `clearChatHistory()` export is called on logout to ensure complete cleanup.

**Rationale**: In-memory storage is automatically cleared on page navigation, tab close, and session end. React state is not accessible to XSS attacks that target persistent storage. Legacy cleanup handles the migration from the previous localStorage-based approach.

**Alternatives considered**:
- **SessionStorage**: Cleared on tab close but persists across page navigations within the tab; still accessible to XSS.
- **Encrypted localStorage**: Adds complexity and the encryption key must be accessible to JavaScript, defeating the purpose.
- **Server-side storage with IDs**: The preferred long-term approach but requires backend chat persistence infrastructure.

**Current status**: ✅ Remediated — `useChatHistory.ts` lines 1–8 (security comment), lines 41–55 (legacy cleanup), lines 63–79 (memory-only state).

---

### RT-019: GraphQL Error Sanitization (Finding #19 — Medium)

**Context**: Raw GitHub GraphQL API error messages surfaced as internal exceptions without sanitization.

**Decision**: The `service.py` in `github_projects/` logs full GraphQL errors at ERROR level for debugging but raises a generic `ValueError("GitHub API request failed")` toward the API layer. No internal query structure, token scope details, or GitHub-specific error messages are exposed in API responses.

**Rationale**: Logging full errors internally preserves debuggability. Generic error messages prevent information leakage that could help attackers understand the system's GitHub integration details.

**Alternatives considered**:
- **Error codes instead of messages**: More structured but adds complexity; the generic message is sufficient since clients cannot take corrective action on GitHub API errors.
- **Selective sanitization**: Risk of accidentally leaking new error formats as GitHub's API evolves; blanket sanitization is safer.

**Current status**: ✅ Remediated — `service.py` lines 446–451.

---

### RT-020: GitHub Actions Permissions (Finding #20 — Low)

**Context**: GitHub Actions workflow had broad `issues: write` permission.

**Decision**: The `branch-issue-link.yml` workflow declares `permissions: {}` at the top level (no default permissions) and grants only `issues: write` and `contents: read` at the job level. These are the minimum permissions needed: `issues: write` to post the branch-link comment, `contents: read` to access repository metadata.

**Rationale**: Empty default permissions with job-level grants follows the principle of least privilege. Each permission is justified by its use in the workflow.

**Alternatives considered**:
- **`issues: read` only**: Insufficient — the workflow needs to post comments, which requires write permission.
- **Removing the workflow**: The branch-issue-link feature provides developer experience value worth the minimal permission grant.

**Current status**: ✅ Remediated — `branch-issue-link.yml` lines 7–8 (global), lines 18–22 (job-level).

---

### RT-021: Avatar URL Domain Validation (Finding #21 — Low)

**Context**: External avatar URLs from GitHub API rendered in `<img>` without domain validation.

**Decision**: The `IssueCard.tsx` component validates avatar URLs through a `validateAvatarUrl()` function that checks: (1) URL is non-empty, (2) protocol is `https:`, (3) hostname is in `ALLOWED_AVATAR_HOSTS` (`['avatars.githubusercontent.com']`). Invalid URLs fall back to an inline SVG placeholder. Label colors are validated against `/^[0-9a-f]{6}$/` regex to prevent CSS injection.

**Rationale**: Whitelist validation is more secure than blacklist — only known-good GitHub avatar domains are allowed. HTTPS enforcement prevents mixed-content warnings and MITM attacks on avatar loading.

**Alternatives considered**:
- **Content-Security-Policy `img-src` directive only**: Already set in nginx but CSP is a second layer; application-level validation provides defense-in-depth.
- **Proxy avatars through backend**: Eliminates direct external requests but adds latency and backend load for minimal security benefit.

**Current status**: ✅ Remediated — `IssueCard.tsx` lines 15–35 (validation function), line 370 (usage).
