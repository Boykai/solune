import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@/test/test-utils';
import { expectNoA11yViolations } from '@/test/a11y-helpers';
import { AgentsPage } from './AgentsPage';

const mockUseProjects = vi.fn();

vi.mock('@tanstack/react-query', async () => {
  const actual =
    await vi.importActual<typeof import('@tanstack/react-query')>('@tanstack/react-query');
  return {
    ...actual,
    useQuery: vi.fn(() => ({ data: undefined, isLoading: false, isError: false })),
    useQueryClient: () => ({ invalidateQueries: vi.fn(), setQueryData: vi.fn() }),
    useMutation: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
  };
});

vi.mock('@/hooks/useAuth', () => ({
  useAuth: () => ({ user: { login: 'test', selected_project_id: null }, isAuthenticated: true }),
}));

vi.mock('@/hooks/useProjects', () => ({
  useProjects: (...args: unknown[]) => mockUseProjects(...args),
}));

vi.mock('@/hooks/useProjectBoard', () => ({
  useProjectBoard: () => ({
    boardData: { columns: [] },
    boardLoading: false,
  }),
}));

vi.mock('@/hooks/useAgentConfig', () => ({
  useAgentConfig: () => ({
    localMappings: {},
    isDirty: false,
    isColumnDirty: () => false,
    addAgent: vi.fn(),
    removeAgent: vi.fn(),
    cloneAgent: vi.fn(),
    reorderAgents: vi.fn(),
    moveAgentToColumn: vi.fn(),
    applyPreset: vi.fn(),
    save: vi.fn(),
    discard: vi.fn(),
    isSaving: false,
    saveError: null,
    isLoaded: true,
    loadConfig: vi.fn(),
  }),
}));

// Mocks for hooks consumed by AgentsPanel (rendered when a project is selected)
vi.mock('@/hooks/useAgents', () => ({
  useAgentsList: () => ({ data: [], isLoading: false, error: null }),
  useAgentsListPaginated: () => ({
    allItems: [],
    isLoading: false,
    isError: false,
    hasNextPage: false,
    isFetchingNextPage: false,
    fetchNextPage: vi.fn(),
    invalidate: vi.fn(),
  }),
  usePendingAgentsList: () => ({ data: [], isLoading: false }),
  useClearPendingAgents: () => ({ mutate: vi.fn(), isPending: false }),
  useDeleteAgent: () => ({ mutate: vi.fn(), isPending: false }),
  useUndoableDeleteAgent: () => ({ deleteAgent: vi.fn(), pendingIds: new Set() }),
  useCreateAgent: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useUpdateAgent: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useBulkUpdateModels: () => ({ mutate: vi.fn(), isPending: false }),
  useCatalogAgents: () => ({ data: [], isLoading: false, isFetching: false, isError: false, refetch: vi.fn() }),
  useImportAgent: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useInstallAgent: () => ({ mutateAsync: vi.fn(), isPending: false }),
}));

vi.mock('@/hooks/useModels', () => ({
  useModels: () => ({ refreshModels: vi.fn(), isRefreshing: false }),
}));

vi.mock('@/hooks/useUnsavedChanges', () => ({
  useUnsavedChanges: () => ({
    blocker: { state: 'unblocked', proceed: vi.fn(), reset: vi.fn() },
    isBlocked: false,
  }),
}));

vi.mock('@/hooks/useConfirmation', () => ({
  useConfirmation: () => ({ confirm: vi.fn().mockResolvedValue(true) }),
}));

describe('AgentsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Default: no project selected
    mockUseProjects.mockReturnValue({
      projects: [],
      selectedProject: null,
      isLoading: false,
      selectProject: vi.fn(),
    });
  });

  it('renders without crashing', () => {
    render(<AgentsPage />);
    expect(document.body).toBeDefined();
  });

  it('renders a compact page header with the expected title', () => {
    render(<AgentsPage />);
    const heading = screen.getByRole('heading', { level: 2 });
    expect(heading).toHaveTextContent('Shape your agent constellation.');
  });

  it('uses a <header> element for the page header', () => {
    const { container } = render(<AgentsPage />);
    expect(container.querySelector('header')).toBeInTheDocument();
  });

  it('has no accessibility violations', async () => {
    const { container } = render(<AgentsPage />);
    await expectNoA11yViolations(container);
  });

  describe('with a project selected', () => {
    beforeEach(() => {
      mockUseProjects.mockReturnValue({
        projects: [{ project_id: 'PVT_1', name: 'Test Project' }],
        selectedProject: { project_id: 'PVT_1', name: 'Test Project' },
        isLoading: false,
        selectProject: vi.fn(),
      });
    });

    it('does not render Orbital map section', () => {
      const { container } = render(<AgentsPage />);
      expect(container.textContent).not.toContain('Orbital map');
      expect(container.textContent).not.toContain('orbital-map');
    });

    it('does not render Agent Archive section', () => {
      const { container } = render(<AgentsPage />);
      expect(container.textContent).not.toContain('Agent Archive');
    });
  });

  it('renders Curate agent rituals and Review assignments action buttons', () => {
    render(<AgentsPage />);
    expect(screen.getByText('Curate agent rituals')).toBeInTheDocument();
    expect(screen.getByText('Review assignments')).toBeInTheDocument();
  });
});
