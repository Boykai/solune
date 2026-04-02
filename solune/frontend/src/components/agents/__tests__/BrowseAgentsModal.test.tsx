import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@/test/test-utils';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import userEvent from '@testing-library/user-event';
import type { ReactNode } from 'react';
import { ApiError } from '@/services/api';
import { BrowseAgentsModal } from '../BrowseAgentsModal';

const mockUseCatalogAgents = vi.fn();
const mockUseImportAgent = vi.fn();

vi.mock('@/hooks/useAgents', () => ({
  useCatalogAgents: (...args: unknown[]) => mockUseCatalogAgents(...args),
  useImportAgent: (...args: unknown[]) => mockUseImportAgent(...args),
}));

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
}

const catalogAgents = [
  { id: 'agent-a', name: 'Agent Alpha', description: 'Helps with alpha tasks', source_url: 'https://example.com/a.md', already_imported: false },
  { id: 'agent-b', name: 'Agent Beta', description: 'Helps with beta tasks', source_url: 'https://example.com/b.md', already_imported: true },
];

describe('BrowseAgentsModal', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseCatalogAgents.mockReturnValue({
      data: catalogAgents,
      error: null,
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    });
    mockUseImportAgent.mockReturnValue({
      mutateAsync: vi.fn().mockResolvedValue(undefined),
      isPending: false,
    });
  });

  it('does not render when closed', () => {
    const { container } = render(
      <BrowseAgentsModal projectId="proj-1" isOpen={false} onClose={vi.fn()} />,
      { wrapper: createWrapper() },
    );
    expect(container.firstChild).toBeNull();
  });

  it('renders catalog agents when open', () => {
    render(
      <BrowseAgentsModal projectId="proj-1" isOpen={true} onClose={vi.fn()} />,
      { wrapper: createWrapper() },
    );
    expect(screen.getByText('Agent Alpha')).toBeInTheDocument();
    expect(screen.getByText('Agent Beta')).toBeInTheDocument();
  });

  it('uses the shared opaque dialog shell styling', () => {
    render(
      <BrowseAgentsModal projectId="proj-1" isOpen={true} onClose={vi.fn()} />,
      { wrapper: createWrapper() },
    );

    const dialog = screen.getByRole('dialog');
    const overlay = dialog.parentElement?.parentElement;

    expect(dialog).toHaveClass('celestial-panel', 'bg-card', 'border-border/80', 'overflow-hidden');
    expect(overlay).toHaveClass('bg-background/80', 'backdrop-blur-sm');
  });

  it('shows imported badge for already-imported agents', () => {
    render(
      <BrowseAgentsModal projectId="proj-1" isOpen={true} onClose={vi.fn()} />,
      { wrapper: createWrapper() },
    );
    expect(screen.getByText('Imported')).toBeInTheDocument();
  });

  it('shows import button for non-imported agents', () => {
    render(
      <BrowseAgentsModal projectId="proj-1" isOpen={true} onClose={vi.fn()} />,
      { wrapper: createWrapper() },
    );
    expect(screen.getByText('Import')).toBeInTheDocument();
  });

  it('imports the selected catalog agent with its snapshot metadata', async () => {
    const user = userEvent.setup();
    const mutateAsync = vi.fn().mockResolvedValue(undefined);
    mockUseImportAgent.mockReturnValue({
      mutateAsync,
      isPending: false,
    });

    render(
      <BrowseAgentsModal projectId="proj-1" isOpen={true} onClose={vi.fn()} />,
      { wrapper: createWrapper() },
    );

    await user.click(screen.getByRole('button', { name: 'Import' }));

    await waitFor(() => {
      expect(mutateAsync).toHaveBeenCalledWith({
        catalog_agent_id: 'agent-a',
        name: 'Agent Alpha',
        description: 'Helps with alpha tasks',
        source_url: 'https://example.com/a.md',
      });
    });
  });

  it('filters agents by search query', async () => {
    const user = userEvent.setup();
    render(
      <BrowseAgentsModal projectId="proj-1" isOpen={true} onClose={vi.fn()} />,
      { wrapper: createWrapper() },
    );

    const searchInput = screen.getByPlaceholderText('Search agents…');
    await user.type(searchInput, 'Alpha');

    await waitFor(() => {
      expect(screen.getByText('Agent Alpha')).toBeInTheDocument();
      expect(screen.queryByText('Agent Beta')).not.toBeInTheDocument();
    });
  });

  it('shows loading state', () => {
    mockUseCatalogAgents.mockReturnValue({
      data: undefined,
      error: null,
      isLoading: true,
      isError: false,
      refetch: vi.fn(),
    });
    render(
      <BrowseAgentsModal projectId="proj-1" isOpen={true} onClose={vi.fn()} />,
      { wrapper: createWrapper() },
    );
    expect(screen.getByText('Loading catalog…')).toBeInTheDocument();
  });

  it('shows warning-style empty state when the catalog is unavailable', () => {
    mockUseCatalogAgents.mockReturnValue({
      data: undefined,
      error: new ApiError(503, {
        error: 'Browser Agents catalog is temporarily unavailable.',
        details: { reason: 'The Awesome Copilot catalog timed out. Retry in a moment.' },
      }),
      isLoading: false,
      isError: true,
      refetch: vi.fn(),
    });
    render(
      <BrowseAgentsModal projectId="proj-1" isOpen={true} onClose={vi.fn()} />,
      { wrapper: createWrapper() },
    );
    expect(
      screen.getByText('Browser Agents catalog is temporarily unavailable.'),
    ).toBeInTheDocument();
    expect(
      screen.getByText('Browser Agents is showing an empty catalog until the upstream source responds again.'),
    ).toBeInTheDocument();
    expect(
      screen.getByText('The Awesome Copilot catalog timed out. Retry in a moment.'),
    ).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Retry' })).toBeInTheDocument();
  });

  it('retries catalog loading from the warning state', async () => {
    const user = userEvent.setup();
    const refetch = vi.fn();
    mockUseCatalogAgents.mockReturnValue({
      data: undefined,
      error: new ApiError(503, {
        error: 'Browser Agents catalog is temporarily unavailable.',
      }),
      isLoading: false,
      isError: true,
      refetch,
    });

    render(
      <BrowseAgentsModal projectId="proj-1" isOpen={true} onClose={vi.fn()} />,
      { wrapper: createWrapper() },
    );

    await user.click(screen.getByRole('button', { name: 'Retry' }));

    expect(refetch).toHaveBeenCalledTimes(1);
  });

  it('calls onClose when Done button is clicked', async () => {
    const onClose = vi.fn();
    const user = userEvent.setup();
    render(
      <BrowseAgentsModal projectId="proj-1" isOpen={true} onClose={onClose} />,
      { wrapper: createWrapper() },
    );

    await user.click(screen.getByText('Done'));
    expect(onClose).toHaveBeenCalled();
  });
});
