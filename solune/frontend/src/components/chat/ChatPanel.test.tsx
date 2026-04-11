import { describe, expect, it, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@/test/test-utils';
import { ChatPanel } from './ChatPanel';

// Mock heavy dependencies
vi.mock('./ChatInterface', () => ({
  ChatInterface: (props: { onSendMessage: () => void }) => (
    <div data-testid="chat-interface">
      <button onClick={props.onSendMessage}>Send</button>
    </div>
  ),
}));

const mockUseChat = vi.fn();
vi.mock('@/hooks/useChat', () => ({
  useChat: (...args: unknown[]) => {
    mockUseChat(...args);
    return {
      messages: [],
      pendingProposals: new Map(),
      pendingStatusChanges: new Map(),
      pendingRecommendations: new Map(),
      isSending: false,
      isStreaming: false,
      streamingContent: '',
      streamingError: null,
      sendMessage: vi.fn(),
      retryMessage: vi.fn(),
      confirmProposal: vi.fn(),
      confirmStatusChange: vi.fn(),
      rejectProposal: vi.fn(),
      updateRecommendationStatus: vi.fn(),
      clearChat: vi.fn(),
    };
  },
}));

vi.mock('@/hooks/usePlan', () => ({
  usePlan: () => ({
    isPlanMode: false,
    setIsPlanMode: vi.fn(),
    activePlan: null,
    setActivePlan: vi.fn(),
    thinkingPhase: null,
    setThinkingPhase: vi.fn(),
    thinkingDetail: '',
    setThinkingDetail: vi.fn(),
    clearThinking: vi.fn(),
    approveMutation: { mutateAsync: vi.fn(), data: null, isPending: false, error: null },
    exitMutation: { mutateAsync: vi.fn() },
  }),
}));

vi.mock('@/hooks/useWorkflow', () => ({
  useWorkflow: () => ({
    confirmRecommendation: vi.fn().mockResolvedValue({ success: true }),
    rejectRecommendation: vi.fn(),
  }),
}));

const mockUpdateConversation = vi.fn().mockResolvedValue(undefined);
vi.mock('@/hooks/useConversations', () => ({
  useConversations: () => ({
    conversations: [],
    updateConversation: mockUpdateConversation,
    createConversation: vi.fn(),
    deleteConversation: vi.fn(),
  }),
}));

vi.mock('@/hooks/useAuth', () => ({
  useAuth: () => ({ user: { selected_project_id: 'proj-1' } }),
}));

vi.mock('@/hooks/useProjects', () => ({
  useProjects: () => ({ selectedProject: { project_id: 'proj-1' } }),
}));

describe('ChatPanel', () => {
  it('renders with a title', () => {
    render(
      <ChatPanel conversationId="conv-1" title="Test Chat" onClose={vi.fn()} />,
    );
    expect(screen.getByText('Test Chat')).toBeInTheDocument();
  });

  it('renders ChatInterface', () => {
    render(
      <ChatPanel conversationId="conv-1" title="My Chat" onClose={vi.fn()} />,
    );
    expect(screen.getByTestId('chat-interface')).toBeInTheDocument();
  });

  it('renders close button when showClose is true', () => {
    render(
      <ChatPanel conversationId="conv-1" title="Chat" onClose={vi.fn()} showClose />,
    );
    expect(screen.getByLabelText('Close chat panel')).toBeInTheDocument();
  });

  it('hides close button when showClose is false', () => {
    render(
      <ChatPanel conversationId="conv-1" title="Chat" onClose={vi.fn()} showClose={false} />,
    );
    expect(screen.queryByLabelText('Close chat panel')).not.toBeInTheDocument();
  });

  it('calls onClose when close button is clicked', async () => {
    const onClose = vi.fn();
    const { userEvent } = await import('@/test/test-utils');
    render(
      <ChatPanel conversationId="conv-1" title="Chat" onClose={onClose} />,
    );
    await userEvent.click(screen.getByLabelText('Close chat panel'));
    expect(onClose).toHaveBeenCalled();
  });

  it('has data-testid for panel', () => {
    render(
      <ChatPanel conversationId="conv-1" title="Chat" onClose={vi.fn()} />,
    );
    expect(screen.getByTestId('chat-panel')).toBeInTheDocument();
  });

  it('passes conversationId to useChat', () => {
    mockUseChat.mockClear();
    render(
      <ChatPanel conversationId="conv-abc" title="Chat" onClose={vi.fn()} />,
    );
    expect(mockUseChat).toHaveBeenCalledWith(
      expect.objectContaining({ conversationId: 'conv-abc' }),
    );
  });

  it('enters title editing mode when title is clicked', async () => {
    const { userEvent } = await import('@/test/test-utils');
    render(
      <ChatPanel conversationId="conv-1" title="My Title" onClose={vi.fn()} />,
    );

    // Click on the title to enter edit mode
    await userEvent.click(screen.getByLabelText('Edit conversation title'));

    // Should show an input with the title value
    const input = screen.getByLabelText('Edit conversation title') as HTMLInputElement;
    expect(input.tagName).toBe('INPUT');
    expect(input.value).toBe('My Title');
  });

  it('saves title on Enter key and calls updateConversation', async () => {
    mockUpdateConversation.mockClear();
    const { userEvent } = await import('@/test/test-utils');
    render(
      <ChatPanel conversationId="conv-1" title="Old Title" onClose={vi.fn()} />,
    );

    // Enter edit mode
    await userEvent.click(screen.getByLabelText('Edit conversation title'));

    // Type new title
    const input = screen.getByLabelText('Edit conversation title') as HTMLInputElement;
    await userEvent.clear(input);
    await userEvent.type(input, 'New Title{Enter}');

    await waitFor(() => {
      expect(mockUpdateConversation).toHaveBeenCalledWith('conv-1', 'New Title');
    });
  });

  it('reverts title on Escape key without saving', async () => {
    mockUpdateConversation.mockClear();
    const { userEvent } = await import('@/test/test-utils');
    render(
      <ChatPanel conversationId="conv-1" title="Original" onClose={vi.fn()} />,
    );

    // Enter edit mode
    await userEvent.click(screen.getByLabelText('Edit conversation title'));

    // Type something then press Escape
    const input = screen.getByLabelText('Edit conversation title') as HTMLInputElement;
    await userEvent.clear(input);
    await userEvent.type(input, 'Something Else{Escape}');

    // Should NOT call updateConversation
    expect(mockUpdateConversation).not.toHaveBeenCalled();
    // Should show original title
    expect(screen.getByText('Original')).toBeInTheDocument();
  });

  it('does not call updateConversation when title is unchanged', async () => {
    mockUpdateConversation.mockClear();
    const { userEvent } = await import('@/test/test-utils');
    render(
      <ChatPanel conversationId="conv-1" title="Same Title" onClose={vi.fn()} />,
    );

    // Enter edit mode and press Enter without changing
    await userEvent.click(screen.getByLabelText('Edit conversation title'));
    const input = screen.getByLabelText('Edit conversation title');
    fireEvent.keyDown(input, { key: 'Enter' });

    await waitFor(() => {
      expect(mockUpdateConversation).not.toHaveBeenCalled();
    });
  });
});
