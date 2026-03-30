/**
 * Authenticated Playwright fixtures for E2E smoke tests.
 *
 * Extends the unauthenticated `fixtures.ts` pattern to return a mock
 * authenticated user and realistic API responses so the test suite can
 * exercise authenticated UI flows (dashboard, project selector, kanban
 * board, navigation) without a running backend.
 *
 * Usage — replace `import { test, expect } from '@playwright/test'` with:
 *   import { test, expect } from './authenticated-fixtures';
 */

import { test as base, expect } from '@playwright/test';

// ── Mock data ────────────────────────────────────────────────────────────────

const MOCK_USER = {
  github_user_id: '12345',
  github_username: 'test-user',
  github_avatar_url: 'https://avatars.githubusercontent.com/u/12345',
  selected_project_id: 'PVT_test123',
};

const MOCK_PROJECTS = {
  projects: [
    {
      project_id: 'PVT_test123',
      owner_id: 'O_owner123',
      owner_login: 'test-user',
      name: 'Test Project',
      type: 'user',
      url: 'https://github.com/users/test-user/projects/1',
      description: 'A test project for E2E testing',
      status_columns: [
        { field_id: 'PVTSSF_f1', name: 'Todo', option_id: 'opt1' },
        { field_id: 'PVTSSF_f1', name: 'In Progress', option_id: 'opt2' },
        { field_id: 'PVTSSF_f1', name: 'Done', option_id: 'opt3' },
      ],
      item_count: 3,
      cached_at: new Date().toISOString(),
    },
  ],
};

const MOCK_BOARD_PROJECTS = {
  projects: [
    {
      project_id: 'PVT_test123',
      name: 'Test Project',
      url: 'https://github.com/users/test-user/projects/1',
      owner_login: 'test-user',
      status_field: {
        field_id: 'PVTSSF_f1',
        options: [
          { option_id: 'opt1', name: 'Backlog', color: 'GRAY' },
          { option_id: 'opt2', name: 'In Progress', color: 'YELLOW' },
          { option_id: 'opt3', name: 'Done', color: 'GREEN' },
        ],
      },
    },
  ],
  rate_limit: null,
};

const MOCK_BOARD_DATA = {
  project: MOCK_BOARD_PROJECTS.projects[0],
  columns: [
    {
      status: { option_id: 'opt1', name: 'Backlog', color: 'GRAY' },
      items: [
        {
          item_id: 'PVTI_item1',
          content_type: 'issue',
          title: 'Set up CI/CD pipeline',
          number: 1,
          status: 'Backlog',
          status_option_id: 'opt1',
          assignees: [],
          labels: [],
          linked_prs: [],
          sub_issues: [],
        },
      ],
      item_count: 1,
      estimate_total: 0,
    },
    {
      status: { option_id: 'opt2', name: 'In Progress', color: 'YELLOW' },
      items: [
        {
          item_id: 'PVTI_item2',
          content_type: 'issue',
          title: 'Implement auth flow',
          number: 2,
          status: 'In Progress',
          status_option_id: 'opt2',
          assignees: [
            {
              login: 'test-user',
              avatar_url: 'https://avatars.githubusercontent.com/u/12345',
            },
          ],
          labels: [],
          linked_prs: [],
          sub_issues: [],
        },
      ],
      item_count: 1,
      estimate_total: 0,
    },
    {
      status: { option_id: 'opt3', name: 'Done', color: 'GREEN' },
      items: [],
      item_count: 0,
      estimate_total: 0,
    },
  ],
  rate_limit: null,
};

const MOCK_CHAT_HISTORY = {
  messages: [],
  total: 0,
  limit: 50,
  offset: 0,
};

// ── Fixture extension ────────────────────────────────────────────────────────

/**
 * Extended test that mocks `/api/**` with authenticated responses.
 *
 * Unlike the base `fixtures.ts` (which returns 401 for `/auth/me`), this
 * fixture returns a 200 with the mock user, enabling tests to exercise
 * authenticated UI flows.
 */
export const test = base.extend({
  page: async function PageFixture({ page }, use) {
    const applyFixture = use;

    await page.route('**/api/**', (route) => {
      const url = new URL(route.request().url());
      const pathname = url.pathname;

      // /auth/me → 200 (authenticated)
      if (pathname.includes('/auth/me')) {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(MOCK_USER),
        });
      }

      // /health → 200
      if (pathname.includes('/health')) {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ status: 'pass', checks: {} }),
        });
      }

      // /projects (exact list) → 200
      if (pathname.match(/\/projects\/?$/) && !pathname.includes('/board')) {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(MOCK_PROJECTS),
        });
      }

      // /board/projects/{id} → 200 with board data
      if (pathname.match(/\/board\/projects\/[^/]+$/)) {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(MOCK_BOARD_DATA),
        });
      }

      // /board/projects → 200 with project list
      if (pathname.includes('/board/projects')) {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(MOCK_BOARD_PROJECTS),
        });
      }

      // /chat/messages GET → 200 with history
      if (
        pathname.includes('/chat/messages') &&
        route.request().method() === 'GET'
      ) {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(MOCK_CHAT_HISTORY),
        });
      }

      // /pipelines → 200 with empty list
      if (pathname.includes('/pipelines')) {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ pipelines: [], total: 0 }),
        });
      }

      // /settings → 200 with defaults
      if (pathname.includes('/settings')) {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({}),
        });
      }

      // Fallback → 404
      return route.fulfill({
        status: 404,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Not found' }),
      });
    });

    await applyFixture(page);
  },
});

export { expect };
