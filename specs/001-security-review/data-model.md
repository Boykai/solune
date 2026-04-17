# Data Model: Security, Privacy & Vulnerability Audit

**Feature**: 001-security-review
**Date**: 2026-04-17
**Spec**: [spec.md](spec.md)

## Overview

This feature is primarily a security hardening effort across existing code. It does not introduce new persistent entities but modifies behaviors of existing ones and adds transient runtime constructs. The data model changes are minimal — most work involves configuration validation, header injection, permission enforcement, and runtime security controls.

## Existing Entities (Modified Behavior)

### Session

Represents an authenticated user session established via OAuth.

| Field | Type | Change | Description |
|-------|------|--------|-------------|
| session_id | UUID | No change | Unique session identifier |
| user_id | int | No change | GitHub user ID |
| access_token | str (encrypted) | Enforcement | Must be encrypted at rest; startup refuses plaintext mode in production |
| refresh_token | str (encrypted) | Enforcement | Same encryption enforcement as access_token |
| expires_at | datetime | No change | Token expiration timestamp |

**Delivery Mechanism** (changed):
- ~~URL query parameter `?session_token=...`~~ → HttpOnly cookie with `SameSite=Strict; Secure` attributes
- **Current state**: Already migrated to cookie-based delivery

**Validation Rules**:
- Session cookie must have `HttpOnly`, `SameSite=Strict`, and `Secure` flags
- `Secure` flag mandatory in non-debug mode (startup validation)

---

### User Project Authorization

Represents the access relationship between a user and their projects.

| Field | Type | Description |
|-------|------|-------------|
| user_id | int | Authenticated user's GitHub ID |
| project_id | str | GitHub project node ID |
| access_verified | bool | Whether access was confirmed via GitHub API |

**State Transitions**:
- `unverified` → `verified`: First access check confirms ownership via GitHub API
- `verified` → `cached`: Subsequent checks use in-memory cache
- `cached` → `expired`: Cache TTL expires, re-verification required

**Validation Rules**:
- Every project-scoped endpoint must call `verify_project_access()` before any action
- WebSocket connections must verify access before upgrade
- Failed verification returns 403 Forbidden with no data leakage

---

### Application Configuration (Settings)

Runtime configuration loaded from environment variables at startup.

| Field | Type | Required (Prod) | Validation |
|-------|------|-----------------|------------|
| ENCRYPTION_KEY | str | Yes | Must be set; Fernet-compatible key |
| GITHUB_WEBHOOK_SECRET | str | Yes | Must be set; used for HMAC-SHA256 verification |
| SESSION_SECRET_KEY | str | Yes | Must be ≥64 characters |
| COOKIE_SECURE | bool | Conditional | Must be true (or FRONTEND_URL must be HTTPS) |
| ENABLE_DOCS | bool | No | Independent of DEBUG; gates API docs visibility |
| CORS_ORIGINS | str | No | Each origin must be well-formed URL with scheme and hostname |
| DEBUG | bool | No | Controls warning vs. error behavior for missing config |

**State Transitions**:
- `startup` → `validated`: All production checks pass → application starts
- `startup` → `failed`: Any production check fails → application refuses to start with clear error

---

## Transient Runtime Constructs

### Rate Limit Counter

In-memory rate limiting state managed by slowapi.

| Dimension | Scope | Description |
|-----------|-------|-------------|
| Per-user | Write/AI endpoints | Prevents single user from exhausting shared quotas |
| Per-IP | OAuth callback | Prevents brute-force attacks on unauthenticated endpoint |

**Configured Limits**:
- OAuth callback: 20 requests/minute per IP
- Chat endpoints: 10 requests/minute per user
- Agent invocation: 5 requests/minute per user
- App endpoints: 10 requests/minute per user

**Behavior**: Returns HTTP 429 Too Many Requests when threshold exceeded.

---

### Chat Message Reference (Client-Side)

In-memory React state — messages are NOT persisted to browser storage.

| Field | Type | Description |
|-------|------|-------------|
| messages | array | In-memory message array, cleared on navigation/refresh |
| Legacy cleanup | N/A | `clearLegacyStorage()` removes pre-v2 localStorage data on init |

**Validation Rules**:
- No message content written to localStorage or sessionStorage
- Legacy `chat-message-history` localStorage key removed on hook initialization
- All local data cleared on logout via `useAuth.ts`

---

## Infrastructure Entities

### Container Configuration

| Container | User | Port Binding | Volume |
|-----------|------|-------------|--------|
| Backend | `appuser` (non-root) | `127.0.0.1:8000` → `8000` | `/var/lib/solune/data` (0700) |
| Frontend | `nginx-app` (non-root) | `127.0.0.1:5173` → `8080` | None (static files) |
| Signal API | dedicated user | Internal only | Signal CLI config volume |

### Database File Permissions

| Resource | Permission | Owner |
|----------|-----------|-------|
| Database directory | 0700 | Application user |
| Database file | 0600 | Application user |
| Recovered database file | 0600 | Application user |

---

## Entity Relationships

```text
User ──owns──> Project(s)
  │                │
  └── Session      └── Tasks, Settings, Workflows, WebSocket
       │
       └── verify_project_access() ── guards ──> All project-scoped operations

Configuration ── validates at startup ──> Application lifecycle
  │
  ├── ENCRYPTION_KEY ──> Token encryption/decryption
  ├── WEBHOOK_SECRET ──> Webhook HMAC verification
  ├── SESSION_SECRET_KEY ──> Session signing
  └── COOKIE_SECURE ──> Cookie security flags

Rate Limiter ── guards ──> Expensive endpoints
  ├── Per-user ──> Chat, Agents, Apps, Workflows
  └── Per-IP ──> OAuth callback
```

## No New Database Migrations Required

All data model changes are behavioral (enforcement of existing fields, runtime validation, permission checks). No new database tables, columns, or migrations are needed. The encryption enforcement requires existing deployments to set the `ENCRYPTION_KEY` environment variable, but the encryption service already handles legacy plaintext token detection gracefully.
