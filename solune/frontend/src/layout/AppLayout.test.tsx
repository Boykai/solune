import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AppLayout } from './AppLayout';

const mockSidebarState = vi.hoisted(() => ({
  isCollapsed: false,
  setCollapsed: vi.fn(),
  toggle: vi.fn(),
}));

const mockUseMediaQuery = vi.hoisted(() => vi.fn(() => false));

// Mock all the hooks used by AppLayout
vi.mock('@/hooks/useAuth', () => ({
  useAuth: () => ({
    user: {
      github_username: 'testuser',
      github_avatar_url: 'https://example.com/avatar.png',
      selected_project_id: 'proj-1',
    },
  }),
}));

vi.mock('@/hooks/useProjects', () => ({
  useProjects: () => ({
    selectedProject: {
      project_id: 'proj-1',
      name: 'Test Project',
      owner_login: 'testuser',
    },
    projects: [],
    isLoading: false,
    selectProject: vi.fn(),
  }),
}));

vi.mock('@/hooks/useAppTheme', () => ({
  useAppTheme: () => ({
    isDarkMode: false,
    toggleTheme: vi.fn(),
  }),
}));

vi.mock('@/hooks/useChat', () => ({
  useChat: () => ({
    messages: [],
    pendingProposals: [],
    pendingStatusChanges: [],
    pendingRecommendations: [],
    isSending: false,
    sendMessage: vi.fn(),
    retryMessage: vi.fn(),
    confirmProposal: vi.fn(),
    confirmStatusChange: vi.fn(),
    rejectProposal: vi.fn(),
    removePendingRecommendation: vi.fn(),
    clearChat: vi.fn(),
  }),
}));

vi.mock('@/hooks/useWorkflow', () => ({
  useWorkflow: () => ({
    confirmRecommendation: vi.fn().mockResolvedValue({ success: true }),
    rejectRecommendation: vi.fn(),
  }),
}));

vi.mock('@/hooks/useSettings', () => ({
  useSignalBanners: () => ({ banners: [] }),
  useDismissBanner: () => ({ dismissBanner: vi.fn(), isPending: false }),
  useUserSettings: () => ({
    settings: null,
    isLoading: false,
    updateSettings: vi.fn().mockResolvedValue(undefined),
  }),
}));

vi.mock('@/hooks/useSidebarState', () => ({
  useSidebarState: () => mockSidebarState,
}));

vi.mock('@/hooks/useProjectBoard', () => ({
  useProjectBoard: () => ({
    boardData: null,
  }),
}));

vi.mock('@/hooks/useRecentParentIssues', () => ({
  useRecentParentIssues: () => [],
}));

vi.mock('@/hooks/useNotifications', () => ({
  useNotifications: () => ({
    notifications: [],
    unreadCount: 0,
    markAllRead: vi.fn(),
  }),
}));

vi.mock('@/hooks/useMediaQuery', () => ({
  useMediaQuery: mockUseMediaQuery,
}));

vi.mock('@/hooks/useGlobalShortcuts', () => ({
  useGlobalShortcuts: vi.fn(),
}));

// Mock child components
vi.mock('./Sidebar', () => ({
  Sidebar: () => <div data-testid="sidebar">Sidebar</div>,
}));

vi.mock('./TopBar', () => ({
  TopBar: () => <div data-testid="topbar">TopBar</div>,
}));

vi.mock('@/components/chat/ChatPopup', () => ({
  ChatPopup: () => <div data-testid="chat-popup">Chat</div>,
}));

vi.mock('@/components/onboarding/SpotlightTour', () => ({
  SpotlightTour: () => null,
}));

vi.mock('@/components/ui/keyboard-shortcut-modal', () => ({
  KeyboardShortcutModal: () => null,
}));

vi.mock('@/components/command-palette/CommandPalette', () => ({
  CommandPalette: () => null,
}));

function renderAppLayout() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/projects']}>
        <Routes>
          <Route element={<AppLayout />}>
            <Route path="/projects" element={<div data-testid="page-content">Projects Page</div>} />
          </Route>
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('AppLayout', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockSidebarState.isCollapsed = false;
    mockSidebarState.setCollapsed.mockReset();
    mockSidebarState.toggle.mockReset();
    mockUseMediaQuery.mockReturnValue(false);
  });

  it('renders the sidebar', () => {
    renderAppLayout();
    expect(screen.getByTestId('sidebar')).toBeInTheDocument();
  });

  it('renders the top bar', () => {
    renderAppLayout();
    expect(screen.getByTestId('topbar')).toBeInTheDocument();
  });

  it('renders the page content via Outlet', () => {
    renderAppLayout();
    expect(screen.getByTestId('page-content')).toBeInTheDocument();
  });

  it('renders the global chat popup', () => {
    renderAppLayout();
    expect(screen.getByTestId('chat-popup')).toBeInTheDocument();
  });

  it('renders main content area', () => {
    renderAppLayout();
    expect(screen.getByRole('main')).toBeInTheDocument();
  });

  it('uses a shrinkable in-app scroll container for routed pages', () => {
    const { container } = renderAppLayout();
    const shell = container.querySelector('.celestial-shell');

    expect(shell).toBeInTheDocument();
    expect(shell).toHaveClass('h-dvh');
    expect(screen.getByRole('main')).toHaveClass('flex', 'min-h-0', 'flex-1', 'flex-col', 'overflow-auto');
  });

  it('auto-collapses the sidebar on the first mobile render when it starts expanded', () => {
    mockUseMediaQuery.mockReturnValue(true);

    renderAppLayout();

    expect(mockSidebarState.setCollapsed).toHaveBeenCalledOnce();
    expect(mockSidebarState.setCollapsed).toHaveBeenCalledWith(true);
  });

  it('does not auto-collapse the sidebar on the first mobile render when it is already collapsed', () => {
    mockUseMediaQuery.mockReturnValue(true);
    mockSidebarState.isCollapsed = true;

    renderAppLayout();

    expect(mockSidebarState.setCollapsed).not.toHaveBeenCalled();
  });
});
