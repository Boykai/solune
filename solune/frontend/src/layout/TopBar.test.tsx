import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { TopBar } from './TopBar';
import type { Notification } from '@/types';

// Mock child components to isolate TopBar logic
vi.mock('./Breadcrumb', () => ({
  Breadcrumb: () => <div data-testid="breadcrumb">Breadcrumb</div>,
}));
vi.mock('./NotificationBell', () => ({
  NotificationBell: ({ unreadCount }: { unreadCount: number }) => (
    <div data-testid="notification-bell">Bell ({unreadCount})</div>
  ),
}));
vi.mock('./RateLimitBar', () => ({
  RateLimitBar: () => <div data-testid="rate-limit-bar">RateLimit</div>,
}));
vi.mock('@/components/auth/LoginButton', () => ({
  LoginButton: () => <div data-testid="login-button">Login</div>,
}));

const defaultProps = {
  isDarkMode: false,
  onToggleTheme: vi.fn(),
  user: { login: 'testuser', avatar_url: 'https://example.com/avatar.png' },
  notifications: [] as Notification[],
  unreadCount: 0,
  onMarkAllRead: vi.fn(),
};

function renderTopBar(props = {}) {
  return render(
    <MemoryRouter>
      <TopBar {...defaultProps} {...props} />
    </MemoryRouter>,
  );
}

describe('TopBar', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders the header element', () => {
    renderTopBar();
    expect(screen.getByRole('banner')).toBeInTheDocument();
  });

  it('renders breadcrumb component', () => {
    renderTopBar();
    expect(screen.getByTestId('breadcrumb')).toBeInTheDocument();
  });

  it('renders search trigger with command palette label', () => {
    renderTopBar();
    expect(screen.getByRole('button', { name: /open command palette/i })).toBeInTheDocument();
  });

  it('dispatches solune:open-command-palette event on search click', () => {
    renderTopBar();
    const spy = vi.fn();
    window.addEventListener('solune:open-command-palette', spy);
    fireEvent.click(screen.getByRole('button', { name: /open command palette/i }));
    expect(spy).toHaveBeenCalledTimes(1);
    window.removeEventListener('solune:open-command-palette', spy);
  });

  it('renders help link to /help', () => {
    renderTopBar();
    const helpLink = screen.getByRole('link', { name: /help/i });
    expect(helpLink).toHaveAttribute('href', '/help');
  });

  it('renders notification bell', () => {
    renderTopBar();
    expect(screen.getByTestId('notification-bell')).toBeInTheDocument();
  });

  it('renders rate limit bar', () => {
    renderTopBar();
    expect(screen.getByTestId('rate-limit-bar')).toBeInTheDocument();
  });

  it('renders user avatar when user has avatar_url', () => {
    renderTopBar();
    const avatar = screen.getByAltText('testuser');
    expect(avatar).toHaveAttribute('src', 'https://example.com/avatar.png');
  });

  it('renders user login name', () => {
    renderTopBar();
    expect(screen.getByText('testuser')).toBeInTheDocument();
  });

  it('does not render user section when no user', () => {
    renderTopBar({ user: undefined });
    expect(screen.queryByText('testuser')).not.toBeInTheDocument();
  });

  it('does not render avatar when user has no avatar_url', () => {
    renderTopBar({ user: { login: 'noavatar' } });
    expect(screen.queryByRole('img')).not.toBeInTheDocument();
    expect(screen.getByText('noavatar')).toBeInTheDocument();
  });

  it('renders login button', () => {
    renderTopBar();
    expect(screen.getByTestId('login-button')).toBeInTheDocument();
  });
});
