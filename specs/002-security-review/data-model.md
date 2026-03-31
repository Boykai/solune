# Data Model: Security, Privacy & Vulnerability Audit

**Feature**: 002-security-review
**Date**: 2026-03-31
**Prerequisites**: [research.md](./research.md)

## Entities

### UserSession (Existing — Modified)

Represents an authenticated user session. The security audit changes how sessions are delivered (cookie-only) and stored (encrypted tokens mandatory in production).

| Field | Type | Source | Notes |
|-------|------|--------|-------|
| `session_id` | `str` | Generated (UUID4) | Unique session identifier |
| `github_user_id` | `int` | GitHub OAuth response | GitHub numeric user ID |
| `github_username` | `str` | GitHub OAuth response | GitHub login username |
| `github_avatar_url` | `str` | GitHub OAuth response | Validated HTTPS GitHub CDN URL |
| `access_token` | `str` | GitHub OAuth exchange | **Encrypted at rest** via Fernet (AES-128 + HMAC). Plaintext prefix detection for migration (`gho_`, `ghp_`, `ghr_`) |
| `refresh_token` | `str \| None` | GitHub OAuth exchange | **Encrypted at rest** via Fernet. Used for token refresh (5-min pre-expiry buffer) |
| `token_expires_at` | `datetime \| None` | GitHub OAuth response | Token expiration timestamp for auto-refresh |
| `selected_project_id` | `str \| None` | User selection | Currently active project ID |
| `created_at` | `datetime` | Auto-generated | Session creation timestamp |
| `expires_at` | `datetime` | `created_at + SESSION_EXPIRE_HOURS` | Default 8 hours; session cookie `max_age` matches |

**Session Delivery** (Security Change):
- Session token stored exclusively in HttpOnly, SameSite=Strict, Secure cookie
- Cookie name: `SESSION_COOKIE_NAME` (configurable)
- Never exposed in URL parameters, response body, or JavaScript-accessible storage

**Validation Rules**:
- `access_token` must be encrypted (Fernet token format) in production mode
- `github_avatar_url` validated to use HTTPS and originate from `avatars.githubusercontent.com`
- `expires_at` enforced server-side; expired sessions rejected on access

---

### Settings (Existing — Modified)

Application configuration validated at startup. The security audit adds mandatory secret validation and new configuration knobs.

| Field | Type | Required (Production) | Constraints | Description |
|-------|------|----------------------|-------------|-------------|
| `ENCRYPTION_KEY` | `str` | **Yes** (mandatory if not debug) | Valid Fernet base64 key (32 bytes) | Encrypts OAuth tokens at rest |
| `GITHUB_WEBHOOK_SECRET` | `str` | **Yes** (mandatory if not debug) | Non-empty string | HMAC-SHA256 webhook signature verification |
| `SESSION_SECRET_KEY` | `str` | **Yes** (always) | **≥ 64 characters** | Session signing key; minimum entropy enforced |
| `ADMIN_GITHUB_USER_ID` | `int` | **Yes** (mandatory if not debug) | > 0 | Numeric GitHub user ID for admin access |
| `cookie_secure` | `bool` | **Yes** (mandatory if not debug) | `True` OR `FRONTEND_URL` starts with `https://` | Enforces Secure flag on cookies |
| `enable_docs` | `bool` | No | Default `false` | Controls Swagger/ReDoc exposure, independent of `DEBUG` |
| `cors_origins` | `str` | No | Each origin validated: scheme + hostname required | Comma-separated allowed CORS origins |
| `DATABASE_PATH` | `str` | **Yes** (mandatory if not debug) | Must be absolute path (not `:memory:`) | SQLite database file path |

**Startup Validation** (`_validate_production_secrets()`):
- All mandatory fields checked on startup; `ValueError` raised with actionable message on failure
- Debug mode: warnings only (non-blocking) for missing secrets
- Always enforced: `SESSION_SECRET_KEY >= 64 chars` regardless of debug mode

---

### Project (Existing — Modified Authorization)

A user-owned project workspace. The security audit adds centralized ownership verification.

| Field | Type | Source | Notes |
|-------|------|--------|-------|
| `project_id` | `str` | GitHub Projects V2 API | GitHub GraphQL node ID |
| `owner_username` | `str` | GitHub API | Project owner's GitHub username |
| `title` | `str` | GitHub API | Project display name |

**Authorization Model**:
- Every endpoint accepting `project_id` calls `verify_project_access(request, project_id, session)`
- Verification: `github_projects_service.list_user_projects(access_token, username)` → confirm `project_id` in list
- Failure: `AuthorizationError` (HTTP 403)
- WebSocket connections: ownership verified before data transmission begins

---

### WebhookSecret (Existing — Modified Comparison)

Server-side secrets used for webhook signature verification.

