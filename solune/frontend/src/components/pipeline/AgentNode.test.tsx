import { describe, expect, it, vi, beforeEach } from 'vitest';
import { fireEvent } from '@testing-library/react';
import { render, screen } from '@/test/test-utils';
import { expectNoA11yViolations } from '@/test/a11y-helpers';
import userEvent from '@testing-library/user-event';
import { AgentNode } from './AgentNode';
import type { PipelineAgentNode } from '@/types';

const mockUseModels = vi.fn();

vi.mock('@/hooks/useModels', () => ({
  useModels: (...args: unknown[]) => mockUseModels(...args),
}));

function createAgentNode(overrides: Partial<PipelineAgentNode> = {}): PipelineAgentNode {
  return {
    id: 'agent-node-1',
    agent_slug: 'copilot',
    agent_display_name: 'GitHub Copilot',
    model_id: '',
    model_name: '',
    tool_ids: [],
    tool_count: 0,
    config: {},
    ...overrides,
  };
}

describe('AgentNode', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseModels.mockReturnValue({
      models: [
        { id: 'gpt-5.4', name: 'GPT-5.4', provider: 'GitHub Models' },
        { id: 'gpt-5.4-mini', name: 'GPT-5.4 Mini', provider: 'GitHub Models' },
      ],
      modelsByProvider: [
        {
          provider: 'GitHub Models',
          models: [
            { id: 'gpt-5.4', name: 'GPT-5.4', provider: 'GitHub Models' },
            { id: 'gpt-5.4-mini', name: 'GPT-5.4 Mini', provider: 'GitHub Models' },
          ],
        },
      ],
      isLoading: false,
      isRefreshing: false,
      refreshModels: vi.fn(),
      error: null,
    });
  });

  it('shows an explicit model control for pipeline agents', () => {
    render(<AgentNode agentNode={createAgentNode()} onModelSelect={vi.fn()} onRemove={vi.fn()} />);

    expect(screen.getByText('Model')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /auto/i })).toBeInTheDocument();
  });

  it('lets the user change the model from the pipeline agent card', async () => {
    const onModelSelect = vi.fn();
    render(
      <AgentNode agentNode={createAgentNode()} onModelSelect={onModelSelect} onRemove={vi.fn()} />
    );

    const user = userEvent.setup();
    await user.click(screen.getByRole('button', { name: /auto/i }));
    await user.click(screen.getByRole('button', { name: /^gpt-5\.4$/i }));

    expect(onModelSelect).toHaveBeenCalledWith('gpt-5.4', 'GPT-5.4', undefined);
  });

  it('stops pointerdown from interactive controls reaching the drag listener', () => {
    const onPointerDown = vi.fn();

    render(
      <AgentNode
        agentNode={createAgentNode()}
        onModelSelect={vi.fn()}
        onRemove={vi.fn()}
        dragHandleListeners={{ onPointerDown } as never}
      />
    );

    fireEvent.pointerDown(screen.getByRole('button', { name: /auto/i }));
    fireEvent.pointerDown(screen.getByRole('button', { name: 'Remove agent' }));

    expect(onPointerDown).not.toHaveBeenCalled();
  });

  it('has no accessibility violations', async () => {
    const { container } = render(
      <AgentNode agentNode={createAgentNode()} onModelSelect={vi.fn()} onRemove={vi.fn()} />
    );

    await expectNoA11yViolations(container);
  });

  // ── Human Agent: Delay Until Auto-Merge ──

  describe('Human agent delay toggle', () => {
    it('shows "Manual review" badge for human agent without delay', () => {
      render(
        <AgentNode
          agentNode={createAgentNode({ agent_slug: 'human', agent_display_name: 'Human' })}
          onModelSelect={vi.fn()}
          onRemove={vi.fn()}
          onConfigChange={vi.fn()}
        />
      );

      expect(screen.getByText('Manual review')).toBeInTheDocument();
    });

    it('shows delay toggle checkbox for human agent with onConfigChange', () => {
      render(
        <AgentNode
          agentNode={createAgentNode({ agent_slug: 'human', agent_display_name: 'Human' })}
          onModelSelect={vi.fn()}
          onRemove={vi.fn()}
          onConfigChange={vi.fn()}
        />
      );

      expect(screen.getByLabelText('Delay until auto-merge')).toBeInTheDocument();
    });

    it('does not show delay toggle for non-human agents', () => {
      render(
        <AgentNode
          agentNode={createAgentNode({ agent_slug: 'copilot' })}
          onModelSelect={vi.fn()}
          onRemove={vi.fn()}
          onConfigChange={vi.fn()}
        />
      );

      expect(screen.queryByLabelText('Delay until auto-merge')).not.toBeInTheDocument();
    });

    it('shows auto-merge badge when delay_seconds is set', () => {
      render(
        <AgentNode
          agentNode={createAgentNode({
            agent_slug: 'human',
            agent_display_name: 'Human',
            config: { delay_seconds: 300 },
          })}
          onModelSelect={vi.fn()}
          onRemove={vi.fn()}
          onConfigChange={vi.fn()}
        />
      );

      expect(screen.getByText(/Auto-merge: 5m/)).toBeInTheDocument();
    });

    it('shows auto-merge badge with hours format for large delays', () => {
      render(
        <AgentNode
          agentNode={createAgentNode({
            agent_slug: 'human',
            agent_display_name: 'Human',
            config: { delay_seconds: 3600 },
          })}
          onModelSelect={vi.fn()}
          onRemove={vi.fn()}
          onConfigChange={vi.fn()}
        />
      );

      expect(screen.getByText(/Auto-merge: 1h/)).toBeInTheDocument();
    });

    it('shows numeric input when delay is enabled', () => {
      render(
        <AgentNode
          agentNode={createAgentNode({
            agent_slug: 'human',
            agent_display_name: 'Human',
            config: { delay_seconds: 300 },
          })}
          onModelSelect={vi.fn()}
          onRemove={vi.fn()}
          onConfigChange={vi.fn()}
        />
      );

      const input = screen.getByLabelText('Delay seconds');
      expect(input).toBeInTheDocument();
      expect(input).toHaveValue(300);
    });

    it('does not show numeric input when delay is disabled', () => {
      render(
        <AgentNode
          agentNode={createAgentNode({ agent_slug: 'human', agent_display_name: 'Human' })}
          onModelSelect={vi.fn()}
          onRemove={vi.fn()}
          onConfigChange={vi.fn()}
        />
      );

      expect(screen.queryByLabelText('Delay seconds')).not.toBeInTheDocument();
    });

    it('calls onConfigChange with delay_seconds when toggle is turned on', async () => {
      const onConfigChange = vi.fn();
      render(
        <AgentNode
          agentNode={createAgentNode({ agent_slug: 'human', agent_display_name: 'Human' })}
          onModelSelect={vi.fn()}
          onRemove={vi.fn()}
          onConfigChange={onConfigChange}
        />
      );

      const user = userEvent.setup();
      await user.click(screen.getByLabelText('Delay until auto-merge'));

      // Should enable delay with default 300s
      expect(onConfigChange).toHaveBeenCalledWith(
        expect.objectContaining({ delay_seconds: 300 })
      );
    });

    it('calls onConfigChange without delay_seconds when toggle is turned off', async () => {
      const onConfigChange = vi.fn();
      render(
        <AgentNode
          agentNode={createAgentNode({
            agent_slug: 'human',
            agent_display_name: 'Human',
            config: { delay_seconds: 300 },
          })}
          onModelSelect={vi.fn()}
          onRemove={vi.fn()}
          onConfigChange={onConfigChange}
        />
      );

      const user = userEvent.setup();
      await user.click(screen.getByLabelText('Delay until auto-merge'));

      // Should disable delay — config should NOT contain delay_seconds
      expect(onConfigChange).toHaveBeenCalledWith(
        expect.not.objectContaining({ delay_seconds: expect.anything() })
      );
    });

    it('shows read-only badge for human agent without onConfigChange', () => {
      render(
        <AgentNode
          agentNode={createAgentNode({
            agent_slug: 'human',
            agent_display_name: 'Human',
            config: { delay_seconds: 60 },
          })}
          onModelSelect={vi.fn()}
          onRemove={vi.fn()}
        />
      );

      expect(screen.getByText(/Auto-merge: 1m/)).toBeInTheDocument();
      // Toggle should NOT be visible in read-only mode
      expect(screen.queryByLabelText('Delay until auto-merge')).not.toBeInTheDocument();
    });

    it('updates delay via numeric input', async () => {
      const onConfigChange = vi.fn();
      render(
        <AgentNode
          agentNode={createAgentNode({
            agent_slug: 'human',
            agent_display_name: 'Human',
            config: { delay_seconds: 300 },
          })}
          onModelSelect={vi.fn()}
          onRemove={vi.fn()}
          onConfigChange={onConfigChange}
        />
      );

      const user = userEvent.setup();
      const input = screen.getByLabelText('Delay seconds');
      await user.clear(input);
      await user.type(input, '600');

      // Should have called onConfigChange with the updated delay
      expect(onConfigChange).toHaveBeenCalledWith(
        expect.objectContaining({ delay_seconds: 600 })
      );
    });
  });
});
