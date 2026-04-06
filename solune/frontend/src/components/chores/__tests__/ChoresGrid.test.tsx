import { describe, it, expect, vi } from 'vitest';
import userEvent from '@testing-library/user-event';

import { render, screen } from '@/test/test-utils';
import { ChoresGrid } from '../ChoresGrid';
import type { Chore } from '@/types';

vi.mock('../ChoreCard', () => ({
  ChoreCard: ({ chore }: { chore: Chore }) => <div>{chore.name}</div>,
}));

vi.mock('@/components/common/InfiniteScrollContainer', () => ({
  InfiniteScrollContainer: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="infinite-scroll">{children}</div>
  ),
}));

function createChore(overrides: Partial<Chore> = {}): Chore {
  return {
    id: 'chore-1',
    project_id: 'proj-1',
    name: 'Weekly Cleanup',
    template_path: '.github/ISSUE_TEMPLATE/cleanup.md',
    template_content: '# Cleanup',
    schedule_type: 'time',
    schedule_value: 7,
    status: 'active',
    last_triggered_at: null,
    last_triggered_count: 0,
    current_issue_number: null,
    current_issue_node_id: null,
    pr_number: null,
    pr_url: null,
    tracking_issue_number: null,
    execution_count: 0,
    ai_enhance_enabled: true,
    agent_pipeline_id: '',
    is_preset: false,
    preset_id: '',
    created_at: '2026-04-06T00:00:00Z',
    updated_at: '2026-04-06T00:00:00Z',
    ...overrides,
  };
}

describe('ChoresGrid', () => {
  it('shows the empty state and resets filters', async () => {
    const user = userEvent.setup();
    const onResetFilters = vi.fn();

    render(
      <ChoresGrid
        chores={[]}
        projectId="proj-1"
        parentIssueCount={0}
        editState={{}}
        onEditStart={vi.fn()}
        onEditChange={vi.fn()}
        onEditSave={vi.fn()}
        onEditDiscard={vi.fn()}
        isSaving={false}
        onResetFilters={onResetFilters}
      />,
    );

    expect(screen.getByText(/no chores match the current filters/i)).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /reset filters/i }));
    expect(onResetFilters).toHaveBeenCalledOnce();
  });

  it('renders chores inside the infinite scroll container when pagination is enabled', () => {
    render(
      <ChoresGrid
        chores={[createChore(), createChore({ id: 'chore-2', name: 'Dependency Update' })]}
        projectId="proj-1"
        parentIssueCount={4}
        editState={{}}
        onEditStart={vi.fn()}
        onEditChange={vi.fn()}
        onEditSave={vi.fn()}
        onEditDiscard={vi.fn()}
        isSaving={false}
        onResetFilters={vi.fn()}
        hasNextPage={true}
        isFetchingNextPage={false}
        fetchNextPage={vi.fn()}
      />,
    );

    expect(screen.getByTestId('infinite-scroll')).toBeInTheDocument();
    expect(screen.getByText('Weekly Cleanup')).toBeInTheDocument();
    expect(screen.getByText('Dependency Update')).toBeInTheDocument();
  });
});
