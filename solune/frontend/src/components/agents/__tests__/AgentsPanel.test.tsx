import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@/test/test-utils';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import userEvent from '@testing-library/user-event';
import type { ReactNode } from 'react';
import { ConfirmationDialogProvider } from '@/hooks/useConfirmation';
import { AgentsPanel } from '../AgentsPanel';
import type { AgentConfig } from '@/services/api';

const mockUseAgentsList = vi.fn();
const mockUseAgentsListPaginated = vi.fn();
const mockUsePendingAgentsList = vi.fn();
const mockUseClearPendingAgents = vi.fn();
const mockUseDeleteAgent = vi.fn();
const mockUseUndoableDeleteAgent = vi.fn();
const mockUseCreateAgent = vi.fn();
const mockUseUpdateAgent = vi.fn();
const mockUseBulkUpdateModels = vi.fn();
const mockUseModels = vi.fn();
const mockUseUnsavedChanges = vi.fn();
const mockUseCatalogAgents = vi.fn();
const mockUseImportAgent = vi.fn();
const mockUseInstallAgent = vi.fn();

vi.mock('@/hooks/useModels', () => ({
  useModels: (...args: unknown[]) => mockUseModels(...args),
}));

vi.mock('@/components/pipeline/ModelSelector', () => ({
  ModelSelector: ({ onSelect }: { onSelect?: (id: string, name: string) => void }) => (
    <button type="button" onClick={() => onSelect?.('model-1', 'GPT-5')}>
      Select model
    </button>
  ),
}));

vi.mock('@/hooks/useAgents', () => ({
  useAgentsList: (...args: unknown[]) => mockUseAgentsList(...args),
  useAgentsListPaginated: (...args: unknown[]) => mockUseAgentsListPaginated(...args),
  usePendingAgentsList: (...args: unknown[]) => mockUsePendingAgentsList(...args),
  useClearPendingAgents: (...args: unknown[]) => mockUseClearPendingAgents(...args),
  useDeleteAgent: (...args: unknown[]) => mockUseDeleteAgent(...args),
  useUndoableDeleteAgent: (...args: unknown[]) => mockUseUndoableDeleteAgent(...args),
  useCreateAgent: (...args: unknown[]) => mockUseCreateAgent(...args),
  useUpdateAgent: (...args: unknown[]) => mockUseUpdateAgent(...args),
  useBulkUpdateModels: (...args: unknown[]) => mockUseBulkUpdateModels(...args),
  useCatalogAgents: (...args: unknown[]) => mockUseCatalogAgents(...args),
  useImportAgent: (...args: unknown[]) => mockUseImportAgent(...args),
  useInstallAgent: (...args: unknown[]) => mockUseInstallAgent(...args),
}));

vi.mock('@/hooks/useUnsavedChanges', () => ({
  useUnsavedChanges: (...args: unknown[]) => mockUseUnsavedChanges(...args),
}));

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <ConfirmationDialogProvider>{children}</ConfirmationDialogProvider>
      </QueryClientProvider>
    );
  };
}

function createAgent(overrides: Partial<AgentConfig> = {}): AgentConfig {
  return {
    id: 'agent-1',
    name: 'Reviewer',
    slug: 'reviewer',
    description: 'Reviews pull requests',
    icon_name: null,
    system_prompt: 'Review carefully',
    default_model_id: '',
    default_model_name: '',
    status: 'pending_pr',
    tools: ['read', 'comment'],
    status_column: null,
    github_issue_number: null,
    github_pr_number: 44,
    branch_name: 'agent/reviewer',
    source: 'local',
    created_at: '2026-03-01T00:00:00Z',
    agent_type: 'custom',
    catalog_source_url: null,
    catalog_agent_id: null,
    imported_at: null,
    ...overrides,
  };
}

