# Research: Security, Privacy & Vulnerability Audit

**Feature**: 001-security-review
**Date**: 2026-04-17
**Status**: Complete

## Research Tasks

### R1: OAuth Session Delivery Mechanism

**Decision**: Use HttpOnly, SameSite=Strict, Secure cookies for session delivery — no credentials in URLs.

**Rationale**: OWASP A02 identifies URL-based token delivery as a critical vulnerability because URLs are logged in browser history, proxy/CDN access logs, and HTTP Referer headers. Cookies with HttpOnly prevent JavaScript access, SameSite=Strict prevents CSRF, and Secure ensures HTTPS-only transmission.

**Current State**: ✅ Already implemented. `auth.py` uses `_set_session_cookie()` (lines 22-39) with `httponly=True`, `samesite="strict"`, and configurable `secure` flag. The OAuth callback at line 131 redirects with no credentials in the URL. Frontend `useAuth.ts` never reads credentials from URL params.

**Alternatives Considered**:
- URL query parameter tokens (rejected: logged everywhere)
- Authorization header with localStorage (rejected: XSS-accessible)
- Short-lived URL tokens with immediate exchange (rejected: still briefly logged)

---

### R2: At-Rest Encryption Enforcement Strategy

**Decision**: Mandatory ENCRYPTION_KEY, GITHUB_WEBHOOK_SECRET, and SESSION_SECRET_KEY (≥64 chars) in non-debug mode. Startup fails with clear error messages if missing.

**Rationale**: Optional encryption silently degrades to plaintext storage, creating a false sense of security. Production deployments must fail fast with explicit error messages rather than silently operating insecurely.

**Current State**: ✅ Already implemented. `config.py` validates all three secrets in `_validate_production_settings()` (lines 177-203). Production mode refuses to start if any are missing. Debug mode logs warnings.

**Alternatives Considered**:
- Auto-generate keys on startup (rejected: keys would differ across restarts, breaking existing encrypted data)
- Environment-based warning only (rejected: too easy to ignore)
- Key rotation with fallback decryption (deferred: separate enhancement)

**Migration Note**: Existing deployments without ENCRYPTION_KEY require a one-time migration to encrypt plaintext tokens before enforcement. The encryption service (`encryption.py`) already handles legacy plaintext token detection via GitHub token prefix matching (lines 98-100, 117-122).

---

### R3: Non-Root Container Best Practices

**Decision**: All containers use dedicated non-root system users. Backend uses `appuser`, frontend uses `nginx-app`.

**Rationale**: Running as root inside containers means any container escape or vulnerability exploitation grants root-level access on the host. Non-root users limit the blast radius of container compromises.

**Current State**: ✅ Already implemented. Backend Dockerfile creates `appuser` (line 41-43). Frontend Dockerfile creates `nginx-app` user with `addgroup -S nginx-app && adduser -S -G nginx-app nginx-app` (lines 27-32), sets `USER nginx-app` (line 46), and uses unprivileged port 8080.

