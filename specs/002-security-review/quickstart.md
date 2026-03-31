# Quickstart: Security, Privacy & Vulnerability Audit

**Feature**: 002-security-review
**Date**: 2026-03-31
**Prerequisites**: [plan.md](./plan.md), [data-model.md](./data-model.md), [contracts/](./contracts/)

## Overview

This feature addresses 21 OWASP Top 10 security findings across 4 severity phases (Critical, High, Medium, Low). Changes span the Python/FastAPI backend, React/nginx frontend, Docker infrastructure, and GitHub Actions workflows. All fixes are surgical modifications to existing modules — no new services or frameworks are introduced.

## Modified Files

### Phase 1 — Critical (3 findings)

#### 1. `solune/backend/src/api/auth.py` — Cookie-Only Session Delivery

**Security control**: OAuth callback sets HttpOnly cookie and redirects with no URL credentials.

```python
# OAuth callback sets cookie, redirects cleanly
response = RedirectResponse(url=frontend_url, status_code=302)
response.set_cookie(
    key=settings.session_cookie_name,
    value=session.session_id,
    httponly=True,
    samesite="strict",
    secure=settings.cookie_secure,
    max_age=int(settings.session_expire_hours * 3600),
)
```

**Also**: Dev login endpoint accepts PAT via POST body only (Finding #7).

#### 2. `solune/backend/src/config.py` — Mandatory Production Secrets

**Security control**: Startup validation for encryption key, webhook secret, session key, cookie secure.

```python
def _validate_production_secrets(self) -> None:
    if not self.debug:
        if not self.encryption_key:
            raise ValueError("ENCRYPTION_KEY required in production")
        if not self.github_webhook_secret:
            raise ValueError("GITHUB_WEBHOOK_SECRET required in production")
    if len(self.session_secret_key) < 64:
        raise ValueError("SESSION_SECRET_KEY must be >= 64 characters")
```

#### 3. `solune/frontend/Dockerfile` — Non-Root Container

**Security control**: nginx runs as dedicated `nginx-app` user.

```dockerfile
RUN addgroup -S nginx-app && adduser -S -G nginx-app nginx-app
USER nginx-app
```

### Phase 2 — High (8 findings)

#### 4. `solune/backend/src/dependencies.py` — Centralized Project Authorization

**Security control**: `verify_project_access()` checks project ownership before any operation.

```python
async def verify_project_access(
    request: Request, project_id: str, session: UserSession
) -> None:
    projects = await github_projects_service.list_user_projects(
        session.access_token, session.github_username
    )
    if project_id not in [p.id for p in projects]:
        raise AuthorizationError("Access denied to project")
```

#### 5. `solune/backend/src/api/signal.py` — Constant-Time Comparison

```python
if not hmac.compare_digest(x_signal_secret, settings.signal_webhook_secret):
    raise AuthorizationError("Invalid webhook secret")
```

#### 6. `solune/frontend/nginx.conf` — Security Headers

```nginx
server_tokens off;
add_header Content-Security-Policy "default-src 'self'; ...";
add_header Strict-Transport-Security "max-age=31536000";
add_header Referrer-Policy "strict-origin-when-cross-origin";
add_header Permissions-Policy "camera=(), microphone=(), geolocation=()";
# No X-XSS-Protection (deprecated)
```

#### 7. `solune/backend/src/services/github_auth.py` — OAuth Scopes

Scopes: `read:user read:org project repo` — `repo` retained due to GitHub API limitation (documented).

#### 8. `docker-compose.yml` — Localhost-Only Bindings

```yaml
ports:
  - "127.0.0.1:8000:8000"  # Backend
  - "127.0.0.1:5173:8080"  # Frontend
```

### Phase 3 — Medium (9 findings)

#### 9. `solune/backend/src/middleware/rate_limit.py` — Rate Limiting

Per-user rate limits via slowapi with fallback to per-IP for unauthenticated requests.

#### 10. `solune/backend/src/api/webhooks.py` — Unconditional Verification

Webhook signature verification always enforced, never conditional on DEBUG.

#### 11. `solune/backend/src/main.py` — Independent Docs Toggle

```python
docs_url="/api/docs" if settings.enable_docs else None,
redoc_url="/api/redoc" if settings.enable_docs else None,
```

#### 12. `solune/backend/src/services/database.py` — File Permissions

```python
os.makedirs(db_dir, mode=0o700, exist_ok=True)
os.chmod(db_path, 0o600)
```

#### 13. `solune/frontend/src/hooks/useChatHistory.ts` — Memory-Only Storage

Chat history in React state only. Legacy localStorage cleared on logout.

#### 14. `solune/backend/src/services/github_projects/graphql.py` — Error Sanitization

Full errors logged server-side; only generic messages returned to clients.

### Phase 4 — Low (2 findings)

#### 15. `.github/workflows/branch-issue-link.yml` — Minimum Permissions

```yaml
permissions: {}
jobs:
  link-branch:
    permissions:
      issues: write
      contents: read
```

#### 16. `solune/frontend/src/components/IssueCard.tsx` — Avatar Validation

```typescript
function validateAvatarUrl(url: string | undefined | null): string {
  if (!url) return placeholder;
  const parsed = new URL(url);
  if (parsed.protocol !== 'https:') return placeholder;
  if (!ALLOWED_AVATAR_HOSTS.includes(parsed.hostname)) return placeholder;
  return url;
}
```

## Verification

After implementation, verify each phase against the behavioral checks:

```bash
# Phase 1: Critical
# V-001: Login flow produces no URL credentials
# V-002: Backend startup fails without ENCRYPTION_KEY
cd solune/backend
ENCRYPTION_KEY="" DEBUG=false uv run python -m src.main  # Should fail

# V-003: Frontend container runs non-root
docker exec solune-frontend id  # Should show non-root UID

# Phase 2: High
# V-004: Unowned project returns 403
curl -X GET http://localhost:8000/api/v1/tasks?project_id=UNOWNED -H "Cookie: session=..." # 403

# V-006: Constant-time comparison (code review)
grep -n "compare_digest" solune/backend/src/api/signal.py solune/backend/src/api/webhooks.py

# V-007: Security headers present
curl -I http://localhost:5173/ | grep -E "Content-Security-Policy|Strict-Transport-Security|Referrer-Policy"

# Phase 3: Medium
# V-008: Rate limiting returns 429
for i in $(seq 1 25); do curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/api/v1/auth/github/callback; done

# V-009: No chat content in localStorage after logout (browser devtools)

# V-010: Database permissions
stat -c "%a" /var/lib/solune/data/     # Should be 700
stat -c "%a" /var/lib/solune/data/settings.db  # Should be 600

# Run existing tests to confirm no regressions
cd solune/backend
uv run pytest tests/unit/ -v --tb=short
uv run ruff check src tests
uv run ruff format --check src tests
uv run pyright src
```

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Cookie-only session delivery | Industry standard; prevents URL-based credential leaks in logs/history/Referer |
| Fail-fast startup validation | Only reliable way to prevent misconfigured production deployments |
| Centralized `verify_project_access` | Eliminates "forgot the check" failure mode; idiomatic FastAPI Depends() |
| `hmac.compare_digest` for all secrets | Standard library constant-time comparison; prevents timing side-channels |
| Per-user rate limits (slowapi) | Avoids NAT/VPN false positives; integrates natively with FastAPI |
| `ENABLE_DOCS` separate from `DEBUG` | Prevents accidental API schema exposure in debug-mode production |
| Memory-only chat storage | Prevents localStorage XSS data exfiltration; cleared on page unload/logout |
| `repo` scope retained | GitHub API requires it for Projects V2 operations; documented accepted risk |
| Non-root containers | Defense-in-depth; limits container escape blast radius |
| 0700/0600 file permissions | Principle of least privilege for database files in container |
