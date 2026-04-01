import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@/test/test-utils';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import userEvent from '@testing-library/user-event';
import type { ReactNode } from 'react';
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
      isLoading: false,
      isError: false,
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
      isLoading: true,
      isError: false,
    });
    render(
      <BrowseAgentsModal projectId="proj-1" isOpen={true} onClose={vi.fn()} />,
      { wrapper: createWrapper() },
    );
    expect(screen.getByText('Loading catalog…')).toBeInTheDocument();
  });

  it('shows error state', () => {
    mockUseCatalogAgents.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
    });
    render(
      <BrowseAgentsModal projectId="proj-1" isOpen={true} onClose={vi.fn()} />,
      { wrapper: createWrapper() },
    );
    expect(screen.getByText('Failed to load catalog. Please try again.')).toBeInTheDocument();
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
