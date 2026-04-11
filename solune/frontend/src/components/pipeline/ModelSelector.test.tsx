/**
 * Tests for ModelSelector component.
 *
 * Covers: default trigger label, model list in popover, selection callback,
 * empty search state, auto option, and custom trigger label.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, userEvent, waitFor } from '@/test/test-utils';
import { ModelSelector } from './ModelSelector';

vi.mock('@/hooks/useModels', () => ({
  useModels: vi.fn(() => ({
    models: [
      { id: 'gpt-4o', name: 'GPT-4o', provider: 'openai', context_window_size: 128000, cost_tier: 'standard' },
      { id: 'claude-3', name: 'Claude 3', provider: 'anthropic', context_window_size: 200000, cost_tier: 'premium' },
    ],
    modelsByProvider: [
      { provider: 'openai', models: [{ id: 'gpt-4o', name: 'GPT-4o', provider: 'openai', context_window_size: 128000, cost_tier: 'standard' }] },
      { provider: 'anthropic', models: [{ id: 'claude-3', name: 'Claude 3', provider: 'anthropic', context_window_size: 200000, cost_tier: 'premium' }] },
    ],
    isLoading: false,
    isRefreshing: false,
    refreshModels: vi.fn(),
  })),
  formatReasoningLabel: vi.fn((level: string) => level.toUpperCase()),
}));

describe('ModelSelector', () => {
  it('renders "Select model" when no model selected', () => {
    render(
      <ModelSelector selectedModelId={null} onSelect={vi.fn()} />,
    );
    expect(screen.getByText('Select model')).toBeInTheDocument();
  });

  it('shows model names in popover when opened', async () => {
    render(
      <ModelSelector selectedModelId={null} onSelect={vi.fn()} />,
    );

    const user = userEvent.setup();
    await user.click(screen.getByText('Select model'));

    await waitFor(() => {
      expect(screen.getByText('GPT-4o')).toBeInTheDocument();
      expect(screen.getByText('Claude 3')).toBeInTheDocument();
    });
  });

  it('calls onSelect with model details on selection', async () => {
    const onSelect = vi.fn();
    render(
      <ModelSelector selectedModelId={null} onSelect={onSelect} />,
    );

    const user = userEvent.setup();
    await user.click(screen.getByText('Select model'));

    await waitFor(() => {
      expect(screen.getByText('GPT-4o')).toBeInTheDocument();
    });

    await user.click(screen.getByText('GPT-4o'));
    expect(onSelect).toHaveBeenCalledWith('gpt-4o', 'GPT-4o', undefined);
  });

  it('shows "No models found" when search matches nothing', async () => {
    render(
      <ModelSelector selectedModelId={null} onSelect={vi.fn()} />,
    );

    const user = userEvent.setup();
    await user.click(screen.getByText('Select model'));

    await waitFor(() => {
      expect(screen.getByPlaceholderText('Search models...')).toBeInTheDocument();
    });

    await user.type(screen.getByPlaceholderText('Search models...'), 'xyznonexistent');

    await waitFor(() => {
      expect(screen.getByText('No models found')).toBeInTheDocument();
    });
  });

  it('shows auto option when allowAuto is true', async () => {
    render(
      <ModelSelector
        selectedModelId={null}
        onSelect={vi.fn()}
        allowAuto={true}
        autoLabel="Auto"
      />,
    );

    const user = userEvent.setup();
    await user.click(screen.getByText('Auto'));

    await waitFor(() => {
      expect(screen.getByText("Use the agent's configured default model")).toBeInTheDocument();
    });
  });

  it('shows custom trigger label when provided', () => {
    render(
      <ModelSelector
        selectedModelId="gpt-4o"
        selectedModelName="GPT-4o"
        onSelect={vi.fn()}
      />,
    );
    expect(screen.getByText('GPT-4o')).toBeInTheDocument();
  });
});
