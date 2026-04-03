/**
 * Tests for ChatPopup — verifies resize event listener scoping.
 *
 * The ChatPopup previously registered window-level mousemove/mouseup listeners
 * for the entire component lifetime. This caused unnecessary event processing
 * on every mouse event. The fix scopes these listeners to active resize
 * operations only.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { expectNoA11yViolations } from '@/test/a11y-helpers';
import { ChatPopup } from './ChatPopup';

// Stub ChatInterface to avoid rendering the full chat component tree.
vi.mock('./ChatInterface', () => ({
  ChatInterface: () => <div data-testid="chat-interface">chat</div>,
}));

const defaultProps = {
  messages: [],
  pendingProposals: new Map(),
  pendingStatusChanges: new Map(),
  pendingRecommendations: new Map(),
  isSending: false,
  onSendMessage: vi.fn(),
  onRetryMessage: vi.fn(),
  onConfirmProposal: vi.fn(),
  onConfirmStatusChange: vi.fn(),
  onConfirmRecommendation: vi.fn().mockResolvedValue({ success: true }),
  onRejectProposal: vi.fn(),
  onRejectRecommendation: vi.fn().mockResolvedValue(undefined),
  onNewChat: vi.fn(),
};

describe('ChatPopup — resize listener scoping', () => {
  let addSpy: ReturnType<typeof vi.spyOn>;
  let removeSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    addSpy = vi.spyOn(window, 'addEventListener');
    removeSpy = vi.spyOn(window, 'removeEventListener');
  });

  afterEach(() => {
    addSpy.mockRestore();
    removeSpy.mockRestore();
  });

  it('does not register mousemove/mouseup on window at mount', () => {
    render(<ChatPopup {...defaultProps} />);

    const mousemoveCalls = addSpy.mock.calls.filter(([type]: [string, ...unknown[]]) => type === 'mousemove');
    const mouseupCalls = addSpy.mock.calls.filter(([type]: [string, ...unknown[]]) => type === 'mouseup');
    expect(mousemoveCalls).toHaveLength(0);
    expect(mouseupCalls).toHaveLength(0);
  });

  it('registers mousemove/mouseup on resize start and removes them on mouseup', () => {
    render(<ChatPopup {...defaultProps} />);

    // Open the chat
    fireEvent.click(screen.getByRole('button', { name: 'Open chat' }));

    // Find the resize handle (aria-hidden div with cursor-nw-resize)
    const resizeHandle = document.querySelector('[aria-hidden="true"]')!;
    expect(resizeHandle).toBeTruthy();

    // Start resize
    addSpy.mockClear();
    fireEvent.mouseDown(resizeHandle, { clientX: 100, clientY: 100 });

    const mousemoveCalls = addSpy.mock.calls.filter(([type]: [string, ...unknown[]]) => type === 'mousemove');
    const mouseupCalls = addSpy.mock.calls.filter(([type]: [string, ...unknown[]]) => type === 'mouseup');
    expect(mousemoveCalls).toHaveLength(1);
    expect(mouseupCalls).toHaveLength(1);

    // Simulate mouseup to end resize
    removeSpy.mockClear();
    fireEvent.mouseUp(window);

    const removeMousemoveCalls = removeSpy.mock.calls.filter(([type]: [string, ...unknown[]]) => type === 'mousemove');
    const removeMouseupCalls = removeSpy.mock.calls.filter(([type]: [string, ...unknown[]]) => type === 'mouseup');
    expect(removeMousemoveCalls).toHaveLength(1);
    expect(removeMouseupCalls).toHaveLength(1);
  });

  it('cleans up resize listeners on unmount during active resize', () => {
    const { unmount } = render(<ChatPopup {...defaultProps} />);

    // Open the chat
    fireEvent.click(screen.getByRole('button', { name: 'Open chat' }));

    const resizeHandle = document.querySelector('[aria-hidden="true"]')!;
    fireEvent.mouseDown(resizeHandle, { clientX: 100, clientY: 100 });

    // Unmount while resize is in progress
    removeSpy.mockClear();
    unmount();

    const removeMousemoveCalls = removeSpy.mock.calls.filter(([type]: [string, ...unknown[]]) => type === 'mousemove');
    const removeMouseupCalls = removeSpy.mock.calls.filter(([type]: [string, ...unknown[]]) => type === 'mouseup');
    expect(removeMousemoveCalls).toHaveLength(1);
    expect(removeMouseupCalls).toHaveLength(1);
  });

  it('uses theme-aware launcher icon colors', () => {
    render(<ChatPopup {...defaultProps} />);

    const toggle = screen.getByRole('button', { name: 'Open chat' });
    expect(toggle).toHaveClass('text-white');
    expect(toggle).toHaveClass('dark:text-black');
  });

  it('has no accessibility violations', async () => {
    const { container } = render(<ChatPopup {...defaultProps} />);
    await expectNoA11yViolations(container);
  });
});

describe('ChatPopup — mobile layout', () => {
  let matchMediaSpy: ReturnType<typeof vi.spyOn>;

  function setMobile(isMobile: boolean) {
    matchMediaSpy = vi.spyOn(window, 'matchMedia').mockImplementation(
      (query: string) =>
        ({
          matches: query === '(max-width: 767px)' ? isMobile : false,
          media: query,
          addEventListener: vi.fn(),
          removeEventListener: vi.fn(),
          addListener: vi.fn(),
          removeListener: vi.fn(),
          onchange: null,
          dispatchEvent: vi.fn(),
        }) as unknown as MediaQueryList,
    );
  }

  afterEach(() => {
    matchMediaSpy?.mockRestore();
  });

  it('renders full-screen on mobile (fixed inset-0)', () => {
    setMobile(true);
    render(<ChatPopup {...defaultProps} />);

    // Open the chat
    fireEvent.click(screen.getByRole('button', { name: 'Open chat' }));

    // The chat container should be full-screen on mobile
    const chatContainer = screen.getByTestId('chat-interface').parentElement!;
    expect(chatContainer.className).toContain('fixed');
    expect(chatContainer.className).toContain('inset-0');
    expect(chatContainer.className).toContain('flex-col');
  });

  it('does not show resize handle on mobile', () => {
    setMobile(true);
    render(<ChatPopup {...defaultProps} />);

    fireEvent.click(screen.getByRole('button', { name: 'Open chat' }));

    // Resize handle should not be rendered on mobile
    const resizeHandle = document.querySelector('.cursor-nw-resize');
    expect(resizeHandle).toBeNull();
  });

  it('does not apply explicit width/height inline styles on mobile', () => {
    setMobile(true);
    render(<ChatPopup {...defaultProps} />);

    fireEvent.click(screen.getByRole('button', { name: 'Open chat' }));

    const chatContainer = screen.getByTestId('chat-interface').parentElement!;
    // On mobile, no explicit width/height should be set (full-screen via CSS classes)
    expect(chatContainer.style.width).toBe('');
    expect(chatContainer.style.height).toBe('');
  });

  it('renders with explicit width/height on desktop', () => {
    setMobile(false);
    render(<ChatPopup {...defaultProps} />);

    fireEvent.click(screen.getByRole('button', { name: 'Open chat' }));

    const chatContainer = screen.getByTestId('chat-interface').parentElement!;
    // Desktop should have inline width and height (default 400x500)
    expect(chatContainer.style.width).toBeTruthy();
    expect(chatContainer.style.height).toBeTruthy();
    expect(chatContainer.className).not.toContain('inset-0');
  });

  it('uses z-index CSS variables for chat toggle and panel', () => {
    setMobile(false);
    render(<ChatPopup {...defaultProps} />);

    const toggle = screen.getByRole('button', { name: 'Open chat' });
    expect(toggle.className).toContain('z-[var(--z-chat-toggle)]');

    fireEvent.click(toggle);

    const chatContainer = screen.getByTestId('chat-interface').parentElement!;
    expect(chatContainer.className).toContain('z-[var(--z-chat)]');
  });
});
