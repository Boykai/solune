import { describe, it, expect, vi, beforeEach } from 'vitest';
import userEvent from '@testing-library/user-event';

import { render, screen } from '@/test/test-utils';
import { PipelineSelector } from '../PipelineSelector';

const mockPipelines = [
  { id: 'pipe-1', name: 'CI Pipeline', description: 'Main CI', stage_count: 2, agent_count: 3 },
  { id: 'pipe-2', name: 'Deploy Pipeline', description: 'Production deploy', stage_count: 3, agent_count: 1 },
];

vi.mock('@tanstack/react-query', async () => {
  const actual = await vi.importActual('@tanstack/react-query');
  return {
    ...actual,
    useQuery: () => ({
      data: { pipelines: mockPipelines },
      isLoading: false,
    }),
  };
});

function defaultProps() {
  return {
    projectId: 'proj-1',
    value: '',
    onChange: vi.fn(),
  };
}

describe('PipelineSelector', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders with the Agent Pipeline label', () => {
    render(<PipelineSelector {...defaultProps()} />);

    expect(screen.getByText('Agent Pipeline')).toBeInTheDocument();
  });

  it('renders the select with Auto as default option', () => {
    render(<PipelineSelector {...defaultProps()} />);

    const select = screen.getByRole('combobox', { name: /agent pipeline/i });
    expect(select).toHaveValue('');
  });

  it('renders pipeline options from the hook', () => {
    render(<PipelineSelector {...defaultProps()} />);

    expect(screen.getByRole('option', { name: 'Auto' })).toBeInTheDocument();
    expect(screen.getByRole('option', { name: 'CI Pipeline' })).toBeInTheDocument();
    expect(screen.getByRole('option', { name: 'Deploy Pipeline' })).toBeInTheDocument();
  });

  it('calls onChange when a pipeline is selected', async () => {
    const user = userEvent.setup();
    const props = defaultProps();
    render(<PipelineSelector {...props} />);

    await user.selectOptions(
      screen.getByRole('combobox', { name: /agent pipeline/i }),
      'pipe-1'
    );

    expect(props.onChange).toHaveBeenCalledWith('pipe-1');
  });

  it('shows Auto description when value is empty', () => {
    render(<PipelineSelector {...defaultProps()} />);

    expect(
      screen.getByText(/auto uses the project.*currently selected/i)
    ).toBeInTheDocument();
  });

  it('shows pipeline description when a specific pipeline is selected', () => {
    render(<PipelineSelector {...defaultProps()} value="pipe-1" />);

    expect(
      screen.getByText(/this chore will use the selected saved agent pipeline/i)
    ).toBeInTheDocument();
  });

  it('shows warning when selected pipeline does not exist', () => {
    render(<PipelineSelector {...defaultProps()} value="pipe-nonexistent" />);

    expect(
      screen.getByText(/selected pipeline no longer available/i)
    ).toBeInTheDocument();
  });

  it('does not show warning when value is empty', () => {
    render(<PipelineSelector {...defaultProps()} />);

    expect(
      screen.queryByText(/selected pipeline no longer available/i)
    ).not.toBeInTheDocument();
  });

  it('disables the select when disabled prop is true', () => {
    render(<PipelineSelector {...defaultProps()} disabled />);

    expect(screen.getByRole('combobox', { name: /agent pipeline/i })).toBeDisabled();
  });
});
