import { describe, expect, it, vi, beforeEach } from 'vitest';
import { render, screen, userEvent, waitFor } from '@/test/test-utils';
import { AgentChatFlow } from '../AgentChatFlow';

const mockMutate = vi.fn();
const mockUseAgentChat = vi.fn();

vi.mock('@/hooks/useAgents', () => ({
  useAgentChat: (...args: unknown[]) => mockUseAgentChat(...args),
}));

describe('AgentChatFlow', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAgentChat.mockReturnValue({
      mutate: mockMutate,
      isPending: false,
      error: null,
    });
  });

  it('auto-sends the initial message on mount', () => {
    render(
      <AgentChatFlow
        projectId="proj-1"
        initialMessage="Help me refine this agent"
        agentName="Planner"
        onAgentReady={vi.fn()}
        onCancel={vi.fn()}
      />,
    );

    expect(mockUseAgentChat).toHaveBeenCalledWith('proj-1');
    expect(mockMutate).toHaveBeenCalledWith(
      { message: 'Help me refine this agent', session_id: null },
      expect.objectContaining({ onSuccess: expect.any(Function) }),
    );
    expect(screen.getByText('Help me refine this agent')).toBeInTheDocument();
  });

  it('sends on Enter but not on Shift+Enter', async () => {
    const user = userEvent.setup();
    mockMutate.mockImplementation((_payload, options) => {
      options?.onSuccess?.({
        reply: 'Need more detail',
        session_id: 'session-1',
        is_complete: false,
        preview: null,
      });
    });

    render(
      <AgentChatFlow
        projectId="proj-1"
        initialMessage="Initial"
        agentName="Planner"
        onAgentReady={vi.fn()}
        onCancel={vi.fn()}
      />,
    );

    const input = screen.getByRole('textbox', { name: /agent creation chat input/i });
    await user.type(input, 'Follow-up');
    await user.keyboard('{Shift>}{Enter}{/Shift}');
    expect(mockMutate).toHaveBeenCalledTimes(1);

    await user.keyboard('{Enter}');

    await waitFor(() => expect(mockMutate).toHaveBeenCalledTimes(2));
    expect(mockMutate).toHaveBeenLastCalledWith(
      { message: 'Follow-up', session_id: 'session-1' },
      expect.objectContaining({ onSuccess: expect.any(Function) }),
    );
  });

  it('disables the input and send button while a request is pending', () => {
    mockUseAgentChat.mockReturnValue({
      mutate: mockMutate,
      isPending: true,
      error: null,
    });

    render(
      <AgentChatFlow
        projectId="proj-1"
        initialMessage="Initial"
        agentName="Planner"
        onAgentReady={vi.fn()}
        onCancel={vi.fn()}
      />,
    );

    expect(screen.getByRole('textbox', { name: /agent creation chat input/i })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Send' })).toBeDisabled();
    expect(screen.getByText('Thinking…')).toBeInTheDocument();
  });

  it('shows the current mutation error to the user', () => {
    mockUseAgentChat.mockReturnValue({
      mutate: mockMutate,
      isPending: false,
      error: new Error('Agent chat failed'),
    });

    render(
      <AgentChatFlow
        projectId="proj-1"
        initialMessage="Initial"
        agentName="Planner"
        onAgentReady={vi.fn()}
        onCancel={vi.fn()}
      />,
    );

    expect(screen.getByRole('alert')).toHaveTextContent('Agent chat failed');
  });
});