**Alternatives Considered**:
- rootless Docker (requires host-level configuration changes, out of scope)
- User namespaces (complementary but doesn't replace in-container non-root)

---

### R4: Centralized Project Access Control Pattern

**Decision**: Use a shared FastAPI dependency (`verify_project_access()`) that checks project ownership before any operation. Apply to all project-scoped endpoints including REST and WebSocket.

**Rationale**: OWASP A01 (Broken Access Control) requires every resource access to be authorized. Centralizing the check in a dependency prevents accidental omissions and ensures consistent enforcement.

**Current State**: ✅ Already implemented. `dependencies.py` provides `verify_project_access()` (line 206+) which verifies user ownership through cached user projects with GitHub API fallback. Returns 403 Forbidden for unauthorized access. Used across `tasks.py`, `projects.py`, `settings.py`, and `workflow.py`.

**Alternatives Considered**:
- Per-endpoint manual checks (rejected: error-prone, inconsistent)
- Middleware-based approach (rejected: too coarse-grained, can't handle varied resource types)
- Database-level row security (not applicable with SQLite)

---

### R5: Constant-Time Secret Comparison

**Decision**: All secret/token comparisons must use `hmac.compare_digest()` to prevent timing attacks.

**Rationale**: Standard string equality (`!=` / `==`) short-circuits on first difference, leaking information about correct characters through response timing. `hmac.compare_digest` always compares all bytes in constant time.

**Current State**: ✅ Already implemented. Signal webhook uses `hmac.compare_digest()` (signal.py line 287). GitHub webhook already used it correctly. All secret comparisons now use constant-time functions.

**Alternatives Considered**:
- Double-HMAC comparison (equivalent security, more complex)
- Custom timing-safe comparison (rejected: stdlib provides a tested implementation)

---

### R6: HTTP Security Headers for nginx

**Decision**: Include Content-Security-Policy, Strict-Transport-Security, Referrer-Policy, and Permissions-Policy. Remove deprecated X-XSS-Protection. Set `server_tokens off`.

**Rationale**: Modern security headers protect against clickjacking, XSS, MIME sniffing, and man-in-the-middle attacks. X-XSS-Protection is deprecated in modern browsers and can introduce vulnerabilities. Server version disclosure aids targeted attacks.

**Current State**: ✅ Already implemented. `nginx.conf` includes all required headers (lines 52-58), sets `server_tokens off` (line 1), and does not include X-XSS-Protection. CSP restricts img-src to self and `avatars.githubusercontent.com`.

**Alternatives Considered**:
- Report-Only CSP initially (good for gradual rollout but not for security audit fix)
- Helmet.js middleware (not applicable: nginx serves static files directly)

---

### R7: Minimal OAuth Scopes

**Decision**: Request `read:user read:org project repo` scopes. The `repo` scope is retained because project management operations require repository-level access for issue creation, label management, and project board mutations.

**Rationale**: While OWASP A01 recommends minimum necessary scopes, the application requires `repo` scope for creating issues, managing labels, and interacting with repository-linked project boards. Narrower scopes like `public_repo` would break private repository support.

**Current State**: ✅ Current scopes (`read:user read:org project repo`) at `github_auth.py` line 74. The comment at line 72 documents the rationale for `repo` scope.

**Alternatives Considered**:
- Remove `repo` entirely (rejected: breaks issue creation and label management on private repos)
- Use fine-grained personal access tokens (not available for OAuth Apps, only GitHub Apps)
- Migrate to GitHub App (significant architectural change, out of current scope)

**Key Decision**: OAuth scope narrowing beyond current set requires migration to GitHub App model. Documented for future consideration.

---

### R8: Rate Limiting Strategy (slowapi)

**Decision**: Per-user rate limits on write/AI endpoints; per-IP rate limit on OAuth callback. Use slowapi (FastAPI-compatible) with in-memory storage.

**Rationale**: Per-user limits prevent a single authenticated user from exhausting shared AI/GitHub quotas. Per-IP limits on unauthenticated endpoints (OAuth callback) prevent brute-force attacks. Per-user preferred over per-IP to avoid penalizing shared NAT/VPN users.

**Current State**: ✅ Already implemented. slowapi integrated in `main.py` (lines 846-858). Rate limits configured on OAuth callback (20/min by IP), chat endpoints (10/min), agent invocation (5/min), and app endpoints (10/min).

**Alternatives Considered**:
- Redis-backed rate limiting (overkill for single-instance SQLite deployment)
- nginx-level rate limiting (less granular, can't do per-user)
- Token bucket algorithm (slowapi uses sliding window, sufficient for this use case)

---

### R9: Secure Client-Side Data Storage

**Decision**: Chat history stored in-memory only (React state), not persisted to localStorage. Legacy localStorage data cleared on logout and on hook initialization.

**Rationale**: Full message content in localStorage survives logout, has no expiration, and is readable by any XSS attack. In-memory state is naturally cleared on tab close and page refresh.

**Current State**: ✅ Already implemented. `useChatHistory.ts` explicitly documents that messages are NOT persisted to localStorage (line 6). The hook clears legacy localStorage data on initialization (line 139: `clearLegacyStorage('chat-message-history')`). `useAuth.ts` clears localStorage on logout (line 66).

**Alternatives Considered**:
- Encrypted localStorage with TTL (adds complexity, still XSS-accessible)
- sessionStorage (cleared on tab close but still XSS-accessible)
- IndexedDB with encryption (overkill for this use case)

---

### R10: API Documentation Toggle

**Decision**: Gate API docs on a dedicated `ENABLE_DOCS` environment variable, independent of `DEBUG`.

**Rationale**: Tying docs to debug mode creates a binary choice: either debug features AND docs, or neither. A separate toggle allows docs in staging without other debug features, and prevents accidental doc exposure in production with debug mode on.

**Current State**: ✅ Already implemented. `config.py` defines `enable_docs: bool = False` (line 99). `main.py` uses `settings.enable_docs` to conditionally enable Swagger/ReDoc (lines 811-812).

**Alternatives Considered**:
- IP-based restriction for docs (adds network complexity)
- Authentication-gated docs (overkill for internal API docs)

---

### R11: GraphQL Error Sanitization

**Decision**: Log full GraphQL error details internally; raise only generic sanitized messages toward API consumers.

**Rationale**: Raw GraphQL error messages can leak query structure, token scope details, and internal API patterns. Generic messages protect against information disclosure while preserving debugging capability.

**Current State**: ✅ Already implemented. `service.py` (line 447-449) logs full error with `logger.error("GraphQL error: %s", error_msg)` then raises a generic `ValueError("GitHub API request failed")` without exposing internal details.

**Alternatives Considered**:
- Error code mapping (adds maintenance overhead for each GraphQL error type)
- Structured error responses with sanitized messages (good enhancement but not required for audit fix)

---

### R12: Docker Network Binding and Volume Mounting

**Decision**: Development services bind to `127.0.0.1`. Data volumes mounted at `/var/lib/solune/data` (outside application root). Database files created with 0700/0600 permissions.

**Rationale**: Binding to `0.0.0.0` exposes services on all network interfaces. Mounting data inside the application directory commingles runtime data with code. Restrictive file permissions limit access to the application user only.

**Current State**: ✅ Already implemented. `docker-compose.yml` binds backend to `127.0.0.1:8000` (line 10) and frontend to `127.0.0.1:5173` (line 60). Data volume mounted at `/var/lib/solune/data` (line 39) using named volume `solune-data` (line 94). `database.py` creates directories with 0o700 (line 37-40) and files with 0o600 (line 54-56).

**Note**: Backend `HOST=0.0.0.0` (line 30) is the in-container bind address, which is correct — the container-level port mapping restricts external access to `127.0.0.1`.

---

### R13: Webhook Verification Independence from Debug Mode

**Decision**: Webhook signature verification must always execute regardless of DEBUG setting. Developers use a locally configured test secret.

**Rationale**: If debug mode accidentally enables in production, skipping webhook verification allows unauthenticated callers to trigger workflows. Mandatory verification with a test secret provides the same developer experience without the security risk.

**Current State**: ✅ Already implemented. `webhooks.py` performs HMAC-SHA256 verification unconditionally using `hmac.compare_digest()` (lines 187-196). No debug-mode bypass exists in the webhook handler.

---

### R14: GitHub Actions Workflow Permissions

**Decision**: Use minimum required permissions with explicit justification comments.

**Current State**: ✅ Already implemented. `branch-issue-link.yml` sets default `permissions: {}` (no permissions) at workflow level, then grants only `issues: write` and `contents: read` at job level with comments explaining why each is needed.

---

### R15: Avatar URL Domain Validation

**Decision**: Validate avatar URLs use HTTPS and originate from `avatars.githubusercontent.com`. Fall back to placeholder SVG on validation failure.

**Current State**: ✅ Already implemented. `IssueCard.tsx` defines `ALLOWED_AVATAR_HOSTS = ['avatars.githubusercontent.com']` (line 16) with validation function that checks protocol and hostname, returning a placeholder SVG data URI for invalid URLs.

---

### R16: Dev Login Endpoint Security

**Decision**: Dev login credentials must arrive in POST request body (JSON), never in URL parameters.

**Current State**: ✅ Already implemented. `auth.py` dev login endpoint accepts credentials via POST body JSON (lines 190-218). Only available in debug mode.

---

### R17: Cookie Secure Flag Enforcement

**Decision**: Non-debug mode startup must fail if cookies are not configured as Secure.

**Current State**: ✅ Already implemented. `config.py` validates `effective_cookie_secure` in production (lines 194-198). The `effective_cookie_secure` property (line 305-312) returns True if `cookie_secure` is set or `frontend_url` starts with `https://`.
