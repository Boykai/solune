import { describe, expect, it, vi } from 'vitest';
import { fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { render, screen } from '@/test/test-utils';
import { PipelineToolbar } from './PipelineToolbar';
import type { PipelineValidationErrors } from '@/types';

// ── Mocks ──

vi.mock('@/hooks/useScrollLock', () => ({
  useScrollLock: vi.fn(),
}));

// ── Helpers ──

const baseProps = {
  boardState: 'creating' as const,
  isDirty: false,
  isSaving: false,
  isPreset: false,
  pipelineName: 'My Pipeline',
  validationErrors: {} as PipelineValidationErrors,
  onSave: vi.fn(),
  onSaveAsCopy: vi.fn(),
  onDelete: vi.fn(),
  onDiscard: vi.fn(),
};

// ── Tests ──

describe('PipelineToolbar', () => {
  it('renders Save, Discard, and Delete buttons', () => {
    render(<PipelineToolbar {...baseProps} />);
    expect(screen.getByText('Save')).toBeInTheDocument();
    expect(screen.getByText('Discard')).toBeInTheDocument();
    expect(screen.getByText('Delete')).toBeInTheDocument();
  });

  it('enables Save when creating', () => {
    render(<PipelineToolbar {...baseProps} boardState="creating" />);
    const saveBtn = screen.getByText('Save').closest('button')!;
    expect(saveBtn).not.toBeDisabled();
  });

  it('enables Save when editing a non-preset', () => {
    render(<PipelineToolbar {...baseProps} boardState="editing" isPreset={false} />);
    const saveBtn = screen.getByText('Save').closest('button')!;
    expect(saveBtn).not.toBeDisabled();
  });

  it('disables Save when saving is in progress', () => {
    render(<PipelineToolbar {...baseProps} isSaving={true} />);
    const saveBtn = screen.getByText('Save').closest('button')!;
    expect(saveBtn).toBeDisabled();
  });

  it('calls onSave when Save button is clicked', () => {
    const onSave = vi.fn();
    render(<PipelineToolbar {...baseProps} onSave={onSave} />);
    fireEvent.click(screen.getByText('Save'));
    expect(onSave).toHaveBeenCalledOnce();
  });

  it('shows validation error count badge', () => {
    const errors = { stage1: ['Missing agent'], stage2: ['Empty name'] } as unknown as PipelineValidationErrors;
    render(<PipelineToolbar {...baseProps} validationErrors={errors} />);
    expect(screen.getByText('2')).toBeInTheDocument();
  });

  it('disables Save when validation errors are present', async () => {
    const user = userEvent.setup();
    const onSave = vi.fn();
    const errors = { stage1: ['Missing agent'] } as unknown as PipelineValidationErrors;

    render(
      <PipelineToolbar
        {...baseProps}
        onSave={onSave}
        validationErrors={errors}
      />
    );

    const saveBtn = screen.getByRole('button', {
      name: 'Save, 1 validation error',
    });

    expect(saveBtn).toBeDisabled();
    await user.click(saveBtn);
    expect(onSave).not.toHaveBeenCalled();
  });

  it('enables Discard when creating and dirty', () => {
    render(<PipelineToolbar {...baseProps} boardState="creating" isDirty={true} />);
    const discardBtn = screen.getByText('Discard').closest('button')!;
    expect(discardBtn).not.toBeDisabled();
  });

  it('disables Discard when not dirty', () => {
    render(<PipelineToolbar {...baseProps} boardState="creating" isDirty={false} />);
    const discardBtn = screen.getByText('Discard').closest('button')!;
    expect(discardBtn).toBeDisabled();
  });

  it('calls onDiscard when Discard is clicked', () => {
    const onDiscard = vi.fn();
    render(<PipelineToolbar {...baseProps} isDirty={true} onDiscard={onDiscard} />);
    fireEvent.click(screen.getByText('Discard'));
    expect(onDiscard).toHaveBeenCalledOnce();
  });

  it('enables Delete when editing non-preset', () => {
    render(<PipelineToolbar {...baseProps} boardState="editing" isPreset={false} />);
    const deleteBtn = screen.getByText('Delete').closest('button')!;
    expect(deleteBtn).not.toBeDisabled();
  });

  it('disables Delete for presets', () => {
    render(<PipelineToolbar {...baseProps} boardState="editing" isPreset={true} />);
    const deleteBtn = screen.getByText('Delete').closest('button')!;
    expect(deleteBtn).toBeDisabled();
  });

  it('calls onDelete when Delete is clicked', () => {
    const onDelete = vi.fn();
    render(<PipelineToolbar {...baseProps} boardState="editing" onDelete={onDelete} />);
    fireEvent.click(screen.getByText('Delete'));
    expect(onDelete).toHaveBeenCalledOnce();
  });

  // ── Preset / Save as Copy ──

  it('shows Save as Copy instead of Save for presets in editing mode', () => {
    render(<PipelineToolbar {...baseProps} boardState="editing" isPreset={true} />);
    expect(screen.getByText('Save as Copy')).toBeInTheDocument();
    expect(screen.queryByText('Save')).not.toBeInTheDocument();
  });

  it('disables Save as Copy for presets with validation errors', () => {
    const errors = { stage1: ['Missing agent'] } as unknown as PipelineValidationErrors;

    render(
      <PipelineToolbar
        {...baseProps}
        boardState="editing"
        isPreset={true}
        validationErrors={errors}
      />
    );

    expect(
      screen.getByRole('button', { name: 'Save as Copy, 1 validation error' })
    ).toBeDisabled();
  });

  it('opens copy dialog when Save as Copy is clicked', () => {
    render(
      <PipelineToolbar
        {...baseProps}
        boardState="editing"
        isPreset={true}
        pipelineName="Default Pipeline"
      />
    );
    fireEvent.click(screen.getByText('Save as Copy'));
    expect(screen.getByPlaceholderText('New pipeline name')).toBeInTheDocument();
    expect(screen.getByDisplayValue('Default Pipeline (Copy)')).toBeInTheDocument();
  });

  it('calls onSaveAsCopy with the entered name', () => {
    const onSaveAsCopy = vi.fn();
    render(
      <PipelineToolbar
        {...baseProps}
        boardState="editing"
        isPreset={true}
        onSaveAsCopy={onSaveAsCopy}
      />
    );
    fireEvent.click(screen.getByText('Save as Copy'));

    const input = screen.getByPlaceholderText('New pipeline name');
    fireEvent.change(input, { target: { value: 'Custom Name' } });

    // Click the Save button inside the dialog
    const dialogSave = screen.getAllByText('Save').find(
      (el) => el.closest('[role="dialog"]')
    )!;
    fireEvent.click(dialogSave);
    expect(onSaveAsCopy).toHaveBeenCalledWith('Custom Name');
  });

  it('submits a trimmed save-as-copy name', async () => {
    const user = userEvent.setup();
    const onSaveAsCopy = vi.fn();

    render(
      <PipelineToolbar
        {...baseProps}
        boardState="editing"
        isPreset={true}
        onSaveAsCopy={onSaveAsCopy}
      />
    );

    await user.click(screen.getByRole('button', { name: /save as copy/i }));

    const input = screen.getByPlaceholderText('New pipeline name');
    await user.clear(input);
    await user.type(input, '  Mission Control Copy  ');
    await user.click(screen.getByRole('button', { name: /^save$/i }));

    expect(onSaveAsCopy).toHaveBeenCalledWith('Mission Control Copy');
  });

  it('closes copy dialog on Cancel', () => {
    render(
      <PipelineToolbar {...baseProps} boardState="editing" isPreset={true} />
    );
    fireEvent.click(screen.getByText('Save as Copy'));
    expect(screen.getByPlaceholderText('New pipeline name')).toBeInTheDocument();

    fireEvent.click(screen.getByText('Cancel'));
    expect(screen.queryByPlaceholderText('New pipeline name')).not.toBeInTheDocument();
  });

  it('disables dialog Save when name is empty', () => {
    render(
      <PipelineToolbar {...baseProps} boardState="editing" isPreset={true} />
    );
    fireEvent.click(screen.getByText('Save as Copy'));

    const input = screen.getByPlaceholderText('New pipeline name');
    fireEvent.change(input, { target: { value: '   ' } });

    const dialogSave = screen.getAllByText('Save').find(
      (el) => el.closest('[role="dialog"]')
    )!;
    expect(dialogSave.closest('button')).toBeDisabled();
  });
});
