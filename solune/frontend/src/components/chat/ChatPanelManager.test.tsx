import { beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, userEvent, waitFor } from '@/test/test-utils';
import { ChatPanelManager } from './ChatPanelManager';

// Mock ChatPanel to avoid wiring up all nested dependencies
vi.mock('./ChatPanel', () => ({
  ChatPanel: ({
    title,
    onClose,
    showClose = true,
  }: {
    title: string;
    onClose: () => void;
    showClose?: boolean;
  }) => (
    <div data-testid="chat-panel">
      <span>{title}</span>
      {showClose && (
        <button type="button" onClick={onClose} aria-label="close">
          Close
        </button>
      )}
    </div>
  ),
}));

const mockConversationState = vi.hoisted(() => ({
  conversations: [] as Array<{
    conversation_id: string;
    title: string;
    session_id: string;
    created_at: string;
    updated_at: string;
  }>,
  isLoading: false,
  isFetching: false,
  error: null as Error | null,
  createConversation: vi.fn(),
  deleteConversation: vi.fn(),
  refetch: vi.fn(),
}));

const mockChatPanelsState = vi.hoisted(() => ({
  panels: [] as Array<{ panelId: string; conversationId: string; widthPercent: number }>,
  addPanel: vi.fn(),
  removePanel: vi.fn(),
  resizePanels: vi.fn(),
  removeStalePanels: vi.fn(),
  seenInitialConversationIds: [] as Array<string | undefined>,
  containerRef: { current: null as HTMLDivElement | null },
}));

const mockUseMediaQuery = vi.hoisted(() => vi.fn(() => false));

vi.mock('@/hooks/useConversations', () => ({
  useConversations: () => mockConversationState,
}));

vi.mock('@/hooks/useChatPanels', () => ({
  useChatPanels: (initialConversationId?: string) => {
    mockChatPanelsState.seenInitialConversationIds.push(initialConversationId);
    return {
      panels: mockChatPanelsState.panels,
      addPanel: mockChatPanelsState.addPanel,
      removePanel: mockChatPanelsState.removePanel,
      resizePanels: mockChatPanelsState.resizePanels,
      updatePanelConversation: vi.fn(),
      removeStalePanels: mockChatPanelsState.removeStalePanels,
      containerRef: mockChatPanelsState.containerRef,
    };
  },
}));

vi.mock('@/hooks/useMediaQuery', () => ({
  useMediaQuery: mockUseMediaQuery,
}));

function makeConversation(conversationId: string, title = 'New Chat') {
  return {
    conversation_id: conversationId,
    title,
    session_id: 'session-1',
    created_at: '',
    updated_at: '',
  };
}

