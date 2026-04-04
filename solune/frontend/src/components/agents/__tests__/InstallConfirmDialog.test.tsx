import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@/test/test-utils';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import userEvent from '@testing-library/user-event';
import type { ReactNode } from 'react';
import { InstallConfirmDialog } from '../InstallConfirmDialog';
import type { AgentConfig } from '@/services/api';

const mockUseInstallAgent = vi.fn();

vi.mock('@/hooks/useAgents', () => ({
  useInstallAgent: (...args: unknown[]) => mockUseInstallAgent(...args),
}));

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
}

function createImportedAgent(overrides: Partial<AgentConfig> = {}): AgentConfig {
  return {
    id: 'imp-1',
    name: 'Test Agent',
    slug: 'test-agent',
    description: 'A test agent',
    icon_name: null,
    system_prompt: '',
    default_model_id: '',
    default_model_name: '',
    status: 'imported',
    tools: [],
    status_column: null,
    github_issue_number: null,
    github_pr_number: null,
    branch_name: null,
    source: 'local',
    created_at: '2026-03-01T00:00:00Z',
    agent_type: 'imported',
    catalog_source_url: 'https://example.com/agent.md',
    catalog_agent_id: 'test-agent',
    imported_at: '2026-03-01T00:00:00Z',
    ...overrides,
  };
}

describe('InstallConfirmDialog', () => {
  const mockMutateAsync = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    mockMutateAsync.mockResolvedValue(undefined);
    mockUseInstallAgent.mockReturnValue({
      mutateAsync: mockMutateAsync,
      isPending: false,
    });
  });

  it('does not render when closed', () => {
    const { container } = render(
      <InstallConfirmDialog
        agent={createImportedAgent()}
        projectId="proj-1"
        isOpen={false}
        onClose={vi.fn()}
      />,
      { wrapper: createWrapper() },
    );
    expect(container.firstChild).toBeNull();
  });

  it('renders agent details when open', () => {
    render(
      <InstallConfirmDialog
        agent={createImportedAgent()}
        projectId="proj-1"
        owner="octo"
        repo="widgets"
        isOpen={true}
        onClose={vi.fn()}
      />,
      { wrapper: createWrapper() },
    );

    expect(screen.getByText('Install Agent to Repository')).toBeInTheDocument();
    expect(screen.getByText('Test Agent')).toBeInTheDocument();
    expect(screen.getByText('octo/widgets')).toBeInTheDocument();
    expect(screen.getByText('.github/agents/test-agent.agent.md')).toBeInTheDocument();
    expect(screen.getByText('.github/prompts/test-agent.prompt.md')).toBeInTheDocument();
  });

  it('uses the shared opaque dialog shell styling', () => {
    render(
      <InstallConfirmDialog
        agent={createImportedAgent()}
        projectId="proj-1"
        isOpen={true}
        onClose={vi.fn()}
      />,
      { wrapper: createWrapper() },
    );

    const dialog = screen.getByRole('alertdialog', { name: /install agent to repository/i });
    const overlay = Array.from(document.body.querySelectorAll('div')).find(
      (element) =>
        element.className.includes('bg-background/80') &&
        element.className.includes('backdrop-blur-sm') &&
        element.className.includes('z-[var(--z-install-confirm)]'),
    );

    expect(dialog).toHaveClass('celestial-panel', 'bg-card', 'border-border/80', 'overflow-hidden');
    expect(overlay).toBeTruthy();
  });

  it('closes when Escape is pressed', async () => {
    const onClose = vi.fn();
    const user = userEvent.setup();

    render(
      <InstallConfirmDialog
        agent={createImportedAgent()}
        projectId="proj-1"
        isOpen={true}
        onClose={onClose}
      />,
      { wrapper: createWrapper() },
    );

    await user.keyboard('{Escape}');

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('calls install API when Install button is clicked', async () => {
    const onClose = vi.fn();
    const user = userEvent.setup();

    render(
      <InstallConfirmDialog
        agent={createImportedAgent()}
        projectId="proj-1"
        isOpen={true}
        onClose={onClose}
      />,
      { wrapper: createWrapper() },
    );

    await user.click(screen.getByText('Install'));
    await waitFor(() => {
      expect(mockMutateAsync).toHaveBeenCalledWith('imp-1');
      expect(onClose).toHaveBeenCalled();
    });
  });

  it('shows error when install fails', async () => {
    mockMutateAsync.mockRejectedValue(new Error('GitHub API error'));
    const user = userEvent.setup();

    render(
      <InstallConfirmDialog
        agent={createImportedAgent()}
        projectId="proj-1"
        isOpen={true}
        onClose={vi.fn()}
      />,
      { wrapper: createWrapper() },
    );

    await user.click(screen.getByText('Install'));
    await waitFor(() => {
      expect(screen.getByText('GitHub API error')).toBeInTheDocument();
    });
  });

  it('clears a previous install error when the dialog is reopened', async () => {
    mockMutateAsync.mockRejectedValue(new Error('GitHub API error'));
    const user = userEvent.setup();
    const onClose = vi.fn();

    const { rerender } = render(
      <InstallConfirmDialog
        agent={createImportedAgent()}
        projectId="proj-1"
        isOpen={true}
        onClose={onClose}
      />,
      { wrapper: createWrapper() },
    );

    await user.click(screen.getByText('Install'));
    await waitFor(() => {
      expect(screen.getByText('GitHub API error')).toBeInTheDocument();
    });

    await user.click(screen.getByText('Cancel'));

    await waitFor(() => {
      expect(onClose).toHaveBeenCalledTimes(1);
      expect(screen.queryByText('GitHub API error')).not.toBeInTheDocument();
    });

    rerender(
      <InstallConfirmDialog
        agent={createImportedAgent()}
        projectId="proj-1"
        isOpen={false}
        onClose={onClose}
      />,
    );

    rerender(
      <InstallConfirmDialog
        agent={createImportedAgent()}
        projectId="proj-1"
        isOpen={true}
        onClose={onClose}
      />,
    );

    expect(screen.queryByText('GitHub API error')).not.toBeInTheDocument();
  });

  it('calls onClose when Cancel button is clicked', async () => {
    const onClose = vi.fn();
    const user = userEvent.setup();

    render(
      <InstallConfirmDialog
        agent={createImportedAgent()}
        projectId="proj-1"
        isOpen={true}
        onClose={onClose}
      />,
      { wrapper: createWrapper() },
    );

    await user.click(screen.getByText('Cancel'));
    expect(onClose).toHaveBeenCalled();
  });
});
