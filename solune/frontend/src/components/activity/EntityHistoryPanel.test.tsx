import { describe, expect, it, vi, afterEach } from 'vitest';
import { fireEvent } from '@testing-library/react';
import { render, screen } from '@/test/test-utils';
import { EntityHistoryPanel } from './EntityHistoryPanel';

// ── Mocks ──

const mockEvents = [
  { id: '1', summary: 'Issue created', created_at: new Date().toISOString(), type: 'created' },
  { id: '2', summary: 'Agent assigned', created_at: new Date(Date.now() - 3600000).toISOString(), type: 'assigned' },
  { id: '3', summary: 'Status updated', created_at: new Date(Date.now() - 86400000 * 2).toISOString(), type: 'status' },
];

vi.mock('@/hooks/useEntityHistory', () => ({
  useEntityHistory: vi.fn(() => ({
    allItems: mockEvents,
    isLoading: false,
  })),
}));

// ── Tests ──

describe('EntityHistoryPanel', () => {
  it('renders the History toggle button', () => {
    render(
      <EntityHistoryPanel projectId="proj-1" entityType="issue" entityId="123" />
    );
    expect(screen.getByText('History')).toBeInTheDocument();
  });

  it('shows event count badge', () => {
    render(
      <EntityHistoryPanel projectId="proj-1" entityType="issue" entityId="123" />
    );
    expect(screen.getByText('3')).toBeInTheDocument();
  });

  it('is collapsed by default', () => {
    render(
      <EntityHistoryPanel projectId="proj-1" entityType="issue" entityId="123" />
    );
    expect(screen.queryByText('Issue created')).not.toBeInTheDocument();
  });

  it('expands when History button is clicked', () => {
    render(
      <EntityHistoryPanel projectId="proj-1" entityType="issue" entityId="123" />
    );
    fireEvent.click(screen.getByText('History'));
    expect(screen.getByText('Issue created')).toBeInTheDocument();
    expect(screen.getByText('Agent assigned')).toBeInTheDocument();
    expect(screen.getByText('Status updated')).toBeInTheDocument();
  });

  it('collapses when History button is clicked again', () => {
    render(
      <EntityHistoryPanel projectId="proj-1" entityType="issue" entityId="123" />
    );
    fireEvent.click(screen.getByText('History'));
    expect(screen.getByText('Issue created')).toBeInTheDocument();
    
    fireEvent.click(screen.getByText('History'));
    expect(screen.queryByText('Issue created')).not.toBeInTheDocument();
  });

  it('shows relative time for events', () => {
    render(
      <EntityHistoryPanel projectId="proj-1" entityType="issue" entityId="123" />
    );
    fireEvent.click(screen.getByText('History'));
    // Most recent event should show "just now" (less than 1 minute)
    expect(screen.getByText('just now')).toBeInTheDocument();
  });
});

describe('EntityHistoryPanel — loading state', () => {
  it('shows loading spinner when data is loading', async () => {
    const { useEntityHistory } = await import('@/hooks/useEntityHistory');
    vi.mocked(useEntityHistory).mockReturnValue({
      allItems: [],
      isLoading: true,
    } as any);

    render(
      <EntityHistoryPanel projectId="proj-1" entityType="issue" entityId="123" />
    );
    fireEvent.click(screen.getByText('History'));
    expect(screen.getByText('Loading…')).toBeInTheDocument();
  });
});

describe('EntityHistoryPanel — empty state', () => {
  it('shows no activity message when events are empty', async () => {
    const { useEntityHistory } = await import('@/hooks/useEntityHistory');
    vi.mocked(useEntityHistory).mockReturnValue({
      allItems: [],
      isLoading: false,
    } as any);

    render(
      <EntityHistoryPanel projectId="proj-1" entityType="issue" entityId="123" />
    );
    fireEvent.click(screen.getByText('History'));
    expect(screen.getByText('No activity recorded')).toBeInTheDocument();
  });
});
