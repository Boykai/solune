/**
 * Tests for ProjectSettings component.
 *
 * Covers: project selector rendering, empty projects state,
 * board display options when project selected, and pipeline mappings textarea.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@/test/test-utils';
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

  it('shows "No projects available" when no projects', () => {
    render(<ProjectSettings projects={[]} />);
    expect(
      screen.getByText('No projects available. Select a project first.'),
    ).toBeInTheDocument();
  });

  it('shows board display options when project is selected', async () => {
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
});
