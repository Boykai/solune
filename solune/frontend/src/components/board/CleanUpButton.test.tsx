import { describe, expect, it, vi } from 'vitest';
import { fireEvent } from '@testing-library/react';
import { render, screen } from '@/test/test-utils';
import { CleanUpButton } from './CleanUpButton';
import { useCleanup } from '@/hooks/useCleanup';

vi.mock('@/hooks/useCleanup', () => ({
  useCleanup: vi.fn(),
}));

vi.mock('./CleanUpConfirmModal', () => ({
  CleanUpConfirmModal: () => <div data-testid="confirm-modal" />,
}));

vi.mock('./CleanUpSummary', () => ({
  CleanUpSummary: () => <div data-testid="summary-modal" />,
}));

vi.mock('./CleanUpAuditHistory', () => ({
  CleanUpAuditHistory: () => <div data-testid="audit-modal" />,
}));

type MockCleanup = ReturnType<typeof useCleanup>;

function createMockCleanup(overrides: Partial<MockCleanup> = {}): MockCleanup {
  return {
    state: 'idle',
    preflightData: null,
    executeResult: null,
    historyData: null,
    error: null,
    permissionError: null,
    startPreflight: vi.fn(),
    confirmExecute: vi.fn(),
    cancel: vi.fn(),
    dismiss: vi.fn(),
    loadHistory: vi.fn(),
    showAuditHistory: vi.fn(),
    closeAuditHistory: vi.fn(),
    ...overrides,
  };
}

describe('CleanUpButton', () => {
  it('renders "Clean Up" button in idle state', () => {
    vi.mocked(useCleanup).mockReturnValue(createMockCleanup());
    render(<CleanUpButton owner="org" repo="repo" projectId="proj-1" />);
    expect(screen.getByRole('button', { name: /clean up/i })).toBeInTheDocument();
    expect(screen.getByText('Clean Up')).toBeInTheDocument();
  });

  it('shows "Analyzing..." when state is loading', () => {
    vi.mocked(useCleanup).mockReturnValue(createMockCleanup({ state: 'loading' }));
    render(<CleanUpButton owner="org" repo="repo" projectId="proj-1" />);
    expect(screen.getByText('Analyzing...')).toBeInTheDocument();
  });

  it('shows "Cleaning up..." when state is executing', () => {
    vi.mocked(useCleanup).mockReturnValue(createMockCleanup({ state: 'executing' }));
    render(<CleanUpButton owner="org" repo="repo" projectId="proj-1" />);
    expect(screen.getByText('Cleaning up...')).toBeInTheDocument();
  });

  it('disables the button when owner or repo is missing', () => {
    vi.mocked(useCleanup).mockReturnValue(createMockCleanup());
    render(<CleanUpButton projectId="proj-1" />);
    expect(screen.getByRole('button', { name: /clean up/i })).toBeDisabled();
  });

  it('calls startPreflight on click', () => {
    const startPreflight = vi.fn();
    vi.mocked(useCleanup).mockReturnValue(createMockCleanup({ startPreflight }));
    render(<CleanUpButton owner="org" repo="repo" projectId="proj-1" />);
    fireEvent.click(screen.getByRole('button', { name: /clean up/i }));
    expect(startPreflight).toHaveBeenCalledWith('org', 'repo', 'proj-1');
  });

  it('shows permission error with retry button', () => {
    const startPreflight = vi.fn();
    vi.mocked(useCleanup).mockReturnValue(
      createMockCleanup({
        permissionError: 'You do not have permission',
        startPreflight,
      }),
    );
    render(<CleanUpButton owner="org" repo="repo" projectId="proj-1" />);
    expect(screen.getByText('You do not have permission')).toBeInTheDocument();
    fireEvent.click(screen.getByText('Retry'));
    expect(startPreflight).toHaveBeenCalledWith('org', 'repo', 'proj-1');
  });

  it('shows confirm modal when state is confirming with preflight data', () => {
    vi.mocked(useCleanup).mockReturnValue(
      createMockCleanup({
        state: 'confirming',
        preflightData: {
          branches_to_delete: [],
          branches_to_preserve: [],
          prs_to_close: [],
          prs_to_preserve: [],
          orphaned_issues: [],
          issues_to_preserve: [],
          open_issues_on_board: 0,
          has_permission: true,
          permission_error: null,
        },
      }),
    );
    render(<CleanUpButton owner="org" repo="repo" projectId="proj-1" />);
    expect(screen.getByTestId('confirm-modal')).toBeInTheDocument();
  });

  it('shows summary modal when state is summary', () => {
    vi.mocked(useCleanup).mockReturnValue(createMockCleanup({ state: 'summary' }));
    render(<CleanUpButton owner="org" repo="repo" projectId="proj-1" />);
    expect(screen.getByTestId('summary-modal')).toBeInTheDocument();
  });

  it('shows audit history modal when state is auditHistory', () => {
    vi.mocked(useCleanup).mockReturnValue(createMockCleanup({ state: 'auditHistory' }));
    render(<CleanUpButton owner="org" repo="repo" projectId="proj-1" />);
    expect(screen.getByTestId('audit-modal')).toBeInTheDocument();
  });
});
