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

const NOW = new Date().toISOString();

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
          repository: {
            owner: 'test-user',
            name: 'solune-demo',
          },
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
          repository: {
            owner: 'test-user',
            name: 'solune-demo',
          },
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

const MOCK_WORKFLOW_CONFIG = {
  project_id: 'PVT_test123',
  repository_owner: 'test-user',
  repository_name: 'solune-demo',
  copilot_assignee: 'Copilot',
  agent_mappings: {
    Backlog: [
      {
        id: 'assign-1',
        slug: 'copilot',
        display_name: 'GitHub Copilot',
        config: null,
      },
    ],
    'In Progress': [],
    Done: [],
  },
  status_backlog: 'Backlog',
  status_ready: 'Backlog',
  status_in_progress: 'In Progress',
  status_in_review: 'Done',
  enabled: true,
};

const MOCK_AVAILABLE_AGENTS = {
  agents: [
    {
      slug: 'copilot',
      display_name: 'GitHub Copilot',
      description: 'Default coding assistant',
      tools: [],
      default_model_id: 'gpt-4o',
      default_model_name: 'GPT-4o',
    },
  ],
};

const MOCK_SETTINGS_USER = {
  ai: {
    provider: 'copilot',
    model: 'gpt-4o',
    temperature: 0.7,
    agent_model: 'gpt-4o',
  },
  display: {
    theme: 'dark',
    default_view: 'board',
    sidebar_collapsed: false,
  },
  workflow: {
    default_repository: 'test-user/solune-demo',
    default_assignee: 'Copilot',
    copilot_polling_interval: 30,
  },
  notifications: {
    task_status_change: true,
    agent_completion: true,
    new_recommendation: true,
    chat_mention: true,
  },
};

const MOCK_SETTINGS_GLOBAL = {
  ...MOCK_SETTINGS_USER,
  allowed_models: ['gpt-4o'],
};

const MOCK_MODELS_RESPONSE = {
  status: 'success',
  models: [
    {
      id: 'gpt-4o',
      name: 'GPT-4o',
      provider: 'copilot',
    },
  ],
  fetched_at: NOW,
  cache_hit: true,
  rate_limit_warning: false,
  message: null,
};

const MOCK_SIGNAL_CONNECTION = {
  connection_id: null,
  status: 'disconnected',
  signal_identifier: null,
  notification_mode: 'all',
  linked_at: null,
  last_active_project_id: null,
};

const MOCK_SIGNAL_PREFERENCES = {
  notification_mode: 'all',
};

const MOCK_SIGNAL_BANNERS = {
  banners: [],
};

const MOCK_PIPELINE_ASSIGNMENT = {
  project_id: 'PVT_test123',
  pipeline_id: '',
};

const MOCK_AGENTS_PAGE = {
  items: [
    {
      id: 'agent-1',
      name: 'GitHub Copilot',
      slug: 'copilot',
      description: 'Default coding assistant',
      icon_name: null,
      system_prompt: 'You are GitHub Copilot.',
      default_model_id: 'gpt-4o',
      default_model_name: 'GPT-4o',
      status: 'active',
      tools: [],
      status_column: 'Backlog',
      github_issue_number: null,
      github_pr_number: null,
      branch_name: null,
      source: 'local',
      created_at: NOW,
    },
  ],
  next_cursor: null,
  has_more: false,
  total_count: 1,
};

const MOCK_CHORES_PAGE = {
  items: [
    {
      id: 'chore-1',
      project_id: 'PVT_test123',
      name: 'Weekly triage',
      template_path: '.github/ISSUE_TEMPLATE/weekly-triage.md',
      template_content: '## Weekly triage\n- Review backlog',
      schedule_type: 'count',
      schedule_value: 5,
      status: 'active',
      last_triggered_at: null,
      last_triggered_count: 0,
      current_issue_number: null,
      current_issue_node_id: null,
      pr_number: null,
      pr_url: null,
      tracking_issue_number: null,
      execution_count: 0,
      ai_enhance_enabled: false,
      agent_pipeline_id: '',
      is_preset: false,
      preset_id: '',
      created_at: NOW,
      updated_at: NOW,
    },
  ],
  next_cursor: null,
  has_more: false,
  total_count: 1,
};

const MOCK_CHORE_TEMPLATES = [
  {
    name: 'Weekly triage',
    about: 'Review backlog health and outstanding work.',
    path: '.github/ISSUE_TEMPLATE/weekly-triage.md',
    content: '## Weekly triage\n- Review backlog',
  },
];

const MOCK_EVALUATE_CHORES = {
  evaluated: 1,
  triggered: 0,
  skipped: 1,
  results: [],
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

      if (pathname === '/api/v1/signal/connection') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(MOCK_SIGNAL_CONNECTION),
        });
      }

      if (pathname === '/api/v1/signal/preferences') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(MOCK_SIGNAL_PREFERENCES),
        });
      }

      if (pathname === '/api/v1/signal/banners') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(MOCK_SIGNAL_BANNERS),
        });
      }

      if (pathname === '/api/v1/settings/user') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(MOCK_SETTINGS_USER),
        });
      }

      if (pathname === '/api/v1/settings/global') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(MOCK_SETTINGS_GLOBAL),
        });
      }

      if (pathname.startsWith('/api/v1/settings/models/')) {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(MOCK_MODELS_RESPONSE),
        });
      }

      if (pathname === '/api/v1/workflow/config') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(MOCK_WORKFLOW_CONFIG),
        });
      }

      if (pathname === '/api/v1/workflow/agents') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(MOCK_AVAILABLE_AGENTS),
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

      if (pathname.match(/\/agents\/[^/]+\/pending$/)) {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify([]),
        });
      }

      if (pathname.match(/\/agents\/[^/]+$/)) {
        const body = url.searchParams.has('limit')
          ? MOCK_AGENTS_PAGE
          : MOCK_AGENTS_PAGE.items;
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(body),
        });
      }

      if (pathname === '/api/v1/chores/evaluate-triggers') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(MOCK_EVALUATE_CHORES),
        });
      }

      if (pathname.match(/\/chores\/[^/]+\/seed-presets$/)) {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ created: 0 }),
        });
      }

      if (pathname.match(/\/chores\/[^/]+\/templates$/)) {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(MOCK_CHORE_TEMPLATES),
        });
      }

      if (pathname.match(/\/chores\/[^/]+\/chore-names$/)) {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(MOCK_CHORES_PAGE.items.map((chore) => chore.name)),
        });
      }

      if (pathname.match(/\/chores\/[^/]+$/)) {
        const body = url.searchParams.has('limit')
          ? MOCK_CHORES_PAGE
          : MOCK_CHORES_PAGE.items;
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(body),
        });
      }

      if (pathname.match(/\/pipelines\/[^/]+\/assignment$/)) {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(MOCK_PIPELINE_ASSIGNMENT),
        });
      }

      if (pathname.match(/\/pipelines\/[^/]+\/seed-presets$/)) {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ seeded: [], skipped: [], total: 0 }),
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
