import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@/test/test-utils';
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

vi.mock('@/hooks/useConversations', () => ({
  useConversations: () => ({
    conversations: [
      { conversation_id: 'conv-1', title: 'Chat 1', session_id: 's1', created_at: '', updated_at: '' },
    ],
    createConversation: vi.fn().mockResolvedValue({
      conversation_id: 'conv-new',
      title: 'New Chat',
      session_id: 's1',
      created_at: '',
      updated_at: '',
    }),
    deleteConversation: vi.fn().mockResolvedValue(undefined),
    isCreating: false,
  }),
}));

vi.mock('@/hooks/useChatPanels', () => ({
  useChatPanels: () => ({
    panels: [
      { panelId: 'p1', conversationId: 'conv-1', widthPercent: 100 },
    ],
    addPanel: vi.fn(),
    removePanel: vi.fn(),
    resizePanels: vi.fn(),
    updatePanelConversation: vi.fn(),
    containerRef: { current: null },
    minWidthPx: 320,
  }),
}));

vi.mock('@/hooks/useMediaQuery', () => ({
  useMediaQuery: () => false, // desktop by default
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
});
