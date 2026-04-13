import { describe, expect, it, vi } from 'vitest';
import { fireEvent } from '@testing-library/react';
import { render, screen } from '@/test/test-utils';
import { ChatInterface } from './ChatInterface';
import type { ChatMessage } from '@/types';

// ── Mock sub-components ──

vi.mock('./MessageBubble', () => ({
  MessageBubble: ({
    message,
    isStreaming,
    streamError,
  }: {
    message: ChatMessage;
    isStreaming?: boolean;
    streamError?: string | null;
  }) => (
    <div data-testid="message-bubble">
      {message.content}
      {isStreaming ? ' [streaming]' : ''}
      {streamError ? ` [${streamError}]` : ''}
    </div>
  ),
}));

vi.mock('./SystemMessage', () => ({
  SystemMessage: ({ message }: { message: ChatMessage }) => (
    <div data-testid="system-message">{message.content}</div>
  ),
}));

vi.mock('./CommandAutocomplete', () => ({
  CommandAutocomplete: () => <div data-testid="command-autocomplete" />,
}));

vi.mock('./MentionAutocomplete', () => ({
  MentionAutocomplete: () => <div data-testid="mention-autocomplete" />,
}));

vi.mock('./MentionInput', () => ({
  MentionInput: vi.fn().mockImplementation(
    ({ value, onChange, placeholder }: { value: string; onChange: (v: string) => void; placeholder?: string }) => (
      <input
        data-testid="mention-input"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
      />
    )
  ),
}));

vi.mock('./PipelineIndicator', () => ({
  PipelineIndicator: () => <div data-testid="pipeline-indicator" />,
}));

vi.mock('./TaskPreview', () => ({
  TaskPreview: () => <div data-testid="task-preview" />,
}));

vi.mock('./StatusChangePreview', () => ({
  StatusChangePreview: () => <div data-testid="status-change-preview" />,
}));

vi.mock('./IssueRecommendationPreview', () => ({
  IssueRecommendationPreview: () => <div data-testid="issue-recommendation-preview" />,
}));

vi.mock('./PlanPreview', () => ({
  PlanPreview: () => <div data-testid="plan-preview" />,
}));

vi.mock('./ChatToolbar', () => ({
  ChatToolbar: () => <div data-testid="chat-toolbar" />,
}));

vi.mock('./FilePreviewChips', () => ({
  FilePreviewChips: () => <div data-testid="file-preview-chips" />,
}));

vi.mock('./PipelineWarningBanner', () => ({
  PipelineWarningBanner: () => <div data-testid="pipeline-warning-banner" />,
}));

vi.mock('@/components/ui/tooltip', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/components/ui/tooltip')>();
  return {
    ...actual,
    Tooltip: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  };
});

// ── Mock hooks ──

vi.mock('@/hooks/useCommands', () => ({
  useCommands: () => ({
    isCommand: vi.fn(() => false),
    getFilteredCommands: vi.fn(() => []),
  }),
}));

vi.mock('@/hooks/useChatHistory', () => ({
  useChatHistory: () => ({
    addToHistory: vi.fn(),
    navigateUp: vi.fn(() => null),
    navigateDown: vi.fn(() => null),
    isNavigating: false,
    resetNavigation: vi.fn(),
    history: [],
    selectFromHistory: vi.fn(),
  }),
}));

vi.mock('@/hooks/useCyclingPlaceholder', () => ({
  useCyclingPlaceholder: vi.fn(() => 'Ask me anything…'),
}));

vi.mock('@/hooks/useFileUpload', () => ({
  useFileUpload: () => ({
    files: [],
    errors: [],
    addFiles: vi.fn(),
    removeFile: vi.fn(),
    uploadAll: vi.fn(async () => []),
    clearAll: vi.fn(),
  }),
}));

