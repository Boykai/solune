import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@/test/test-utils';
import { expectNoA11yViolations } from '@/test/a11y-helpers';
import { ChoresPage } from './ChoresPage';

const mocks = vi.hoisted(() => ({
  selectedProject: null as { project_id: string; name: string; owner_login: string } | null,
  boardData: null as {
    columns: {
      status: { option_id: string; name: string; color: string };
      items: { repository?: { owner: string; name: string } }[];
      item_count: number;
    }[];
  } | null,
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

vi.mock('@/hooks/useChores', () => ({
  useChoresListPaginated: () => ({ allItems: [], isLoading: false }),
  useEvaluateChoresTriggers: vi.fn(),
  choreKeys: { list: () => ['chores'] },
}));

vi.mock('@/hooks/useUnsavedChanges', () => ({
  useUnsavedChanges: () => ({ isBlocked: false, blocker: undefined }),
}));

vi.mock('@/services/api', () => ({
  choresApi: { seedPresets: vi.fn().mockResolvedValue(undefined) },
  workflowApi: {},
}));

describe('ChoresPage', () => {
  beforeEach(() => {
    mocks.selectedProject = null;
    mocks.boardData = null;
  });

  it('renders without crashing', () => {
    render(<ChoresPage />);
    expect(document.body).toBeDefined();
  });

  it('renders a compact page header with the expected title', () => {
    render(<ChoresPage />);
    const heading = screen.getByRole('heading', { level: 2 });
    expect(heading).toHaveTextContent('Turn upkeep into a visible rhythm.');
  });

  it('uses a <header> element for the page header', () => {
    const { container } = render(<ChoresPage />);
    expect(container.querySelector('header')).toBeInTheDocument();
  });

  it('shows the eyebrow text "Ritual Maintenance"', () => {
    render(<ChoresPage />);
    expect(screen.getByText('Ritual Maintenance')).toBeInTheDocument();
  });

  it('shows "Awaiting repository" badge when no project is selected', () => {
    render(<ChoresPage />);
    expect(screen.getByText('Awaiting repository')).toBeInTheDocument();
  });

  it('renders stats chips for board columns, project, repository, and automation', () => {
    render(<ChoresPage />);
    expect(screen.getByText('Board columns')).toBeInTheDocument();
    expect(screen.getByText('0')).toBeInTheDocument();
    expect(screen.getByText('Project')).toBeInTheDocument();
    expect(screen.getByText('Unselected')).toBeInTheDocument();
    expect(screen.getByText('Repository')).toBeInTheDocument();
    expect(screen.getByText('Unlinked')).toBeInTheDocument();
    expect(screen.getByText('Automation mode')).toBeInTheDocument();
    expect(screen.getByText('Idle')).toBeInTheDocument();
  });

  it('renders action links for planning work and reviewing cadence', () => {
    render(<ChoresPage />);
    const planLink = screen.getByRole('link', { name: /plan recurring work/i });
    expect(planLink).toHaveAttribute('href', '#chores-catalog');
    const reviewLink = screen.getByRole('link', { name: /review upkeep cadence/i });
    expect(reviewLink).toHaveAttribute('href', '#chore-templates');
  });

  it('shows repo badge when board data provides repository info', () => {
    mocks.boardData = {
      columns: [
        {
          status: { option_id: 'c1', name: 'Todo', color: 'GRAY' },
          items: [{ repository: { owner: 'Boykai', name: 'solune' } }],
          item_count: 1,
        },
      ],
    };

    render(<ChoresPage />);
    // The badge shows owner/repo format
    expect(screen.getByText('Boykai/solune')).toBeInTheDocument();
  });

  it('has no accessibility violations', async () => {
    const { container } = render(<ChoresPage />);
    await expectNoA11yViolations(container);
  });
});
