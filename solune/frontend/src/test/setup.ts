/**
 * Test setup for Vitest
 */
import '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import { vi, type Mock } from 'vitest';

// ─── crypto.randomUUID stub ──────────────────────────────────────────────
// happy-dom may not implement crypto.randomUUID; stub once globally.
if (typeof globalThis.crypto === 'undefined') {
  (globalThis as { crypto: Partial<Crypto> }).crypto = {};
}
if (typeof globalThis.crypto.randomUUID !== 'function') {
  let _counter = 0;
  globalThis.crypto.randomUUID = () =>
    `00000000-0000-4000-8000-${String(++_counter).padStart(12, '0')}` as `${string}-${string}-${string}-${string}-${string}`;
}

// ─── Mock WebSocket ──────────────────────────────────────────────────────

class MockWebSocket {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;

  readyState = MockWebSocket.CONNECTING;
  onopen: ((ev: Event) => void) | null = null;
  onclose: ((ev: CloseEvent) => void) | null = null;
  onmessage: ((ev: MessageEvent) => void) | null = null;
  onerror: ((ev: Event) => void) | null = null;

  constructor(public url: string) {
    // Simulate async connection
    setTimeout(() => {
      this.readyState = MockWebSocket.OPEN;
      this.onopen?.(new Event('open'));
    }, 10);
  }

  send(_data: string) {
    // Mock send
  }

  close() {
    this.readyState = MockWebSocket.CLOSED;
    this.onclose?.(new CloseEvent('close'));
  }
}

(global as Record<string, unknown>).WebSocket = MockWebSocket;

// ─── Mock window.location / window.history ───────────────────────────────

Object.defineProperty(window, 'location', {
  value: {
    protocol: 'http:',
    host: 'localhost:5173',
    href: 'http://localhost:5173/',
    pathname: '/',
    search: '',
    hash: '',
  },
  writable: true,
});

Object.defineProperty(window, 'history', {
  value: {
    replaceState: vi.fn(),
    pushState: vi.fn(),
  },
  writable: true,
});

// ─── createMockApi() — typed API mock factory ────────────────────────────
// Produces a deep mock of every namespace in `@/services/api` so tests can
// `vi.mock('@/services/api', () => createMockApi())` in one line.

export interface MockApiShape {
  ApiError: typeof import('@/services/api').ApiError;
  authApi: {
    login: Mock;
    getCurrentUser: Mock;
    logout: Mock;
  };
  projectsApi: {
    list: Mock;
    get: Mock;
    select: Mock;
  };
  tasksApi: {
    listByProject: Mock;
    create: Mock;
    updateStatus: Mock;
  };
  chatApi: {
    getMessages: Mock;
    clearMessages: Mock;
    sendMessage: Mock;
    confirmProposal: Mock;
    cancelProposal: Mock;
  };
  boardApi: {
    listProjects: Mock;
    getBoardData: Mock;
  };
  settingsApi: {
    getUserSettings: Mock;
    updateUserSettings: Mock;
    getGlobalSettings: Mock;
    updateGlobalSettings: Mock;
    getProjectSettings: Mock;
    updateProjectSettings: Mock;
    fetchModels: Mock;
  };
  mcpApi: {
    listMcps: Mock;
    createMcp: Mock;
    deleteMcp: Mock;
  };
  workflowApi: {
    confirmRecommendation: Mock;
    rejectRecommendation: Mock;
    getConfig: Mock;
    updateConfig: Mock;
    listAgents: Mock;
    getPipelineState: Mock;
  };
  metadataApi: {
    getMetadata: Mock;
    refreshMetadata: Mock;
  };
  cleanupApi: {
    preflight: Mock;
    execute: Mock;
    history: Mock;
  };
  choresApi: {
    seedPresets: Mock;
    list: Mock;
    listPaginated: Mock;
    listTemplates: Mock;
    listChoreNames: Mock;
    create: Mock;
    update: Mock;
    delete: Mock;
    trigger: Mock;
    chat: Mock;
    inlineUpdate: Mock;
    createWithAutoMerge: Mock;
    evaluateTriggers: Mock;
  };
  agentsApi: {
    list: Mock;
    listPaginated: Mock;
    pending: Mock;
    clearPending: Mock;
    create: Mock;
    update: Mock;
    delete: Mock;
    chat: Mock;
    bulkUpdateModels: Mock;
    syncMcps: Mock;
    browseCatalog: Mock;
    importAgent: Mock;
    installAgent: Mock;
  };
  pipelinesApi: {
    list: Mock;
    listPaginated: Mock;
    get: Mock;
    create: Mock;
    update: Mock;
    delete: Mock;
    seedPresets: Mock;
    getAssignment: Mock;
    setAssignment: Mock;
    launch: Mock;
    listRuns: Mock;
    getRun: Mock;
  };
  modelsApi: {
    list: Mock;
  };
  toolsApi: {
    getRepoConfig: Mock;
    updateRepoServer: Mock;
    deleteRepoServer: Mock;
    listPresets: Mock;
    list: Mock;
    listPaginated: Mock;
    get: Mock;
    create: Mock;
    update: Mock;
    sync: Mock;
    delete: Mock;
  };
  agentToolsApi: {
    getTools: Mock;
    updateTools: Mock;
  };
  appsApi: {
    list: Mock;
    listPaginated: Mock;
    create: Mock;
    get: Mock;
    update: Mock;
    delete: Mock;
    assets: Mock;
    start: Mock;
    stop: Mock;
    status: Mock;
    owners: Mock;
  };
  activityApi: {
    feed: Mock;
    stats: Mock;
    entityHistory: Mock;
  };
}

