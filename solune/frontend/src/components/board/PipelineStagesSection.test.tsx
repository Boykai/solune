import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@/test/test-utils';
import { PipelineStagesSection } from './PipelineStagesSection';
import type { StatusColor } from '@/types';

vi.mock('react-router-dom', async (importOriginal) => ({
  ...(await importOriginal<typeof import('react-router-dom')>()),
  Link: ({ children, to, ...rest }: { children: React.ReactNode; to: string }) => (
    <a href={to} {...rest}>{children}</a>
  ),
}));

interface BoardColumn {
  status: { option_id: string; name: string; color: StatusColor };
  items: unknown[];
  item_count: number;
}

function createColumn(name: string, color: StatusColor = 'GRAY', itemCount = 0): BoardColumn {
  return {
    status: { option_id: `opt-${name}`, name, color },
    items: [],
    item_count: itemCount,
  };
}

const defaultMutation = { mutate: vi.fn(), isPending: false };

describe('PipelineStagesSection', () => {
  it('renders stage cards for each column', () => {
    const columns = [createColumn('Todo', 'BLUE', 3), createColumn('In Progress', 'GREEN', 5)];
    render(
      <PipelineStagesSection
        columns={columns}
        savedPipelines={[]}
        assignedPipelineId={undefined}
        assignPipelineMutation={defaultMutation}
      />,
    );
    expect(screen.getByText('Todo')).toBeInTheDocument();
    expect(screen.getByText('In Progress')).toBeInTheDocument();
    expect(screen.getByText('3 items')).toBeInTheDocument();
    expect(screen.getByText('5 items')).toBeInTheDocument();
  });

  it('renders heading "Pipeline Stages"', () => {
    render(
      <PipelineStagesSection
        columns={[]}
        savedPipelines={[]}
        assignedPipelineId={undefined}
        assignPipelineMutation={defaultMutation}
      />,
    );
    expect(screen.getByText('Pipeline Stages')).toBeInTheDocument();
  });

  it('shows "Create new pipeline" link when no saved pipelines', () => {
    render(
      <PipelineStagesSection
        columns={[]}
        savedPipelines={[]}
        assignedPipelineId={undefined}
        assignPipelineMutation={defaultMutation}
      />,
    );
    expect(screen.getByText('Create new pipeline')).toBeInTheDocument();
  });

  it('shows pipeline selector trigger when saved pipelines exist', () => {
    const pipelines = [{ id: 'p1', name: 'My Pipeline', stages: [] }];
    render(
      <PipelineStagesSection
        columns={[createColumn('Todo')]}
        savedPipelines={pipelines}
        assignedPipelineId={undefined}
        assignPipelineMutation={defaultMutation}
      />,
    );
    expect(screen.getByRole('button', { name: 'Agent Pipeline' })).toBeInTheDocument();
    expect(screen.getByText('No pipeline selected')).toBeInTheDocument();
  });

  it('shows assigned pipeline name when one is selected', () => {
    const pipelines = [{ id: 'p1', name: 'My Pipeline', stages: [] }];
    render(
      <PipelineStagesSection
        columns={[createColumn('Todo')]}
        savedPipelines={pipelines}
        assignedPipelineId="p1"
        assignPipelineMutation={defaultMutation}
      />,
    );
    expect(screen.getByText('My Pipeline')).toBeInTheDocument();
  });

  it('shows "No agents" when no agents are assigned to a stage', () => {
    render(
      <PipelineStagesSection
        columns={[createColumn('Todo')]}
        savedPipelines={[]}
        assignedPipelineId={undefined}
        assignPipelineMutation={defaultMutation}
      />,
    );
    expect(screen.getByText('No agents')).toBeInTheDocument();
  });
});
