import { describe, it, expect, vi, beforeEach } from 'vitest';
import userEvent from '@testing-library/user-event';

import { render, screen, waitFor } from '@/test/test-utils';
import { McpCatalogBrowse } from '../McpCatalogBrowse';
import type { CatalogMcpServer } from '@/types';

const mockUseMcpCatalog = vi.fn();
const mockUseImportMcpServer = vi.fn();

vi.mock('@/hooks/useTools', () => ({
  useMcpCatalog: (...args: unknown[]) => mockUseMcpCatalog(...args),
  useImportMcpServer: (...args: unknown[]) => mockUseImportMcpServer(...args),
}));

function createMockCatalogServer(overrides: Partial<CatalogMcpServer> = {}): CatalogMcpServer {
  return {
    id: 'test-mcp',
    name: 'Test MCP Server',
    description: 'A test MCP server for development',
    repo_url: 'https://github.com/test/test-mcp',
    category: 'Developer Tools',
    server_type: 'http',
    install_config: {
      transport: 'http',
      url: 'https://example.com/mcp',
    },
    quality_score: 'A',
    already_installed: false,
    ...overrides,
  };
}

const defaultCatalogReturn = {
  servers: [] as CatalogMcpServer[],
  isLoading: false,
  isError: false,
  error: null,
  refetch: vi.fn(),
};

const defaultImportReturn = {
  importServer: vi.fn(),
  isImporting: false,
  importingId: null,
  importError: null,
  reset: vi.fn(),
};

