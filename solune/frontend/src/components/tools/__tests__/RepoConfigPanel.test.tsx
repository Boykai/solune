import { describe, it, expect, vi, beforeEach } from 'vitest';
import userEvent from '@testing-library/user-event';

import { render, screen } from '@/test/test-utils';
import { RepoConfigPanel } from '../RepoConfigPanel';
import type { RepoMcpConfigResponse, RepoMcpServerConfig } from '@/types';

function createMockServer(overrides: Partial<RepoMcpServerConfig> = {}): RepoMcpServerConfig {
  return {
    name: 'sentry',
    config: { type: 'http', url: 'https://mcp.sentry.io' },
    source_paths: ['.copilot/mcp.json'],
    ...overrides,
  };
}

function createMockRepoConfig(
  overrides: Partial<RepoMcpConfigResponse> = {},
): RepoMcpConfigResponse {
  return {
    paths_checked: ['.copilot/mcp.json', '.vscode/mcp.json'],
    available_paths: ['.copilot/mcp.json'],
    primary_path: '.copilot/mcp.json',
    servers: [],
    ...overrides,
  };
}

describe('RepoConfigPanel', () => {
  const onRefresh = vi.fn();
  const onEdit = vi.fn();
  const onDelete = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the section heading', () => {
    render(
      <RepoConfigPanel
        repoConfig={null}
        isLoading={false}
        error={null}
        onRefresh={onRefresh}
        onEdit={onEdit}
        onDelete={onDelete}
      />,
    );
    expect(screen.getByText('Current repository config')).toBeInTheDocument();
  });

  it('shows loading state', () => {
    render(
      <RepoConfigPanel
        repoConfig={null}
        isLoading={true}
        error={null}
        onRefresh={onRefresh}
        onEdit={onEdit}
        onDelete={onDelete}
      />,
    );
    expect(screen.getByText('Loading repository MCP config')).toBeInTheDocument();
  });

  it('shows error state and calls onRefresh on retry', async () => {
    const user = userEvent.setup();
    render(
      <RepoConfigPanel
        repoConfig={null}
        isLoading={false}
        error="Server error"
        onRefresh={onRefresh}
        onEdit={onEdit}
        onDelete={onDelete}
      />,
    );
    expect(screen.getByText(/could not load repository config/i)).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /retry/i }));
    expect(onRefresh).toHaveBeenCalled();
  });

  it('shows empty state when no servers', () => {
    render(
      <RepoConfigPanel
        repoConfig={createMockRepoConfig({ servers: [] })}
        isLoading={false}
        error={null}
        onRefresh={onRefresh}
        onEdit={onEdit}
        onDelete={onDelete}
      />,
    );
    expect(screen.getByText(/no mcp servers found/i)).toBeInTheDocument();
  });

  it('renders server cards with name and type', () => {
    const server = createMockServer({ name: 'sentry', config: { type: 'http', url: 'https://mcp.sentry.io' } });
    render(
      <RepoConfigPanel
        repoConfig={createMockRepoConfig({ servers: [server] })}
        isLoading={false}
        error={null}
        onRefresh={onRefresh}
        onEdit={onEdit}
        onDelete={onDelete}
      />,
    );
    expect(screen.getByText('sentry')).toBeInTheDocument();
    expect(screen.getByText('http')).toBeInTheDocument();
    expect(screen.getByText('https://mcp.sentry.io')).toBeInTheDocument();
  });

  it('shows "Managed" badge for managed servers', () => {
    const server = createMockServer({ name: 'sentry' });
    render(
      <RepoConfigPanel
        repoConfig={createMockRepoConfig({ servers: [server] })}
        isLoading={false}
        error={null}
        onRefresh={onRefresh}
        onEdit={onEdit}
        onDelete={onDelete}
        managedServerNames={['sentry']}
      />,
    );
    expect(screen.getByText('Managed')).toBeInTheDocument();
  });

  it('shows "Repo only" badge for unmanaged servers', () => {
    const server = createMockServer({ name: 'sentry' });
    render(
      <RepoConfigPanel
        repoConfig={createMockRepoConfig({ servers: [server] })}
        isLoading={false}
        error={null}
        onRefresh={onRefresh}
        onEdit={onEdit}
        onDelete={onDelete}
        managedServerNames={[]}
      />,
    );
    expect(screen.getByText('Repo only')).toBeInTheDocument();
  });

  it('calls onEdit when edit button is clicked', async () => {
    const user = userEvent.setup();
    const server = createMockServer({ name: 'sentry' });
    render(
      <RepoConfigPanel
        repoConfig={createMockRepoConfig({ servers: [server] })}
        isLoading={false}
        error={null}
        onRefresh={onRefresh}
        onEdit={onEdit}
        onDelete={onDelete}
      />,
    );
    await user.click(screen.getByRole('button', { name: /edit repository mcp sentry/i }));
    expect(onEdit).toHaveBeenCalledWith(server);
  });

  it('calls onDelete when delete button is clicked', async () => {
    const user = userEvent.setup();
    const server = createMockServer({ name: 'sentry' });
    render(
      <RepoConfigPanel
        repoConfig={createMockRepoConfig({ servers: [server] })}
        isLoading={false}
        error={null}
        onRefresh={onRefresh}
        onEdit={onEdit}
        onDelete={onDelete}
      />,
    );
    await user.click(screen.getByRole('button', { name: /delete repository mcp sentry/i }));
    expect(onDelete).toHaveBeenCalledWith(server);
  });

  it('disables edit button when editingServerName matches', () => {
    const server = createMockServer({ name: 'sentry' });
    render(
      <RepoConfigPanel
        repoConfig={createMockRepoConfig({ servers: [server] })}
        isLoading={false}
        error={null}
        onRefresh={onRefresh}
        onEdit={onEdit}
        onDelete={onDelete}
        editingServerName="sentry"
      />,
    );
    expect(screen.getByRole('button', { name: /edit repository mcp sentry/i })).toBeDisabled();
  });

  it('calls onRefresh when Refresh button is clicked', async () => {
    const user = userEvent.setup();
    render(
      <RepoConfigPanel
        repoConfig={createMockRepoConfig()}
        isLoading={false}
        error={null}
        onRefresh={onRefresh}
        onEdit={onEdit}
        onDelete={onDelete}
      />,
    );
    await user.click(screen.getByRole('button', { name: /refresh/i }));
    expect(onRefresh).toHaveBeenCalled();
  });
});