describe('ChatPanelManager', () => {
  beforeEach(() => {
    cleanup();
    localStorage.clear();
    vi.clearAllMocks();
    mockUseMediaQuery.mockReturnValue(false);
    mockChatPanelsState.panels = [];
    mockChatPanelsState.addPanel.mockReset();
    mockChatPanelsState.removePanel.mockReset();
    mockChatPanelsState.resizePanels.mockReset();
    mockChatPanelsState.removeStalePanels.mockReset();
    mockChatPanelsState.seenInitialConversationIds = [];
    mockConversationState.conversations = [];
    mockConversationState.isLoading = false;
    mockConversationState.isFetching = false;
    mockConversationState.error = null;
    mockConversationState.createConversation.mockReset().mockResolvedValue(makeConversation('conv-new'));
    mockConversationState.deleteConversation.mockReset().mockResolvedValue(undefined);
    mockConversationState.refetch.mockReset().mockResolvedValue(undefined);
  });

  it('hydrates the first panel from an existing conversation', async () => {
    mockConversationState.conversations = [makeConversation('conv-1', 'Chat 1')];

    render(<ChatPanelManager />);

    await waitFor(() => {
      expect(mockChatPanelsState.seenInitialConversationIds).toContain('conv-1');
    });
    expect(mockConversationState.createConversation).not.toHaveBeenCalled();
  });

  it('creates a new conversation when the session is empty', async () => {
    render(<ChatPanelManager />);

    await waitFor(() => {
      expect(mockConversationState.createConversation).toHaveBeenCalledWith('New Chat');
    });
    await waitFor(() => {
      expect(mockChatPanelsState.seenInitialConversationIds).toContain('conv-new');
    });
    expect(screen.getByText('Opening your chat...')).toBeInTheDocument();
  });

  it('does not remove the freshly created initial conversation while conversations refetch', async () => {
    const view = render(<ChatPanelManager />);

    await waitFor(() => {
      expect(mockConversationState.createConversation).toHaveBeenCalledWith('New Chat');
    });
    await waitFor(() => {
      expect(mockChatPanelsState.seenInitialConversationIds).toContain('conv-new');
    });

    mockChatPanelsState.panels = [
      { panelId: 'panel-conv-new', conversationId: 'conv-new', widthPercent: 100 },
    ];

    view.rerender(<ChatPanelManager />);

    expect(mockChatPanelsState.removeStalePanels).not.toHaveBeenCalled();
  });

  it('waits for the conversations refetch before reconciling stale panels', async () => {
    const view = render(<ChatPanelManager />);

    mockChatPanelsState.panels = [
      { panelId: 'panel-conv-2', conversationId: 'conv-2', widthPercent: 100 },
    ];
    mockConversationState.isFetching = true;

    view.rerender(<ChatPanelManager />);

    expect(mockChatPanelsState.removeStalePanels).not.toHaveBeenCalled();

    mockConversationState.isFetching = false;

    view.rerender(<ChatPanelManager />);

    expect(mockChatPanelsState.removeStalePanels).toHaveBeenCalledWith(new Set());
  });

  it('shows a retryable error when loading conversations fails', async () => {
    const user = userEvent.setup();
    mockConversationState.error = new Error('Network down');

    render(<ChatPanelManager />);

    expect(await screen.findByRole('alert')).toBeInTheDocument();
    expect(screen.getByText('Could not start your chat')).toBeInTheDocument();
    expect(screen.getByText('Network down')).toBeInTheDocument();
    expect(mockConversationState.createConversation).not.toHaveBeenCalled();

    await user.click(screen.getByRole('button', { name: /retry/i }));

    expect(mockConversationState.refetch).toHaveBeenCalledOnce();
  });

  it('retries bootstrap when conversation creation fails', async () => {
    const user = userEvent.setup();
    mockConversationState.createConversation
      .mockRejectedValueOnce(new Error('Create failed'))
      .mockResolvedValueOnce(makeConversation('conv-retry'));

    render(<ChatPanelManager />);

    expect(await screen.findByRole('alert')).toBeInTheDocument();
    expect(screen.getByText('Create failed')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /retry/i }));

    await waitFor(() => {
      expect(mockConversationState.createConversation).toHaveBeenCalledTimes(2);
    });
    await waitFor(() => {
      expect(mockChatPanelsState.seenInitialConversationIds).toContain('conv-retry');
    });
    expect(mockConversationState.refetch).toHaveBeenCalledOnce();
    expect(screen.getByText('Opening your chat...')).toBeInTheDocument();
  });

  it('adds a second panel when the add button succeeds', async () => {
    const user = userEvent.setup();
    mockChatPanelsState.panels = [
      { panelId: 'panel-conv-1', conversationId: 'conv-1', widthPercent: 100 },
    ];
    mockConversationState.conversations = [makeConversation('conv-1', 'Chat 1')];
    mockConversationState.createConversation.mockResolvedValueOnce(makeConversation('conv-2', 'Chat 2'));

    render(<ChatPanelManager />);

    expect(screen.getByText('Chat 1')).toBeInTheDocument();

    await user.click(screen.getByLabelText('Add new chat'));

    await waitFor(() => {
      expect(mockConversationState.createConversation).toHaveBeenCalledWith('New Chat');
    });
    expect(mockChatPanelsState.addPanel).toHaveBeenCalledWith('conv-2');
  });
});
