# Implementation Plan: Security, Privacy & Vulnerability Audit

**Branch**: `001-security-review` | **Date**: 2026-04-17 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-security-review/spec.md`

## Summary

Comprehensive security hardening across the Solune application addressing 21 findings from the OWASP Top 10 audit: 3 Critical, 8 High, 9 Medium, and 2 Low severity items. The audit spans authentication flow, encryption enforcement, container configuration, access control, HTTP security headers, rate limiting, client-side data handling, and supply chain hardening.

**Key finding from codebase analysis**: The majority of security controls identified in the audit have **already been implemented** in the current codebase. This plan documents the current state of each finding, confirms existing mitigations, and identifies any remaining gaps.

## Technical Context

**Language/Version**: Python 3.11 (backend), TypeScript/React (frontend), nginx (reverse proxy)
**Primary Dependencies**: FastAPI, slowapi, cryptography (Fernet), githubkit, React 19, Vite
**Storage**: SQLite with Fernet at-rest encryption for OAuth tokens
**Testing**: pytest with coverage (backend), Vitest (frontend)
**Target Platform**: Linux containers (Docker), single-instance deployment
**Project Type**: Web application (backend + frontend)
**Performance Goals**: No user-visible performance regression from security changes (SC-012)
**Constraints**: Single-instance SQLite deployment; in-memory rate limiting and OAuth state
**Scale/Scope**: Single-tenant deployment; 21 security findings across ~15 source files

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Pre-Research Gate (Phase 0 Entry)

| Principle | Status | Evidence |
|-----------|--------|----------|
| I. Specification-First | ✅ PASS | `spec.md` contains 12 prioritized user stories (P1–P4) with Given-When-Then acceptance scenarios and independent test criteria |
| II. Template-Driven | ✅ PASS | All artifacts follow canonical templates from `.specify/templates/` |
| III. Agent-Orchestrated | ✅ PASS | Plan produced by `speckit.plan` agent with clear inputs (spec.md) and outputs (plan.md, research.md, data-model.md, contracts/, quickstart.md) |
| IV. Test Optionality | ✅ PASS | Feature spec includes verification checks; tests guided by spec requirements, not mandated globally |
| V. Simplicity and DRY | ✅ PASS | Security hardening modifies existing code patterns rather than introducing new abstractions. Centralized `verify_project_access()` avoids per-endpoint duplication |

### Post-Design Gate (Phase 1 Exit)

| Principle | Status | Evidence |
|-----------|--------|----------|
| I. Specification-First | ✅ PASS | All 12 user stories mapped to concrete implementation files with verification criteria |
| II. Template-Driven | ✅ PASS | plan.md, research.md, data-model.md, contracts/, quickstart.md all follow templates |
| III. Agent-Orchestrated | ✅ PASS | Handoff to `speckit.tasks` for task decomposition is clear |
| IV. Test Optionality | ✅ PASS | Verification checklist (10 behavior-based checks) defined in spec; no unnecessary test overhead |
| V. Simplicity and DRY | ✅ PASS | No new abstractions needed; all changes use existing patterns (FastAPI dependencies, nginx directives, Docker directives) |

## Project Structure

### Documentation (this feature)

```text
specs/001-security-review/
├── plan.md              # This file
├── research.md          # Phase 0: Research findings for all 21 audit items
├── data-model.md        # Phase 1: Entity modifications and behavioral contracts
├── quickstart.md        # Phase 1: Setup and verification guide
├── contracts/           # Phase 1: Security behavioral contracts
│   ├── README.md
│   ├── security-headers.yaml
│   ├── startup-validation.yaml
│   ├── access-control.yaml
│   └── rate-limiting.yaml
├── checklists/          # Quality checklists (from speckit.checklist)
└── tasks.md             # Phase 2 output (speckit.tasks — NOT created by speckit.plan)
```

### Source Code (repository root)

```text
solune/
├── backend/
│   ├── src/
│   │   ├── api/
│   │   │   ├── auth.py              # OAuth flow, session cookies, dev login (Finding 1, 7)
│   │   │   ├── webhooks.py          # HMAC-SHA256 webhook verification (Finding 5, 13)
│   │   │   ├── signal.py            # Constant-time webhook comparison (Finding 5)
│   │   │   ├── tasks.py             # Project access control (Finding 4)
│   │   │   ├── projects.py          # Project access control (Finding 4)
│   │   │   ├── settings.py          # Project access control (Finding 4)
│   │   │   ├── workflow.py          # Project access control (Finding 4)
│   │   │   └── chat.py              # Rate limiting (Finding 11)
│   │   ├── services/
│   │   │   ├── encryption.py        # Fernet at-rest encryption (Finding 2)
│   │   │   ├── github_auth.py       # OAuth scopes (Finding 8)
│   │   │   └── github_projects/
│   │   │       └── service.py       # GraphQL error sanitization (Finding 19)
│   │   ├── config.py                # Startup validation (Findings 2, 9, 12, 16)
│   │   ├── dependencies.py          # Centralized verify_project_access() (Finding 4)
│   │   ├── database.py              # File permissions 0700/0600 (Finding 15)
│   │   └── main.py                  # Rate limiting, ENABLE_DOCS (Findings 11, 14)
│   ├── tests/
│   └── Dockerfile                   # Non-root appuser (Finding 3)
├── frontend/
│   ├── src/
│   │   ├── hooks/
│   │   │   ├── useAuth.ts           # Cookie auth, localStorage cleanup (Findings 1, 18)
│   │   │   └── useChatHistory.ts    # In-memory only, legacy cleanup (Finding 18)
│   │   └── components/
│   │       └── board/
│   │           └── IssueCard.tsx     # Avatar URL validation (Finding 21)
│   ├── nginx.conf                   # Security headers, server_tokens off (Finding 6)
│   ├── Dockerfile                   # Non-root nginx-app (Finding 3)
│   └── tests/
├── docker-compose.yml               # 127.0.0.1 binding, /var/lib/solune/data (Findings 10, 17)
└── .github/workflows/
    └── branch-issue-link.yml        # Minimal permissions (Finding 20)
