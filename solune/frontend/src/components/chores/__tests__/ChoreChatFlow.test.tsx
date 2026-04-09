import { describe, it, expect, vi, beforeEach } from 'vitest';
import userEvent from '@testing-library/user-event';

import { render, screen } from '@/test/test-utils';
import { ChoreChatFlow } from '../ChoreChatFlow';

const mockMutate = vi.fn();

vi.mock('@/hooks/useChores', () => ({
  useChoreChat: () => ({
    mutate: mockMutate,
    isPending: false,
  }),
}));

function defaultProps() {
  return {
    projectId: 'proj-1',
    initialMessage: 'Create a weekly cleanup chore',
    choreName: 'Weekly Cleanup',
    onTemplateReady: vi.fn(),
    onCancel: vi.fn(),
  };
}

describe('ChoreChatFlow', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the chat heading with the chore name', () => {
    render(<ChoreChatFlow {...defaultProps()} />);

    expect(
      screen.getByText((_content, el) =>
        el?.textContent === 'Building template for \u201cWeekly Cleanup\u201d')
    ).toBeInTheDocument();
  });

  it('renders the initial user message', () => {
    render(<ChoreChatFlow {...defaultProps()} />);

    expect(screen.getByText('Create a weekly cleanup chore')).toBeInTheDocument();
  });

  it('sends initial message on mount via chatMutation', () => {
    render(<ChoreChatFlow {...defaultProps()} />);

    expect(mockMutate).toHaveBeenCalledTimes(1);
    expect(mockMutate).toHaveBeenCalledWith(
      { content: 'Create a weekly cleanup chore', conversation_id: null, ai_enhance: true },
      expect.objectContaining({ onSuccess: expect.any(Function) })
    );
  });

  it('renders send button and chat input', () => {
    render(<ChoreChatFlow {...defaultProps()} />);

    expect(screen.getByRole('button', { name: /send/i })).toBeInTheDocument();
    expect(screen.getByRole('textbox', { name: /chore template chat input/i })).toBeInTheDocument();
  });

  it('disables send button when input is empty', () => {
    render(<ChoreChatFlow {...defaultProps()} />);

    expect(screen.getByRole('button', { name: /send/i })).toBeDisabled();
  });

  it('sends user message when send button is clicked', async () => {
    const user = userEvent.setup();
    render(<ChoreChatFlow {...defaultProps()} />);

    // Clear the initial mount call
    mockMutate.mockClear();

    const input = screen.getByRole('textbox', { name: /chore template chat input/i });
    await user.type(input, 'Add a title field');
    await user.click(screen.getByRole('button', { name: /send/i }));

    expect(mockMutate).toHaveBeenCalledWith(
      expect.objectContaining({ content: 'Add a title field' }),
      expect.any(Object)
    );
  });

  it('calls onCancel when cancel button is clicked', async () => {
    const user = userEvent.setup();
    const props = defaultProps();
    render(<ChoreChatFlow {...props} />);

    await user.click(screen.getByRole('button', { name: /cancel/i }));

    expect(props.onCancel).toHaveBeenCalledTimes(1);
  });

  it('shows AI metadata notice when aiEnhance is false', () => {
    render(<ChoreChatFlow {...defaultProps()} aiEnhance={false} />);

    expect(
      screen.getByText(/your input will be used as the template body/i)
    ).toBeInTheDocument();
  });

  it('does not show AI metadata notice when aiEnhance is true', () => {
    render(<ChoreChatFlow {...defaultProps()} aiEnhance={true} />);

    expect(
      screen.queryByText(/your input will be used as the template body/i)
    ).not.toBeInTheDocument();
  });

  it('shows template preview when template is ready', () => {
    // Simulate template ready response
    mockMutate.mockImplementation((_payload: unknown, opts: { onSuccess: (data: unknown) => void }) => {
      opts.onSuccess({
        conversation_id: 'conv-1',
        message: 'Here is your template',
        template_ready: true,
        template_content: '# Weekly Cleanup\n\n- [ ] Task 1',
      });
    });

    const props = defaultProps();
    render(<ChoreChatFlow {...props} />);

    expect(screen.getByText('Template Preview')).toBeInTheDocument();
    expect(screen.getByText(/# Weekly Cleanup/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /use this template/i })).toBeInTheDocument();
  });

  it('calls onTemplateReady when Use This Template is clicked', async () => {
    const user = userEvent.setup();
    mockMutate.mockImplementation((_payload: unknown, opts: { onSuccess: (data: unknown) => void }) => {
      opts.onSuccess({
        conversation_id: 'conv-1',
        message: 'Done',
        template_ready: true,
        template_content: '# Template',
      });
    });

    const props = defaultProps();
    render(<ChoreChatFlow {...props} />);

    await user.click(screen.getByRole('button', { name: /use this template/i }));

    expect(props.onTemplateReady).toHaveBeenCalledWith('# Template');
  });
});
