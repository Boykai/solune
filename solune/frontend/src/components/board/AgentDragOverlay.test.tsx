import { describe, expect, it } from 'vitest';
import { render, screen } from '@/test/test-utils';
import { AgentDragOverlay } from './AgentDragOverlay';
import type { AgentAssignment, AvailableAgent } from '@/types';

function createAgent(overrides: Partial<AgentAssignment> = {}): AgentAssignment {
  return {
    id: 'agent-1',
    slug: 'copilot',
    display_name: 'GitHub Copilot',
    config: null,
    ...overrides,
  };
}

function createAvailable(overrides: Partial<AvailableAgent> = {}): AvailableAgent {
  return {
    slug: 'copilot',
    display_name: 'GitHub Copilot',
    description: 'AI pair programmer',
    default_model_name: 'GPT-5',
    tools_count: 3,
    source: 'builtin',
    ...overrides,
  };
}

describe('AgentDragOverlay', () => {
  it('renders without crashing', () => {
    const { container } = render(<AgentDragOverlay agent={createAgent()} />);
    expect(container.firstElementChild).toBeTruthy();
  });

  it('shows the agent display name', () => {
    render(<AgentDragOverlay agent={createAgent()} />);
    expect(screen.getByText('GitHub Copilot')).toBeInTheDocument();
  });

  it('shows metadata line with model and tools count', () => {
    render(
      <AgentDragOverlay
        agent={createAgent()}
        availableAgents={[createAvailable()]}
      />,
    );
    expect(screen.getByText('GPT-5 · 3 tools')).toBeInTheDocument();
  });

  it('applies custom width when provided', () => {
    const { container } = render(
      <AgentDragOverlay agent={createAgent()} width={400} />,
    );
    expect(container.firstElementChild).toHaveStyle({ width: '400px' });
  });

  it('uses assigned pipeline model over agent default', () => {
    const agent = createAgent({
      config: { model_name: 'GPT-5.4' },
    });
    render(
      <AgentDragOverlay agent={agent} availableAgents={[createAvailable()]} />,
    );
    expect(screen.getByText(/GPT-5.4/)).toBeInTheDocument();
  });
});
