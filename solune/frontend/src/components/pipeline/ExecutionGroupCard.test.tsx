import type { ReactNode } from 'react';
import { describe, expect, it, vi } from 'vitest';
import { render, screen, userEvent } from '@/test/test-utils';
import { ExecutionGroupCard } from './ExecutionGroupCard';
import type { ExecutionGroup, PipelineAgentNode } from '@/types';

vi.mock('@/components/ui/tooltip', () => ({
  Tooltip: ({ children }: { children: ReactNode }) => <>{children}</>,
  TooltipProvider: ({ children }: { children: ReactNode }) => <>{children}</>,
}));

vi.mock('@dnd-kit/core', () => ({
  DndContext: ({ children }: { children: ReactNode }) => <>{children}</>,
  closestCenter: vi.fn(),
  PointerSensor: function PointerSensor() {},
  KeyboardSensor: function KeyboardSensor() {},
  useSensor: vi.fn(() => ({})),
  useSensors: vi.fn((...sensors: unknown[]) => sensors),
}));

vi.mock('@dnd-kit/sortable', () => ({
  SortableContext: ({ children }: { children: ReactNode }) => <>{children}</>,
  rectSortingStrategy: vi.fn(),
  verticalListSortingStrategy: vi.fn(),
  sortableKeyboardCoordinates: vi.fn(),
  arrayMove: <T,>(items: T[]) => items,
  useSortable: vi.fn(() => ({
    attributes: {},
    listeners: {},
    setNodeRef: vi.fn(),
    transform: null,
    transition: undefined,
    isDragging: false,
  })),
}));

vi.mock('@dnd-kit/utilities', () => ({
  CSS: {
    Transform: {
      toString: () => undefined,
    },
  },
}));

vi.mock('./AgentNode', () => ({
  AgentNode: ({
    agentNode,
    onRemove,
  }: {
    agentNode: PipelineAgentNode;
    onRemove: () => void;
  }) => (
    <div>
      <span>{agentNode.agent_display_name}</span>
      <button type="button" onClick={onRemove}>
        Remove {agentNode.agent_display_name}
      </button>
    </div>
  ),
}));

function makeAgent(id: string, name: string): PipelineAgentNode {
  return {
    id,
    agent_slug: name.toLowerCase(),
    agent_display_name: name,
    model_id: 'gpt-4o',
    model_name: 'GPT-4o',
    tool_ids: [],
    tool_count: 0,
    config: {},
  };
}

function makeGroup(overrides: Partial<ExecutionGroup> = {}): ExecutionGroup {
  return {
    id: 'group-1',
    order: 1,
    execution_mode: 'parallel',
    agents: [makeAgent('agent-1', 'Planner'), makeAgent('agent-2', 'Reviewer')],
    ...overrides,
  };
}

describe('ExecutionGroupCard', () => {
  it('renders all agents in the group', () => {
    render(
      <ExecutionGroupCard
        group={makeGroup()}
        stageId="stage-1"
        canDelete={false}
        onRemoveGroup={vi.fn()}
        onToggleMode={vi.fn()}
        onRemoveAgent={vi.fn()}
        onUpdateAgent={vi.fn()}
        onReorderAgents={vi.fn()}
        onToolsClick={vi.fn()}
      />,
    );

    expect(screen.getByText('Planner')).toBeInTheDocument();
    expect(screen.getByText('Reviewer')).toBeInTheDocument();
    expect(screen.getByText('2 agents')).toBeInTheDocument();
  });

  it('toggles execution mode when the mode button is clicked', async () => {
    const onToggleMode = vi.fn();
    const user = userEvent.setup();

    render(
      <ExecutionGroupCard
        group={makeGroup({ execution_mode: 'parallel' })}
        stageId="stage-1"
        canDelete={false}
        onRemoveGroup={vi.fn()}
        onToggleMode={onToggleMode}
        onRemoveAgent={vi.fn()}
        onUpdateAgent={vi.fn()}
        onReorderAgents={vi.fn()}
        onToolsClick={vi.fn()}
      />,
    );

    await user.click(screen.getByRole('button', { name: 'Switch to sequential mode' }));
    expect(onToggleMode).toHaveBeenCalledWith('sequential');
  });

  it('removes an agent when its remove action is triggered', async () => {
    const onRemoveAgent = vi.fn();
    const user = userEvent.setup();

    render(
      <ExecutionGroupCard
        group={makeGroup()}
        stageId="stage-1"
        canDelete={false}
        onRemoveGroup={vi.fn()}
        onToggleMode={vi.fn()}
        onRemoveAgent={onRemoveAgent}
        onUpdateAgent={vi.fn()}
        onReorderAgents={vi.fn()}
        onToolsClick={vi.fn()}
      />,
    );

    await user.click(screen.getByRole('button', { name: 'Remove Planner' }));
    expect(onRemoveAgent).toHaveBeenCalledWith('agent-1');
  });
});
