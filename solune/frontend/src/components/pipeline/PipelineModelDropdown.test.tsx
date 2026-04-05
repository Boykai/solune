import { describe, expect, it, vi } from 'vitest';
import { fireEvent } from '@testing-library/react';
import { render, screen, userEvent } from '@/test/test-utils';
import { PipelineModelDropdown } from './PipelineModelDropdown';
import type { AIModel, PipelineModelOverride } from '@/types';

const models: AIModel[] = [
  { id: 'gpt-4o', name: 'GPT-4o', provider: 'copilot' },
  { id: 'o3-mini', name: 'o3-mini', provider: 'azure' },
];

const currentOverride: PipelineModelOverride = {
  mode: 'auto',
  modelId: '',
  modelName: '',
};

describe('PipelineModelDropdown', () => {
  it('opens and closes the menu from the trigger button', async () => {
    const user = userEvent.setup();
    render(
      <PipelineModelDropdown
        models={models}
        currentOverride={currentOverride}
        onModelChange={vi.fn()}
      />,
    );

    const trigger = screen.getByRole('button', { name: /auto/i });
    expect(screen.queryByText('GPT-4o')).not.toBeInTheDocument();
    await user.click(trigger);
    expect(screen.getByText('GPT-4o')).toBeInTheDocument();

    await user.click(trigger);
    expect(screen.queryByText('GPT-4o')).not.toBeInTheDocument();
  });

  it('calls onModelChange when a specific model is selected', async () => {
    const onModelChange = vi.fn();
    const user = userEvent.setup();

    render(
      <PipelineModelDropdown
        models={models}
        currentOverride={currentOverride}
        onModelChange={onModelChange}
      />,
    );

    await user.click(screen.getByRole('button', { name: /auto/i }));
    await user.click(screen.getByRole('button', { name: 'GPT-4o' }));

    expect(onModelChange).toHaveBeenCalledWith({
      mode: 'specific',
      modelId: 'gpt-4o',
      modelName: 'GPT-4o',
      reasoningEffort: undefined,
    });
  });

  it('closes when clicking outside the dropdown', async () => {
    const user = userEvent.setup();
    render(
      <div>
        <PipelineModelDropdown
          models={models}
          currentOverride={currentOverride}
          onModelChange={vi.fn()}
        />
        <button type="button">outside</button>
      </div>,
    );

    await user.click(screen.getByRole('button', { name: /auto/i }));
    expect(screen.getByText('GPT-4o')).toBeInTheDocument();

    fireEvent.mouseDown(screen.getByRole('button', { name: 'outside' }));
    expect(screen.queryByText('GPT-4o')).not.toBeInTheDocument();
  });
});
