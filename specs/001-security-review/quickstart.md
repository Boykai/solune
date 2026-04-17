# Quickstart: Security, Privacy & Vulnerability Audit

**Feature**: 001-security-review
**Date**: 2026-04-17

## Prerequisites

- Docker and Docker Compose installed
- Python 3.11+ with uv package manager
- Node.js 20+ with npm
- A GitHub OAuth App configured

## Environment Setup

### Required Environment Variables (Production)

```bash
# Generate encryption key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Generate webhook secret
openssl rand -hex 32

# Generate session secret (must be ≥64 characters)
openssl rand -hex 32
```

Set in `.env` or environment:

```bash
ENCRYPTION_KEY=<generated-fernet-key>
GITHUB_WEBHOOK_SECRET=<generated-secret>
SESSION_SECRET_KEY=<generated-64+-char-secret>
COOKIE_SECURE=true                    # Or use https:// FRONTEND_URL
FRONTEND_URL=https://your-domain.com
ADMIN_GITHUB_USER_ID=<your-github-id>
# ENABLE_DOCS=true                    # Optional: enable API docs
```

### Development Mode

In debug mode, missing secrets produce warnings instead of startup failures:

```bash
DEBUG=true
# Secrets are optional but recommended even in development
```

## Running the Application

```bash
cd solune
docker compose up --build
```

### Verify Security Controls

```bash
# 1. Check frontend security headers
curl -I http://127.0.0.1:5173

# Expected: Content-Security-Policy, Strict-Transport-Security,
#           Referrer-Policy, Permissions-Policy present
#           No nginx version in Server header

# 2. Check container runs as non-root
docker exec <frontend-container> id
# Expected: uid != 0

docker exec <backend-container> id
# Expected: uid != 0

# 3. Check database permissions
docker exec <backend-container> ls -la /var/lib/solune/data/
# Expected: drwx------ (0700) for directory

docker exec <backend-container> ls -la /var/lib/solune/data/settings.db
# Expected: -rw------- (0600) for file

# 4. Check port bindings (from host)
ss -tlnp | grep -E '8000|5173'
# Expected: 127.0.0.1:8000 and 127.0.0.1:5173 (not 0.0.0.0)
```

## Running Tests

### Backend

```bash
cd solune/backend
uv sync --locked --extra dev
uv run pytest --cov=src --cov-report=term-missing
```

### Frontend

```bash
cd solune/frontend
npm ci
npm run test
npm run type-check
npm run build
```

## Verification Checklist

| # | Check | How to Verify |
|---|-------|--------------|
| 1 | No credentials in URL after login | Inspect browser URL bar and history after OAuth login |
| 2 | Backend refuses to start without ENCRYPTION_KEY | Unset ENCRYPTION_KEY, start in non-debug mode |
| 3 | Frontend container is non-root | `docker exec <container> id` → non-root UID |
| 4 | Unauthorized project access returns 403 | Request with unowned project_id |
| 5 | WebSocket rejects unowned projects | Connect to unowned project WebSocket |
| 6 | Constant-time secret comparisons | Code review of `hmac.compare_digest` usage |
| 7 | Security headers present | `curl -I` frontend |
| 8 | Rate limiting returns 429 | Exceed rate limit threshold |
| 9 | No chat content in localStorage after logout | Check browser devtools |
| 10 | Database permissions are 0700/0600 | `ls -la` in container |

## Key Files

### Backend

| File | Security Function |
|------|------------------|
| `src/config.py` | Startup validation, secret enforcement |
| `src/api/auth.py` | OAuth flow, session cookies, dev login |
| `src/dependencies.py` | Centralized `verify_project_access()` |
| `src/api/webhooks.py` | HMAC-SHA256 webhook verification |
| `src/api/signal.py` | Constant-time webhook secret comparison |
| `src/services/encryption.py` | Fernet at-rest token encryption |
| `src/services/github_auth.py` | OAuth scopes configuration |
| `src/services/github_projects/service.py` | GraphQL error sanitization |
| `src/database.py` | File permission enforcement (0700/0600) |
| `src/main.py` | Rate limiting, ENABLE_DOCS toggle |

### Frontend

| File | Security Function |
|------|------------------|
| `Dockerfile` | Non-root user (`nginx-app`) |
| `nginx.conf` | Security headers, `server_tokens off` |
| `src/hooks/useAuth.ts` | Cookie-based auth, localStorage cleanup |
| `src/hooks/useChatHistory.ts` | In-memory only, legacy data cleanup |
| `src/components/board/IssueCard.tsx` | Avatar URL domain validation |

### Infrastructure

| File | Security Function |
|------|------------------|
| `docker-compose.yml` | 127.0.0.1 binding, external data volume |
| `.github/workflows/branch-issue-link.yml` | Minimal workflow permissions |
