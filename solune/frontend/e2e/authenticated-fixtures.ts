/**
 * Authenticated Playwright fixtures for realistic UX tests.
 *
 * The fixture exposes a mutable in-memory mock backend through `mockApi`, so
 * E2E specs can exercise authenticated flows with stateful responses instead of
 * shallow page-load checks.
 */

import { test as base, expect, type Route } from '@playwright/test';

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
        { field_id: 'PVTSSF_f1', name: 'Backlog', option_id: 'opt1' },
        { field_id: 'PVTSSF_f1', name: 'In Progress', option_id: 'opt2' },
        { field_id: 'PVTSSF_f1', name: 'Done', option_id: 'opt3' },
      ],
      item_count: 3,
      cached_at: NOW,
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
          body: 'Create a resilient CI pipeline for pull requests and releases.',
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
          body: 'Finish the GitHub sign-in path and make redirects predictable.',
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
      source: 'repository',
    },
  ],
};

const MOCK_SETTINGS_USER = {
  ai: {
    provider: 'copilot',
    model: 'gpt-4o',
    temperature: 0.7,
    agent_model: 'gpt-4o',
    reasoning_effort: 'medium',
    agent_reasoning_effort: 'medium',
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

const MOCK_TOOLS_PAGE = {
  tools: [],
  count: 0,
};

type JsonObject = Record<string, unknown>;

function clone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

function slugify(value: string): string {
  const slug = value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
  return slug || 'agent';
}

function createIssueRecommendationMessage(userContent: string) {
  return {
    message_id: 'msg-recommendation-1',
    session_id: 'chat-session-1',
    sender_type: 'assistant',
    content: `I drafted an issue recommendation for: ${userContent}`,
    action_type: 'issue_create',
    action_data: {
      recommendation_id: 'rec-1',
      proposed_title: 'Ship saved search filters',
      user_story: 'As a project lead, I want reusable saved searches so triage stays fast.',
      ui_ux_description:
        'Add a saved-search strip to the project board so people can switch between curated views without rebuilding filters.',
      functional_requirements: [
        'Allow creating named saved searches from current board filters.',
        'Persist saved searches per user.',
        'Support editing and deleting saved searches.',
      ],
      metadata: {
        priority: 'P1',
        size: 'M',
        estimate_hours: 6,
        start_date: '2025-01-10',
        target_date: '2025-01-17',
        labels: ['feature', 'frontend', 'testing'],
        assignees: ['test-user'],
        branch: 'feature/saved-search-filters',
      },
      status: 'pending',
    },
    timestamp: NOW,
  };
}

function createWorkflowResult() {
  return {
    success: true,
    issue_id: 'issue-node-101',
    issue_number: 101,
    issue_url: 'https://github.com/test-user/solune-demo/issues/101',
    project_item_id: 'PVTI_issue101',
    current_status: 'Backlog',
    message: 'Issue created successfully',
  };
}

function buildPageResponse<T>(items: T[]) {
  return {
    items: clone(items),
    next_cursor: null,
    has_more: false,
    total_count: items.length,
  };
}

function readRequestBody(route: Route): JsonObject {
  const raw = route.request().postData();
  if (!raw) {
    return {};
  }
  try {
    return JSON.parse(raw) as JsonObject;
  } catch {
    return {};
  }
}

function json(route: Route, body: unknown, status = 200) {
  return route.fulfill({
    status,
    contentType: 'application/json',
    body: JSON.stringify(body),
  });
}

function mergeNested<T extends JsonObject>(target: T, patch: JsonObject): T {
  for (const [key, value] of Object.entries(patch)) {
    if (value === undefined) {
      continue;
    }
    if (value && typeof value === 'object' && !Array.isArray(value)) {
      const existing =
        target[key] && typeof target[key] === 'object' && !Array.isArray(target[key])
          ? (target[key] as JsonObject)
          : {};
      target[key] = mergeNested({ ...existing }, value as JsonObject) as T[keyof T];
      continue;
    }
    target[key] = value as T[keyof T];
  }
  return target;
}

function updateRecommendationStatus(mockApi: MockApiState, recommendationId: string, status: 'confirmed' | 'rejected') {
  for (const message of mockApi.chatHistory.messages) {
    if (
      message.action_type === 'issue_create' &&
      message.action_data?.recommendation_id === recommendationId
    ) {
      message.action_data.status = status;
    }
  }
}

function createMockApiState() {
  return {
    user: clone(MOCK_USER),
    projects: clone(MOCK_PROJECTS),
    boardProjects: clone(MOCK_BOARD_PROJECTS),
    boardDataByProject: {
      PVT_test123: clone(MOCK_BOARD_DATA),
    },
    chatHistory: clone(MOCK_CHAT_HISTORY),
    settingsUser: clone(MOCK_SETTINGS_USER),
    settingsGlobal: clone(MOCK_SETTINGS_GLOBAL),
    modelsResponse: clone(MOCK_MODELS_RESPONSE),
    signalConnection: clone(MOCK_SIGNAL_CONNECTION),
    signalPreferences: clone(MOCK_SIGNAL_PREFERENCES),
    signalBanners: clone(MOCK_SIGNAL_BANNERS),
    workflowConfig: clone(MOCK_WORKFLOW_CONFIG),
    availableAgents: clone(MOCK_AVAILABLE_AGENTS),
    agentsByProject: {
      PVT_test123: clone(MOCK_AGENTS_PAGE.items),
    },
    pendingAgentsByProject: {
      PVT_test123: [],
    },
    choresByProject: {
      PVT_test123: clone(MOCK_CHORES_PAGE.items),
    },
    choreTemplates: clone(MOCK_CHORE_TEMPLATES),
    evaluateChores: clone(MOCK_EVALUATE_CHORES),
    toolsByProject: {
      PVT_test123: clone(MOCK_TOOLS_PAGE),
    },
    pipelineAssignmentByProject: {
      PVT_test123: clone(MOCK_PIPELINE_ASSIGNMENT),
    },
    nextChatResponse: createIssueRecommendationMessage('Create a saved search filter experience'),
    workflowResultsByRecommendationId: {
      'rec-1': createWorkflowResult(),
    },
  };
}

export type MockApiState = ReturnType<typeof createMockApiState>;

async function handleApiRoute(route: Route, mockApi: MockApiState) {
  const url = new URL(route.request().url());
  const pathname = url.pathname;
  const method = route.request().method();

  if (pathname.includes('/auth/me')) {
    return json(route, mockApi.user);
  }

  if (pathname.includes('/auth/logout') && method === 'POST') {
    mockApi.user.selected_project_id = undefined;
    return json(route, { message: 'Logged out' });
  }

  if (pathname.includes('/health')) {
    return json(route, { status: 'pass', checks: {} });
  }

  if (pathname === '/api/v1/signal/connection') {
    return json(route, mockApi.signalConnection);
  }

  if (pathname === '/api/v1/signal/preferences') {
    return json(route, mockApi.signalPreferences);
  }

  if (pathname === '/api/v1/signal/banners') {
    return json(route, mockApi.signalBanners);
  }

  if (pathname === '/api/v1/settings/user') {
    if (method === 'PUT') {
      mergeNested(mockApi.settingsUser, readRequestBody(route));
    }
    return json(route, mockApi.settingsUser);
  }

  if (pathname === '/api/v1/settings/global') {
    if (method === 'PUT') {
      mergeNested(mockApi.settingsGlobal, readRequestBody(route));
    }
    return json(route, mockApi.settingsGlobal);
  }

  if (pathname.startsWith('/api/v1/settings/models/')) {
    return json(route, mockApi.modelsResponse);
  }

  if (pathname === '/api/v1/workflow/config') {
    if (method === 'PUT') {
      mergeNested(mockApi.workflowConfig, readRequestBody(route));
    }
    return json(route, mockApi.workflowConfig);
  }

  if (pathname === '/api/v1/workflow/agents') {
    return json(route, mockApi.availableAgents);
  }

  const confirmMatch = pathname.match(/\/workflow\/recommendations\/([^/]+)\/confirm$/);
  if (confirmMatch && method === 'POST') {
    const recommendationId = confirmMatch[1];
    updateRecommendationStatus(mockApi, recommendationId, 'confirmed');
    const result = mockApi.workflowResultsByRecommendationId[recommendationId] ?? createWorkflowResult();
    return json(route, result);
  }

  const rejectMatch = pathname.match(/\/workflow\/recommendations\/([^/]+)\/reject$/);
  if (rejectMatch && method === 'POST') {
    updateRecommendationStatus(mockApi, rejectMatch[1], 'rejected');
    return json(route, {});
  }

  const selectProjectMatch = pathname.match(/\/projects\/([^/]+)\/select$/);
  if (selectProjectMatch && method === 'POST') {
    const projectId = selectProjectMatch[1];
    mockApi.user.selected_project_id = projectId;
    mockApi.signalConnection.last_active_project_id = projectId;
    mockApi.workflowConfig.project_id = projectId;
    return json(route, mockApi.user);
  }

  const projectTasksMatch = pathname.match(/\/projects\/([^/]+)\/tasks$/);
  if (projectTasksMatch && method === 'GET') {
    return json(route, { tasks: [] });
  }

  if (pathname.match(/\/projects\/?$/) && !pathname.includes('/board')) {
    return json(route, mockApi.projects);
  }

  const updateBoardStatusMatch = pathname.match(/\/board\/projects\/([^/]+)\/items\/([^/]+)\/status$/);
  if (updateBoardStatusMatch && method === 'PATCH') {
    const [, projectId, itemId] = updateBoardStatusMatch;
    const board = mockApi.boardDataByProject[projectId];
    if (!board) {
      return json(route, { detail: 'Project not found' }, 404);
    }
    const request = readRequestBody(route);
    const nextStatus = typeof request.status === 'string' ? request.status : null;
    if (!nextStatus) {
      return json(route, { detail: 'Status is required' }, 400);
    }
    let movedItem: Record<string, unknown> | null = null;
    for (const column of board.columns) {
      const matchIndex = column.items.findIndex((item) => item.item_id === itemId);
      if (matchIndex >= 0) {
        movedItem = { ...column.items[matchIndex], status: nextStatus };
        column.items.splice(matchIndex, 1);
        column.item_count = column.items.length;
        break;
      }
    }
    const targetColumn = board.columns.find((column) => column.status.name === nextStatus);
    if (!movedItem || !targetColumn) {
      return json(route, { detail: 'Board item not found' }, 404);
    }
    targetColumn.items.push({
      ...movedItem,
      status_option_id: targetColumn.status.option_id,
    });
    targetColumn.item_count = targetColumn.items.length;
    return json(route, { success: true });
  }

  const boardDataMatch = pathname.match(/\/board\/projects\/([^/]+)$/);
  if (boardDataMatch) {
    const projectId = boardDataMatch[1];
    const boardData = mockApi.boardDataByProject[projectId];
    if (!boardData) {
      return json(route, { detail: 'Board not found' }, 404);
    }
    return json(route, boardData);
  }

  if (pathname === '/api/v1/board/projects') {
    return json(route, mockApi.boardProjects);
  }

  if (pathname === '/api/v1/chat/messages' && method === 'GET') {
    return json(route, mockApi.chatHistory);
  }

  if (pathname === '/api/v1/chat/messages' && method === 'DELETE') {
    mockApi.chatHistory.messages = [];
    return json(route, { message: 'Chat cleared' });
  }

  if (pathname === '/api/v1/chat/messages' && method === 'POST') {
    const request = readRequestBody(route);
    const content = typeof request.content === 'string' ? request.content : 'Untitled request';
    const userMessage = {
      message_id: `msg-user-${mockApi.chatHistory.messages.length + 1}`,
      session_id: 'chat-session-1',
      sender_type: 'user',
      content,
      timestamp: new Date().toISOString(),
    };
    const responseMessage = clone(mockApi.nextChatResponse);
    responseMessage.content = `I drafted an issue recommendation for: ${content}`;
    responseMessage.timestamp = new Date().toISOString();
    mockApi.chatHistory.messages.push(userMessage, responseMessage);
    return json(route, responseMessage);
  }

  const pendingAgentsMatch = pathname.match(/\/agents\/([^/]+)\/pending$/);
  if (pendingAgentsMatch) {
    const projectId = pendingAgentsMatch[1];
    if (method === 'DELETE') {
      const deletedCount = mockApi.pendingAgentsByProject[projectId]?.length ?? 0;
      mockApi.pendingAgentsByProject[projectId] = [];
      return json(route, { success: true, deleted_count: deletedCount });
    }
    return json(route, clone(mockApi.pendingAgentsByProject[projectId] ?? []));
  }

  const agentDetailMatch = pathname.match(/\/agents\/([^/]+)\/([^/]+)$/);
  if (agentDetailMatch && method === 'PATCH') {
    const [, projectId, agentId] = agentDetailMatch;
    const updates = readRequestBody(route);
    const agent = mockApi.agentsByProject[projectId]?.find((entry) => entry.id === agentId);
    if (!agent) {
      return json(route, { detail: 'Agent not found' }, 404);
    }
    mergeNested(agent as JsonObject, updates);
    return json(route, {
      agent,
      pr_url: `https://github.com/test-user/solune-demo/pull/42`,
      pr_number: 42,
      issue_number: null,
      branch_name: `agents/${agent.slug}`,
    });
  }

  if (agentDetailMatch && method === 'DELETE') {
    const [, projectId, agentId] = agentDetailMatch;
    mockApi.agentsByProject[projectId] = (mockApi.agentsByProject[projectId] ?? []).filter(
      (entry) => entry.id !== agentId,
    );
    return json(route, {
      success: true,
      pr_url: 'https://github.com/test-user/solune-demo/pull/43',
      pr_number: 43,
      issue_number: null,
    });
  }

  const agentsMatch = pathname.match(/\/agents\/([^/]+)$/);
  if (agentsMatch) {
    const projectId = agentsMatch[1];
    if (method === 'POST') {
      const request = readRequestBody(route);
      const name = typeof request.name === 'string' ? request.name.trim() : 'New Agent';
      const slug = slugify(name);
      const createdAt = new Date().toISOString();
      const newAgent = {
        id: `agent-${Date.now()}`,
        name,
        slug,
        description: typeof request.description === 'string' ? request.description : '',
        icon_name: typeof request.icon_name === 'string' ? request.icon_name : null,
        system_prompt:
          typeof request.system_prompt === 'string' ? request.system_prompt : 'New system prompt',
        default_model_id: 'gpt-4o',
        default_model_name: 'GPT-4o',
        status: 'pending_pr',
        tools: Array.isArray(request.tools)
          ? request.tools.filter((tool): tool is string => typeof tool === 'string')
          : [],
        status_column: 'Backlog',
        github_issue_number: null,
        github_pr_number: 41,
        branch_name: `agents/${slug}`,
        source: 'local',
        created_at: createdAt,
      };
      mockApi.pendingAgentsByProject[projectId] = [
        newAgent,
        ...(mockApi.pendingAgentsByProject[projectId] ?? []),
      ];
      return json(route, {
        agent: newAgent,
        pr_url: 'https://github.com/test-user/solune-demo/pull/41',
        pr_number: 41,
        issue_number: null,
        branch_name: `agents/${slug}`,
      });
    }

    const agents = mockApi.agentsByProject[projectId] ?? [];
    const body = url.searchParams.has('limit') ? buildPageResponse(agents) : clone(agents);
    return json(route, body);
  }

  if (pathname === '/api/v1/chores/evaluate-triggers') {
    return json(route, mockApi.evaluateChores);
  }

  if (pathname.match(/\/chores\/[^/]+\/seed-presets$/)) {
    return json(route, { created: 0 });
  }

  if (pathname.match(/\/chores\/[^/]+\/templates$/)) {
    return json(route, mockApi.choreTemplates);
  }

  const choreNamesMatch = pathname.match(/\/chores\/([^/]+)\/chore-names$/);
  if (choreNamesMatch) {
    const projectId = choreNamesMatch[1];
    return json(
      route,
      (mockApi.choresByProject[projectId] ?? []).map((chore) => chore.name),
    );
  }

  const choresMatch = pathname.match(/\/chores\/([^/]+)$/);
  if (choresMatch) {
    const projectId = choresMatch[1];
    const chores = mockApi.choresByProject[projectId] ?? [];
    const body = url.searchParams.has('limit') ? buildPageResponse(chores) : clone(chores);
    return json(route, body);
  }

  const pipelineAssignmentMatch = pathname.match(/\/pipelines\/([^/]+)\/assignment$/);
  if (pipelineAssignmentMatch) {
    const projectId = pipelineAssignmentMatch[1];
    if (method === 'PUT') {
      const request = readRequestBody(route);
      const pipelineId = typeof request.pipeline_id === 'string' ? request.pipeline_id : '';
      mockApi.pipelineAssignmentByProject[projectId] = { project_id: projectId, pipeline_id: pipelineId };
    }
    return json(
      route,
      mockApi.pipelineAssignmentByProject[projectId] ?? { project_id: projectId, pipeline_id: '' },
    );
  }

  if (pathname.match(/\/pipelines\/[^/]+\/seed-presets$/)) {
    return json(route, { seeded: [], skipped: [], total: 0 });
  }

  if (pathname.match(/\/pipelines\/[^/]+\/launch$/) && method === 'POST') {
    return json(route, createWorkflowResult());
  }

  if (pathname.includes('/pipelines')) {
    return json(route, { pipelines: [], total: 0 });
  }

  const toolsMatch = pathname.match(/\/tools\/([^/]+)$/);
  if (toolsMatch) {
    const projectId = toolsMatch[1];
    return json(route, mockApi.toolsByProject[projectId] ?? clone(MOCK_TOOLS_PAGE));
  }

  return json(route, { detail: 'Not found' }, 404);
}

export const test = base.extend<{ mockApi: MockApiState }>({
  mockApi: async (_args, applyFixture) => {
    await applyFixture(createMockApiState());
  },
  page: async ({ page, mockApi }, applyFixture) => {
    await page.addInitScript(() => {
      window.localStorage.setItem('solune-onboarding-completed', 'true');
    });
    await page.route('**/api/**', (route) => handleApiRoute(route, mockApi));
    await applyFixture(page);
  },
});

export { expect };
