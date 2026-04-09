import { describe, it, expect, vi, beforeEach } from 'vitest';
import userEvent from '@testing-library/user-event';
import { renderWithProviders, screen } from '@/test/test-utils';
import type { AgentConfig } from '@/services/api';

const mockMutateAsync = vi.fn();

vi.mock('@/hooks/useAgents', () => ({
  useUpdateAgent: () => ({
    mutateAsync: mockMutateAsync,
    isPending: false,
    isError: false,
    error: null,
  }),
}));

vi.mock('@/components/agents/AgentIconCatalog', () => ({
  AgentIconCatalog: () => <div data-testid="icon-catalog" />,
}));

vi.mock('@/components/agents/ToolsEditor', () => ({
  ToolsEditor: () => <div data-testid="tools-editor" />,
}));

vi.mock('@/components/activity/EntityHistoryPanel', () => ({
  EntityHistoryPanel: () => <div data-testid="entity-history" />,
}));

import { AgentInlineEditor } from '../AgentInlineEditor';

function createAgent(overrides: Partial<AgentConfig> = {}): AgentConfig {
  return {
    id: 'a-1',
    name: 'Code Reviewer',
    slug: 'code-reviewer',
    description: 'Reviews pull requests',
    icon_name: null,
    system_prompt: 'You review code.',
    default_model_id: 'm-1',
    default_model_name: 'GPT-4',
    status: 'active',
    tools: ['eslint'],
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

describe('AgentInlineEditor', () => {
  const onDirtyChange = vi.fn();
  const onCancel = vi.fn();
  const onSaved = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    mockMutateAsync.mockResolvedValue({ pr_url: 'https://github.com/pr/1' });
  });

  it('renders name input with agent name', () => {
    renderWithProviders(
      <AgentInlineEditor
        agent={createAgent()}
        projectId="proj-1"
        onDirtyChange={onDirtyChange}
        onCancel={onCancel}
        onSaved={onSaved}
      />,
    );
    const nameInput = screen.getByLabelText('Name');
    expect(nameInput).toHaveValue('Code Reviewer');
  });

  it('renders system prompt textarea', () => {
    renderWithProviders(
      <AgentInlineEditor
        agent={createAgent()}
        projectId="proj-1"
        onDirtyChange={onDirtyChange}
        onCancel={onCancel}
        onSaved={onSaved}
      />,
    );
    const promptInput = screen.getByLabelText(/system prompt/i);
    expect(promptInput).toHaveValue('You review code.');
  });

  it('renders the agent heading', () => {
    renderWithProviders(
      <AgentInlineEditor
        agent={createAgent()}
        projectId="proj-1"
        onDirtyChange={onDirtyChange}
        onCancel={onCancel}
        onSaved={onSaved}
      />,
    );
    expect(screen.getByText('Editing agent definition')).toBeInTheDocument();
    expect(screen.getByText('Code Reviewer')).toBeInTheDocument();
  });

  it('renders Close Editor button that calls onCancel', async () => {
    const user = userEvent.setup();
    renderWithProviders(
      <AgentInlineEditor
        agent={createAgent()}
        projectId="proj-1"
        onDirtyChange={onDirtyChange}
        onCancel={onCancel}
        onSaved={onSaved}
      />,
    );
    await user.click(screen.getByText('Close Editor'));
    expect(onCancel).toHaveBeenCalledTimes(1);
  });

  it('shows Save Changes button', () => {
    renderWithProviders(
      <AgentInlineEditor
        agent={createAgent()}
        projectId="proj-1"
        onDirtyChange={onDirtyChange}
        onCancel={onCancel}
        onSaved={onSaved}
      />,
    );
    expect(screen.getByText('Save Changes')).toBeInTheDocument();
  });

  it('renders icon catalog section', () => {
    renderWithProviders(
      <AgentInlineEditor
        agent={createAgent()}
        projectId="proj-1"
        onDirtyChange={onDirtyChange}
        onCancel={onCancel}
        onSaved={onSaved}
      />,
    );
    expect(screen.getByText('Celestial Icon')).toBeInTheDocument();
  });

  it('notifies dirty state when name is changed', async () => {
    const user = userEvent.setup();
    renderWithProviders(
      <AgentInlineEditor
        agent={createAgent()}
        projectId="proj-1"
        onDirtyChange={onDirtyChange}
        onCancel={onCancel}
        onSaved={onSaved}
      />,
    );
    const nameInput = screen.getByLabelText('Name');
    await user.clear(nameInput);
    await user.type(nameInput, 'New Agent Name');
    // onDirtyChange should have been called with true at some point
    expect(onDirtyChange).toHaveBeenCalledWith(true);
  });

  it('shows Unsaved changes badge when form is dirty', async () => {
    const user = userEvent.setup();
    renderWithProviders(
      <AgentInlineEditor
        agent={createAgent()}
        projectId="proj-1"
        onDirtyChange={onDirtyChange}
        onCancel={onCancel}
        onSaved={onSaved}
      />,
    );
    const nameInput = screen.getByLabelText('Name');
    await user.clear(nameInput);
    await user.type(nameInput, 'Different Name');
    expect(screen.getByText('Unsaved changes')).toBeInTheDocument();
  });

  it('shows validation error when saving with empty name', async () => {
    const user = userEvent.setup();
    renderWithProviders(
      <AgentInlineEditor
        agent={createAgent()}
        projectId="proj-1"
        onDirtyChange={onDirtyChange}
        onCancel={onCancel}
        onSaved={onSaved}
      />,
    );
    const nameInput = screen.getByLabelText('Name');
    await user.clear(nameInput);
    await user.click(screen.getByText('Save Changes'));
    expect(screen.getByText('Name is required')).toBeInTheDocument();
    expect(mockMutateAsync).not.toHaveBeenCalled();
  });

  it('shows validation error when saving with empty system prompt', async () => {
    const user = userEvent.setup();
    renderWithProviders(
      <AgentInlineEditor
        agent={createAgent()}
        projectId="proj-1"
        onDirtyChange={onDirtyChange}
        onCancel={onCancel}
        onSaved={onSaved}
      />,
    );
    const promptInput = screen.getByLabelText(/system prompt/i);
    await user.clear(promptInput);
    await user.click(screen.getByText('Save Changes'));
    expect(screen.getByText('System prompt is required')).toBeInTheDocument();
    expect(mockMutateAsync).not.toHaveBeenCalled();
  });

  it('calls mutateAsync with correct data on successful save', async () => {
    const user = userEvent.setup();
    renderWithProviders(
      <AgentInlineEditor
        agent={createAgent()}
        projectId="proj-1"
        onDirtyChange={onDirtyChange}
        onCancel={onCancel}
        onSaved={onSaved}
      />,
    );
    await user.click(screen.getByText('Save Changes'));
    expect(mockMutateAsync).toHaveBeenCalledWith(
      expect.objectContaining({
        agentId: 'a-1',
        data: expect.objectContaining({
          name: 'Code Reviewer',
          system_prompt: 'You review code.',
        }),
      }),
    );
    expect(onSaved).toHaveBeenCalledWith('https://github.com/pr/1', 'Code Reviewer');
  });

  it('displays error when save fails', async () => {
    mockMutateAsync.mockRejectedValueOnce(new Error('Network error'));
    const user = userEvent.setup();
    renderWithProviders(
      <AgentInlineEditor
        agent={createAgent()}
        projectId="proj-1"
        onDirtyChange={onDirtyChange}
        onCancel={onCancel}
        onSaved={onSaved}
      />,
    );
    await user.click(screen.getByText('Save Changes'));
    expect(screen.getByText('Network error')).toBeInTheDocument();
    expect(onSaved).not.toHaveBeenCalled();
  });

  it('resets fields when Discard is clicked after making changes', async () => {
    const user = userEvent.setup();
    renderWithProviders(
      <AgentInlineEditor
        agent={createAgent()}
        projectId="proj-1"
        onDirtyChange={onDirtyChange}
        onCancel={onCancel}
        onSaved={onSaved}
      />,
    );
    const nameInput = screen.getByLabelText('Name');
    await user.clear(nameInput);
    await user.type(nameInput, 'Different Name');
    // Discard should now be enabled
    await user.click(screen.getByText('Discard'));
    expect(nameInput).toHaveValue('Code Reviewer');
  });
});
