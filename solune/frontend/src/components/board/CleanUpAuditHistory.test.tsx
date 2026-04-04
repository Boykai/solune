import { describe, expect, it, vi } from 'vitest';
import { fireEvent } from '@testing-library/react';
import { render, screen } from '@/test/test-utils';
import { CleanUpAuditHistory } from './CleanUpAuditHistory';
import type { CleanupHistoryResponse, CleanupAuditLogEntry } from '@/types';

// ── Mocks ──

vi.mock('react-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-dom')>();
  return {
    ...actual,
    createPortal: (children: React.ReactNode) => children,
  };
});

vi.mock('@/hooks/useScrollLock', () => ({
  useScrollLock: vi.fn(),
}));

// ── Helpers ──

function makeOperation(overrides: Partial<CleanupAuditLogEntry> = {}): CleanupAuditLogEntry {
  return {
    id: 'op-1',
    started_at: '2025-01-15T10:30:00Z',
    completed_at: '2025-01-15T10:31:00Z',
    status: 'completed',
    branches_deleted: 3,
    branches_preserved: 1,
    prs_closed: 2,
    prs_preserved: 0,
    errors_count: 0,
    details: null,
    ...overrides,
  };
}

function makeHistoryData(
  overrides: Partial<CleanupHistoryResponse> = {}
): CleanupHistoryResponse {
  return {
    operations: [],
    count: 0,
    ...overrides,
  };
}

// ── Tests ──

describe('CleanUpAuditHistory', () => {
  it('renders the modal heading', () => {
    render(
      <CleanUpAuditHistory data={makeHistoryData()} onClose={vi.fn()} />
    );
    expect(screen.getByText('Cleanup Audit History')).toBeInTheDocument();
  });

  it('shows empty state when no operations exist', () => {
    render(
      <CleanUpAuditHistory data={makeHistoryData()} onClose={vi.fn()} />
    );
    expect(
      screen.getByText('No cleanup operations found for this repository.')
    ).toBeInTheDocument();
  });

  it('shows empty state for null data', () => {
    render(
      <CleanUpAuditHistory data={null} onClose={vi.fn()} />
    );
    expect(
      screen.getByText('No cleanup operations found for this repository.')
    ).toBeInTheDocument();
  });

  it('displays operation stats', () => {
    const data = makeHistoryData({
      operations: [
        makeOperation({
          branches_deleted: 5,
          prs_closed: 2,
          branches_preserved: 1,
          prs_preserved: 3,
        }),
      ],
      count: 1,
    });
    render(<CleanUpAuditHistory data={data} onClose={vi.fn()} />);
    expect(screen.getByText('Branches deleted: 5')).toBeInTheDocument();
    expect(screen.getByText('PRs closed: 2')).toBeInTheDocument();
    expect(screen.getByText('Branches preserved: 1')).toBeInTheDocument();
    expect(screen.getByText('PRs preserved: 3')).toBeInTheDocument();
  });

  it('shows errors count when present', () => {
    const data = makeHistoryData({
      operations: [makeOperation({ errors_count: 3 })],
      count: 1,
    });
    render(<CleanUpAuditHistory data={data} onClose={vi.fn()} />);
    expect(screen.getByText('Errors: 3')).toBeInTheDocument();
  });

  it('hides errors count when zero', () => {
    const data = makeHistoryData({
      operations: [makeOperation({ errors_count: 0 })],
      count: 1,
    });
    render(<CleanUpAuditHistory data={data} onClose={vi.fn()} />);
    expect(screen.queryByText(/Errors:/)).not.toBeInTheDocument();
  });

  it('displays status badge for completed operations', () => {
    const data = makeHistoryData({
      operations: [makeOperation({ status: 'completed' })],
      count: 1,
    });
    render(<CleanUpAuditHistory data={data} onClose={vi.fn()} />);
    expect(screen.getByText('completed')).toBeInTheDocument();
  });

  it('displays status badge for failed operations', () => {
    const data = makeHistoryData({
      operations: [makeOperation({ status: 'failed' })],
      count: 1,
    });
    render(<CleanUpAuditHistory data={data} onClose={vi.fn()} />);
    expect(screen.getByText('failed')).toBeInTheDocument();
  });

  it('calls onClose when Close button is clicked', () => {
    const onClose = vi.fn();
    render(<CleanUpAuditHistory data={makeHistoryData()} onClose={onClose} />);
    fireEvent.click(screen.getByText('Close'));
    expect(onClose).toHaveBeenCalledOnce();
  });

  it('calls onClose when X button is clicked', () => {
    const onClose = vi.fn();
    render(<CleanUpAuditHistory data={makeHistoryData()} onClose={onClose} />);
    fireEvent.click(screen.getByLabelText('Close'));
    expect(onClose).toHaveBeenCalledOnce();
  });

  it('calls onClose when Escape is pressed', () => {
    const onClose = vi.fn();
    render(<CleanUpAuditHistory data={makeHistoryData()} onClose={onClose} />);
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(onClose).toHaveBeenCalledOnce();
  });

  it('renders multiple operations', () => {
    const data = makeHistoryData({
      operations: [
        makeOperation({ id: 'op-1', branches_deleted: 1 }),
        makeOperation({ id: 'op-2', branches_deleted: 7 }),
      ],
      count: 2,
    });
    render(<CleanUpAuditHistory data={data} onClose={vi.fn()} />);
    expect(screen.getByText('Branches deleted: 1')).toBeInTheDocument();
    expect(screen.getByText('Branches deleted: 7')).toBeInTheDocument();
  });
});
