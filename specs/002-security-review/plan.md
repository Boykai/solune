# Implementation Plan: Security, Privacy & Vulnerability Audit

**Branch**: `002-security-review` | **Date**: 2026-03-31 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-security-review/spec.md`

## Summary

A comprehensive security audit identified 21 findings across OWASP Top 10 categories (3 Critical, 8 High, 9 Medium, 2 Low) covering authentication, authorization, container hardening, transport security, data protection, and supply-chain controls. Research confirms that **all 21 findings have already been remediated** in the current codebase. The remaining work is verification, documentation, and one deferred trade-off: the OAuth `repo` scope is intentionally retained because GitHub's API returns misleading 404 errors for project write operations with narrower scopes. This plan documents each remediation, the technical approach taken, and the verification strategy.

## Technical Context

**Language/Version**: Python 3.13+ (backend), TypeScript/React (frontend)
**Primary Dependencies**: FastAPI, Pydantic, slowapi (rate limiting), cryptography (Fernet encryption), nginx 1.29.x (reverse proxy)
**Storage**: SQLite via aiosqlite (encrypted at rest with Fernet when ENCRYPTION_KEY configured)
**Testing**: pytest + pytest-asyncio (backend), Vitest (frontend)
**Target Platform**: Linux server (Docker — Alpine-based images)
**Project Type**: Web application (backend + frontend monorepo under `solune/`)
**Performance Goals**: Rate limits enforce per-user budgets on expensive endpoints (chat, agents, workflow); OAuth callback limited to 20/minute per IP
**Constraints**: All containers non-root; all secrets mandatory in production; cookies HttpOnly+SameSite=Strict+Secure
**Scale/Scope**: 21 security findings across ~15 backend files, ~3 frontend files, 2 Dockerfiles, 1 nginx config, 1 docker-compose, 1 GitHub Actions workflow

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Specification-First | ✅ PASS | `spec.md` exists with 19 prioritized user stories (P1–P4), Given-When-Then acceptance scenarios, 30 functional requirements, and 12 measurable success criteria |
| II. Template-Driven | ✅ PASS | All artifacts follow canonical templates from `.specify/templates/` |
| III. Agent-Orchestrated | ✅ PASS | Single-responsibility: this plan phase produces design artifacts; implementation deferred to `/speckit.tasks` + `/speckit.implement` |
| IV. Test Optionality | ✅ PASS | Spec mandates behavior-based verification (10 checks); unit tests recommended but not required for configuration/infrastructure changes |
| V. Simplicity and DRY | ✅ PASS | Remediations use existing patterns: centralized `verify_project_access` dependency, shared `limiter` middleware, existing `EncryptionService`. No new frameworks or abstractions introduced |

**Gate Result**: ALL PASS — proceeding to Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/002-security-review/
├── plan.md              # This file
├── research.md          # Phase 0: Research findings for each audit item
├── data-model.md        # Phase 1: Security-relevant entity models
├── quickstart.md        # Phase 1: Verification and deployment guide
├── contracts/           # Phase 1: Security contract definitions
│   └── security-controls.yaml  # Security controls interface contract
└── tasks.md             # Phase 2 output (/speckit.tasks — NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
solune/backend/
├── src/
│   ├── api/
│   │   ├── auth.py              # EXISTING: OAuth callback (cookie-based), dev-login (POST body)
│   │   ├── signal.py            # EXISTING: hmac.compare_digest for webhook secret
│   │   ├── webhooks.py          # EXISTING: Unconditional signature verification
│   │   ├── chat.py              # EXISTING: Rate-limited endpoints
│   │   ├── agents.py            # EXISTING: Rate-limited, project-scoped
│   │   ├── workflow.py          # EXISTING: Rate-limited, project-scoped
│   │   ├── tasks.py             # EXISTING: Project-scoped via verify_project_access
│   │   ├── projects.py          # EXISTING: Project-scoped via verify_project_access
│   │   └── settings.py          # EXISTING: Project-scoped via verify_project_access
│   ├── config.py                # EXISTING: Production validation gates for all secrets
│   ├── dependencies.py          # EXISTING: verify_project_access centralized check
│   ├── main.py                  # EXISTING: enable_docs gating, CORS middleware
│   ├── middleware/
│   │   └── rate_limit.py        # EXISTING: slowapi per-user + per-IP rate limiting
│   └── services/
│       ├── database.py          # EXISTING: 0700 dir / 0600 file permissions
│       ├── encryption.py        # EXISTING: Fernet encryption with plaintext detection
│       ├── github_auth.py       # EXISTING: OAuth scope (repo retained with justification)
│       └── github_projects/
│           └── service.py       # EXISTING: GraphQL errors sanitized
└── tests/
    └── unit/                    # Existing unit test infrastructure

solune/frontend/
├── Dockerfile                   # EXISTING: USER nginx-app (non-root), port 8080
├── nginx.conf                   # EXISTING: All security headers, server_tokens off
└── src/
    ├── hooks/
    │   ├── useAuth.ts           # EXISTING: Cookie-only auth, URL cleanup
    │   └── useChatHistory.ts    # EXISTING: Memory-only, localStorage cleared
    └── components/
        └── board/
            └── IssueCard.tsx    # EXISTING: Avatar URL domain validation

docker-compose.yml               # EXISTING: 127.0.0.1 bindings, /var/lib/solune/data volume
.github/workflows/
    └── branch-issue-link.yml    # EXISTING: Minimal permissions with justification
```

**Structure Decision**: Web application structure. All 21 security remediations are implemented across the existing backend, frontend, Docker, and CI files. No new modules required — changes hardened existing code paths.

## Constitution Re-Check (Post-Design)

*Re-evaluation after Phase 1 design artifacts are complete.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Specification-First | ✅ PASS | All 30 functional requirements from spec.md are traceable to implemented remediations in research.md |
| II. Template-Driven | ✅ PASS | All generated artifacts (research.md, data-model.md, contracts/, quickstart.md) follow canonical templates |
| III. Agent-Orchestrated | ✅ PASS | Plan phase complete; handoff to `/speckit.tasks` for task decomposition and verification |
| IV. Test Optionality | ✅ PASS | Behavior-based verification checklist defined in quickstart.md; unit tests recommended for config validation |
| V. Simplicity and DRY | ✅ PASS | No new abstractions; remediations reuse existing patterns (`verify_project_access`, `limiter`, `EncryptionService`, Pydantic validators) |

**Gate Result**: ALL PASS — ready for Phase 2 (`/speckit.tasks`).

## Complexity Tracking

> No constitution violations — this section is intentionally empty.
