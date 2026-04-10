/**
 * Tests for ProjectSettings component.
 *
 * Covers: project selector rendering, empty projects state,
 * board display options when project selected, pipeline mappings textarea,
 * project selection interaction, and placeholder option.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@/test/test-utils';
import { ProjectSettings } from './ProjectSettings';

vi.mock('@/hooks/useSettings', () => ({
  useProjectSettings: vi.fn(() => ({
    settings: null,
    isLoading: false,
    updateSettings: vi.fn(),
  })),
}));

const projects = [
  { project_id: 'proj-1', name: 'Project Alpha' },
  { project_id: 'proj-2', name: 'Project Beta' },
];

describe('ProjectSettings', () => {
  it('renders project selector with projects', () => {
    render(<ProjectSettings projects={projects} />);
    const select = screen.getByLabelText('Project') as HTMLSelectElement;
    expect(select).toBeInTheDocument();

    const options = Array.from(select.options).map((o) => o.textContent);
    expect(options).toContain('Project Alpha');
    expect(options).toContain('Project Beta');
  });

  it('shows placeholder option in project selector', () => {
    render(<ProjectSettings projects={projects} />);
    const select = screen.getByLabelText('Project') as HTMLSelectElement;
    expect(select.value).toBe('');
    expect(Array.from(select.options).map((o) => o.textContent)).toContain('Select a project...');
  });

  it('shows "No projects available" when no projects', () => {
    render(<ProjectSettings projects={[]} />);
    expect(
      screen.getByText('No projects available. Select a project first.'),
    ).toBeInTheDocument();
  });

  it('shows board display options when project is selected', () => {
    render(<ProjectSettings projects={projects} selectedProjectId="proj-1" />);

    // With a selected project, board display heading should appear
    expect(screen.getByText('Board Display')).toBeInTheDocument();
    expect(screen.getByLabelText('Column Order (comma-separated)')).toBeInTheDocument();
    expect(screen.getByLabelText('Collapsed Columns (comma-separated)')).toBeInTheDocument();
    expect(screen.getByText('Show estimates')).toBeInTheDocument();
  });

  it('shows pipeline mappings textarea when project is selected', () => {
    render(<ProjectSettings projects={projects} selectedProjectId="proj-1" />);
    expect(screen.getByText('Pipeline Mappings')).toBeInTheDocument();
    expect(screen.getByLabelText('JSON (status → agent list)')).toBeInTheDocument();
  });

  it('shows board display after selecting a project from the dropdown', () => {
    render(<ProjectSettings projects={projects} />);
    const select = screen.getByLabelText('Project') as HTMLSelectElement;

    // Initially no project selected — board display hidden
    expect(screen.queryByText('Board Display')).not.toBeInTheDocument();

    // Select a project
    fireEvent.change(select, { target: { value: 'proj-1' } });
    expect(screen.getByText('Board Display')).toBeInTheDocument();
    expect(screen.getByText('Pipeline Mappings')).toBeInTheDocument();
  });
});
