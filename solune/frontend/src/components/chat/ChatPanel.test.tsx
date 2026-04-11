import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@/test/test-utils';
import { ChatPanel } from './ChatPanel';

// Mock heavy dependencies
vi.mock('./ChatInterface', () => ({
  ChatInterface: (props: { onSendMessage: () => void }) => (
    <div data-testid="chat-interface">
      <button onClick={props.onSendMessage}>Send</button>
    </div>
  ),
}));

vi.mock('@/hooks/useChat', () => ({
  useChat: () => ({
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
  }),
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

vi.mock('@/hooks/useConversations', () => ({
  useConversations: () => ({
    conversations: [],
    updateConversation: vi.fn(),
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
});
