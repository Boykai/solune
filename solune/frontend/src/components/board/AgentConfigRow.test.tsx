import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@/test/test-utils';
import type { BoardColumn } from '@/types';

vi.mock('@dnd-kit/core', () => ({
  DndContext: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  DragOverlay: () => null,
  closestCenter: vi.fn(),
  KeyboardSensor: vi.fn(),
  PointerSensor: vi.fn(),
  TouchSensor: vi.fn(),
  useSensors: () => [],
  useSensor: () => ({}),
  useDroppable: () => ({ setNodeRef: vi.fn(), isOver: false }),
}));

vi.mock('@dnd-kit/sortable', () => ({
  SortableContext: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  verticalListSortingStrategy: {},
  sortableKeyboardCoordinates: vi.fn(),
  arrayMove: vi.fn(),
  useSortable: () => ({
    attributes: {},
    listeners: {},
    setNodeRef: vi.fn(),
    transform: null,
    transition: null,
    isDragging: false,
  }),
}));

vi.mock('@dnd-kit/utilities', () => ({
  CSS: { Translate: { toString: () => undefined } },
}));

import { AgentConfigRow } from './AgentConfigRow';

function createColumn(name: string): BoardColumn {
  return {
    status: { option_id: `opt-${name}`, name, color: 'GRAY' },
    items: [],
    item_count: 0,
    estimate_total: 0,
  };
}

const mockAgentConfig = {
  localMappings: {} as Record<string, never[]>,
  isDirty: false,
  isColumnDirty: () => false,
  removeAgent: vi.fn(),
  cloneAgent: vi.fn(),
  reorderAgents: vi.fn(),
  moveAgentToColumn: vi.fn(),
  save: vi.fn(),
  discard: vi.fn(),
  isSaving: false,
  saveError: null,
  isLoaded: true,
  applyPreset: vi.fn(),
  addAgent: vi.fn(),
};

describe('AgentConfigRow', () => {
  it('renders without crashing when loaded', () => {
    render(
      <AgentConfigRow
        columnCount={2}
        columns={[createColumn('Todo'), createColumn('Done')]}
        agentConfig={mockAgentConfig as never}
      />,
    );
    expect(screen.getByRole('region', { name: /agent column assignments/i })).toBeInTheDocument();
  });

  it('shows loading skeleton when not loaded', () => {
    const { container } = render(
      <AgentConfigRow
        columnCount={1}
        columns={[createColumn('Todo')]}
        agentConfig={{ ...mockAgentConfig, isLoaded: false } as never}
      />,
    );
    expect(container.querySelector('.animate-pulse')).toBeTruthy();
  });

  it('renders title text', () => {
    render(
      <AgentConfigRow
        columnCount={1}
        columns={[createColumn('Todo')]}
        agentConfig={mockAgentConfig as never}
        title="Custom Title"
      />,
    );
    expect(screen.getByText('Custom Title')).toBeInTheDocument();
  });
});
