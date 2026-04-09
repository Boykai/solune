import { describe, it, expect, vi, beforeEach } from 'vitest';
import userEvent from '@testing-library/user-event';
import { renderWithProviders, screen } from '@/test/test-utils';
import type { AgentConfig } from '@/services/api';
import { BulkModelUpdateDialog } from '../BulkModelUpdateDialog';

const mockMutate = vi.fn();

vi.mock('@/hooks/useAgents', () => ({
  useBulkUpdateModels: () => ({
    mutate: mockMutate,
    isPending: false,
    isError: false,
    error: null,
  }),
}));

vi.mock('@/components/pipeline/ModelSelector', () => ({
  ModelSelector: ({
    onSelect,
  }: {
    selectedModelId: string | null;
    onSelect: (id: string, name: string) => void;
  }) => (
    <button
      type="button"
      data-testid="model-selector"
      onClick={() => onSelect('model-1', 'GPT-4o')}
    >
      Select Model
    </button>
  ),
}));

function createAgent(overrides: Partial<AgentConfig> = {}): AgentConfig {
  return {
    id: 'a-1',
    name: 'Agent One',
    slug: 'agent-one',
    description: '',
    icon_name: null,
    system_prompt: '',
    default_model_id: 'm-old',
    default_model_name: 'Old Model',
    status: 'active',
    tools: [],
    status_column: null,
    github_issue_number: null,
    github_pr_number: null,
    branch_name: null,
    source: 'local',
    created_at: '2025-01-01T00:00:00Z',
    agent_type: 'custom',
    ...overrides,
  };
}

describe('BulkModelUpdateDialog', () => {
  const agents = [
    createAgent({ id: 'a-1', name: 'Agent One' }),
    createAgent({ id: 'a-2', name: 'Agent Two' }),
  ];

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('returns null when not open', () => {
    const { container } = renderWithProviders(
      <BulkModelUpdateDialog
        open={false}
        onOpenChange={vi.fn()}
        agents={agents}
        projectId="proj-1"
        onSuccess={vi.fn()}
      />,
    );
    expect(container.querySelector('[role="dialog"]')).toBeNull();
  });

  it('renders step 1 with title and agent count', () => {
    renderWithProviders(
      <BulkModelUpdateDialog
        open={true}
        onOpenChange={vi.fn()}
        agents={agents}
        projectId="proj-1"
        onSuccess={vi.fn()}
      />,
    );
    expect(screen.getByText('Update All Agent Models')).toBeInTheDocument();
    expect(screen.getByText(/all 2 agents/i)).toBeInTheDocument();
  });

  it('renders Cancel button on step 1', () => {
    renderWithProviders(
      <BulkModelUpdateDialog
        open={true}
        onOpenChange={vi.fn()}
        agents={agents}
        projectId="proj-1"
        onSuccess={vi.fn()}
      />,
    );
    expect(screen.getByText('Cancel')).toBeInTheDocument();
  });

  it('disables Next button until a model is selected', () => {
    renderWithProviders(
      <BulkModelUpdateDialog
        open={true}
        onOpenChange={vi.fn()}
        agents={agents}
        projectId="proj-1"
        onSuccess={vi.fn()}
      />,
    );
    expect(screen.getByText('Next')).toBeDisabled();
  });

  it('enables Next after selecting a model and navigates to step 2', async () => {
    const user = userEvent.setup();
    renderWithProviders(
      <BulkModelUpdateDialog
        open={true}
        onOpenChange={vi.fn()}
        agents={agents}
        projectId="proj-1"
        onSuccess={vi.fn()}
      />,
    );

    await user.click(screen.getByTestId('model-selector'));
    expect(screen.getByText('Next')).toBeEnabled();

    await user.click(screen.getByText('Next'));
    expect(screen.getByText('Confirm Bulk Update')).toBeInTheDocument();
    expect(screen.getByText('Agent One')).toBeInTheDocument();
    expect(screen.getByText('Agent Two')).toBeInTheDocument();
  });

  it('shows Back button on step 2 that returns to step 1', async () => {
    const user = userEvent.setup();
    renderWithProviders(
      <BulkModelUpdateDialog
        open={true}
        onOpenChange={vi.fn()}
        agents={agents}
        projectId="proj-1"
        onSuccess={vi.fn()}
      />,
    );

    await user.click(screen.getByTestId('model-selector'));
    await user.click(screen.getByText('Next'));
    expect(screen.getByText('Confirm Bulk Update')).toBeInTheDocument();

    await user.click(screen.getByText('Back'));
    expect(screen.getByText('Update All Agent Models')).toBeInTheDocument();
  });

  it('calls mutate on Confirm', async () => {
    const user = userEvent.setup();
    renderWithProviders(
      <BulkModelUpdateDialog
        open={true}
        onOpenChange={vi.fn()}
        agents={agents}
        projectId="proj-1"
        onSuccess={vi.fn()}
      />,
    );

    await user.click(screen.getByTestId('model-selector'));
    await user.click(screen.getByText('Next'));
    await user.click(screen.getByText('Confirm'));

    expect(mockMutate).toHaveBeenCalledWith(
      { targetModelId: 'model-1', targetModelName: 'GPT-4o' },
      expect.objectContaining({ onSuccess: expect.any(Function) }),
    );
  });
});