/**
 * Create a fully-mocked version of the API service module.
 *
 * Usage in a test file:
 * ```ts
 * import { createMockApi, type MockApiShape } from '@/test/setup';
 * vi.mock('@/services/api', () => createMockApi());
 * // ... then import the module to get the mock reference:
 * import * as api from '@/services/api';
 * const mockApi = api as unknown as MockApiShape;
 * ```
 */
export function createMockApi(): MockApiShape {
  return {
    ApiError: class extends Error {
      constructor(
        public status: number,
        public error: { error: string }
      ) {
        super(error.error);
        this.name = 'ApiError';
      }
    },
    authApi: {
      login: vi.fn(),
      getCurrentUser: vi.fn(),
      logout: vi.fn(),
    },
    projectsApi: {
      list: vi.fn(),
      get: vi.fn(),
      select: vi.fn(),
    },
    tasksApi: {
      listByProject: vi.fn(),
      create: vi.fn(),
      updateStatus: vi.fn(),
    },
    chatApi: {
      getMessages: vi.fn(),
      clearMessages: vi.fn(),
      sendMessage: vi.fn(),
      confirmProposal: vi.fn(),
      cancelProposal: vi.fn(),
    },
    boardApi: {
      listProjects: vi.fn(),
      getBoardData: vi.fn(),
    },
    settingsApi: {
      getUserSettings: vi.fn(),
      updateUserSettings: vi.fn(),
      getGlobalSettings: vi.fn(),
      updateGlobalSettings: vi.fn(),
      getProjectSettings: vi.fn(),
      updateProjectSettings: vi.fn(),
      fetchModels: vi.fn(),
    },
    mcpApi: {
      listMcps: vi.fn(),
      createMcp: vi.fn(),
      deleteMcp: vi.fn(),
    },
    workflowApi: {
      confirmRecommendation: vi.fn(),
      rejectRecommendation: vi.fn(),
      getConfig: vi.fn(),
      updateConfig: vi.fn(),
      listAgents: vi.fn(),
      getPipelineState: vi.fn(),
    },
    metadataApi: {
      getMetadata: vi.fn(),
      refreshMetadata: vi.fn(),
    },
    cleanupApi: {
      preflight: vi.fn(),
      execute: vi.fn(),
      history: vi.fn(),
    },
    choresApi: {
      seedPresets: vi.fn(),
      list: vi.fn(),
      listPaginated: vi.fn(),
      listTemplates: vi.fn(),
      listChoreNames: vi.fn(),
      create: vi.fn(),
      update: vi.fn(),
      delete: vi.fn(),
      trigger: vi.fn(),
      chat: vi.fn(),
      inlineUpdate: vi.fn(),
      createWithAutoMerge: vi.fn(),
      evaluateTriggers: vi.fn(),
    },
    agentsApi: {
      list: vi.fn(),
      listPaginated: vi.fn(),
      pending: vi.fn(),
      clearPending: vi.fn(),
      create: vi.fn(),
      update: vi.fn(),
      delete: vi.fn(),
      chat: vi.fn(),
      bulkUpdateModels: vi.fn(),
      syncMcps: vi.fn(),
      browseCatalog: vi.fn(),
      importAgent: vi.fn(),
      installAgent: vi.fn(),
    },
    pipelinesApi: {
      list: vi.fn(),
      listPaginated: vi.fn(),
      get: vi.fn(),
      create: vi.fn(),
      update: vi.fn(),
      delete: vi.fn(),
      seedPresets: vi.fn(),
      getAssignment: vi.fn(),
      setAssignment: vi.fn(),
      launch: vi.fn(),
      listRuns: vi.fn(),
      getRun: vi.fn(),
    },
    modelsApi: {
      list: vi.fn(),
    },
    toolsApi: {
      getRepoConfig: vi.fn(),
      updateRepoServer: vi.fn(),
      deleteRepoServer: vi.fn(),
      listPresets: vi.fn(),
      list: vi.fn(),
      listPaginated: vi.fn(),
      get: vi.fn(),
      create: vi.fn(),
      update: vi.fn(),
      sync: vi.fn(),
      delete: vi.fn(),
    },
    agentToolsApi: {
      getTools: vi.fn(),
      updateTools: vi.fn(),
    },
    appsApi: {
      list: vi.fn(),
      listPaginated: vi.fn(),
      create: vi.fn(),
      get: vi.fn(),
      update: vi.fn(),
      delete: vi.fn(),
      assets: vi.fn(),
      start: vi.fn(),
      stop: vi.fn(),
      status: vi.fn(),
      owners: vi.fn(),
    },
    activityApi: {
      feed: vi.fn(),
      stats: vi.fn(),
      entityHistory: vi.fn(),
    },
  };
}
