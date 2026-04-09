import { describe, it, expect, vi, beforeEach } from 'vitest';
import userEvent from '@testing-library/user-event';

import { render, screen } from '@/test/test-utils';
import { ToolCard } from '../ToolCard';
import type { McpToolConfig } from '@/types';

function createMockTool(overrides: Partial<McpToolConfig> = {}): McpToolConfig {
  return {
    id: 'tool-1',
    name: 'Sentry MCP',
    description: 'Error tracking integration',
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

describe('ToolCard', () => {
  const onEdit = vi.fn();
  const onSync = vi.fn();
  const onDelete = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders tool name and description', () => {
    const tool = createMockTool();
    render(
      <ToolCard tool={tool} onEdit={onEdit} onSync={onSync} onDelete={onDelete} />,
    );
    expect(screen.getByText('Sentry MCP')).toBeInTheDocument();
    expect(screen.getByText('Error tracking integration')).toBeInTheDocument();
  });

  it('displays the sync status badge', () => {
    const tool = createMockTool({ sync_status: 'synced' });
    render(
      <ToolCard tool={tool} onEdit={onEdit} onSync={onSync} onDelete={onDelete} />,
    );
    expect(screen.getByText('Synced to GitHub')).toBeInTheDocument();
  });

  it('displays the sync error badge and error message when status is error', () => {
    const tool = createMockTool({ sync_status: 'error', sync_error: 'Auth failed' });
    render(
      <ToolCard tool={tool} onEdit={onEdit} onSync={onSync} onDelete={onDelete} />,
    );
    expect(screen.getByText('Sync Error')).toBeInTheDocument();
    expect(screen.getByText('Auth failed')).toBeInTheDocument();
  });

  it('renders github repo target when present', () => {
    const tool = createMockTool({ github_repo_target: 'acme/project' });
    render(
      <ToolCard tool={tool} onEdit={onEdit} onSync={onSync} onDelete={onDelete} />,
    );
    expect(screen.getByText(/Target: acme\/project/)).toBeInTheDocument();
  });

  it('calls onEdit when edit button is clicked', async () => {
    const user = userEvent.setup();
    const tool = createMockTool();
    render(
      <ToolCard tool={tool} onEdit={onEdit} onSync={onSync} onDelete={onDelete} />,
    );
    await user.click(screen.getByRole('button', { name: /edit tool/i }));
    expect(onEdit).toHaveBeenCalledWith(tool);
  });

  it('calls onSync when re-sync button is clicked', async () => {
    const user = userEvent.setup();
    const tool = createMockTool();
    render(
      <ToolCard tool={tool} onEdit={onEdit} onSync={onSync} onDelete={onDelete} />,
    );
    await user.click(screen.getByRole('button', { name: /re-sync to github/i }));
    expect(onSync).toHaveBeenCalledWith('tool-1');
  });

  it('calls onDelete when delete button is clicked', async () => {
    const user = userEvent.setup();
    const tool = createMockTool();
    render(
      <ToolCard tool={tool} onEdit={onEdit} onSync={onSync} onDelete={onDelete} />,
    );
    await user.click(screen.getByRole('button', { name: /delete tool/i }));
    expect(onDelete).toHaveBeenCalledWith('tool-1');
  });

  it('disables re-sync button when isSyncing is true', () => {
    const tool = createMockTool();
    render(
      <ToolCard tool={tool} onEdit={onEdit} onSync={onSync} onDelete={onDelete} isSyncing />,
    );
    expect(screen.getByRole('button', { name: /re-sync to github/i })).toBeDisabled();
  });

  it('disables delete button when isDeleting is true', () => {
    const tool = createMockTool();
    render(
      <ToolCard tool={tool} onEdit={onEdit} onSync={onSync} onDelete={onDelete} isDeleting />,
    );
    expect(screen.getByRole('button', { name: /delete tool/i })).toBeDisabled();
  });

  it('shows "Created" timestamp when synced_at is null', () => {
    const tool = createMockTool({ synced_at: null });
    render(
      <ToolCard tool={tool} onEdit={onEdit} onSync={onSync} onDelete={onDelete} />,
    );
    expect(screen.getByText(/Created/)).toBeInTheDocument();
  });
});
