# Data Model: Security, Privacy & Vulnerability Audit

**Feature**: 002-security-review
**Date**: 2026-03-31
**Prerequisites**: [research.md](./research.md)

## Entities

### Session (Existing — Hardened)

Represents an authenticated user session. The security audit changed the transport mechanism (cookie-based, never URL) and added production-mode validation for the secret key.

| Field | Type | Security Property | Notes |
|-------|------|-------------------|-------|
| `session_id` | `UUID` | HttpOnly cookie transport | Never appears in URLs, logs, or Referer headers |
| `access_token` | `str` | Encrypted at rest (Fernet) | Stored encrypted in SQLite when ENCRYPTION_KEY is set |
| `refresh_token` | `str \| None` | Encrypted at rest (Fernet) | Same encryption as access_token |
| `github_user_id` | `int` | Identifier | Used for per-user rate limiting |
| `github_username` | `str` | Identifier | Used for project access verification |
| `selected_project_id` | `str \| None` | Authorization scope | Verified via `verify_project_access` before use |
| `expires_at` | `datetime` | Session lifetime | 8-hour default (`session_expire_hours`) |
| `updated_at` | `datetime` | Audit trail | Tracks last session activity |

**Security Invariants**:
1. Session ID transmitted only via `Set-Cookie` with `HttpOnly; SameSite=Strict; Secure` attributes
2. Session secret key (`SESSION_SECRET_KEY`) must be ≥64 characters
3. Access/refresh tokens encrypted at rest when `ENCRYPTION_KEY` is configured
4. Legacy plaintext tokens (prefixed `gho_`, `ghp_`, `ghr_`, `ghu_`, `ghs_`, `github_pat_`) detected and transparently encrypted on access

---

### SecurityConfig (Existing — Enhanced Validation)

Represents the application security configuration validated at startup. Defined as fields within the Pydantic `Settings` model in `config.py`.

| Field | Type | Required In | Validation Rule |
|-------|------|-------------|-----------------|
| `encryption_key` | `str \| None` | Production | Must be set; Fernet key format |
| `github_webhook_secret` | `str \| None` | Production | Must be set; used for HMAC-SHA256 signature verification |
| `session_secret_key` | `str` | All modes | Must be ≥64 characters |
| `cookie_secure` | `bool` | Production | `effective_cookie_secure` must be `True` (auto-detected from HTTPS or explicit) |
| `cors_origins` | `str` | All modes | Each origin validated: must have scheme (`http`/`https`) and hostname |
| `enable_docs` | `bool` | N/A | Default `False`; independent of `DEBUG` flag |
| `admin_github_user_id` | `int \| None` | Production | Must be set; numeric GitHub user ID |
| `debug` | `bool` | N/A | Default `False`; does NOT disable security controls |

**Startup Validation Flow**:

```text
[Application Start]
    │
    ├── Non-debug mode?
    │   ├── ENCRYPTION_KEY set? → ERROR if missing
    │   ├── GITHUB_WEBHOOK_SECRET set? → ERROR if missing
    │   ├── effective_cookie_secure? → ERROR if False
    │   ├── ADMIN_GITHUB_USER_ID set? → ERROR if missing
    │   └── All pass → Continue startup
    │
    ├── All modes:
    │   ├── SESSION_SECRET_KEY ≥ 64 chars? → ERROR if too short
    │   ├── CORS origins well-formed? → ERROR on malformed
    │   └── All pass → Continue startup
    │
    └── Debug mode?
        └── Warn on missing optional secrets (non-blocking)
```

---

### ProjectAuthorization (Existing — Centralized)

Represents the authorization check for project-scoped operations. Implemented as the `verify_project_access` FastAPI dependency in `dependencies.py`.

| Field | Type | Description |
|-------|------|-------------|
| `project_id` | `str` | Target project identifier from request |
| `session` | `UserSession` | Authenticated user session (from cookie) |
| `user_projects` | `list[Project]` | User's accessible projects (fetched from GitHub API) |

**Authorization Flow**:

```text
[API Request with project_id]
    │
    ├── Extract session from cookie → UserSession
    ├── Fetch user's projects via GitHub API
    ├── Check: project_id in user's project list?
    │   ├── Yes → Allow request
    │   └── No → 403 Forbidden
    │
    └── API error during fetch → 403 "Unable to verify project access"
```

**Applied to endpoints**: `tasks.py`, `projects.py`, `settings.py`, `workflow.py`, `agents.py`, `activity.py`, `pipelines.py`, `tools.py`

