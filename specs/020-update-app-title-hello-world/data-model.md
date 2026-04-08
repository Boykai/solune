# Data Model: Update App Title to "Hello World"

**Feature**: 020-update-app-title-hello-world | **Date**: 2026-04-08

## Overview

This feature has no data model changes — it is a static text replacement in the frontend UI layer. This document serves as the change map defining the exact source-to-target transformations.

## Change Map

### Source Files (UI-Visible Title)

| # | File | Line | Old Value | New Value | Context |
|---|------|------|-----------|-----------|---------|
| S1 | `solune/frontend/index.html` | 7 | `<title>Solune</title>` | `<title>Hello World</title>` | HTML document title (browser tab) |
| S2 | `solune/frontend/src/layout/Sidebar.tsx` | 97 | `Solune` | `Hello World` | Brand heading in sidebar (expanded state) |
| S3 | `solune/frontend/src/pages/LoginPage.tsx` | 102 | `Solune` | `Hello World` | h2 heading on login page |

### Unit Test Files

| # | File | Line | Old Assertion | New Assertion |
|---|------|------|---------------|---------------|
| T1 | `solune/frontend/src/layout/Sidebar.test.tsx` | 36 | `screen.getByText('Solune')` | `screen.getByText('Hello World')` |
| T2 | `solune/frontend/src/layout/Sidebar.test.tsx` | 41 | `screen.queryByText('Solune')` | `screen.queryByText('Hello World')` |

### E2E Test Files

| # | File | Line | Old Assertion | New Assertion |
|---|------|------|---------------|---------------|
| E1 | `solune/frontend/e2e/auth.spec.ts` | 8 | `getByRole('heading', { name: 'Solune' })` | `getByRole('heading', { name: 'Hello World' })` |
| E2 | `solune/frontend/e2e/ui.spec.ts` | 47 | `toContainText('Solune')` | `toContainText('Hello World')` |
| E3 | `solune/frontend/e2e/ui.spec.ts` | 71 | `toContainText('Solune')` | `toContainText('Hello World')` |
| E4 | `solune/frontend/e2e/integration.spec.ts` | 82 | `toContainText('Solune')` | `toContainText('Hello World')` |
| E5 | `solune/frontend/e2e/protected-routes.spec.ts` | 12 | `toContainText('Solune')` | `toContainText('Hello World')` |

## Entity Relationships

```
index.html <title>  ──────────  Browser tab display
Sidebar.tsx brand   ──────────  Authenticated layout header
LoginPage.tsx h2    ──────────  Unauthenticated landing page
```

All three are independent — no shared state, no data flow between them. Each is a static text node rendered by the browser/React.

## Validation Rules

- The `<title>` tag must contain exactly "Hello World" (no extra whitespace)
- The Sidebar brand text must render "Hello World" when `isCollapsed` is `false`
- The LoginPage h2 must render "Hello World" for unauthenticated users
- No other functional behavior should change

## State Transitions

N/A — static text replacement, no state machine involved.
