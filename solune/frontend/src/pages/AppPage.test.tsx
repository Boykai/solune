import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@/test/test-utils';
import { AppPage } from './AppPage';

// Mock ChatPanelManager so we don't need to wire up all the hooks/providers
vi.mock('@/components/chat/ChatPanelManager', () => ({
  ChatPanelManager: () => <div data-testid="chat-panel-manager">Chat Panel Manager</div>,
}));

describe('AppPage', () => {
  it('renders ChatPanelManager', () => {
    render(<AppPage />);
    expect(screen.getByTestId('chat-panel-manager')).toBeInTheDocument();
  });

  it('does not render marketing content', () => {
    render(<AppPage />);
    expect(screen.queryByText('Change your project mindset.')).not.toBeInTheDocument();
    expect(screen.queryByText('Daily affirmations for delivery')).not.toBeInTheDocument();
  });

  it('fills the available app layout height without introducing another viewport lock', () => {
    render(<AppPage />);
    const container = screen.getByTestId('chat-panel-manager').parentElement;
    expect(container).toHaveClass('h-full', 'min-h-0', 'overflow-hidden');
    expect(container).not.toHaveClass('h-[calc(100vh-4rem)]');
  });
});
