# Security Audit Checklist (P1)

**Category**: Security Vulnerabilities
**Priority**: P1 — Highest
**Scope**: All source files in `solune/backend/src/` and `solune/frontend/src/`

## Automated Scans

- [ ] Run `bandit -r src/ -ll -ii --skip B104` on backend — review all findings
- [ ] Run ESLint security plugin on frontend — review all findings
- [ ] Run `pip-audit` on backend dependencies — review all advisories
- [ ] Grep for hardcoded secrets: API keys, tokens, passwords in source and config files

## Manual Audit Areas

### Authentication & Authorization

- [ ] `src/api/auth.py` — Verify all auth endpoints validate tokens correctly
- [ ] `src/middleware/admin_guard.py` — Verify admin-only routes are properly guarded
- [ ] `src/middleware/csrf.py` — Verify CSRF protection covers all state-changing routes
- [ ] `src/services/github_auth.py` — Verify OAuth flow has no bypasses
- [ ] `src/services/session_store.py` — Verify session tokens are properly validated and expired

### Input Validation

- [ ] All API endpoints — Verify request bodies are validated via Pydantic models
- [ ] `src/api/webhooks.py` — Verify webhook payloads are validated before processing
- [ ] `src/services/chat_agent.py` — Verify user input is sanitized before LLM calls
- [ ] `src/api/signal.py` — Verify Signal bridge inputs are validated

### Cryptography & Secrets

- [ ] `src/services/encryption.py` — Verify encryption implementation uses secure algorithms
- [ ] `src/config.py` — Verify no secrets are hardcoded; all use environment variables
- [ ] `.env.example` — Verify example file contains only placeholder values

### Network Security

- [ ] `src/middleware/csp.py` — Verify Content Security Policy is restrictive
- [ ] `src/middleware/rate_limit.py` — Verify rate limiting covers all sensitive endpoints
- [ ] `src/services/mcp_server/auth.py` — Verify MCP server authentication is correct

### Frontend Security

- [ ] Verify no `dangerouslySetInnerHTML` without sanitization
- [ ] Verify API tokens are not stored in localStorage (use httpOnly cookies or memory)
- [ ] Verify all user-supplied data is escaped in rendered output

## Fix Criteria

For each finding:

1. Determine if the fix is obvious (clear vulnerability with clear solution)
2. If obvious: fix + add regression test
3. If ambiguous: add `TODO(bug-bash)` comment with options and rationale
