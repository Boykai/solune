import { describe, it, expect, vi } from 'vitest';
import { render, screen, userEvent } from '@/test/test-utils';
import { expectNoA11yViolations } from '@/test/a11y-helpers';

import { UnsavedChangesDialog } from './UnsavedChangesDialog';

describe('UnsavedChangesDialog', () => {
  const defaultProps = {
    isOpen: true,
    onSave: vi.fn(),
    onDiscard: vi.fn(),
    onCancel: vi.fn(),
  };

  it('renders nothing when not open', () => {
    const { container } = render(<UnsavedChangesDialog {...defaultProps} isOpen={false} />);
    expect(container.innerHTML).toBe('');
  });

  it('renders dialog content when open', () => {
    render(<UnsavedChangesDialog {...defaultProps} />);
    expect(screen.getByText('Unsaved Changes')).toBeInTheDocument();
  });

  it('shows action description when provided', () => {
    render(<UnsavedChangesDialog {...defaultProps} actionDescription="Navigate away" />);
    expect(screen.getByText(/navigate away/i)).toBeInTheDocument();
  });

  it('calls onSave when Save Changes is clicked', async () => {
    const onSave = vi.fn();
    render(<UnsavedChangesDialog {...defaultProps} onSave={onSave} />);
    const user = userEvent.setup();

    await user.click(screen.getByRole('button', { name: /save changes/i }));

    expect(onSave).toHaveBeenCalledOnce();
  });

  it('calls onDiscard when Discard is clicked', async () => {
    const onDiscard = vi.fn();
    render(<UnsavedChangesDialog {...defaultProps} onDiscard={onDiscard} />);
    const user = userEvent.setup();

    await user.click(screen.getByRole('button', { name: /discard/i }));

    expect(onDiscard).toHaveBeenCalledOnce();
  });

  it('calls onCancel when Cancel is clicked', async () => {
    const onCancel = vi.fn();
    render(<UnsavedChangesDialog {...defaultProps} onCancel={onCancel} />);
    const user = userEvent.setup();

    await user.click(screen.getByRole('button', { name: /^cancel$/i }));

    expect(onCancel).toHaveBeenCalledOnce();
  });

  it('has no accessibility violations', async () => {
    const { container } = render(<UnsavedChangesDialog {...defaultProps} />);
    await expectNoA11yViolations(container);
  });
});