```

**Structure Decision**: Web application (Option 2) — existing backend/frontend/infrastructure structure. No new directories needed; all changes modify existing files.

## Implementation Phases

### Phase 1 — Critical (Findings 1–3)

All three Critical findings have been resolved in the current codebase:

| Finding | OWASP | Status | Implementation |
|---------|-------|--------|----------------|
| 1. Session token in URL | A02 | ✅ Resolved | `auth.py`: `_set_session_cookie()` with HttpOnly/SameSite=Strict/Secure; no URL credentials; `useAuth.ts`: no URL param reading |
| 2. Encryption not enforced | A02 | ✅ Resolved | `config.py`: `_validate_production_settings()` enforces ENCRYPTION_KEY, GITHUB_WEBHOOK_SECRET, SESSION_SECRET_KEY ≥64 chars in non-debug mode |
| 3. Frontend runs as root | A05 | ✅ Resolved | Frontend `Dockerfile`: `nginx-app` user created, `USER nginx-app` directive, unprivileged port 8080 |

### Phase 2 — High (Findings 4–10)

All seven High findings have been resolved in the current codebase:

| Finding | OWASP | Status | Implementation |
|---------|-------|--------|----------------|
| 4. No project scoping | A01 | ✅ Resolved | `dependencies.py`: `verify_project_access()` centralized dependency; used in tasks, projects, settings, workflow endpoints |
| 5. Timing attack (Signal) | A07 | ✅ Resolved | `signal.py` line 287: `hmac.compare_digest()` for constant-time comparison |
| 6. Missing security headers | A05 | ✅ Resolved | `nginx.conf`: CSP, HSTS, Referrer-Policy, Permissions-Policy present; `server_tokens off`; no X-XSS-Protection |
| 7. PAT in URL (dev) | A02 | ✅ Resolved | `auth.py`: dev login accepts credentials via POST body JSON only |
| 8. Broad OAuth scopes | A01 | ✅ Resolved | `github_auth.py` line 74: `read:user read:org project repo` — documented rationale for `repo` scope retention |
| 9. No session key entropy | A07 | ✅ Resolved | `config.py` line 188-193: SESSION_SECRET_KEY must be ≥64 characters |
| 10. Services on 0.0.0.0 | A05 | ✅ Resolved | `docker-compose.yml`: backend `127.0.0.1:8000`, frontend `127.0.0.1:5173` |

### Phase 3 — Medium (Findings 11–19)

All nine Medium findings have been resolved in the current codebase:

| Finding | OWASP | Status | Implementation |
|---------|-------|--------|----------------|
| 11. No rate limiting | A04 | ✅ Resolved | slowapi integrated; OAuth 20/min/IP, chat 10/min, agents 5/min, apps 10/min |
| 12. Cookie Secure not enforced | A02 | ✅ Resolved | `config.py`: `effective_cookie_secure` validated at startup in non-debug mode |
| 13. Debug bypasses webhooks | A05 | ✅ Resolved | `webhooks.py`: HMAC verification unconditional; no debug bypass |
| 14. API docs on DEBUG | A05 | ✅ Resolved | `config.py`: `enable_docs` boolean; `main.py`: docs gated on `settings.enable_docs` |
| 15. World-readable DB | A02 | ✅ Resolved | `database.py`: directory 0o700, file 0o600 with explicit `chmod` calls |
| 16. CORS not validated | A05 | ✅ Resolved | `config.py`: `cors_origins_list` property validates each origin has scheme and hostname |
| 17. Data volume in app dir | A05 | ✅ Resolved | `docker-compose.yml`: named volume `solune-data` mounted at `/var/lib/solune/data` |
| 18. Chat in localStorage | A02 | ✅ Resolved | `useChatHistory.ts`: in-memory only; legacy cleanup on init; `useAuth.ts`: clears on logout |
| 19. GraphQL error exposure | A09 | ✅ Resolved | `service.py`: logs full error, raises generic `ValueError("GitHub API request failed")` |

### Phase 4 — Low (Findings 20–21)

Both Low findings have been resolved in the current codebase:

| Finding | OWASP | Status | Implementation |
|---------|-------|--------|----------------|
| 20. Broad workflow permissions | Supply Chain | ✅ Resolved | `branch-issue-link.yml`: default `permissions: {}`, job-level `issues: write` + `contents: read` with comments |
| 21. Unvalidated avatar URLs | A03 | ✅ Resolved | `IssueCard.tsx`: `ALLOWED_AVATAR_HOSTS` validation, HTTPS check, SVG placeholder fallback |

## Verification Matrix

| # | Check | Method | Expected Result |
|---|-------|--------|----------------|
| 1 | No credentials in URL after login | Inspect browser URL bar, history, and access logs after OAuth login | No session tokens, OAuth tokens, or PATs in any URL |
| 2 | Backend refuses to start without ENCRYPTION_KEY | Start in non-debug mode without ENCRYPTION_KEY | Application exits with clear error message |
| 3 | Frontend container is non-root | `docker exec <frontend> id` | Non-root UID (nginx-app) |
| 4 | Unauthorized project access returns 403 | Request with unowned project_id | 403 Forbidden, no data leakage |
| 5 | WebSocket rejects unowned projects | Connect to unowned project WebSocket | Connection rejected before data sent |
| 6 | Constant-time secret comparisons | Code review for `hmac.compare_digest` usage | All webhook/signal comparisons use constant-time |
| 7 | Security headers present | `curl -I <frontend>` | CSP, HSTS, Referrer-Policy, Permissions-Policy present; no nginx version |
| 8 | Rate limiting returns 429 | Exceed rate limit threshold on expensive endpoints | 429 Too Many Requests |
| 9 | No chat content in localStorage after logout | Check browser devtools | localStorage empty of message content |
| 10 | Database permissions | `ls -la` in container | Directory 0700, file 0600 |

## Key Decisions

| Decision | Rationale | Impact |
|----------|-----------|--------|
| Retain `repo` OAuth scope | Required for issue creation, label management, and project board mutations on private repositories. Narrower scopes break functionality. | Users requesting minimum scopes would need GitHub App migration (out of scope) |
| Fernet for at-rest encryption | Industry-standard authenticated encryption; cryptography library already in dependencies | Existing plaintext tokens auto-detected via GitHub token prefix pattern |
| In-memory rate limiting | Adequate for single-instance SQLite deployment; no external dependency needed | Multi-instance deployments would need Redis-backed storage |
| Per-user over per-IP rate limits | Avoids penalizing users behind shared NAT/VPN | Unauthenticated endpoints (OAuth callback) use per-IP as fallback |

## Complexity Tracking

> No constitution violations detected. All changes follow existing patterns.

| Aspect | Assessment |
|--------|-----------|
| New abstractions | None — all changes use existing FastAPI dependencies, nginx directives, Docker directives |
| New dependencies | None — slowapi, cryptography already in project |
| Database migrations | None — behavioral changes only (enforcement of existing encryption) |
| Breaking changes | Encryption enforcement requires ENCRYPTION_KEY for non-debug deployments (migration: set env var) |
| Cross-cutting concerns | `verify_project_access()` centralized in `dependencies.py` prevents per-endpoint duplication |

## Generated Artifacts

| Artifact | Path | Description |
|----------|------|-------------|
| Research | [research.md](research.md) | Decision records for all 17 research topics across 21 findings |
| Data Model | [data-model.md](data-model.md) | Modified entities, transient constructs, and infrastructure configuration |
| Contracts | [contracts/](contracts/) | Security behavioral contracts (headers, startup, access control, rate limiting) |
| Quickstart | [quickstart.md](quickstart.md) | Setup guide with verification checklist |