describe('AgentsPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAgentsList.mockReturnValue({
      data: [],
      isLoading: false,
      error: null,
    });
    mockUseAgentsListPaginated.mockReturnValue({
      allItems: [],
      isLoading: false,
      isError: false,
      hasNextPage: false,
      isFetchingNextPage: false,
      fetchNextPage: vi.fn(),
      invalidate: vi.fn(),
    });
    mockUsePendingAgentsList.mockReturnValue({
      data: [],
      isLoading: false,
    });
    mockUseClearPendingAgents.mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
      isSuccess: false,
      isError: false,
      data: undefined,
      error: null,
    });
    mockUseDeleteAgent.mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
      isSuccess: false,
      isError: false,
      data: undefined,
      error: null,
    });
    mockUseUndoableDeleteAgent.mockReturnValue({
      deleteAgent: vi.fn(),
      pendingIds: new Set<string>(),
    });
    mockUseCreateAgent.mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    });
    mockUseUpdateAgent.mockReturnValue({
      mutateAsync: vi.fn().mockResolvedValue({ pr_url: 'https://example.test/pr/1' }),
      isPending: false,
    });
    mockUseBulkUpdateModels.mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
      isSuccess: false,
      isError: false,
      data: undefined,
      error: null,
    });
    mockUseCatalogAgents.mockReturnValue({
      data: [],
      isLoading: false,
      isError: false,
    });
    mockUseImportAgent.mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    });
    mockUseInstallAgent.mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    });
    mockUseModels.mockReturnValue({
      refreshModels: vi.fn(),
      isRefreshing: false,
    });
    mockUseUnsavedChanges.mockReturnValue({
      blocker: { state: 'unblocked', proceed: vi.fn(), reset: vi.fn() },
      isBlocked: false,
    });
  });

  it('renders the themed add agent CTA', () => {
    render(<AgentsPanel projectId="PVT_1" />, { wrapper: createWrapper() });

    const addButton = screen.getByRole('button', { name: /\+ add agent/i });
    expect(addButton).toBeInTheDocument();
    expect(addButton).toHaveClass('backlog-cta');
  });

  it('does not render Featured Agents section', () => {
    const agents = [
      createAgent({ id: 'a1', slug: 'alpha', name: 'Alpha', created_at: '2026-03-01T00:00:00Z' }),
      createAgent({ id: 'a2', slug: 'beta', name: 'Beta', created_at: '2026-03-01T00:00:00Z' }),
    ];
    mockUseAgentsList.mockReturnValue({ data: agents, isLoading: false, error: null });
    mockUseAgentsListPaginated.mockReturnValue({ allItems: agents, isLoading: false, isError: false, hasNextPage: false, isFetchingNextPage: false, fetchNextPage: vi.fn(), invalidate: vi.fn() });

    render(
      <AgentsPanel
        projectId="PVT_1"
        agentUsageCounts={{ alpha: 7, beta: 5 }}
      />,
      { wrapper: createWrapper() }
    );

    expect(screen.queryByText('Featured agents')).not.toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'The agents setting the tone right now' })).not.toBeInTheDocument();
  });

  it('renders Catalog Controls before Awesome Catalog when agents are loaded', () => {
    const agents = [
      createAgent({ id: 'a1', slug: 'alpha', name: 'Alpha' }),
    ];
    mockUseAgentsList.mockReturnValue({ data: agents, isLoading: false, error: null });
    mockUseAgentsListPaginated.mockReturnValue({ allItems: agents, isLoading: false, isError: false, hasNextPage: false, isFetchingNextPage: false, fetchNextPage: vi.fn(), invalidate: vi.fn() });

    render(<AgentsPanel projectId="PVT_1" />, { wrapper: createWrapper() });

    const catalogHeading = screen.getByRole('heading', { name: 'Filter the constellation' });
    const awesomeHeading = screen.getByRole('heading', { name: 'Browse Awesome Copilot Agents' });

    // Node.DOCUMENT_POSITION_FOLLOWING (4) means awesomeHeading appears after catalogHeading
    expect(catalogHeading.compareDocumentPosition(awesomeHeading) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it('collapses and expands the Pending Changes section', async () => {
    const user = userEvent.setup();
    mockUsePendingAgentsList.mockReturnValue({
      data: [createAgent()],
      isLoading: false,
    });

    render(<AgentsPanel projectId="PVT_1" />, { wrapper: createWrapper() });

    expect(screen.getByText('Pending changes')).toBeInTheDocument();
    const pendingHeading = screen.getByRole('heading', { name: 'Agent PRs waiting on main' });
    expect(pendingHeading).toBeInTheDocument();
    expect(screen.getByText('Reviewer')).toBeInTheDocument();

    const toggleButton = pendingHeading.closest('button');
    expect(toggleButton).not.toBeNull();
    await user.click(toggleButton!);

    expect(screen.queryByText('Reviewer')).not.toBeInTheDocument();

    await user.click(toggleButton!);
    expect(screen.getByText('Reviewer')).toBeInTheDocument();
  });

  it('collapses and expands the Catalog Controls section', async () => {
    const user = userEvent.setup();
    const agents = [createAgent({ id: 'a1', slug: 'alpha', name: 'Alpha' })];
    mockUseAgentsList.mockReturnValue({ data: agents, isLoading: false, error: null });
    mockUseAgentsListPaginated.mockReturnValue({ allItems: agents, isLoading: false, isError: false, hasNextPage: false, isFetchingNextPage: false, fetchNextPage: vi.fn(), invalidate: vi.fn() });

    render(<AgentsPanel projectId="PVT_1" />, { wrapper: createWrapper() });

    const catalogHeading = screen.getByRole('heading', { name: 'Filter the constellation' });
    expect(screen.getByPlaceholderText('Search by name, slug, description, or tool')).toBeInTheDocument();

    const toggleButton = catalogHeading.closest('button');
    expect(toggleButton).not.toBeNull();
    await user.click(toggleButton!);

    expect(screen.queryByPlaceholderText('Search by name, slug, description, or tool')).not.toBeInTheDocument();

    await user.click(toggleButton!);
    expect(screen.getByPlaceholderText('Search by name, slug, description, or tool')).toBeInTheDocument();
  });

  it('collapses and expands the Awesome Catalog section', async () => {
    const user = userEvent.setup();
    mockUseCatalogAgents.mockReturnValue({
      data: [
        {
          id: 'catalog-1',
          name: 'Catalog Alpha',
          description: 'Helps with alpha work',
          source_url: 'https://example.test/catalog-alpha',
          already_imported: false,
        },
      ],
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    });

    render(<AgentsPanel projectId="PVT_1" />, { wrapper: createWrapper() });

    const awesomeHeading = screen.getByRole('heading', { name: 'Browse Awesome Copilot Agents' });
    expect(screen.getByText('Catalog Alpha')).toBeInTheDocument();

    const toggleButton = awesomeHeading.closest('button');
    expect(toggleButton).not.toBeNull();
    await user.click(toggleButton!);

    expect(screen.queryByText('Catalog Alpha')).not.toBeInTheDocument();

    await user.click(toggleButton!);
    expect(screen.getByText('Catalog Alpha')).toBeInTheDocument();
  });

  it('collapsible sections default to expanded with aria-expanded true', () => {
    const agents = [createAgent({ id: 'a1', slug: 'alpha', name: 'Alpha' })];
    mockUseAgentsList.mockReturnValue({ data: agents, isLoading: false, error: null });
    mockUseAgentsListPaginated.mockReturnValue({ allItems: agents, isLoading: false, isError: false, hasNextPage: false, isFetchingNextPage: false, fetchNextPage: vi.fn(), invalidate: vi.fn() });
    mockUsePendingAgentsList.mockReturnValue({
      data: [createAgent({ id: 'p1', slug: 'beta', name: 'Beta', status: 'pending_pr' })],
      isLoading: false,
    });

    render(<AgentsPanel projectId="PVT_1" />, { wrapper: createWrapper() });

    const pendingToggle = screen.getByRole('heading', { name: 'Agent PRs waiting on main' }).closest('button');
    const catalogToggle = screen.getByRole('heading', { name: 'Filter the constellation' }).closest('button');
    const awesomeToggle = screen.getByRole('heading', { name: 'Browse Awesome Copilot Agents' }).closest('button');

    expect(pendingToggle).toHaveAttribute('aria-expanded', 'true');
    expect(catalogToggle).toHaveAttribute('aria-expanded', 'true');
    expect(awesomeToggle).toHaveAttribute('aria-expanded', 'true');
  });

  it('toggle buttons report aria-expanded false when collapsed', async () => {
    const user = userEvent.setup();
    mockUsePendingAgentsList.mockReturnValue({
      data: [createAgent()],
      isLoading: false,
    });

    render(<AgentsPanel projectId="PVT_1" />, { wrapper: createWrapper() });

    const toggle = screen.getByRole('heading', { name: 'Agent PRs waiting on main' }).closest('button')!;
    expect(toggle).toHaveAttribute('aria-expanded', 'true');

    await user.click(toggle);
    expect(toggle).toHaveAttribute('aria-expanded', 'false');

    await user.click(toggle);
    expect(toggle).toHaveAttribute('aria-expanded', 'true');
  });

  it('keeps section header visible when section body is collapsed', async () => {
    const user = userEvent.setup();
    mockUseCatalogAgents.mockReturnValue({
      data: [
        {
          id: 'catalog-1',
          name: 'Catalog Alpha',
          description: 'Helps with alpha work',
          source_url: 'https://example.test/catalog-alpha',
          already_imported: false,
        },
      ],
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    });

    render(<AgentsPanel projectId="PVT_1" />, { wrapper: createWrapper() });

    const awesomeHeading = screen.getByRole('heading', { name: 'Browse Awesome Copilot Agents' });
    const toggle = awesomeHeading.closest('button')!;
    await user.click(toggle);

    // Header text and description remain visible even when collapsed
    expect(screen.getByRole('heading', { name: 'Browse Awesome Copilot Agents' })).toBeInTheDocument();
    expect(screen.getByText('Awesome catalog')).toBeInTheDocument();
    // But the body content (search and catalog items) is hidden
    expect(screen.queryByPlaceholderText('Search catalog agents…')).not.toBeInTheDocument();
    expect(screen.queryByText('Catalog Alpha')).not.toBeInTheDocument();
  });

  it('hides agent cards in Catalog Controls when collapsed', async () => {
    const user = userEvent.setup();
    const agents = [createAgent({ id: 'a1', slug: 'alpha', name: 'Alpha', source: 'repo', status: 'active' })];
    mockUseAgentsList.mockReturnValue({ data: agents, isLoading: false, error: null });
    mockUseAgentsListPaginated.mockReturnValue({ allItems: agents, isLoading: false, isError: false, hasNextPage: false, isFetchingNextPage: false, fetchNextPage: vi.fn(), invalidate: vi.fn() });

    render(<AgentsPanel projectId="PVT_1" />, { wrapper: createWrapper() });

    // Agent card is visible initially
    expect(screen.getByText('Alpha')).toBeInTheDocument();

    const catalogToggle = screen.getByRole('heading', { name: 'Filter the constellation' }).closest('button')!;
    await user.click(catalogToggle);

    // Agent card hidden after collapse
    expect(screen.queryByText('Alpha')).not.toBeInTheDocument();
  });

  it('opens the bulk model update dialog from the catalog controls', async () => {
    mockUseAgentsList.mockReturnValue({
      data: [createAgent({ id: 'a1', slug: 'alpha', name: 'Alpha' })],
      isLoading: false,
      error: null,
    });
    mockUseAgentsListPaginated.mockReturnValue({ allItems: [createAgent({ id: 'a1', slug: 'alpha', name: 'Alpha' })], isLoading: false, isError: false, hasNextPage: false, isFetchingNextPage: false, fetchNextPage: vi.fn(), invalidate: vi.fn() });
    mockUsePendingAgentsList.mockReturnValue({
      data: [createAgent({ id: 'p1', slug: 'beta', name: 'Beta', status: 'pending_pr' })],
      isLoading: false,
    });

    render(<AgentsPanel projectId="PVT_1" />, { wrapper: createWrapper() });
    const user = userEvent.setup();

    await user.click(screen.getByRole('button', { name: /update agents/i }));

    expect(screen.getByRole('dialog', { name: 'Update All Agent Models' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Update All Agent Models' })).toBeInTheDocument();
    expect(
      screen.getByText(/Select the target model to apply to all 2 agents/i)
    ).toBeInTheDocument();
  });

  it('renders the Awesome Copilot catalog inline instead of a browse modal trigger', () => {
    mockUseCatalogAgents.mockReturnValue({
      data: [
        {
          id: 'catalog-1',
          name: 'Catalog Alpha',
          description: 'Helps with alpha work',
          source_url: 'https://example.test/catalog-alpha',
          already_imported: false,
        },
      ],
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    });

    render(<AgentsPanel projectId="PVT_1" />, { wrapper: createWrapper() });

    expect(screen.getByRole('heading', { name: 'Browse Awesome Copilot Agents' })).toBeInTheDocument();
    expect(screen.getByText('Catalog Alpha')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Browse Agents' })).not.toBeInTheDocument();
  });

  it('filters inline catalog agents by search query', async () => {
    const user = userEvent.setup();
    mockUseCatalogAgents.mockReturnValue({
      data: [
        {
          id: 'catalog-1',
          name: 'Catalog Alpha',
          description: 'Helps with alpha work',
          source_url: 'https://example.test/catalog-alpha',
          already_imported: false,
        },
        {
          id: 'catalog-2',
          name: 'Catalog Beta',
          description: 'Helps with beta work',
          source_url: 'https://example.test/catalog-beta',
          already_imported: true,
        },
      ],
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    });

    render(<AgentsPanel projectId="PVT_1" />, { wrapper: createWrapper() });

    await user.type(screen.getByPlaceholderText('Search catalog agents…'), 'Alpha');

    await waitFor(() => {
      expect(screen.getByText('Catalog Alpha')).toBeInTheDocument();
      expect(screen.queryByText('Catalog Beta')).not.toBeInTheDocument();
    });
  });

  it('shows an inline empty state when the catalog search has no matches', async () => {
    const user = userEvent.setup();
    mockUseCatalogAgents.mockReturnValue({
      data: [
        {
          id: 'catalog-1',
          name: 'Catalog Alpha',
          description: 'Helps with alpha work',
          source_url: 'https://example.test/catalog-alpha',
          already_imported: false,
        },
      ],
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    });

    render(<AgentsPanel projectId="PVT_1" />, { wrapper: createWrapper() });

    await user.type(screen.getByPlaceholderText('Search catalog agents…'), 'Zeta');

    await waitFor(() => {
      expect(screen.getByText('No agents match your search.')).toBeInTheDocument();
      expect(screen.queryByText('Catalog Alpha')).not.toBeInTheDocument();
    });
  });

  it('imports inline catalog agents with their snapshot metadata', async () => {
    const user = userEvent.setup();
    const mutateAsync = vi.fn().mockResolvedValue(undefined);
    mockUseCatalogAgents.mockReturnValue({
      data: [
        {
          id: 'catalog-1',
          name: 'Catalog Alpha',
          description: 'Helps with alpha work',
          source_url: 'https://example.test/catalog-alpha',
          already_imported: false,
        },
      ],
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    });
    mockUseImportAgent.mockReturnValue({
      mutateAsync,
      isPending: false,
    });

    render(<AgentsPanel projectId="PVT_1" />, { wrapper: createWrapper() });

    // Expand the catalog tile by clicking it
    await user.click(screen.getByRole('button', { name: /Catalog Alpha/i }));

    // Click the import button inside the expanded tile
    await user.click(screen.getByRole('button', { name: 'Import to project' }));

    await waitFor(() => {
      expect(mutateAsync).toHaveBeenCalledWith({
        catalog_agent_id: 'catalog-1',
        name: 'Catalog Alpha',
        description: 'Helps with alpha work',
        source_url: 'https://example.test/catalog-alpha',
      });
    });
  });

  it('opens the inline editor for pending local agents', async () => {
    mockUsePendingAgentsList.mockReturnValue({
      data: [createAgent()],
      isLoading: false,
    });

    render(<AgentsPanel projectId="PVT_1" />, { wrapper: createWrapper() });
    const user = userEvent.setup();

    await waitFor(() => {
      expect(screen.getByText('Pending changes')).toBeInTheDocument();
    });

    await user.click(screen.getByRole('button', { name: 'Edit' }));

    await waitFor(() => {
      expect(screen.getByText('Editing agent definition')).toBeInTheDocument();
    });

    expect(screen.getByDisplayValue('Reviewer')).toBeInTheDocument();
    expect(screen.getByDisplayValue('Review carefully')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Save Changes' })).toBeInTheDocument();
  });

  it('allows editing repository agents so tools can be updated', async () => {
    mockUseAgentsList.mockReturnValue({
      data: [createAgent({ id: 'repo:reviewer', source: 'repo', status: 'active' })],
      isLoading: false,
      error: null,
    });
    mockUseAgentsListPaginated.mockReturnValue({ allItems: [createAgent({ id: 'repo:reviewer', source: 'repo', status: 'active' })], isLoading: false, isError: false, hasNextPage: false, isFetchingNextPage: false, fetchNextPage: vi.fn(), invalidate: vi.fn() });

    render(<AgentsPanel projectId="PVT_1" />, { wrapper: createWrapper() });
    const user = userEvent.setup();

    await user.click(screen.getAllByRole('button', { name: 'Edit' })[0]);

    await waitFor(() => {
      expect(screen.getByText('Editing agent definition')).toBeInTheDocument();
    });

    expect(screen.getByText('MCP Tools')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Add Tools' })).toBeInTheDocument();
  });

  it('renders pretty names for spec kit agents in the catalog', () => {
    mockUseAgentsList.mockReturnValue({
      data: [
        createAgent({
          id: 'repo:speckit-clarify',
          name: 'Speckit.Clarify',
          slug: 'speckit.clarify',
          source: 'repo',
          status: 'active',
        }),
      ],
      isLoading: false,
      error: null,
    });
    mockUseAgentsListPaginated.mockReturnValue({ allItems: [ createAgent({ id: 'repo:speckit-clarify', name: 'Speckit.Clarify', slug: 'speckit.clarify', source: 'repo', status: 'active', }), ], isLoading: false, isError: false, hasNextPage: false, isFetchingNextPage: false, fetchNextPage: vi.fn(), invalidate: vi.fn() });

    render(<AgentsPanel projectId="PVT_1" />, { wrapper: createWrapper() });

    expect(screen.getByText('Clarify (Spec Kit)')).toBeInTheDocument();
    expect(screen.queryByText('Speckit.Clarify')).not.toBeInTheDocument();
  });

  it('shows recently added for new agents and pending sub-issue counts from cached board data', () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-03-08T12:00:00Z'));

    mockUseAgentsList.mockReturnValue({
      data: [
        createAgent({
          id: 'repo:alpha',
          slug: 'alpha',
          name: 'Alpha',
          source: 'repo',
          status: 'active',
          created_at: '2026-03-07T08:00:00Z',
        }),
      ],
      isLoading: false,
      error: null,
    });
    mockUseAgentsListPaginated.mockReturnValue({
      allItems: [
        createAgent({
          id: 'repo:alpha',
          slug: 'alpha',
          name: 'Alpha',
          source: 'repo',
          status: 'active',
          created_at: '2026-03-07T08:00:00Z',
        }),
      ],
      isLoading: false,
      isError: false,
      hasNextPage: false,
      isFetchingNextPage: false,
      fetchNextPage: vi.fn(),
      invalidate: vi.fn(),
    });

    render(<AgentsPanel projectId="PVT_1" pendingSubIssueCounts={{ alpha: 3 }} />, {
      wrapper: createWrapper(),
    });

    expect(screen.getAllByText('Recently added')).toHaveLength(1);
    expect(screen.getAllByText('Assigned sub-issues')).toHaveLength(1);
    expect(screen.getAllByText('3 open')).toHaveLength(1);

    vi.useRealTimers();
  });

  it('shows config pill counts from saved pipeline usage', () => {
    mockUseAgentsList.mockReturnValue({
      data: [
        createAgent({
          id: 'repo:alpha',
          slug: 'alpha',
          name: 'Alpha',
          source: 'repo',
          status: 'active',
        }),
      ],
      isLoading: false,
      error: null,
    });
    mockUseAgentsListPaginated.mockReturnValue({
      allItems: [
        createAgent({
          id: 'repo:alpha',
          slug: 'alpha',
          name: 'Alpha',
          source: 'repo',
          status: 'active',
        }),
      ],
      isLoading: false,
      isError: false,
      hasNextPage: false,
      isFetchingNextPage: false,
      fetchNextPage: vi.fn(),
      invalidate: vi.fn(),
    });

    render(
      <AgentsPanel
        projectId="PVT_1"
        agentUsageCounts={{ alpha: 9 }}
        pipelineConfigCounts={{ alpha: 2 }}
      />,
      { wrapper: createWrapper() }
    );

    expect(screen.getAllByText('2 configs')).toHaveLength(1);
    expect(screen.queryByText('9 configs')).not.toBeInTheDocument();
  });

  it('shows the creation timestamp after the recent window expires', () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-03-08T12:00:00Z'));

    const createdAt = '2026-03-04T08:00:00Z';
    const expected = new Intl.DateTimeFormat(undefined, {
      dateStyle: 'medium',
      timeStyle: 'short',
    }).format(Date.parse(createdAt));

    mockUseAgentsList.mockReturnValue({
      data: [
        createAgent({
          id: 'repo:alpha',
          slug: 'alpha',
          name: 'Alpha',
          source: 'repo',
          status: 'active',
          created_at: createdAt,
        }),
      ],
      isLoading: false,
      error: null,
    });
    mockUseAgentsListPaginated.mockReturnValue({ allItems: [ createAgent({ id: 'repo:alpha', slug: 'alpha', name: 'Alpha', source: 'repo', status: 'active', created_at: createdAt, }), ], isLoading: false, isError: false, hasNextPage: false, isFetchingNextPage: false, fetchNextPage: vi.fn(), invalidate: vi.fn() });

    render(<AgentsPanel projectId="PVT_1" />, { wrapper: createWrapper() });

    expect(screen.getByText(expected)).toBeInTheDocument();

    vi.useRealTimers();
  });

  it('saves inline edits and surfaces the PR link', async () => {
    const mutateAsync = vi.fn().mockResolvedValue({ pr_url: 'https://example.test/pr/99' });
    mockUseAgentsList.mockReturnValue({
      data: [createAgent({ status: 'active', source: 'both' })],
      isLoading: false,
      error: null,
    });
    mockUseAgentsListPaginated.mockReturnValue({ allItems: [createAgent({ status: 'active', source: 'both' })], isLoading: false, isError: false, hasNextPage: false, isFetchingNextPage: false, fetchNextPage: vi.fn(), invalidate: vi.fn() });
    mockUseUpdateAgent.mockReturnValue({
      mutateAsync,
      isPending: false,
    });

    render(<AgentsPanel projectId="PVT_1" />, { wrapper: createWrapper() });
    const user = userEvent.setup();

    await user.click(screen.getAllByRole('button', { name: 'Edit' })[0]);
    await user.clear(screen.getByLabelText('Name'));
    await user.type(screen.getByLabelText('Name'), 'Reviewer Updated');
    await user.click(screen.getByRole('button', { name: 'Save Changes' }));

    await waitFor(() => {
      expect(mutateAsync).toHaveBeenCalledWith({
        agentId: 'agent-1',
        data: {
          name: 'Reviewer Updated',
          system_prompt: 'Review carefully',
          tools: ['read', 'comment'],
        },
      });
    });

    expect(await screen.findByRole('link', { name: 'View Pull Request' })).toHaveAttribute(
      'href',
      'https://example.test/pr/99'
    );
  });

  it('opens the install confirmation dialog for imported agents', async () => {
    mockUseAgentsList.mockReturnValue({
      data: [
        createAgent({
          id: 'imp-1',
          name: 'Catalog Agent',
          slug: 'catalog-agent',
          status: 'imported',
          agent_type: 'imported',
          source: 'local',
          github_pr_number: null,
          branch_name: null,
        }),
      ],
      isLoading: false,
      error: null,
    });
    mockUseAgentsListPaginated.mockReturnValue({
      allItems: [
        createAgent({
          id: 'imp-1',
          name: 'Catalog Agent',
          slug: 'catalog-agent',
          status: 'imported',
          agent_type: 'imported',
          source: 'local',
          github_pr_number: null,
          branch_name: null,
        }),
      ],
      isLoading: false,
      isError: false,
      hasNextPage: false,
      isFetchingNextPage: false,
      fetchNextPage: vi.fn(),
      invalidate: vi.fn(),
    });

    render(<AgentsPanel projectId="PVT_1" owner="octo" repo="widgets" />, {
      wrapper: createWrapper(),
    });
    const user = userEvent.setup();

    await user.click(screen.getByRole('button', { name: 'Add to repo' }));

    expect(screen.getByRole('heading', { name: 'Install Agent to Repository' })).toBeInTheDocument();
    expect(screen.getByText('octo/widgets')).toBeInTheDocument();
    expect(screen.getByText('.github/agents/catalog-agent.agent.md')).toBeInTheDocument();
  });
});
