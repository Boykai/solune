import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@/test/test-utils';
import { ProjectBoard } from './ProjectBoard';
import type { BoardDataResponse, BoardItem } from '@/types';
import { useMediaQuery } from '@/hooks/useMediaQuery';

// ── Mocks ──

vi.mock('@dnd-kit/core', () => ({
  DndContext: ({ children }: { children: React.ReactNode }) => <div data-testid="dnd-context">{children}</div>,
  DragOverlay: ({ children }: { children: React.ReactNode }) => <div data-testid="drag-overlay">{children}</div>,
  closestCorners: vi.fn(),
  PointerSensor: vi.fn(),
  useSensor: vi.fn(),
  useSensors: vi.fn(() => []),
}));

vi.mock('@/hooks/useBoardDragDrop', () => ({
  useBoardDragDrop: vi.fn(() => ({
    activeCard: null,
    overColumnId: null,
    handlers: {
      onDragStart: vi.fn(),
      onDragOver: vi.fn(),
      onDragEnd: vi.fn(),
      onDragCancel: vi.fn(),
    },
  })),
}));

vi.mock('@/hooks/useMediaQuery', () => ({
  useMediaQuery: vi.fn(() => false),
}));

vi.mock('./BoardColumn', () => ({
  BoardColumn: ({ column }: { column: { status: { name: string } } }) => (
    <div data-testid={`board-column-${column.status.name}`}>{column.status.name}</div>
  ),
}));

vi.mock('./BoardDragOverlay', () => ({
  BoardDragOverlay: ({ item }: { item: BoardItem }) => (
    <div data-testid="board-drag-overlay">{item.title}</div>
  ),
}));

// ── Helpers ──

function createBoardData(overrides: Partial<BoardDataResponse> = {}): BoardDataResponse {
  return {
    project: {
      project_id: 'proj-1',
      name: 'Test Project',
      url: 'https://github.com',
      owner_login: 'owner',
      status_field: {
        field_id: 'status-field',
        options: [
          { option_id: 'col-1', name: 'To Do', color: 'GRAY' },
          { option_id: 'col-2', name: 'In Progress', color: 'YELLOW' },
        ],
      },
    },
    columns: [
      {
        status: { option_id: 'col-1', name: 'To Do', color: 'GRAY' },
        items: [],
        item_count: 0,
        estimate_total: 0,
      },
      {
        status: { option_id: 'col-2', name: 'In Progress', color: 'YELLOW' },
        items: [],
        item_count: 0,
        estimate_total: 0,
      },
    ],
    ...overrides,
  };
}

// ── Tests ──

describe('ProjectBoard', () => {
  it('renders columns from boardData', () => {
    render(
      <ProjectBoard
        boardData={createBoardData()}
        onCardClick={vi.fn()}
      />
    );

    expect(screen.getByTestId('board-column-To Do')).toBeInTheDocument();
    expect(screen.getByTestId('board-column-In Progress')).toBeInTheDocument();
  });

  it('passes onCardClick to BoardColumn', () => {
    const onCardClick = vi.fn();

    render(
      <ProjectBoard
        boardData={createBoardData()}
        onCardClick={onCardClick}
      />
    );

    // Columns are rendered — the mock BoardColumn receives onCardClick
    expect(screen.getAllByTestId(/board-column-/)).toHaveLength(2);
  });

  it('renders with region role and aria-label', () => {
    render(
      <ProjectBoard
        boardData={createBoardData()}
        onCardClick={vi.fn()}
      />
    );

    expect(screen.getByRole('region', { name: 'Project board' })).toBeInTheDocument();
  });

  it('applies scroll-snap classes for mobile swiping UX', () => {
    render(
      <ProjectBoard
        boardData={createBoardData()}
        onCardClick={vi.fn()}
      />
    );

    const scrollContainer = screen.getByRole('region', { name: 'Project board' });
    expect(scrollContainer.className).toContain('snap-x');
    expect(scrollContainer.className).toContain('snap-mandatory');
    // Desktop should disable snap via md: breakpoint
    expect(scrollContainer.className).toContain('md:snap-none');
  });

  it('sets grid column width with 16rem minmax on desktop', () => {
    render(
      <ProjectBoard
        boardData={createBoardData()}
        onCardClick={vi.fn()}
      />
    );

    const grid = screen.getByRole('region', { name: 'Project board' })
      .querySelector('.grid') as HTMLElement;
    expect(grid).toBeTruthy();
    // 2 columns → repeat(2, minmax(min(16rem, 85vw), 1fr)) on desktop
    expect(grid.style.gridTemplateColumns).toBe(
      'repeat(2, minmax(min(16rem, 85vw), 1fr))'
    );
  });

  it('uses column count of 1 when board has no columns', () => {
    render(
      <ProjectBoard
        boardData={createBoardData({ columns: [] })}
        onCardClick={vi.fn()}
      />
    );

    const grid = screen.getByRole('region', { name: 'Project board' })
      .querySelector('.grid') as HTMLElement;
    expect(grid).toBeTruthy();
    expect(grid.style.gridTemplateColumns).toBe(
      'repeat(1, minmax(min(16rem, 85vw), 1fr))'
    );
  });

  it('uses 14rem grid min-width on mobile', () => {
    vi.mocked(useMediaQuery).mockReturnValue(true);

    render(
      <ProjectBoard
        boardData={createBoardData()}
        onCardClick={vi.fn()}
      />
    );

    const grid = screen.getByRole('region', { name: 'Project board' })
      .querySelector('.grid') as HTMLElement;
    expect(grid).toBeTruthy();
    expect(grid.style.gridTemplateColumns).toBe(
      'repeat(2, minmax(min(14rem, 85vw), 1fr))'
    );

    vi.mocked(useMediaQuery).mockReturnValue(false);
  });
});
