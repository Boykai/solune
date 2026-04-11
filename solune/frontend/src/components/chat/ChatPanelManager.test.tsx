import { describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@/test/test-utils';
import { ChatPanelManager } from './ChatPanelManager';

// Mock ChatPanel to avoid wiring up all nested dependencies
vi.mock('./ChatPanel', () => ({
  ChatPanel: ({ title, onClose }: { title: string; onClose: () => void }) => (
    <div data-testid="chat-panel">
      <span>{title}</span>
      <button onClick={onClose} aria-label="close">Close</button>
    </div>
  ),
}));

const mockCreateConversation = vi.fn().mockResolvedValue({
  conversation_id: 'conv-new',
  title: 'New Chat',
  session_id: 's1',
  created_at: '',
  updated_at: '',
});
const mockDeleteConversation = vi.fn().mockResolvedValue(undefined);
const mockAddPanel = vi.fn();
const mockRemovePanel = vi.fn();

vi.mock('@/hooks/useConversations', () => ({
  useConversations: () => ({
    conversations: [
      { conversation_id: 'conv-1', title: 'Chat 1', session_id: 's1', created_at: '', updated_at: '' },
    ],
    createConversation: mockCreateConversation,
    deleteConversation: mockDeleteConversation,
    isCreating: false,
  }),
}));

vi.mock('@/hooks/useChatPanels', () => ({
  useChatPanels: () => ({
    panels: [
      { panelId: 'p1', conversationId: 'conv-1', widthPercent: 100 },
    ],
    addPanel: mockAddPanel,
    removePanel: mockRemovePanel,
    resizePanels: vi.fn(),
    updatePanelConversation: vi.fn(),
    containerRef: { current: null },
    minWidthPx: 320,
  }),
}));

const mockIsMobile = false;
vi.mock('@/hooks/useMediaQuery', () => ({
  useMediaQuery: () => mockIsMobile,
}));

describe('ChatPanelManager', () => {
  it('renders the panel manager container', () => {
    render(<ChatPanelManager />);
    expect(screen.getByTestId('chat-panel-manager')).toBeInTheDocument();
  });

  it('renders a chat panel by default', () => {
    render(<ChatPanelManager />);
    expect(screen.getByTestId('chat-panel')).toBeInTheDocument();
  });

  it('renders an "Add new chat" button', () => {
    render(<ChatPanelManager />);
    expect(screen.getByLabelText('Add new chat')).toBeInTheDocument();
  });

  it('renders panel title from conversations', () => {
    render(<ChatPanelManager />);
    expect(screen.getByText('Chat 1')).toBeInTheDocument();
  });

  it('calls createConversation and addPanel when add button is clicked', async () => {
    mockCreateConversation.mockClear();
    mockAddPanel.mockClear();
    const { userEvent } = await import('@/test/test-utils');

    render(<ChatPanelManager />);
    await userEvent.click(screen.getByLabelText('Add new chat'));

    await waitFor(() => {
      expect(mockCreateConversation).toHaveBeenCalledWith('New Chat');
    });
    await waitFor(() => {
      expect(mockAddPanel).toHaveBeenCalledWith('conv-new');
    });
  });

  it('calls removePanel and deleteConversation when panel close is clicked', async () => {
    mockRemovePanel.mockClear();
    mockDeleteConversation.mockClear();
    const { userEvent } = await import('@/test/test-utils');

    render(<ChatPanelManager />);
    await userEvent.click(screen.getByLabelText('close'));

    await waitFor(() => {
      expect(mockRemovePanel).toHaveBeenCalledWith('p1');
    });
    await waitFor(() => {
      expect(mockDeleteConversation).toHaveBeenCalledWith('conv-1');
    });
  });

  it('does not render resize handle with a single panel in desktop mode', () => {
    render(<ChatPanelManager />);
    // With single panel, no resize handle should appear
    expect(screen.queryByLabelText('Resize panels')).not.toBeInTheDocument();
  });
});
