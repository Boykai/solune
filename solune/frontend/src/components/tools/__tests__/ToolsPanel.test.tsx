import { describe, it, expect, vi, beforeEach } from 'vitest';
import userEvent from '@testing-library/user-event';

import { render, screen } from '@/test/test-utils';
import { ToolsPanel } from '../ToolsPanel';
import type { McpToolConfig } from '@/types';

function createMockTool(overrides: Partial<McpToolConfig> = {}): McpToolConfig {
  return {
    id: 'tool-1',
    name: 'Sentry MCP',
    description: 'Error tracking',
    endpoint_url: 'https://mcp.sentry.io',
    config_content: '{"mcpServers":{"sentry":{"type":"http","url":"https://mcp.sentry.io"}}}',
    sync_status: 'synced',
    sync_error: '',
    synced_at: new Date().toISOString(),
    github_repo_target: 'owner/repo',
    is_active: true,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    ...overrides,
  };
}

const mockUseToolsList = vi.fn();
const mockUseToolsListPaginated = vi.fn();
const mockUseUndoableDeleteTool = vi.fn();
const mockUseRepoMcpConfig = vi.fn();
const mockUseMcpPresets = vi.fn();
const mockUseConfirmation = vi.fn();

vi.mock('@/hooks/useTools', () => ({
  useToolsList: (...args: unknown[]) => mockUseToolsList(...args),
  useToolsListPaginated: (...args: unknown[]) => mockUseToolsListPaginated(...args),
  useUndoableDeleteTool: (...args: unknown[]) => mockUseUndoableDeleteTool(...args),
}));

vi.mock('@/hooks/useRepoMcpConfig', () => ({
  useRepoMcpConfig: (...args: unknown[]) => mockUseRepoMcpConfig(...args),
}));

vi.mock('@/hooks/useMcpPresets', () => ({
  useMcpPresets: () => mockUseMcpPresets(),
}));

vi.mock('@/hooks/useConfirmation', () => ({
  useConfirmation: () => mockUseConfirmation(),
}));

const defaultToolsListReturn = {
  tools: [] as McpToolConfig[],
  isLoading: false,
  error: null,
  rawError: null,
  refetch: vi.fn(),
  uploadTool: vi.fn(),
  isUploading: false,
  uploadError: null,
  resetUploadError: vi.fn(),
  updateTool: vi.fn(),
  isUpdating: false,
  updateError: null,
  resetUpdateError: vi.fn(),
  syncTool: vi.fn(),
  syncingId: null,
  syncError: null,
  deleteTool: vi.fn(),
  deletingId: null,
  deleteError: null,
};

const defaultPaginatedReturn = {
  allItems: [] as McpToolConfig[],
  hasNextPage: false,
  isFetchingNextPage: false,
  fetchNextPage: vi.fn(),
  isError: false,
};

const defaultRepoConfigReturn = {
  repoConfig: null,
  isLoading: false,
  error: null,
  rawError: null,
  refetch: vi.fn(),
  updateRepoServer: vi.fn(),
  isUpdating: false,
  updatingServerName: null,
  updateError: null,
  resetUpdateError: vi.fn(),
  deleteRepoServer: vi.fn(),
  isDeleting: false,
  deletingServerName: null,
  deleteError: null,
  resetDeleteError: vi.fn(),
};

const defaultPresetsReturn = {
  presets: [],
  isLoading: false,
  error: null,
  rawError: null,
  refetch: vi.fn(),
};

describe('ToolsPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseToolsList.mockReturnValue({ ...defaultToolsListReturn });
    mockUseToolsListPaginated.mockReturnValue({ ...defaultPaginatedReturn });
    mockUseUndoableDeleteTool.mockReturnValue({ deleteTool: vi.fn() });
    mockUseRepoMcpConfig.mockReturnValue({ ...defaultRepoConfigReturn });
    mockUseMcpPresets.mockReturnValue({ ...defaultPresetsReturn });
    mockUseConfirmation.mockReturnValue({ confirm: vi.fn() });
  });

  it('renders the panel heading', () => {
    render(<ToolsPanel projectId="proj-1" />);
    expect(screen.getByText('MCP Tools')).toBeInTheDocument();
  });

  it('shows the Upload MCP Config button', () => {
    render(<ToolsPanel projectId="proj-1" />);
    expect(screen.getByRole('button', { name: /upload mcp config/i })).toBeInTheDocument();
  });

  it('shows empty state when no tools', () => {
    render(<ToolsPanel projectId="proj-1" />);
    expect(screen.getByText(/no mcp tools configured yet/i)).toBeInTheDocument();
  });

  it('shows loading state', () => {
    mockUseToolsList.mockReturnValue({ ...defaultToolsListReturn, isLoading: true });
    render(<ToolsPanel projectId="proj-1" />);
    expect(screen.getByText('Loading MCP tools')).toBeInTheDocument();
  });

  it('shows error state with retry button', async () => {
    const user = userEvent.setup();
    const refetch = vi.fn();
    mockUseToolsList.mockReturnValue({ ...defaultToolsListReturn, error: 'Failed', refetch });
    render(<ToolsPanel projectId="proj-1" />);
    expect(screen.getByText(/could not load tools/i)).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /retry/i }));
    expect(refetch).toHaveBeenCalled();
  });

  it('renders tool cards when tools are present', () => {
    const tools = [
      createMockTool({ id: 't1', name: 'Sentry' }),
      createMockTool({ id: 't2', name: 'Linear' }),
    ];
    mockUseToolsList.mockReturnValue({ ...defaultToolsListReturn, tools });
    render(<ToolsPanel projectId="proj-1" />);
    expect(screen.getByText('Sentry')).toBeInTheDocument();
    expect(screen.getByText('Linear')).toBeInTheDocument();
  });

  it('filters tools via search input', async () => {
    const user = userEvent.setup();
    const tools = [
      createMockTool({ id: 't1', name: 'Sentry' }),
      createMockTool({ id: 't2', name: 'Linear' }),
    ];
    mockUseToolsList.mockReturnValue({ ...defaultToolsListReturn, tools });
    render(<ToolsPanel projectId="proj-1" />);

    const searchInput = screen.getByPlaceholderText(/search by name or description/i);
    await user.type(searchInput, 'Sentry');

    expect(screen.getByText('Sentry')).toBeInTheDocument();
    expect(screen.queryByText('Linear')).not.toBeInTheDocument();
  });

  it('shows "no tools match" when search yields no results', async () => {
    const user = userEvent.setup();
    const tools = [createMockTool({ id: 't1', name: 'Sentry' })];
    mockUseToolsList.mockReturnValue({ ...defaultToolsListReturn, tools });
    render(<ToolsPanel projectId="proj-1" />);

    const searchInput = screen.getByPlaceholderText(/search by name or description/i);
    await user.type(searchInput, 'nonexistent');

    expect(screen.getByText(/no tools match the current filters/i)).toBeInTheDocument();
  });

  it('renders the repo config section', () => {
    render(<ToolsPanel projectId="proj-1" />);
    expect(screen.getByText('Current repository config')).toBeInTheDocument();
  });

  it('renders the presets gallery section', () => {
    render(<ToolsPanel projectId="proj-1" />);
    expect(screen.getByText('Quick-add MCP presets')).toBeInTheDocument();
  });

  it('renders the GitHub config generator section', () => {
    render(<ToolsPanel projectId="proj-1" />);
    expect(screen.getByText('MCP Configuration for GitHub Agents')).toBeInTheDocument();
  });
});
