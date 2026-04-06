import { describe, expect, it } from 'vitest';
import { render, screen } from '@/test/test-utils';
import { BoardDragOverlay } from './BoardDragOverlay';
import type { BoardItem } from '@/types';

function createBoardItem(overrides: Partial<BoardItem> = {}): BoardItem {
  return {
    item_id: 'item-1',
    content_type: 'issue',
    title: 'Fix the bug',
    status: 'In Progress',
    status_option_id: 'opt-1',
    assignees: [],
    labels: [],
    linked_prs: [],
    sub_issues: [],
    ...overrides,
  };
}

describe('BoardDragOverlay', () => {
  it('renders the item title', () => {
    render(<BoardDragOverlay item={createBoardItem()} />);
    expect(screen.getByText('Fix the bug')).toBeInTheDocument();
  });

  it('has role="status" for accessibility', () => {
    render(<BoardDragOverlay item={createBoardItem()} />);
    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('has descriptive aria-label', () => {
    render(<BoardDragOverlay item={createBoardItem({ title: 'My Task' })} />);
    expect(screen.getByRole('status')).toHaveAttribute(
      'aria-label',
      'Dragging card: My Task',
    );
  });

  it('renders labels (max 3)', () => {
    const item = createBoardItem({
      labels: [
        { id: 'l1', name: 'bug', color: 'ff0000' },
        { id: 'l2', name: 'urgent', color: '00ff00' },
        { id: 'l3', name: 'frontend', color: '0000ff' },
        { id: 'l4', name: 'hidden', color: 'ffffff' },
      ],
    });
    render(<BoardDragOverlay item={item} />);
    expect(screen.getByText('bug')).toBeInTheDocument();
    expect(screen.getByText('urgent')).toBeInTheDocument();
    expect(screen.getByText('frontend')).toBeInTheDocument();
    expect(screen.queryByText('hidden')).not.toBeInTheDocument();
    expect(screen.getByText('+1')).toBeInTheDocument();
  });

  it('renders priority badge when present', () => {
    const item = createBoardItem({
      priority: { id: 'p1', name: 'P0' },
    });
    render(<BoardDragOverlay item={item} />);
    expect(screen.getByText('P0')).toBeInTheDocument();
  });

  it('renders assignees when present', () => {
    const item = createBoardItem({
      assignees: [{ login: 'octocat', avatar_url: '' }],
    });
    render(<BoardDragOverlay item={item} />);
    expect(screen.getByText('octocat')).toBeInTheDocument();
  });
});
