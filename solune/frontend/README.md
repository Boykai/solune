# Solune Frontend

The Solune frontend is a React 19 + Vite 8 single-page application that provides the authenticated shell, board, chat, pipeline, apps, activity, and settings experiences.

## Stack

- **React 19** with **React Router 7** for page-based navigation
- **Vite 8** for development and production builds
- **TypeScript 6** for static typing
- **TanStack Query v5** for server-state fetching and caching
- **Tailwind CSS 4** for styling
- **Vitest** + **React Testing Library** for unit tests
- **Playwright** for end-to-end coverage

## Project Structure

```text
frontend/
├── src/
│   ├── components/   # Reusable UI grouped by domain (chat, board, apps, tools, etc.)
│   ├── hooks/        # Domain-specific React hooks for data fetching and UI state
│   ├── layout/       # Shared app shell: sidebar, top bar, project selector, rate-limit bar
│   ├── pages/        # Route entry points (AppPage, ProjectsPage, AppsPage, SettingsPage, ...)
│   ├── services/     # API client and schema adapters
│   ├── test/         # Shared test setup, helpers, and factories
│   └── utils/        # Small reusable utilities
├── e2e/              # Playwright specs and snapshot baselines
├── package.json
├── vite.config.ts
├── vitest.config.ts
└── playwright.config.ts
```

## Key Areas

- **`src/pages/AppPage.tsx`** — full-screen multi-chat workspace
- **`src/layout/`** — authenticated shell, navigation, breadcrumbs, notifications, and project selection
- **`src/components/chat/`** — popup chat, multi-panel chat, markdown rendering, plan previews, uploads, and streaming UI
- **`src/components/board/`** — GitHub Project board, issue cards, cleanup UI, and pipeline-stage helpers
- **`src/components/apps/`** — app creation, import, preview, detail, and build-progress flows
- **`src/hooks/`** — 60+ hooks covering auth, chat, projects, pipelines, apps, activity, onboarding, tools, and settings

## Development Commands

```bash
cd solune/frontend
npm install
npm run dev
```

## Validation Commands

```bash
# Lint and type-check
npm run lint
npm run type-check

# Unit tests
npm test

# Coverage
npm run test:coverage

# End-to-end tests
npm run test:e2e

# Production build
npm run build
```

## Notes

- The frontend expects the backend API under `/api/v1` by default (`VITE_API_BASE_URL`).
- `npm run dev` starts the Vite dev server; the production container uses the repository `nginx.conf`.
- Route components are lazy-loaded with retry logic from `src/lib/lazyWithRetry.ts`.
