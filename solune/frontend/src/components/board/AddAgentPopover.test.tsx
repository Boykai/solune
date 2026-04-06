import React from 'react';
import { describe, expect, it, vi } from 'vitest';
import { fireEvent } from '@testing-library/react';
import { render, screen } from '@/test/test-utils';
import { AddAgentPopover } from './AddAgentPopover';
import type { AvailableAgent, AgentAssignment } from '@/types';

vi.mock('react-dom', async (importOriginal) => ({
  ...(await importOriginal<typeof import('react-dom')>()),
  createPortal: (children: React.ReactNode) => children,
}));

function createAvailableAgent(overrides: Partial<AvailableAgent> = {}): AvailableAgent {
  return {
    slug: 'reviewer',
    display_name: 'Reviewer',
    description: 'Reviews code',
    source: 'builtin',
    ...overrides,
  };
}

function createAssignment(overrides: Partial<AgentAssignment> = {}): AgentAssignment {
  return {
    id: 'a-1',
    slug: 'reviewer',
    display_name: 'Reviewer',
    config: null,
    ...overrides,
  };
}

const defaultProps = {
  status: 'In Progress',
  availableAgents: [] as AvailableAgent[],
  assignedAgents: [] as AgentAssignment[],
  isLoading: false,
  error: null,
  onRetry: vi.fn(),
  onAddAgent: vi.fn(),
};

describe('AddAgentPopover', () => {
  it('renders trigger button', () => {
    render(<AddAgentPopover {...defaultProps} />);
    expect(screen.getByRole('button', { name: /add agent to in progress/i })).toBeInTheDocument();
  });

  it('shows loading state when popover is open', () => {
    render(<AddAgentPopover {...defaultProps} isLoading={true} />);
    fireEvent.click(screen.getByRole('button', { name: /add agent/i }));
    expect(screen.getByText('Loading agents...')).toBeInTheDocument();
  });

  it('shows error with retry button when popover is open', () => {
    const onRetry = vi.fn();
    render(
      <AddAgentPopover {...defaultProps} error="Failed to load" onRetry={onRetry} />,
    );
    fireEvent.click(screen.getByRole('button', { name: /add agent/i }));
    expect(screen.getByText('Failed to load')).toBeInTheDocument();
    fireEvent.click(screen.getByText('Retry'));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it('renders agent list items when popover is open', () => {
    const agents = [
      createAvailableAgent({ slug: 'copilot', display_name: 'Copilot' }),
      createAvailableAgent({ slug: 'reviewer', display_name: 'Reviewer' }),
    ];
    render(<AddAgentPopover {...defaultProps} availableAgents={agents} />);
    fireEvent.click(screen.getByRole('button', { name: /add agent/i }));
    expect(screen.getByText('copilot')).toBeInTheDocument();
    expect(screen.getByText('reviewer')).toBeInTheDocument();
  });

  it('calls onAddAgent when an agent is selected', () => {
    const onAddAgent = vi.fn();
    const agents = [createAvailableAgent({ slug: 'copilot', display_name: 'Copilot' })];
    render(<AddAgentPopover {...defaultProps} availableAgents={agents} onAddAgent={onAddAgent} />);
    fireEvent.click(screen.getByRole('button', { name: /add agent/i }));
    fireEvent.click(screen.getByRole('button', { name: 'Copilot' }));
    expect(onAddAgent).toHaveBeenCalledWith('In Progress', agents[0]);
  });

  it('shows duplicate indicator for already assigned agents', () => {
    const agents = [createAvailableAgent({ slug: 'reviewer', display_name: 'Reviewer' })];
    const assigned = [createAssignment({ slug: 'reviewer' })];
    render(
      <AddAgentPopover
        {...defaultProps}
        availableAgents={agents}
        assignedAgents={assigned}
      />,
    );
    fireEvent.click(screen.getByRole('button', { name: /add agent/i }));
    expect(screen.getByText('already assigned')).toBeInTheDocument();
  });
});