vi.mock('@/hooks/useVoiceInput', () => ({
  useVoiceInput: () => ({
    isRecording: false,
    isSupported: false,
    startRecording: vi.fn(),
    stopRecording: vi.fn(),
  }),
}));

vi.mock('@/hooks/useMentionAutocomplete', () => ({
  useMentionAutocomplete: () => ({
    isAutocompleteOpen: false,
    clearTokens: vi.fn(),
    handleMentionDismiss: vi.fn(),
    handleMentionTrigger: vi.fn(),
    suggestions: [],
    selectedIndex: 0,
    selectSuggestion: vi.fn(),
    activePipelineId: undefined,
  }),
}));

vi.mock('@/hooks/useSelectedPipeline', () => ({
  useSelectedPipeline: () => ({
    pipelineId: '',
    pipelineName: '',
    isLoading: false,
    hasAssignment: false,
  }),
}));

// ── Helpers ──

function createMessage(overrides: Partial<ChatMessage> = {}): ChatMessage {
  return {
    message_id: 'msg-1',
    session_id: 'session-1',
    sender_type: 'user',
    content: 'Hello world',
    timestamp: new Date().toISOString(),
    ...overrides,
  };
}

function renderChat(overrides: Partial<React.ComponentProps<typeof ChatInterface>> = {}) {
  const defaultProps: React.ComponentProps<typeof ChatInterface> = {
    messages: [],
    pendingProposals: new Map(),
    pendingStatusChanges: new Map(),
    pendingRecommendations: new Map(),
    isSending: false,
    onSendMessage: vi.fn(),
    onRetryMessage: vi.fn(),
    onConfirmProposal: vi.fn(),
    onConfirmStatusChange: vi.fn(),
    onConfirmRecommendation: vi.fn(),
    onRejectProposal: vi.fn(),
    onRejectRecommendation: vi.fn(),
    onNewChat: vi.fn(),
    ...overrides,
  };

  return render(<ChatInterface {...defaultProps} />);
}

// ── Tests ──

