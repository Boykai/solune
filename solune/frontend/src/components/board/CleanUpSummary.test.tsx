import { describe, expect, it, vi } from 'vitest';
import { fireEvent } from '@testing-library/react';
import { render, screen } from '@/test/test-utils';
import { CleanUpSummary } from './CleanUpSummary';
import type { CleanupExecuteResponse, CleanupItemResult } from '@/types';

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

function makeResult(overrides: Partial<CleanupItemResult> = {}): CleanupItemResult {
  return {
    item_type: 'branch',
    identifier: 'feature/test',
    action: 'deleted',
    reason: null,
    error: null,
    ...overrides,
  };
}

function makeResponse(overrides: Partial<CleanupExecuteResponse> = {}): CleanupExecuteResponse {
  return {
    operation_id: 'op-1',
    branches_deleted: 0,
    branches_preserved: 0,
    prs_closed: 0,
    prs_preserved: 0,
    issues_deleted: 0,
    errors: [],
    results: [],
    ...overrides,
  };
}

// ── Tests ──

describe('CleanUpSummary', () => {
  it('returns null when result and error are both null', () => {
    const { container } = render(
      <CleanUpSummary result={null} error={null} onDismiss={vi.fn()} />
    );
    expect(container.innerHTML).toBe('');
  });

  it('shows fatal error dialog when error is present with no result', () => {
    render(
      <CleanUpSummary result={null} error="Something went wrong" onDismiss={vi.fn()} />
    );
    expect(screen.getByText('Cleanup Failed')).toBeInTheDocument();
    expect(screen.getByText('Something went wrong')).toBeInTheDocument();
  });

  it('calls onDismiss when Dismiss button is clicked in error state', () => {
    const onDismiss = vi.fn();
    render(
      <CleanUpSummary result={null} error="fail" onDismiss={onDismiss} />
    );
    fireEvent.click(screen.getByText('Dismiss'));
    expect(onDismiss).toHaveBeenCalledOnce();
  });

  it('shows Cleanup Complete for successful operation', () => {
    render(
      <CleanUpSummary
        result={makeResponse({ branches_deleted: 3, prs_closed: 1 })}
        error={null}
        onDismiss={vi.fn()}
      />
    );
    expect(screen.getByText('Cleanup Complete')).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument();
    expect(screen.getByText('Branches Deleted')).toBeInTheDocument();
    expect(screen.getByText('1')).toBeInTheDocument();
    expect(screen.getByText('PRs Closed')).toBeInTheDocument();
  });

  it('shows Cleanup Completed with Errors when there are failed items', () => {
    const results = [
      makeResult({ item_type: 'branch', action: 'failed', error: 'perm denied' }),
    ];
    render(
      <CleanUpSummary
        result={makeResponse({ results })}
        error={null}
        onDismiss={vi.fn()}
      />
    );
    expect(screen.getByText('Cleanup Completed with Errors')).toBeInTheDocument();
    expect(screen.getByText('Failed Operations (1)')).toBeInTheDocument();
    expect(screen.getByText('perm denied')).toBeInTheDocument();
  });

  it('lists successfully deleted branches', () => {
    const results = [
      makeResult({ item_type: 'branch', identifier: 'fix/bug-1', action: 'deleted' }),
      makeResult({ item_type: 'branch', identifier: 'fix/bug-2', action: 'deleted' }),
    ];
    render(
      <CleanUpSummary
        result={makeResponse({ results, branches_deleted: 2 })}
        error={null}
        onDismiss={vi.fn()}
      />
    );
    expect(screen.getByText('Deleted Branches')).toBeInTheDocument();
    expect(screen.getByText('fix/bug-1')).toBeInTheDocument();
    expect(screen.getByText('fix/bug-2')).toBeInTheDocument();
  });

  it('lists successfully closed PRs', () => {
    const results = [
      makeResult({ item_type: 'pr', identifier: '42', action: 'closed' }),
    ];
    render(
      <CleanUpSummary
        result={makeResponse({ results, prs_closed: 1 })}
        error={null}
        onDismiss={vi.fn()}
      />
    );
    expect(screen.getByText('Closed Pull Requests')).toBeInTheDocument();
    expect(screen.getByText('#42')).toBeInTheDocument();
  });

  it('lists successfully deleted issues', () => {
    const results = [
      makeResult({ item_type: 'issue', identifier: '99', action: 'deleted' }),
    ];
    render(
      <CleanUpSummary
        result={makeResponse({ results, issues_deleted: 1 })}
        error={null}
        onDismiss={vi.fn()}
      />
    );
    expect(screen.getByText('Deleted Orphaned Issues')).toBeInTheDocument();
    expect(screen.getByText('#99')).toBeInTheDocument();
  });

  it('calls onDismiss when Escape is pressed', () => {
    const onDismiss = vi.fn();
    render(
      <CleanUpSummary result={makeResponse()} error={null} onDismiss={onDismiss} />
    );
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(onDismiss).toHaveBeenCalledOnce();
  });

  it('shows View Audit History button when callback is provided', () => {
    const onViewHistory = vi.fn();
    render(
      <CleanUpSummary
        result={makeResponse()}
        error={null}
        onDismiss={vi.fn()}
        onViewHistory={onViewHistory}
      />
    );
    const btn = screen.getByText('View Audit History');
    expect(btn).toBeInTheDocument();
    fireEvent.click(btn);
    expect(onViewHistory).toHaveBeenCalledOnce();
  });

  it('hides View Audit History when no callback provided', () => {
    render(
      <CleanUpSummary result={makeResponse()} error={null} onDismiss={vi.fn()} />
    );
    expect(screen.queryByText('View Audit History')).not.toBeInTheDocument();
  });

  it('displays issues_deleted count defaulting to 0', () => {
    render(
      <CleanUpSummary
        result={makeResponse({ issues_deleted: 0 })}
        error={null}
        onDismiss={vi.fn()}
      />
    );
    expect(screen.getByText('Issues Deleted')).toBeInTheDocument();
  });
});
