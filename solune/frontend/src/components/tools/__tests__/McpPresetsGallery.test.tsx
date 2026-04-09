import { describe, it, expect, vi, beforeEach } from 'vitest';
import userEvent from '@testing-library/user-event';

import { render, screen } from '@/test/test-utils';
import { McpPresetsGallery } from '../McpPresetsGallery';
import { ApiError } from '@/services/api';
import type { McpPreset } from '@/types';

function createMockPreset(overrides: Partial<McpPreset> = {}): McpPreset {
  return {
    id: 'preset-1',
    name: 'Sentry MCP',
    description: 'Sentry error tracking',
    category: 'Observability',
    icon: 'sentry',
    config_content: '{"mcpServers":{"sentry":{"type":"http","url":"https://mcp.sentry.io"}}}',
    ...overrides,
  };
}

describe('McpPresetsGallery', () => {
  const onSelectPreset = vi.fn();
  const onRetry = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders section heading', () => {
    render(
      <McpPresetsGallery
        presets={[]}
        isLoading={false}
        error={null}
        onSelectPreset={onSelectPreset}
      />,
    );
    expect(screen.getByText('Quick-add MCP presets')).toBeInTheDocument();
  });

  it('shows loading state', () => {
    render(
      <McpPresetsGallery
        presets={[]}
        isLoading={true}
        error={null}
        onSelectPreset={onSelectPreset}
      />,
    );
    expect(screen.getByText('Loading presets')).toBeInTheDocument();
  });

  it('shows error state with retry button', async () => {
    const user = userEvent.setup();
    render(
      <McpPresetsGallery
        presets={[]}
        isLoading={false}
        error="Network failure"
        onSelectPreset={onSelectPreset}
        onRetry={onRetry}
      />,
    );
    expect(screen.getByText(/could not load presets/i)).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /retry/i }));
    expect(onRetry).toHaveBeenCalled();
  });

  it('shows rate limit message when rawError is a rate limit error', () => {
    const rawError = new ApiError(429, { error: 'Rate limited' });
    render(
      <McpPresetsGallery
        presets={[]}
        isLoading={false}
        error="Rate limited"
        rawError={rawError}
        onSelectPreset={onSelectPreset}
      />,
    );
    expect(screen.getByText(/rate limit reached/i)).toBeInTheDocument();
  });

  it('shows empty state when no presets', () => {
    render(
      <McpPresetsGallery
        presets={[]}
        isLoading={false}
        error={null}
        onSelectPreset={onSelectPreset}
      />,
    );
    expect(screen.getByText(/no presets available yet/i)).toBeInTheDocument();
  });

  it('renders preset cards and calls onSelectPreset on click', async () => {
    const user = userEvent.setup();
    const presets = [
      createMockPreset({ id: 'p1', name: 'Sentry MCP', category: 'Observability' }),
      createMockPreset({ id: 'p2', name: 'Linear MCP', category: 'Project Management' }),
    ];
    render(
      <McpPresetsGallery
        presets={presets}
        isLoading={false}
        error={null}
        onSelectPreset={onSelectPreset}
      />,
    );
    expect(screen.getByText('Sentry MCP')).toBeInTheDocument();
    expect(screen.getByText('Linear MCP')).toBeInTheDocument();
    expect(screen.getByText('Observability')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /use sentry mcp preset/i }));
    expect(onSelectPreset).toHaveBeenCalledWith(presets[0]);
  });
});
