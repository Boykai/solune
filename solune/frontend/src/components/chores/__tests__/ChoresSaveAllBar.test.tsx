import { describe, it, expect, vi, beforeEach } from 'vitest';
import userEvent from '@testing-library/user-event';

import { render, screen } from '@/test/test-utils';
import { ChoresSaveAllBar } from '../ChoresSaveAllBar';

function defaultProps() {
  return {
    isVisible: true,
    isSaving: false,
    onDiscardAll: vi.fn(),
    onSaveAll: vi.fn(),
  };
}

describe('ChoresSaveAllBar', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders nothing when isVisible is false', () => {
    const { container } = render(<ChoresSaveAllBar {...defaultProps()} isVisible={false} />);

    expect(container.innerHTML).toBe('');
  });

  it('renders the unsaved changes message when visible', () => {
    render(<ChoresSaveAllBar {...defaultProps()} />);

    expect(screen.getByText('You have unsaved changes')).toBeInTheDocument();
  });

  it('renders Discard All and Save All buttons', () => {
    render(<ChoresSaveAllBar {...defaultProps()} />);

    expect(screen.getByRole('button', { name: /discard all/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /save all/i })).toBeInTheDocument();
  });

  it('calls onDiscardAll when Discard All is clicked', async () => {
    const user = userEvent.setup();
    const props = defaultProps();
    render(<ChoresSaveAllBar {...props} />);

    await user.click(screen.getByRole('button', { name: /discard all/i }));

    expect(props.onDiscardAll).toHaveBeenCalledTimes(1);
  });

  it('calls onSaveAll when Save All is clicked', async () => {
    const user = userEvent.setup();
    const props = defaultProps();
    render(<ChoresSaveAllBar {...props} />);

    await user.click(screen.getByRole('button', { name: /save all/i }));

    expect(props.onSaveAll).toHaveBeenCalledTimes(1);
  });

  it('disables buttons when isSaving is true', () => {
    render(<ChoresSaveAllBar {...defaultProps()} isSaving />);

    expect(screen.getByRole('button', { name: /discard all/i })).toBeDisabled();
    expect(screen.getByRole('button', { name: /saving/i })).toBeDisabled();
  });

  it('shows Saving… text when isSaving is true', () => {
    render(<ChoresSaveAllBar {...defaultProps()} isSaving />);

    expect(screen.getByRole('button', { name: /saving/i })).toHaveTextContent('Saving…');
  });

  it('has a status role with polite aria-live', () => {
    render(<ChoresSaveAllBar {...defaultProps()} />);

    const status = screen.getByRole('status');
    expect(status).toHaveAttribute('aria-live', 'polite');
  });
});
