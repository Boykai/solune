import { describe, it, expect, vi } from 'vitest';
import userEvent from '@testing-library/user-event';

import { render, screen } from '@/test/test-utils';
import { ConfirmChoreModal } from '../ConfirmChoreModal';

describe('ConfirmChoreModal', () => {
  it('walks through the two-step confirmation flow', async () => {
    const user = userEvent.setup();
    const onConfirm = vi.fn();

    render(
      <ConfirmChoreModal
        isOpen={true}
        choreName="Bug Bash"
        isLoading={false}
        onConfirm={onConfirm}
        onCancel={vi.fn()}
      />,
    );

    expect(screen.getByText(/add chore to repository/i)).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /i understand, continue/i }));
    expect(screen.getByText(/confirm chore creation/i)).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /yes, create chore/i }));

    expect(onConfirm).toHaveBeenCalledOnce();
  });

  it('resets to step one when reopened', async () => {
    const user = userEvent.setup();
    const { rerender } = render(
      <ConfirmChoreModal
        isOpen={true}
        choreName="Bug Bash"
        isLoading={false}
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />,
    );

    await user.click(screen.getByRole('button', { name: /i understand, continue/i }));
    expect(screen.getByText(/confirm chore creation/i)).toBeInTheDocument();

    rerender(
      <ConfirmChoreModal
        isOpen={false}
        choreName="Bug Bash"
        isLoading={false}
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />,
    );
    rerender(
      <ConfirmChoreModal
        isOpen={true}
        choreName="Bug Bash"
        isLoading={false}
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />,
    );

    expect(screen.getByText(/add chore to repository/i)).toBeInTheDocument();
  });
});
