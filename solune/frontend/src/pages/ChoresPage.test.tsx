import { describe, it, expect, vi, beforeEach } from 'vitest';
import { fireEvent, render, screen } from '@/test/test-utils';
import { expectNoA11yViolations } from '@/test/a11y-helpers';
import { ChoresPage } from './ChoresPage';

const selectProjectMock = vi.fn();
const projectsState = {
  projects: [] as Array<{ project_id: string; name: string }>,
  selectedProject: null as { project_id: string; name: string } | null,
  isLoading: false,
  selectProject: selectProjectMock,
};

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
  useProjects: () => projectsState,
}));

vi.mock('@/hooks/useProjectBoard', () => ({
  useProjectBoard: () => ({ boardData: null, boardLoading: false }),
}));

vi.mock('@/hooks/useChores', () => ({
  useChoresListPaginated: () => ({ allItems: [], isLoading: false }),
  useEvaluateChoresTriggers: vi.fn(),
  choreKeys: { list: () => ['chores'] },
}));

vi.mock('@/hooks/useUnsavedChanges', () => ({
  useUnsavedChanges: () => ({ isBlocked: false, blocker: undefined }),
}));

vi.mock('@/components/chores/AddChoreModal', () => ({
  AddChoreModal: ({ isOpen }: { isOpen: boolean }) =>
    isOpen ? <div role="dialog">Add Chore Modal</div> : null,
}));

vi.mock('@/components/chores/ChoresPanel', () => ({
  ChoresPanel: () => <div>Chores Panel</div>,
}));

vi.mock('@/services/api', () => ({
  choresApi: { seedPresets: vi.fn().mockResolvedValue(undefined) },
  workflowApi: {},
}));

describe('ChoresPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    projectsState.projects = [];
    projectsState.selectedProject = null;
    projectsState.isLoading = false;
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

  it('does not render "Plan recurring work" button', () => {
    render(<ChoresPage />);
    expect(screen.queryByText('Plan recurring work')).not.toBeInTheDocument();
  });

  it('does not render "Featured Rituals" section', () => {
    render(<ChoresPage />);
    expect(screen.queryByText('Featured Rituals')).not.toBeInTheDocument();
  });

  it('does not render "Review upkeep cadence" button', () => {
    render(<ChoresPage />);
    expect(screen.queryByText('Review upkeep cadence')).not.toBeInTheDocument();
  });

  it('has no accessibility violations', async () => {
    const { container } = render(<ChoresPage />);
    await expectNoA11yViolations(container);
  });
});

describe('ChoresPage — with selected project', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    projectsState.selectedProject = { project_id: 'PVT_1', name: 'Project Alpha' };
  });

  it('renders "+ Create Chore" and opens the modal', () => {
    render(<ChoresPage />);
    const createButton = screen.getByRole('button', { name: /\+ create chore/i });
    expect(createButton).toBeInTheDocument();

    fireEvent.click(createButton);

    expect(screen.getByRole('dialog')).toHaveTextContent('Add Chore Modal');
  });

  it('does not auto-reopen the modal after project changes back', () => {
    const { rerender } = render(<ChoresPage />);

    // Open the modal
    fireEvent.click(screen.getByRole('button', { name: /\+ create chore/i }));
    expect(screen.getByRole('dialog')).toBeInTheDocument();

    // Simulate project deselection then re-selection
    projectsState.selectedProject = null;
    rerender(<ChoresPage />);

    projectsState.selectedProject = { project_id: 'PVT_1', name: 'Project Alpha' };
    rerender(<ChoresPage />);

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });
});
