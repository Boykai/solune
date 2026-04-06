import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@/test/test-utils';

vi.mock('@dnd-kit/core', () => ({
  useDroppable: () => ({ setNodeRef: vi.fn(), isOver: false }),
}));

vi.mock('@dnd-kit/sortable', () => ({
  SortableContext: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  verticalListSortingStrategy: {},
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

import { AgentColumnCell } from './AgentColumnCell';

describe('AgentColumnCell', () => {
  const defaultProps = {
    status: 'In Progress',
    agents: [],
    isModified: false,
    onRemoveAgent: vi.fn(),
    onCloneAgent: vi.fn(),
    onReorderAgents: vi.fn(),
  };

  it('renders without crashing', () => {
    render(<AgentColumnCell {...defaultProps} />);
    expect(screen.getByRole('group')).toBeInTheDocument();
  });

  it('has correct aria-label', () => {
    render(<AgentColumnCell {...defaultProps} />);
    expect(screen.getByRole('group')).toHaveAttribute(
      'aria-label',
      'In Progress column, 0 agents',
    );
  });

  it('renders agent list region', () => {
    render(<AgentColumnCell {...defaultProps} />);
    expect(screen.getByRole('list', { name: /agents in in progress/i })).toBeInTheDocument();
  });
});
