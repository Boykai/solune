# Quickstart: Security, Privacy & Vulnerability Audit

**Feature**: 002-security-review
**Date**: 2026-03-31
**Prerequisites**: [plan.md](./plan.md), [data-model.md](./data-model.md), [contracts/](./contracts/)

## Overview

This feature addresses 21 security findings from a comprehensive OWASP Top 10 audit. All remediations are implemented across the existing codebase (see [research.md](./research.md) for per-finding file/line references) — no new modules or dependencies are required. This quickstart documents the verification procedures for each finding and the deployment considerations for operators.

## Remediated Files

### Backend (`solune/backend/src/`)

| File | Findings Addressed | Key Changes |
|------|--------------------|-------------|
| `config.py` | #2, #9, #12, #14, #16 | Production startup validation for secrets, cookie security, CORS origins, docs toggle |
| `api/auth.py` | #1, #7 | Cookie-based session transport, POST-body dev login |
| `api/signal.py` | #5 | `hmac.compare_digest` for webhook secret |
| `api/webhooks.py` | #13 | Unconditional webhook signature verification |
| `dependencies.py` | #4 | Centralized `verify_project_access` dependency |
| `middleware/rate_limit.py` | #11 | Per-user + per-IP rate limiting via slowapi |
| `services/database.py` | #15 | Directory 0700, file 0600 permissions |
| `services/encryption.py` | #2 | Fernet encryption with legacy plaintext detection |
| `services/github_auth.py` | #8 | OAuth scope documentation (repo retained with justification) |
| `services/github_projects/service.py` | #19 | GraphQL error sanitization |
| `main.py` | #14 | `enable_docs` gating for Swagger/ReDoc |

### Frontend (`solune/frontend/`)

| File | Findings Addressed | Key Changes |
|------|--------------------|-------------|
| `Dockerfile` | #3 | Non-root `nginx-app` user, port 8080 |
| `nginx.conf` | #6 | All security headers, `server_tokens off` |
| `src/hooks/useAuth.ts` | #1 | Cookie-only auth, URL cleanup |
| `src/hooks/useChatHistory.ts` | #18 | Memory-only storage, legacy cleanup |
| `src/components/board/IssueCard.tsx` | #21 | Avatar URL domain validation |

### Infrastructure

| File | Findings Addressed | Key Changes |
|------|--------------------|-------------|
| `docker-compose.yml` | #10, #17 | 127.0.0.1 bindings, `/var/lib/solune/data` volume |
| `.github/workflows/branch-issue-link.yml` | #20 | Minimal permissions with justification |

## Verification Checklist

Run these checks to verify all security controls are in place:

### 1. Authentication Flow (Findings #1, #7)

```bash
# Verify OAuth callback sets cookie, no credentials in URL
# Start the application and complete an OAuth flow
# Check: redirect URL is /auth/callback with NO query parameters

# Verify dev login accepts POST body only
curl -X POST http://localhost:8000/api/v1/auth/dev-login \
  -H "Content-Type: application/json" \
  -d '{"github_token": "ghp_test_token"}'
# Expected: 200 OK (debug mode) or 404 (production mode)

# Verify dev login rejects GET with query param
curl http://localhost:8000/api/v1/auth/dev-login?github_token=ghp_test
# Expected: 405 Method Not Allowed or 404
```

### 2. Startup Validation (Findings #2, #9, #12)

```bash
# Verify production startup fails without ENCRYPTION_KEY
DEBUG=false ENCRYPTION_KEY= python -c "from src.config import get_settings; get_settings()"
# Expected: Error about missing ENCRYPTION_KEY

# Verify startup fails with short session key
SESSION_SECRET_KEY="short" python -c "from src.config import get_settings; get_settings()"
# Expected: Error about SESSION_SECRET_KEY length

# Verify CORS validation catches malformed origins
CORS_ORIGINS="not-a-url" python -c "from src.config import get_settings; s = get_settings(); s.cors_origins_list"
# Expected: ValueError about malformed CORS origin
```

### 3. Container Security (Finding #3)

```bash
# Verify frontend container runs as non-root
docker compose up -d frontend
docker exec solune-frontend id
# Expected: uid=100(nginx-app) gid=101(nginx-app)

docker exec solune-frontend ps aux | head -5
# Expected: nginx processes running as nginx-app, not root
```

### 4. Project Authorization (Finding #4)

