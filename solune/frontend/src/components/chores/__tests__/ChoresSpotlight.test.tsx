import { describe, it, expect, vi, beforeEach } from 'vitest';
import userEvent from '@testing-library/user-event';

import { render, screen, within } from '@/test/test-utils';
import { ChoresSpotlight } from '../ChoresSpotlight';
import type { Chore, ChoreTemplate } from '@/types';

vi.mock('../ChoreCard', () => ({
  ChoreCard: ({ chore }: { chore: Chore }) => (
    <div data-testid={`chore-card-${chore.id}`}>{chore.name}</div>
  ),
}));

function createChore(overrides: Partial<Chore> = {}): Chore {
  return {
    id: 'chore-1',
    project_id: 'proj-1',
    name: 'Weekly Cleanup',
    template_path: '.github/ISSUE_TEMPLATE/cleanup.md',
    template_content: '# Cleanup',
    schedule_type: 'time',
    schedule_value: 7,
    status: 'active',
    last_triggered_at: null,
    last_triggered_count: 0,
    current_issue_number: null,
    current_issue_node_id: null,
    pr_number: null,
    pr_url: null,
    tracking_issue_number: null,
    execution_count: 0,
    ai_enhance_enabled: true,
    agent_pipeline_id: '',
    is_preset: false,
    preset_id: '',
    created_at: '2026-04-06T00:00:00Z',
    updated_at: '2026-04-06T00:00:00Z',
    ...overrides,
  };
}

function createTemplate(overrides: Partial<ChoreTemplate> = {}): ChoreTemplate {
  return {
    name: 'Bug Report',
    about: 'Report a bug in the project',
    path: '.github/ISSUE_TEMPLATE/bug_report.md',
    content: '# Bug Report\n\n## Description',
    ...overrides,
  };
}

function defaultProps() {
  return {
    chores: [createChore()],
    uncreatedTemplates: [] as ChoreTemplate[],
    spotlightChores: [createChore()],
    projectId: 'proj-1',
    parentIssueCount: 3,
    activeCount: 5,
    pausedCount: 2,
    unscheduledCount: 1,
    editState: {},
    onEditStart: vi.fn(),
    onEditChange: vi.fn(),
    onEditSave: vi.fn(),
    onEditDiscard: vi.fn(),
    isSaving: false,
    onTemplateClick: vi.fn(),
  };
}

describe('ChoresSpotlight', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders nothing when no uncreated templates and no spotlight chores', () => {
    const { container } = render(
      <ChoresSpotlight
        {...defaultProps()}
        uncreatedTemplates={[]}
        spotlightChores={[]}
      />
    );

    expect(container.innerHTML).toBe('');
  });

  it('renders featured rituals heading', () => {
    render(<ChoresSpotlight {...defaultProps()} />);

    expect(screen.getByText('Featured rituals')).toBeInTheDocument();
  });

  it('renders stats cards with correct values', () => {
    render(
      <ChoresSpotlight
        {...defaultProps()}
        chores={[createChore(), createChore({ id: 'chore-2' }), createChore({ id: 'chore-3' })]}
        activeCount={5}
        pausedCount={2}
        unscheduledCount={1}
      />
    );

    const labels = ['Total chores', 'Active', 'Paused', 'Unscheduled'];
    labels.forEach((label) => {
      expect(screen.getByText(label)).toBeInTheDocument();
    });

    // Verify specific stat values next to their labels
    const totalCard = screen.getByText('Total chores').closest('div')!;
    expect(within(totalCard).getByText('3')).toBeInTheDocument();

    const activeCard = screen.getByText('Active').closest('div')!;
    expect(within(activeCard).getByText('5')).toBeInTheDocument();

    const pausedCard = screen.getByText('Paused').closest('div')!;
    expect(within(pausedCard).getByText('2')).toBeInTheDocument();

    const unscheduledCard = screen.getByText('Unscheduled').closest('div')!;
    expect(within(unscheduledCard).getByText('1')).toBeInTheDocument();
  });

  it('renders uncreated templates when available', () => {
    const templates = [
      createTemplate({ name: 'Bug Report', path: 'tpl-1' }),
      createTemplate({ name: 'Feature Request', path: 'tpl-2' }),
    ];

    render(
      <ChoresSpotlight {...defaultProps()} uncreatedTemplates={templates} />
    );

    expect(screen.getByText('Bug Report')).toBeInTheDocument();
    expect(screen.getByText('Feature Request')).toBeInTheDocument();
  });

  it('calls onTemplateClick when a template card is clicked', async () => {
    const user = userEvent.setup();
    const template = createTemplate({ name: 'Bug Report', path: 'tpl-1' });
    const props = defaultProps();
    render(<ChoresSpotlight {...props} uncreatedTemplates={[template]} />);

    await user.click(screen.getByText('Bug Report'));

    expect(props.onTemplateClick).toHaveBeenCalledWith(template);
  });

  it('renders spotlight ChoreCards when no uncreated templates', () => {
    const chore = createChore({ id: 'chore-spotlight', name: 'Spotlight Chore' });
    render(
      <ChoresSpotlight
        {...defaultProps()}
        uncreatedTemplates={[]}
        spotlightChores={[chore]}
      />
    );

    expect(screen.getByTestId('chore-card-chore-spotlight')).toBeInTheDocument();
    expect(screen.getByText('Spotlight Chore')).toBeInTheDocument();
  });

  it('shows template about text when available', () => {
    const template = createTemplate({
      name: 'Custom',
      path: 'tpl-about',
      about: 'A custom template for testing',
    });
    render(<ChoresSpotlight {...defaultProps()} uncreatedTemplates={[template]} />);

    expect(screen.getByText('A custom template for testing')).toBeInTheDocument();
  });

  it('limits uncreated templates to 3', () => {
    const templates = Array.from({ length: 5 }, (_, i) =>
      createTemplate({ name: `Template ${i}`, path: `tpl-${i}` })
    );
    render(<ChoresSpotlight {...defaultProps()} uncreatedTemplates={templates} />);

    expect(screen.getByText('Template 0')).toBeInTheDocument();
    expect(screen.getByText('Template 1')).toBeInTheDocument();
    expect(screen.getByText('Template 2')).toBeInTheDocument();
    expect(screen.queryByText('Template 3')).not.toBeInTheDocument();
  });
});
