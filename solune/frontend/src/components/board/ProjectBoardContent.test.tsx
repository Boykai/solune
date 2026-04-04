import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@/test/test-utils';
import { ProjectBoardContent } from './ProjectBoardContent';
import type { BoardDataResponse, AvailableAgent } from '@/types';

// ── Mocks ──

vi.mock('@/components/board/ProjectBoard', () => ({
  ProjectBoard: () => <div data-testid="project-board">ProjectBoard</div>,
}));

vi.mock('@/hooks/useUndoRedo', () => ({
  useUndoRedo: () => ({
    nextUndoDescription: null,
    canUndo: false,
    undo: vi.fn(),
  }),
}));

// ── Helpers ──

function makeBoardData(overrides: Partial<BoardDataResponse> = {}): BoardDataResponse {
  return {
    columns: [
      { name: 'Todo', items: [], id: 'col-1', color: 'GRAY' },
      { name: 'Done', items: [], id: 'col-2', color: 'GREEN' },
    ],
    ...overrides,
  } as BoardDataResponse;
}

const defaultBoardControls = {
  hasActiveControls: false,
  clearAll: vi.fn(),
  getGroups: () => null,
};

const emptyAgents: AvailableAgent[] = [];

// ── Tests ──

describe('ProjectBoardContent', () => {
  it('shows empty state when all columns are empty', () => {
    render(
      <ProjectBoardContent
        boardData={makeBoardData()}
        boardControls={defaultBoardControls}
        onCardClick={vi.fn()}
        availableAgents={emptyAgents}
      />
    );
    expect(screen.getByText('No items yet')).toBeInTheDocument();
    expect(
      screen.getByText('This project has no items. Add items in GitHub to see them here.')
    ).toBeInTheDocument();
  });

  it('shows filter-aware empty state when controls are active', () => {
    render(
      <ProjectBoardContent
        boardData={makeBoardData()}
        boardControls={{ ...defaultBoardControls, hasActiveControls: true }}
        onCardClick={vi.fn()}
        availableAgents={emptyAgents}
      />
    );
    expect(screen.getByText('No issues match the current view')).toBeInTheDocument();
    expect(screen.getByText('Clear all filters')).toBeInTheDocument();
  });

  it('renders the project board when items exist', () => {
    const data = makeBoardData({
      columns: [
        {
          name: 'Todo',
          items: [{ id: 'item-1', title: 'Fix bug', number: 1 }],
          id: 'col-1',
          color: 'GRAY',
        } as any,
      ],
    });
    render(
      <ProjectBoardContent
        boardData={data}
        boardControls={defaultBoardControls}
        onCardClick={vi.fn()}
        availableAgents={emptyAgents}
      />
    );
    expect(screen.getByTestId('project-board')).toBeInTheDocument();
  });

  it('calls clearAll when Clear all filters button is clicked', () => {
    const clearAll = vi.fn();
    render(
      <ProjectBoardContent
        boardData={makeBoardData()}
        boardControls={{ ...defaultBoardControls, hasActiveControls: true, clearAll }}
        onCardClick={vi.fn()}
        availableAgents={emptyAgents}
      />
    );
    screen.getByText('Clear all filters').click();
    expect(clearAll).toHaveBeenCalledOnce();
  });
});
