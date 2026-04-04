import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@/test/test-utils';
import userEvent from '@testing-library/user-event';

import { PipelineToolbar } from './PipelineToolbar';

function renderToolbar(overrides: Partial<React.ComponentProps<typeof PipelineToolbar>> = {}) {
  const props: React.ComponentProps<typeof PipelineToolbar> = {
    boardState: 'creating',
    isDirty: true,
    isSaving: false,
    isPreset: false,
    pipelineName: 'Delivery Flow',
    validationErrors: {},
    onSave: vi.fn(),
    onSaveAsCopy: vi.fn(),
    onDelete: vi.fn(),
    onDiscard: vi.fn(),
    ...overrides,
  };

  return {
    ...render(<PipelineToolbar {...props} />),
    props,
  };
}

describe('PipelineToolbar', () => {
  it('disables save when validation errors are present', async () => {
    const user = userEvent.setup();
    const { props } = renderToolbar({
      validationErrors: { name: 'Name is required' },
    });

    const saveButton = screen.getByRole('button', { name: 'Save, 1 validation error' });
    expect(saveButton).toBeDisabled();
    expect(screen.getByText('1')).toBeInTheDocument();

    await user.click(saveButton);
    expect(props.onSave).not.toHaveBeenCalled();
  });

  it('saves when no validation errors exist', async () => {
    const user = userEvent.setup();
    const { props } = renderToolbar();

    await user.click(screen.getByRole('button', { name: /^save$/i }));

    expect(props.onSave).toHaveBeenCalledTimes(1);
  });

  it('disables save as copy for preset pipelines with validation errors', () => {
    renderToolbar({
      boardState: 'editing',
      isPreset: true,
      validationErrors: { stages: 'At least one stage is required' },
    });

    expect(
      screen.getByRole('button', { name: 'Save as Copy, 1 validation error' })
    ).toBeDisabled();
  });

  it('submits a trimmed save-as-copy name', async () => {
    const user = userEvent.setup();
    const { props } = renderToolbar({
      boardState: 'editing',
      isPreset: true,
      validationErrors: {},
    });

    await user.click(screen.getByRole('button', { name: /save as copy/i }));

    const input = screen.getByPlaceholderText('New pipeline name');
    await user.clear(input);
    await user.type(input, '  Mission Control Copy  ');
    await user.click(screen.getByRole('button', { name: /^save$/i }));

    expect(props.onSaveAsCopy).toHaveBeenCalledWith('Mission Control Copy');
  });
});