import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@/test/test-utils';
import type { AgentConfig } from '@/services/api';

const mockDeleteAgent = vi.fn();
const mockConfirm = vi.fn();
const mockMutateAsync = vi.fn();

vi.mock('@/hooks/useAgents', () => ({
  useUndoableDeleteAgent: () => ({ deleteAgent: mockDeleteAgent, pendingIds: new Set() }),
  useUpdateAgent: () => ({
    mutateAsync: mockMutateAsync,
    isPending: false,
    isError: false,
    error: null,
  }),
}));

vi.mock('@/hooks/useConfirmation', () => ({
  useConfirmation: () => ({ confirm: mockConfirm }),
}));

vi.mock('@/components/agents/AgentIconPickerModal', () => ({
  AgentIconPickerModal: () => null,
}));

vi.mock('@/components/agents/InstallConfirmDialog', () => ({
  InstallConfirmDialog: () => null,
}));

import { AgentCard } from '../AgentCard';

function createAgent(overrides: Partial<AgentConfig> = {}): AgentConfig {
  return {
    id: 'a-1',
    name: 'Code Reviewer',
    slug: 'code-reviewer',
    description: 'Reviews pull requests',
    icon_name: null,
    system_prompt: 'You are a code reviewer.',
    default_model_id: 'm-1',
    default_model_name: 'GPT-4',
    status: 'active',
    tools: ['eslint', 'prettier'],
    status_column: null,
    github_issue_number: null,
    github_pr_number: null,
    branch_name: null,
    source: 'local',
    created_at: '2025-01-15T00:00:00Z',
    agent_type: 'custom',
    ...overrides,
  };
}

describe('AgentCard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockConfirm.mockResolvedValue(false);
  });

  it('renders the agent display name', () => {
    render(<AgentCard agent={createAgent()} projectId="proj-1" />);
    expect(screen.getByText('Code Reviewer')).toBeInTheDocument();
  });

  it('renders the Active status badge for an active agent', () => {
    render(<AgentCard agent={createAgent()} projectId="proj-1" />);
    expect(screen.getByText('Active')).toBeInTheDocument();
  });

  it('renders the Pending PR status badge', () => {
    render(<AgentCard agent={createAgent({ status: 'pending_pr' })} projectId="proj-1" />);
    expect(screen.getByText('Pending PR')).toBeInTheDocument();
  });

  it('renders agent description', () => {
    render(<AgentCard agent={createAgent()} projectId="proj-1" />);
    expect(screen.getByText('Reviews pull requests')).toBeInTheDocument();
  });

  it('renders tool chips', () => {
    render(<AgentCard agent={createAgent()} projectId="proj-1" />);
    expect(screen.getByText('eslint')).toBeInTheDocument();
    expect(screen.getByText('prettier')).toBeInTheDocument();
  });

  it('shows tool count', () => {
    render(<AgentCard agent={createAgent()} projectId="proj-1" />);
    expect(screen.getByText('2 tools')).toBeInTheDocument();
  });

  it('renders Edit button when onEdit is provided', () => {
    render(<AgentCard agent={createAgent()} projectId="proj-1" onEdit={vi.fn()} />);
    expect(screen.getByText('Edit')).toBeInTheDocument();
  });

  it('does not render Edit button when onEdit is not provided', () => {
    render(<AgentCard agent={createAgent()} projectId="proj-1" />);
    expect(screen.queryByText('Edit')).not.toBeInTheDocument();
  });

  it('renders Delete button for deletable agents', () => {
    render(<AgentCard agent={createAgent()} projectId="proj-1" />);
    expect(screen.getByText('Delete')).toBeInTheDocument();
  });

  it('hides Delete button for pending_deletion agents', () => {
    render(<AgentCard agent={createAgent({ status: 'pending_deletion' })} projectId="proj-1" />);
    expect(screen.queryByText('Delete')).not.toBeInTheDocument();
    expect(screen.getByText('Deletion pending')).toBeInTheDocument();
  });

  it('shows "Awaiting merge to main" for pending_pr local agents', () => {
    render(
      <AgentCard
        agent={createAgent({ status: 'pending_pr', source: 'local' })}
        projectId="proj-1"
      />,
    );
    expect(screen.getByText('Awaiting merge to main')).toBeInTheDocument();
  });

  it('shows pipeline config count', () => {
    render(<AgentCard agent={createAgent()} projectId="proj-1" pipelineConfigCount={3} />);
    expect(screen.getByText('3 configs')).toBeInTheDocument();
  });

  it('shows pending sub-issue count', () => {
    render(<AgentCard agent={createAgent()} projectId="proj-1" pendingSubIssueCount={5} />);
    expect(screen.getByText('5 open')).toBeInTheDocument();
  });

  it('renders source label as Local for local agents', () => {
    render(<AgentCard agent={createAgent({ source: 'local' })} projectId="proj-1" />);
    expect(screen.getByText('Local')).toBeInTheDocument();
  });

  it('renders source label as Repository for repo agents', () => {
    render(<AgentCard agent={createAgent({ source: 'repo' })} projectId="proj-1" />);
    expect(screen.getByText('Repository')).toBeInTheDocument();
  });
});
