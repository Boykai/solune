import { describe, it, expect, vi, beforeEach } from 'vitest';
import userEvent from '@testing-library/user-event';

import { render, screen } from '@/test/test-utils';
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
    expect(importServer).toHaveBeenCalledWith('mcp-1');
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
});