---

### RateLimitBucket (Existing — Implemented)

Represents a rate limit tracking bucket for endpoint protection. Managed by the `RateLimitKeyMiddleware` and `slowapi` limiter.

| Field | Type | Description |
|-------|------|-------------|
| `key` | `str` | Rate limit key: `github_user_id`, `user:{session_id}`, or `ip:{address}` |
| `endpoint` | `str` | Rate-limited endpoint path |
| `limit` | `str` | Rate limit expression (e.g., `"20/minute"`) |
| `remaining` | `int` | Remaining requests in current window |
| `reset_at` | `datetime` | Window reset time |

**Key Resolution Order**:

```text
[Request] → RateLimitKeyMiddleware
    │
    ├── 1. GitHub user ID (from session lookup) → "12345"
    ├── 2. Session cookie → "user:abc-def-123"
    └── 3. IP address (fallback) → "ip:192.168.1.1"
```

---

### EncryptedToken (Existing — Enhanced)

Represents an OAuth token stored with Fernet encryption. Managed by the `EncryptionService`.

| Field | Type | Description |
|-------|------|-------------|
| `ciphertext` | `bytes` | Fernet-encrypted token (AES-128-CBC + HMAC-SHA256) |
| `plaintext_prefix` | `str \| None` | Known GitHub token prefix for legacy detection |

**Legacy Detection Prefixes**: `gho_`, `ghp_`, `ghr_`, `ghu_`, `ghs_`, `github_pat_`

**Encryption/Decryption Flow**:

```text
[Store Token]
    │
    ├── ENCRYPTION_KEY set?
    │   ├── Yes → Fernet.encrypt(token) → store ciphertext
    │   └── No (debug only) → store plaintext with warning
    │
[Read Token]
    │
    ├── Value starts with known prefix? → Legacy plaintext token
    │   └── Encrypt-on-read if ENCRYPTION_KEY now available
    └── Otherwise → Fernet.decrypt(ciphertext) → return plaintext
```

---

### WebhookVerification (Existing — Unconditional)

Represents the webhook signature verification model. Used by `webhooks.py` (GitHub) and `signal.py` (Signal).

| Provider | Secret Source | Algorithm | Comparison |
|----------|-------------|-----------|------------|
| GitHub | `GITHUB_WEBHOOK_SECRET` | HMAC-SHA256 | `hmac.compare_digest` |
| Signal | `SIGNAL_WEBHOOK_SECRET` | Direct match | `hmac.compare_digest` |

**Verification Flow (both providers)**:

```text
[Webhook Request]
    │
    ├── Secret configured?
    │   ├── No → REJECT (never bypass)
    │   └── Yes → Verify signature
    │       ├── Valid → Process webhook
    │       └── Invalid → REJECT (log warning)
    │
    └── Debug mode has NO effect on this flow
```

---

## Relationships

```text
SecurityConfig (startup validation)
    │
    ├── Gates: Session creation (encryption_key, session_secret_key)
    ├── Gates: Cookie security (effective_cookie_secure)
    ├── Gates: Webhook verification (github_webhook_secret)
    ├── Gates: CORS policy (cors_origins_list)
    └── Gates: API docs visibility (enable_docs)

Session (authenticated user)
    │
    ├── Transport: HttpOnly + SameSite=Strict + Secure cookie
    ├── Encryption: EncryptedToken (access_token, refresh_token)
    ├── Authorization: ProjectAuthorization (verify_project_access)
    └── Rate Limiting: RateLimitBucket (per-user key)

ProjectAuthorization
    │
    ├── Input: Session + project_id
    ├── Check: GitHub API (user's project list)
    └── Applied to: 8+ API endpoint modules

WebhookVerification
    │
    ├── GitHub: HMAC-SHA256 signature verification
    └── Signal: Constant-time secret comparison
```

## State Transitions

The security audit primarily hardens existing flows rather than introducing new stateful entities. The key state transitions are:

### Startup Validation State

```text
[Unconfigured] → validate_production_settings()
    │
    ├── All secrets valid → [Running]
    ├── Missing/invalid secrets → [Startup Failed] (exit with error)
    └── Debug mode, missing optional → [Running with Warnings]
```

### Token Encryption Migration State

```text
[Legacy Plaintext Token] → decrypt() detects prefix
    │
    ├── ENCRYPTION_KEY available → encrypt-on-read → [Encrypted Token]
    └── ENCRYPTION_KEY missing (debug) → return plaintext → [Legacy Plaintext]
```
