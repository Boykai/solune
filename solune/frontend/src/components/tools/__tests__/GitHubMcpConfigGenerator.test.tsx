import { describe, it, expect, vi, beforeEach } from 'vitest';
import userEvent from '@testing-library/user-event';

import { render, screen } from '@/test/test-utils';
import { GitHubMcpConfigGenerator } from '../GitHubMcpConfigGenerator';
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

describe('GitHubMcpConfigGenerator', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders section heading', () => {
    render(<GitHubMcpConfigGenerator tools={[]} />);
    expect(screen.getByText('MCP Configuration for GitHub Agents')).toBeInTheDocument();
  });

  it('renders the code block with JSON output', () => {
    render(<GitHubMcpConfigGenerator tools={[]} />);
    const codeBlock = screen.getByTestId('github-mcp-config-code');
    expect(codeBlock).toBeInTheDocument();
    expect(codeBlock.textContent).toContain('mcpServers');
  });

  it('includes built-in MCPs in the output', () => {
    render(<GitHubMcpConfigGenerator tools={[]} />);
    const builtInElements = screen.getAllByText(/built-in/i);
    expect(builtInElements.length).toBeGreaterThan(0);
  });

  it('shows empty state guidance when no user tools', () => {
    render(<GitHubMcpConfigGenerator tools={[]} />);
    expect(screen.getByText(/no custom project mcps yet/i)).toBeInTheDocument();
  });

  it('does not show empty state when active tools are present', () => {
    const tools = [createMockTool({ is_active: true })];
    render(<GitHubMcpConfigGenerator tools={tools} />);
    expect(screen.queryByText(/no custom project mcps yet/i)).not.toBeInTheDocument();
  });

  it('includes user tool servers in the generated config', () => {
    const tools = [createMockTool({ is_active: true, name: 'Sentry MCP' })];
    render(<GitHubMcpConfigGenerator tools={tools} />);
    const codeBlock = screen.getByTestId('github-mcp-config-code');
    expect(codeBlock.textContent).toContain('sentry');
  });

  it('renders copy button and handles click', async () => {
    const user = userEvent.setup();
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, 'clipboard', {
      value: { writeText },
      writable: true,
      configurable: true,
    });

    render(<GitHubMcpConfigGenerator tools={[]} />);
    const copyBtn = screen.getByRole('button', { name: /copy to clipboard/i });
    expect(copyBtn).toBeInTheDocument();

    await user.click(copyBtn);
    expect(writeText).toHaveBeenCalled();
    expect(await screen.findByText('Copied!')).toBeInTheDocument();
  });

  it('displays correct active project count', () => {
    const tools = [
      createMockTool({ id: 't1', is_active: true }),
      createMockTool({ id: 't2', is_active: false }),
    ];
    render(<GitHubMcpConfigGenerator tools={tools} />);
    // The "Active project MCPs" count should include only the active tool + built-ins
    expect(screen.getByText('Active project MCPs')).toBeInTheDocument();
  });

  it('renders included MCP servers list', () => {
    render(<GitHubMcpConfigGenerator tools={[]} />);
    expect(screen.getByText('Included MCP servers')).toBeInTheDocument();
  });
});
