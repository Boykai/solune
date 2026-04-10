/**
 * Tests for SignalConnection component.
 *
 * Covers: loading state, disconnected status, connect button click,
 * connected status, disconnect button click with confirmation,
 * and phone number display.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderWithProviders, screen, fireEvent } from '@/test/test-utils';
import { SignalConnection } from './SignalConnection';

const mockInitiateLink = vi.fn();
const mockDisconnect = vi.fn();
const mockResetLink = vi.fn();

vi.mock('@/hooks/useSettings', () => ({
  useSignalConnection: vi.fn(() => ({ connection: null, isLoading: false })),
  useInitiateSignalLink: vi.fn(() => ({
    initiateLink: mockInitiateLink,
    data: null,
    isPending: false,
    error: null,
    reset: mockResetLink,
  })),
  useSignalLinkStatus: vi.fn(() => ({ linkStatus: null })),
  useDisconnectSignal: vi.fn(() => ({ disconnect: mockDisconnect, isPending: false })),
  useSignalPreferences: vi.fn(() => ({ preferences: null, isLoading: true })),
  useUpdateSignalPreferences: vi.fn(() => ({ updatePreferences: vi.fn(), isPending: false })),
  useSignalBanners: vi.fn(() => ({ banners: [] })),
  useDismissBanner: vi.fn(() => ({ dismissBanner: vi.fn(), isPending: false })),
}));

// Dynamic import to allow re-mocking per test
async function getHookModule() {
  return await import('@/hooks/useSettings');
}

describe('SignalConnection', () => {
  beforeEach(() => {
    mockInitiateLink.mockClear();
    mockDisconnect.mockClear();
    mockResetLink.mockClear();
  });

  it('shows loading state when isLoading', async () => {
    const mod = await getHookModule();
    vi.mocked(mod.useSignalConnection).mockReturnValue({
      connection: null,
      isLoading: true,
    } as unknown as ReturnType<typeof mod.useSignalConnection>);

    renderWithProviders(<SignalConnection />);
    expect(screen.getByText('Loading Signal connection status…')).toBeInTheDocument();
  });

  it('shows "Not Connected" status when disconnected', async () => {
    const mod = await getHookModule();
    vi.mocked(mod.useSignalConnection).mockReturnValue({
      connection: null,
      isLoading: false,
    } as unknown as ReturnType<typeof mod.useSignalConnection>);

    renderWithProviders(<SignalConnection />);
    expect(screen.getByText('Not Connected')).toBeInTheDocument();
  });

  it('shows "Connect Signal Account" button when not connected', async () => {
    const mod = await getHookModule();
    vi.mocked(mod.useSignalConnection).mockReturnValue({
      connection: null,
      isLoading: false,
    } as unknown as ReturnType<typeof mod.useSignalConnection>);

    renderWithProviders(<SignalConnection />);
    expect(screen.getByText('Connect Signal Account')).toBeInTheDocument();
  });

  it('calls initiateLink when Connect button is clicked', async () => {
    const mod = await getHookModule();
    vi.mocked(mod.useSignalConnection).mockReturnValue({
      connection: null,
      isLoading: false,
    } as unknown as ReturnType<typeof mod.useSignalConnection>);

    renderWithProviders(<SignalConnection />);
    fireEvent.click(screen.getByText('Connect Signal Account'));
    expect(mockResetLink).toHaveBeenCalled();
    expect(mockInitiateLink).toHaveBeenCalled();
  });

  it('shows "Connected" status when connected', async () => {
    const mod = await getHookModule();
    vi.mocked(mod.useSignalConnection).mockReturnValue({
      connection: { status: 'connected', signal_identifier: '+1234567890' },
      isLoading: false,
    } as unknown as ReturnType<typeof mod.useSignalConnection>);

    renderWithProviders(<SignalConnection />);
    expect(screen.getByText('Connected')).toBeInTheDocument();
  });

  it('displays phone number when connected', async () => {
    const mod = await getHookModule();
    vi.mocked(mod.useSignalConnection).mockReturnValue({
      connection: { status: 'connected', signal_identifier: '+1234567890' },
      isLoading: false,
    } as unknown as ReturnType<typeof mod.useSignalConnection>);

    renderWithProviders(<SignalConnection />);
    expect(screen.getByText('+1234567890')).toBeInTheDocument();
  });

  it('shows Disconnect button when connected', async () => {
    const mod = await getHookModule();
    vi.mocked(mod.useSignalConnection).mockReturnValue({
      connection: { status: 'connected', signal_identifier: '+1234567890' },
      isLoading: false,
    } as unknown as ReturnType<typeof mod.useSignalConnection>);

    renderWithProviders(<SignalConnection />);
    expect(screen.getByText('Disconnect Signal')).toBeInTheDocument();
  });

  it('shows confirmation when Disconnect is clicked', async () => {
    const mod = await getHookModule();
    vi.mocked(mod.useSignalConnection).mockReturnValue({
      connection: { status: 'connected', signal_identifier: '+1234567890' },
      isLoading: false,
    } as unknown as ReturnType<typeof mod.useSignalConnection>);

    renderWithProviders(<SignalConnection />);
    fireEvent.click(screen.getByText('Disconnect Signal'));
    expect(screen.getByText('Yes, Disconnect')).toBeInTheDocument();
    expect(screen.getByText(/Are you sure/)).toBeInTheDocument();
  });
});
