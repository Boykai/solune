import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@/test/test-utils';
import { expectNoA11yViolations } from '@/test/a11y-helpers';
import { ToolsPage } from './ToolsPage';

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

vi.mock('@/hooks/useTools', () => ({
  useToolsList: () => ({ tools: [], isLoading: false, error: null }),
  useToolsListPaginated: () => ({ allItems: [], hasNextPage: false, isFetchingNextPage: false, fetchNextPage: () => {}, isError: false, isLoading: false }),
}));

describe('ToolsPage', () => {
  beforeEach(() => {
    mocks.selectedProject = null;
    mocks.boardData = null;
  });

  it('renders without crashing', () => {
    render(<ToolsPage />);
    expect(document.body).toBeDefined();
  });

  it('renders a compact page header with the expected title', () => {
    render(<ToolsPage />);
    const heading = screen.getByRole('heading', { level: 2 });
    expect(heading).toHaveTextContent('Equip your agents with MCP tools.');
  });

  it('uses a <header> element for the page header', () => {
    const { container } = render(<ToolsPage />);
    expect(container.querySelector('header')).toBeInTheDocument();
  });

  it('shows the eyebrow text "Tool Forge"', () => {
    render(<ToolsPage />);
    expect(screen.getByText('Tool Forge')).toBeInTheDocument();
  });

  it('shows "Awaiting repository" badge when no board data is available', () => {
    render(<ToolsPage />);
    expect(screen.getByText('Awaiting repository')).toBeInTheDocument();
  });

  it('shows the repository name as badge when board data has a repository', () => {
    mocks.boardData = {
      columns: [
        {
          status: { option_id: 'c1', name: 'Todo', color: 'GRAY' },
          items: [{ repository: { owner: 'Boykai', name: 'solune' } }],
          item_count: 1,
        },
      ],
    };

    const { container } = render(<ToolsPage />);
    // Badge is the truncated pill element next to the eyebrow
    const badge = container.querySelector('span.rounded-full.border-primary\\/25');
    expect(badge).toHaveTextContent('solune');
  });

  it('renders stats chips for repository and project', () => {
    render(<ToolsPage />);
    expect(screen.getByText('Repository')).toBeInTheDocument();
    expect(screen.getByText('Unlinked')).toBeInTheDocument();
    expect(screen.getByText('Project')).toBeInTheDocument();
    expect(screen.getByText('Unselected')).toBeInTheDocument();
  });

  it('renders action links for browsing tools, MCP docs, and discover', () => {
    render(<ToolsPage />);
    const browseLink = screen.getByRole('link', { name: /browse tools/i });
    expect(browseLink).toHaveAttribute('href', '#tools-catalog');
    const docsLink = screen.getByRole('link', { name: /mcp docs/i });
    expect(docsLink).toHaveAttribute('href', 'https://docs.github.com/en/copilot/concepts/context/mcp');
    const discoverLink = screen.getByRole('link', { name: /discover mcp integrations/i });
    expect(discoverLink).toHaveAttribute('href', 'https://github.com/mcp');
  });

  it('has no accessibility violations', async () => {
    const { container } = render(<ToolsPage />);
    await expectNoA11yViolations(container);
  });
});