describe('McpCatalogBrowse', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseMcpCatalog.mockReturnValue({ ...defaultCatalogReturn });
    mockUseImportMcpServer.mockReturnValue({ ...defaultImportReturn });
  });

  it('renders the catalog section heading', () => {
    render(<McpCatalogBrowse projectId="proj-1" />);
    expect(screen.getByText('Browse MCP Servers')).toBeInTheDocument();
  });

  it('renders the search input', () => {
    render(<McpCatalogBrowse projectId="proj-1" />);
    expect(screen.getByPlaceholderText('Search MCP servers…')).toBeInTheDocument();
  });

  it('renders category filter chips', () => {
    render(<McpCatalogBrowse projectId="proj-1" />);
    expect(screen.getByText('Developer Tools')).toBeInTheDocument();
    expect(screen.getByText('Cloud')).toBeInTheDocument();
    expect(screen.getByText('Database')).toBeInTheDocument();
  });

  it('shows loading state', () => {
    mockUseMcpCatalog.mockReturnValue({ ...defaultCatalogReturn, isLoading: true });
    render(<McpCatalogBrowse projectId="proj-1" />);
    expect(screen.getByText('Loading catalog…')).toBeInTheDocument();
  });

  it('shows error state with retry button', async () => {
    const user = userEvent.setup();
    const refetch = vi.fn();
    mockUseMcpCatalog.mockReturnValue({
      ...defaultCatalogReturn,
      isError: true,
      error: { message: 'unavailable' },
      refetch,
    });
    render(<McpCatalogBrowse projectId="proj-1" />);
    expect(screen.getByText('MCP catalog is temporarily unavailable.')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /retry/i }));
    expect(refetch).toHaveBeenCalled();
  });

  it('shows empty state when no servers', () => {
    render(<McpCatalogBrowse projectId="proj-1" />);
    expect(screen.getByText('No MCP servers available in the catalog.')).toBeInTheDocument();
  });

  it('shows empty search state when search yields no results', async () => {
    const user = userEvent.setup();
    render(<McpCatalogBrowse projectId="proj-1" />);

    await user.type(screen.getByPlaceholderText('Search MCP servers…'), 'nonexistent');
    expect(screen.getByText('No MCP servers match your search.')).toBeInTheDocument();
  });

  it('passes the search query to the catalog hook', async () => {
    const user = userEvent.setup();
    render(<McpCatalogBrowse projectId="proj-1" />);

    await user.type(screen.getByPlaceholderText('Search MCP servers…'), 'github');

    await waitFor(() => {
      expect(mockUseMcpCatalog).toHaveBeenLastCalledWith('proj-1', 'github', '');
    });
  });

  it('renders server cards when servers are present', () => {
    const servers = [
      createMockCatalogServer({ id: 's1', name: 'GitHub MCP' }),
      createMockCatalogServer({ id: 's2', name: 'Sentry MCP' }),
    ];
    mockUseMcpCatalog.mockReturnValue({ ...defaultCatalogReturn, servers });
    render(<McpCatalogBrowse projectId="proj-1" />);
    expect(screen.getByText('GitHub MCP')).toBeInTheDocument();
    expect(screen.getByText('Sentry MCP')).toBeInTheDocument();
  });

  it('renders quality score badges', () => {
    const servers = [createMockCatalogServer({ quality_score: 'A' })];
    mockUseMcpCatalog.mockReturnValue({ ...defaultCatalogReturn, servers });
    render(<McpCatalogBrowse projectId="proj-1" />);
    expect(screen.getByText('A')).toBeInTheDocument();
  });

  it('renders type badges (Remote for http)', () => {
    const servers = [createMockCatalogServer({ server_type: 'http' })];
    mockUseMcpCatalog.mockReturnValue({ ...defaultCatalogReturn, servers });
    render(<McpCatalogBrowse projectId="proj-1" />);
    expect(screen.getByText('Remote')).toBeInTheDocument();
  });

  it('renders type badges (Local for stdio)', () => {
    const servers = [createMockCatalogServer({ server_type: 'stdio' })];
    mockUseMcpCatalog.mockReturnValue({ ...defaultCatalogReturn, servers });
    render(<McpCatalogBrowse projectId="proj-1" />);
    expect(screen.getByText('Local')).toBeInTheDocument();
  });

  it('shows Installed badge for already_installed servers', () => {
    const servers = [createMockCatalogServer({ already_installed: true })];
    mockUseMcpCatalog.mockReturnValue({ ...defaultCatalogReturn, servers });
    render(<McpCatalogBrowse projectId="proj-1" />);
    expect(screen.getByText('Installed')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /import/i })).not.toBeInTheDocument();
  });

  it('shows Import button for non-installed servers', () => {
    const servers = [createMockCatalogServer({ already_installed: false })];
    mockUseMcpCatalog.mockReturnValue({ ...defaultCatalogReturn, servers });
    render(<McpCatalogBrowse projectId="proj-1" />);
    expect(screen.getByRole('button', { name: /import/i })).toBeInTheDocument();
  });

  it('calls importServer when Import is clicked', async () => {
    const user = userEvent.setup();
    const importServer = vi.fn().mockResolvedValue({});
    mockUseImportMcpServer.mockReturnValue({ ...defaultImportReturn, importServer });

    const servers = [createMockCatalogServer({ id: 'mcp-1', already_installed: false })];
    mockUseMcpCatalog.mockReturnValue({ ...defaultCatalogReturn, servers });

    render(<McpCatalogBrowse projectId="proj-1" />);
    await user.click(screen.getByRole('button', { name: /import/i }));
    expect(importServer).toHaveBeenCalledWith(servers[0]);
  });

  it('renders repo link when repo_url is present', () => {
    const servers = [
      createMockCatalogServer({ repo_url: 'https://github.com/test/repo' }),
    ];
    mockUseMcpCatalog.mockReturnValue({ ...defaultCatalogReturn, servers });
    render(<McpCatalogBrowse projectId="proj-1" />);
    expect(screen.getByLabelText(/view .* repository/i)).toBeInTheDocument();
  });

  it('toggles category filter chips', async () => {
    const user = userEvent.setup();
    render(<McpCatalogBrowse projectId="proj-1" />);

    // Click a category
    await user.click(screen.getByText('Cloud'));

    // Clear filter button should appear
    expect(screen.getByText('Clear filter')).toBeInTheDocument();

    // Click same category again to deselect
    await user.click(screen.getByText('Cloud'));
    expect(screen.queryByText('Clear filter')).not.toBeInTheDocument();
  });

  it('passes the selected category to the catalog hook', async () => {
    const user = userEvent.setup();
    render(<McpCatalogBrowse projectId="proj-1" />);

    await user.click(screen.getByText('Cloud'));

    await waitFor(() => {
      expect(mockUseMcpCatalog).toHaveBeenLastCalledWith('proj-1', '', 'Cloud');
    });
  });

  it('disables Import button while importing that server', () => {
    const servers = [createMockCatalogServer({ id: 'mcp-1', already_installed: false })];
    mockUseMcpCatalog.mockReturnValue({ ...defaultCatalogReturn, servers });
    mockUseImportMcpServer.mockReturnValue({
      ...defaultImportReturn,
      isImporting: true,
      importingId: 'mcp-1',
    });
    render(<McpCatalogBrowse projectId="proj-1" />);
    const importButton = screen.getByRole('button', { name: /import/i });
    expect(importButton).toBeDisabled();
  });

  it('does not disable Import button for other servers during import', () => {
    const servers = [
      createMockCatalogServer({ id: 'mcp-1', already_installed: false }),
      createMockCatalogServer({ id: 'mcp-2', name: 'Other MCP', already_installed: false }),
    ];
    mockUseMcpCatalog.mockReturnValue({ ...defaultCatalogReturn, servers });
    mockUseImportMcpServer.mockReturnValue({
      ...defaultImportReturn,
      isImporting: true,
      importingId: 'mcp-2',
    });
    render(<McpCatalogBrowse projectId="proj-1" />);
    const importButtons = screen.getAllByRole('button', { name: /import/i });
    // First button (mcp-1) should be enabled, second (mcp-2) disabled
    expect(importButtons[0]).not.toBeDisabled();
    expect(importButtons[1]).toBeDisabled();
  });

  it('hides repo link when repo_url is not present', () => {
    const servers = [createMockCatalogServer({ repo_url: null })];
    mockUseMcpCatalog.mockReturnValue({ ...defaultCatalogReturn, servers });
    render(<McpCatalogBrowse projectId="proj-1" />);
    expect(screen.queryByLabelText(/view .* repository/i)).not.toBeInTheDocument();
  });

  it('renders the clear filter button and clears category', async () => {
    const user = userEvent.setup();
    render(<McpCatalogBrowse projectId="proj-1" />);

    await user.click(screen.getByText('Database'));
    expect(screen.getByText('Clear filter')).toBeInTheDocument();

    await user.click(screen.getByText('Clear filter'));
    expect(screen.queryByText('Clear filter')).not.toBeInTheDocument();
  });

  it('renders server category text when present', () => {
    const servers = [createMockCatalogServer({ category: 'Monitoring' })];
    mockUseMcpCatalog.mockReturnValue({ ...defaultCatalogReturn, servers });
    render(<McpCatalogBrowse projectId="proj-1" />);
    // 'Monitoring' appears both as a chip and in the card; at least two instances
    const elements = screen.getAllByText('Monitoring');
    expect(elements.length).toBeGreaterThanOrEqual(2);
  });

  it('does not show quality badge when score is null', () => {
    const servers = [createMockCatalogServer({ quality_score: null })];
    mockUseMcpCatalog.mockReturnValue({ ...defaultCatalogReturn, servers });
    render(<McpCatalogBrowse projectId="proj-1" />);
    // Quality badges show A, B, or C — none should be present
    expect(screen.queryByText('A')).not.toBeInTheDocument();
    expect(screen.queryByText('B')).not.toBeInTheDocument();
    expect(screen.queryByText('C')).not.toBeInTheDocument();
  });
});
