import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@/test/test-utils';
import { expectNoA11yViolations } from '@/test/a11y-helpers';
import { SettingsPage } from './SettingsPage';

// ── Mocks ──

const mockUseUserSettings = vi.fn();

vi.mock('@/hooks/useSettings', () => ({
  useUserSettings: () => mockUseUserSettings(),
  useModelOptions: () => ({ data: undefined, isLoading: false, refetch: vi.fn() }),
  useSignalConnection: () => ({ connection: undefined, isLoading: false, error: null, refetch: vi.fn() }),
  useInitiateSignalLink: () => ({ initiateLink: vi.fn(), data: undefined, isPending: false, error: null, reset: vi.fn() }),
  useSignalLinkStatus: () => ({ data: undefined, isLoading: false }),
  useDisconnectSignal: () => ({ disconnect: vi.fn(), isPending: false }),
  useSignalPreferences: () => ({ data: undefined, isLoading: false }),
  useUpdateSignalPreferences: () => ({ updatePreferences: vi.fn(), isPending: false }),
  useSignalBanners: () => ({ banners: [], isLoading: false, error: null }),
  useDismissBanner: () => ({ dismissBanner: vi.fn(), isPending: false }),
}));

// ── Helpers ──

function userSettingsHook(overrides = {}) {
  return {
    settings: undefined,
    isLoading: false,
    error: null,
    updateSettings: vi.fn().mockResolvedValue(undefined),
    isUpdating: false,
    ...overrides,
  };
}

const mockUserSettings = {
  ai: { provider: 'copilot', model: 'gpt-4o', agent_model: 'gpt-4o', temperature: 0.7 },
  display: { theme: 'dark', default_view: 'board', sidebar_collapsed: false },
  workflow: { default_repository: null, default_assignee: '', copilot_polling_interval: 30 },
  notifications: {
    task_status_change: true,
    agent_completion: true,
    new_recommendation: false,
    chat_mention: true,
  },
};

// ── Tests ──

describe('SettingsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseUserSettings.mockReturnValue(userSettingsHook());
  });

  // ── Layout & Headings ──

  it('renders the settings heading and subtitle', () => {
    render(<SettingsPage />);
    expect(screen.getByText('Settings')).toBeInTheDocument();
    expect(screen.getByText('Configure your preferences for Solune.')).toBeInTheDocument();
  });

  // ── Loading State ──

  it('shows loading indicator while user settings load', () => {
    mockUseUserSettings.mockReturnValue(userSettingsHook({ isLoading: true }));
    render(<SettingsPage />);
    expect(screen.getByText('Loading user settings…')).toBeInTheDocument();
    // Should not render the main heading while loading
    expect(screen.queryByText('Settings')).not.toBeInTheDocument();
  });

  // ── Loaded State with Data ──

  it('renders PrimarySettings when user settings are available', () => {
    mockUseUserSettings.mockReturnValue(
      userSettingsHook({ settings: mockUserSettings })
    );
    render(<SettingsPage />);
    expect(screen.getByText('AI Configuration')).toBeInTheDocument();
  });

  // ── Removed Sections ──

  it('does not render AdvancedSettings', () => {
    mockUseUserSettings.mockReturnValue(
      userSettingsHook({ settings: mockUserSettings })
    );
    render(<SettingsPage />);
    expect(screen.queryByText('Advanced Settings')).not.toBeInTheDocument();
  });

  it('does not render removed subsections', () => {
    mockUseUserSettings.mockReturnValue(
      userSettingsHook({ settings: mockUserSettings })
    );
    render(<SettingsPage />);
    expect(screen.queryByText('Display Preferences')).not.toBeInTheDocument();
    expect(screen.queryByText('Workflow Defaults')).not.toBeInTheDocument();
    expect(screen.queryByText('Notification Preferences')).not.toBeInTheDocument();
    expect(screen.queryByText('Global Settings')).not.toBeInTheDocument();
  });

  // ── No-Data Guard ──

  it('does not render PrimarySettings when settings are undefined', () => {
    render(<SettingsPage />);
    expect(screen.queryByText('AI Configuration')).not.toBeInTheDocument();
  });

  // ── Accessibility ──

  it('has no accessibility violations', async () => {
    const { container } = render(<SettingsPage />);
    await expectNoA11yViolations(container);
  });

  it('has no accessibility violations when loaded with data', async () => {
    mockUseUserSettings.mockReturnValue(
      userSettingsHook({ settings: mockUserSettings })
    );
    const { container } = render(<SettingsPage />);
    await expectNoA11yViolations(container);
  });
});