describe('ChatInterface', () => {
  const scrollTo = vi.fn(function scrollTo(
    this: HTMLElement,
    options?: number | ScrollToOptions,
  ) {
    if (typeof options === 'number') {
      this.scrollTop = options;
      return;
    }

    if (options?.top != null) {
      this.scrollTop = options.top;
    }
  });

  Object.defineProperty(HTMLElement.prototype, 'scrollTo', {
    configurable: true,
    value: scrollTo,
  });

  it('renders the New Chat button when messages exist', () => {
    renderChat({ messages: [createMessage()] });

    expect(screen.getByText('New Chat')).toBeInTheDocument();
  });

  it('renders messages in the message list', () => {
    const messages = [
      createMessage({ message_id: 'msg-1', content: 'First message' }),
      createMessage({ message_id: 'msg-2', content: 'Second message', sender_type: 'assistant' }),
    ];

    renderChat({ messages });

    expect(screen.getByText('First message')).toBeInTheDocument();
    expect(screen.getByText('Second message')).toBeInTheDocument();
  });

  it('shows the empty state when no messages are present', () => {
    renderChat();

    expect(screen.getByText('Start a conversation')).toBeInTheDocument();
  });

  it('renders a plan preview without duplicating the raw assistant bubble', () => {
    renderChat({
      messages: [
        createMessage({
          sender_type: 'assistant',
          content: 'Done! I created the parent issue and launched the pipeline.',
          action_type: 'plan_create',
          action_data: {
            plan_id: 'plan-1',
            title: 'Plan title',
            summary: 'Plan summary',
            status: 'draft',
            project_id: 'PVT_1',
            project_name: 'Roadmap',
            repo_owner: 'octocat',
            repo_name: 'hello-world',
            steps: [],
          },
        }),
      ],
    });

    expect(screen.getByTestId('plan-preview')).toBeInTheDocument();
    expect(
      screen.queryByText('Done! I created the parent issue and launched the pipeline.')
    ).not.toBeInTheDocument();
    expect(screen.queryByTestId('message-bubble')).not.toBeInTheDocument();
  });

  it('calls onNewChat when the New Chat button is clicked', () => {
    const onNewChat = vi.fn();
    renderChat({ onNewChat, messages: [createMessage()] });

    fireEvent.click(screen.getByText('New Chat'));

    expect(onNewChat).toHaveBeenCalledOnce();
  });

  it('renders transient streaming content before the final message arrives', () => {
    renderChat({
      messages: [createMessage({ content: 'User prompt' })],
      isStreaming: true,
      streamingContent: 'Assistant is typing',
    });

    expect(screen.getByText('Assistant is typing [streaming]')).toBeInTheDocument();
  });

  it('keeps partial streaming content visible when the stream errors', () => {
    renderChat({
      messages: [createMessage({ content: 'User prompt' })],
      streamingContent: 'Partial answer',
      streamingError: 'Stream error',
    });

    expect(screen.getByText('Partial answer [Stream error]')).toBeInTheDocument();
  });

  it('pauses auto-follow when the user scrolls away from the bottom', () => {
    scrollTo.mockClear();
    const baseMessages = [createMessage({ content: 'User prompt' })];

    const { rerender } = renderChat({
      messages: baseMessages,
      streamingContent: 'First token',
    });

    const viewport = screen.getByTestId('chat-messages-viewport');
    Object.defineProperty(viewport, 'scrollHeight', { configurable: true, value: 400 });
    Object.defineProperty(viewport, 'clientHeight', { configurable: true, value: 100 });
    Object.defineProperty(viewport, 'scrollTop', { configurable: true, value: 200, writable: true });

    fireEvent.scroll(viewport);
    scrollTo.mockClear();

    rerender(
      <ChatInterface
        messages={baseMessages}
        pendingProposals={new Map()}
        pendingStatusChanges={new Map()}
        pendingRecommendations={new Map()}
        isSending={false}
        streamingContent="Second token"
        onSendMessage={vi.fn()}
        onRetryMessage={vi.fn()}
        onConfirmProposal={vi.fn()}
        onConfirmStatusChange={vi.fn()}
        onConfirmRecommendation={vi.fn()}
        onRejectProposal={vi.fn()}
        onRejectRecommendation={vi.fn()}
        onNewChat={vi.fn()}
      />
    );

    expect(scrollTo).not.toHaveBeenCalled();
  });

  it('resumes auto-follow after the user scrolls back to the bottom', () => {
    scrollTo.mockClear();
    const baseMessages = [createMessage({ content: 'User prompt' })];

    const { rerender } = renderChat({
      messages: baseMessages,
      streamingContent: 'First token',
    });

    const viewport = screen.getByTestId('chat-messages-viewport');
    Object.defineProperty(viewport, 'scrollHeight', { configurable: true, value: 400 });
    Object.defineProperty(viewport, 'clientHeight', { configurable: true, value: 100 });
    Object.defineProperty(viewport, 'scrollTop', { configurable: true, value: 200, writable: true });

    fireEvent.scroll(viewport);
    scrollTo.mockClear();

    viewport.scrollTop = 300;
    fireEvent.scroll(viewport);

    rerender(
      <ChatInterface
        messages={baseMessages}
        pendingProposals={new Map()}
        pendingStatusChanges={new Map()}
        pendingRecommendations={new Map()}
        isSending={false}
        streamingContent="Second token"
        onSendMessage={vi.fn()}
        onRetryMessage={vi.fn()}
        onConfirmProposal={vi.fn()}
        onConfirmStatusChange={vi.fn()}
        onConfirmRecommendation={vi.fn()}
        onRejectProposal={vi.fn()}
        onRejectRecommendation={vi.fn()}
        onNewChat={vi.fn()}
      />
    );

    expect(scrollTo).toHaveBeenCalled();
  });
});
