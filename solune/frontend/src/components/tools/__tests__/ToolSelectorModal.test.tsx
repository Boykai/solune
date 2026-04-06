import { describe, it, expect, vi, beforeEach } from 'vitest';
import userEvent from '@testing-library/user-event';

import { render, screen, waitFor } from '@/test/test-utils';
import { ToolSelectorModal } from '../ToolSelectorModal';

const mockUseToolsList = vi.fn();

vi.mock('@/hooks/useTools', () => ({
  useToolsList: (...args: unknown[]) => mockUseToolsList(...args),
}));

const tools = [
  { id: 'tool-1', name: 'Read', description: 'Read files' },
  { id: 'tool-2', name: 'Lint', description: 'Run linting' },
];

describe('ToolSelectorModal', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseToolsList.mockReturnValue({ tools, isLoading: false });
  });

  it('preserves search across unrelated rerenders but resets on reopen', async () => {
    const user = userEvent.setup();
    const onConfirm = vi.fn();
    const { rerender } = render(
      <ToolSelectorModal
        isOpen={true}
        onClose={vi.fn()}
        onConfirm={onConfirm}
        initialSelectedIds={['tool-1']}
        projectId="proj-1"
      />,
    );

    const input = screen.getByPlaceholderText(/search tools/i);
    await user.type(input, 'lint');
    expect(input).toHaveValue('lint');

    rerender(
      <ToolSelectorModal
        isOpen={true}
        onClose={vi.fn()}
        onConfirm={onConfirm}
        initialSelectedIds={['tool-1']}
        projectId="proj-1"
      />,
    );

    expect(screen.getByPlaceholderText(/search tools/i)).toHaveValue('lint');

    rerender(
      <ToolSelectorModal
        isOpen={false}
        onClose={vi.fn()}
        onConfirm={onConfirm}
        initialSelectedIds={['tool-1']}
        projectId="proj-1"
      />,
    );
    rerender(
      <ToolSelectorModal
        isOpen={true}
        onClose={vi.fn()}
        onConfirm={onConfirm}
        initialSelectedIds={['tool-1']}
        projectId="proj-1"
      />,
    );

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/search tools/i)).toHaveValue('');
    });
  });

  it('returns the selected tool ids on confirm', async () => {
    const user = userEvent.setup();
    const onConfirm = vi.fn();

    render(
      <ToolSelectorModal
        isOpen={true}
        onClose={vi.fn()}
        onConfirm={onConfirm}
        initialSelectedIds={['tool-1']}
        projectId="proj-1"
      />,
    );

    await user.click(screen.getByRole('button', { name: /lint/i }));
    await user.click(screen.getByRole('button', { name: 'Confirm' }));

    expect(onConfirm).toHaveBeenCalledWith(expect.arrayContaining(['tool-1', 'tool-2']));
  });
});
