import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@/test/test-utils';
import { expectNoA11yViolations } from '@/test/a11y-helpers';
import { AgentsPage } from './AgentsPage';

const mocks = vi.hoisted(() => ({
  selectedProject: null as { project_id: string; name: string; owner_login: string } | null,
  boardData: null as {
    columns: {
      status: { option_id: string; name: string; color: string };
      items: { repository?: { owner: string; name: string } }[];
      item_count: number;
    }[];
  } | null,
  localMappings: {} as Record<string, unknown>,
}));

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
  useProjects: () => ({
    projects: [],
    selectedProject: mocks.selectedProject,
    isLoading: false,
    selectProject: vi.fn(),
  }),
}));

vi.mock('@/hooks/useProjectBoard', () => ({
  useProjectBoard: () => ({ boardData: mocks.boardData, boardLoading: false }),
}));

vi.mock('@/hooks/useAgentConfig', () => ({
  useAgentConfig: () => ({
    localMappings: mocks.localMappings,
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

describe('AgentsPage', () => {
  beforeEach(() => {
    mocks.selectedProject = null;
    mocks.boardData = null;
    mocks.localMappings = {};
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

  it('shows the eyebrow text "Celestial Catalog"', () => {
    render(<AgentsPage />);
    expect(screen.getByText('Celestial Catalog')).toBeInTheDocument();
  });

  it('renders stats chips with board column, assignment, and mapping counts', () => {
    mocks.boardData = {
      columns: [
        { status: { option_id: 'c1', name: 'Todo', color: 'GRAY' }, items: [], item_count: 0 },
        { status: { option_id: 'c2', name: 'Done', color: 'GREEN' }, items: [], item_count: 0 },
      ],
    };
    mocks.localMappings = { 'col-a': [{ slug: 'designer', config: {} }] };

    render(<AgentsPage />);

    expect(screen.getByText('Board columns')).toBeInTheDocument();
    expect(screen.getByText('2')).toBeInTheDocument();
    const assignmentsLabel = screen.getByText('Assignments');
    expect(assignmentsLabel.parentElement).toHaveTextContent('1');
    const mappedStatesLabel = screen.getByText('Mapped states');
    expect(mappedStatesLabel.parentElement).toHaveTextContent('1');
  });

  it('shows "Awaiting repository" badge when no project is selected', () => {
    render(<AgentsPage />);
    expect(screen.getByText('Awaiting repository')).toBeInTheDocument();
  });

  it('shows owner/repo badge when board data has a repository', () => {
    mocks.boardData = {
      columns: [
        {
          status: { option_id: 'c1', name: 'Todo', color: 'GRAY' },
          items: [{ repository: { owner: 'Boykai', name: 'solune' } }],
          item_count: 1,
        },
      ],
    };

    render(<AgentsPage />);
    expect(screen.getByText('Boykai/solune')).toBeInTheDocument();
  });

  it('renders action links for agent catalog and assignments', () => {
    render(<AgentsPage />);
    const curateLink = screen.getByRole('link', { name: /curate agent rituals/i });
    expect(curateLink).toHaveAttribute('href', '#agents-catalog');
    const assignLink = screen.getByRole('link', { name: /review assignments/i });
    expect(assignLink).toHaveAttribute('href', '#agent-assignments');
  });

  it('shows "Unselected" for the Project stat when no project is selected', () => {
    render(<AgentsPage />);
    expect(screen.getByText('Unselected')).toBeInTheDocument();
  });

  it('has no accessibility violations', async () => {
    const { container } = render(<AgentsPage />);
    await expectNoA11yViolations(container);
  });
});