```bash
# Verify unauthorized project access returns 403
# Authenticate as User A, get session cookie
# Attempt to access User B's project:
curl -b "session_id=user_a_session" \
  http://localhost:8000/api/v1/projects/user_b_project_id/tasks
# Expected: 403 Forbidden
```

### 5. Security Headers (Finding #6)

```bash
# Verify all security headers present
curl -I http://localhost:5173/ 2>/dev/null | grep -iE \
  "content-security-policy|strict-transport|referrer-policy|permissions-policy|x-content-type|server:"
# Expected output includes:
#   Content-Security-Policy: default-src 'self'; ...
#   Strict-Transport-Security: max-age=31536000; includeSubDomains
#   Referrer-Policy: strict-origin-when-cross-origin
#   Permissions-Policy: camera=(), microphone=(), geolocation=()
#   X-Content-Type-Options: nosniff
#   Server: nginx  (no version number)

# Verify X-XSS-Protection is absent
curl -I http://localhost:5173/ 2>/dev/null | grep -i "x-xss-protection"
# Expected: no output (header absent)
```

### 6. Constant-Time Comparisons (Findings #5, #13)

```bash
# Code review verification — search for timing-safe comparisons
cd solune/backend
grep -rn "hmac.compare_digest" src/
# Expected: Found in api/signal.py and api/webhooks.py

# Verify no standard equality on secrets
grep -rn "webhook_secret\s*[!=]=" src/ | grep -v "hmac\|compare_digest\|#\|\.pyc"
# Expected: no results (all comparisons use hmac.compare_digest)
```

### 7. Rate Limiting (Finding #11)

```bash
# Verify rate limiting is active on OAuth callback
for i in $(seq 1 25); do
  curl -s -o /dev/null -w "%{http_code}\n" \
    "http://localhost:8000/api/v1/auth/github/callback?code=test&state=test"
done
# Expected: 429 responses after ~20 requests
```

### 8. Database Permissions (Finding #15)

```bash
# Verify directory and file permissions
docker exec solune-backend stat -c '%a' /var/lib/solune/data
# Expected: 700

docker exec solune-backend stat -c '%a' /var/lib/solune/data/settings.db
# Expected: 600
```

### 9. Chat Storage (Finding #18)

```bash
# In browser devtools after login and sending messages:
# Console: localStorage.getItem('chat-message-history')
# Expected: null (no message content stored)

# After logout:
# Console: Object.keys(localStorage).filter(k => k.includes('chat'))
# Expected: empty array
```

### 10. Docker Network Binding (Finding #10)

```bash
# Verify loopback-only port binding
docker compose ps --format "{{.Name}}: {{.Ports}}"
# Expected: 127.0.0.1:8000->8000, 127.0.0.1:5173->8080

# Verify signal-api is not exposed on host
docker compose ps signal-api --format "{{.Ports}}"
# Expected: 8080/tcp (no host binding)
```

## Deferred Items

### OAuth Scope (Finding #8)

The `repo` scope is intentionally retained in `github_auth.py` because GitHub's API returns misleading 404 errors for project write operations (issue creation, label assignment, project card management) when the token has only `project` scope. This is documented inline with a comment explaining the trade-off.

**Future action**: Monitor GitHub's scope model for changes that would allow narrower scoping. Consider migrating to GitHub App authentication for granular repository permissions.

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Cookie-based sessions (not Bearer tokens) | HttpOnly cookies prevent XSS access to session credentials |
| Fernet encryption (not custom AES) | Standard library handles nonce/IV management, reducing implementation error risk |
| Centralized `verify_project_access` dependency | Single point of enforcement prevents authorization bypass from missed endpoints |
| Per-user rate limiting (not per-IP) | Avoids penalizing shared NAT/VPN users per audit recommendation |
| `enable_docs` separate from `DEBUG` | Prevents accidental API schema exposure when debug mode is misconfigured |
| Unconditional webhook verification | Eliminates class of vulnerabilities from debug-conditional security bypasses |
| Memory-only chat storage | Eliminates XSS-accessible persistent storage without backend chat infrastructure |
| Avatar URL whitelist (not blocklist) | Only known-good domains allowed; more secure than blocking known-bad patterns |
| `server_tokens off` in nginx | Prevents version-based vulnerability scanning and targeted exploits |
| 0700/0600 file permissions | Minimum privileges for SQLite operation; other container processes cannot read DB |