| Field | Type | Source | Notes |
|-------|------|--------|-------|
| `github_webhook_secret` | `str` | Environment variable | Used for GitHub webhook HMAC-SHA256 verification |
| `signal_webhook_secret` | `str` | Environment variable | Used for Signal webhook header verification |

**Comparison Rules**:
- All comparisons use `hmac.compare_digest()` (constant-time)
- Never use `==` or `!=` for secret/token comparison
- Verification is unconditional (not gated on DEBUG mode)

---

### ChatMessage (Existing — Modified Storage)

A message in a conversation. The security audit changes client-side storage behavior.

| Field | Type | Storage | Notes |
|-------|------|---------|-------|
| `message_id` | `str` | Server (SQLite) + Client (memory only) | Unique message identifier |
| `content` | `str` | **Server only** | Full message text; never persisted to client localStorage |
| `role` | `str` | Server + Client (memory) | `user` or `assistant` |
| `timestamp` | `datetime` | Server | Message creation time |

**Client-Side Storage Rules**:
- Message content stored in React state (memory) only
- No localStorage, sessionStorage, or IndexedDB persistence
- `clearLegacyStorage('chat-message-history')` removes pre-v2 localStorage on logout
- All chat state cleared on logout via `clearChatHistory()` callback

---

### RateLimitState (New — Runtime)

Runtime rate limit tracking per user/IP. Not persisted to database — maintained by slowapi in-memory store.

| Field | Type | Source | Notes |
|-------|------|--------|-------|
| `key` | `str` | Middleware | `user:{github_user_id}`, `user:{session_id}`, or `ip:{remote_addr}` |
| `window` | `str` | Decorator | Rate limit window (e.g., `20/minute`, `100/hour`) |
| `hits` | `int` | Runtime | Current request count in window |
| `remaining` | `int` | Runtime | Requests remaining before 429 |
| `reset_at` | `datetime` | Runtime | Window reset timestamp |

**Key Resolution Order**:
1. `user:{github_user_id}` (most reliable, avoids NAT/VPN false positives)
2. `user:{session_id}` (fallback if user_id not resolved in middleware)
3. `ip:{remote_addr}` (unauthenticated requests only)

---

## Relationships

```text
UserSession ──belongs_to──► User (1:1 active session per user)
    │
    ├── access_token: encrypted at rest via EncryptionService
    ├── session_id: delivered via HttpOnly cookie (never URL)
    └── selected_project_id ──references──► Project

Project ──owned_by──► User
    │
    └── verify_project_access() confirms ownership before any operation

Settings ──validates_at_startup──► ENCRYPTION_KEY, WEBHOOK_SECRET, SESSION_SECRET_KEY
    │
    ├── _validate_production_secrets() → fail-fast on missing/weak secrets
    └── cors_origins_list → validated URL format

WebhookSecret ──compared_via──► hmac.compare_digest() (constant-time)
    │
    ├── GitHub webhook: HMAC-SHA256 payload verification
    └── Signal webhook: header secret comparison

ChatMessage ──stored_in──► Server (persistent) + Client (memory-only)
    │
    └── On logout: client state cleared, legacy localStorage removed

RateLimitState ──tracked_per──► User (per-user) or IP (unauthenticated)
    │
    └── Exceeded → HTTP 429 Too Many Requests
```

## State Transitions

### Session Lifecycle

```text
[OAuth Callback] → [Create UserSession]
                        │
                        ├── Set HttpOnly cookie (session_id)
                        ├── Encrypt access_token (Fernet)
                        └── Redirect to frontend (no URL params)
                        │
[API Request] → [Read session cookie] → [Validate session]
                                              │
                                              ├── Valid → process request
                                              ├── Expired token → auto-refresh (5-min buffer)
                                              └── Invalid/missing → 401 Unauthorized
                                              │
[Logout] → [Revoke session (DB)] → [Delete cookie] → [Clear client state]
```

### Startup Validation

```text
[App Startup] → [Load Settings] → [_validate_production_secrets()]
                                        │
                                        ├── DEBUG=true: warnings for missing secrets
                                        └── DEBUG=false:
                                              ├── ENCRYPTION_KEY missing → ValueError (halt)
                                              ├── WEBHOOK_SECRET missing → ValueError (halt)
                                              ├── SESSION_KEY < 64 chars → ValueError (halt)
                                              ├── cookie_secure=false + non-HTTPS → ValueError (halt)
                                              ├── ADMIN_USER_ID = 0 → ValueError (halt)
                                              └── All pass → continue startup
```

### Authorization Check

```text
[API Request with project_id] → [verify_project_access()]
                                      │
                                      ├── Fetch user's projects from GitHub API
                                      ├── project_id in user's projects → allow
                                      └── project_id NOT in user's projects → 403 Forbidden
```
