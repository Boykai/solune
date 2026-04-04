import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ProjectSelector } from './ProjectSelector';
import type { Project } from '@/types';

// Mock hooks
const mockCreateProject = {
  mutate: vi.fn(),
  isPending: false,
};

vi.mock('@/hooks/useApps', () => ({
  useOwners: () => ({
    data: [
      { login: 'testuser', type: 'User' },
      { login: 'testorg', type: 'Organization' },
    ],
  }),
}));

vi.mock('@/hooks/useProjects', () => ({
  useCreateProject: () => mockCreateProject,
}));

const projects: Project[] = [
  {
    project_id: 'proj-1',
    name: 'Project Alpha',
    owner_login: 'testuser',
    project_number: 1,
    columns: [],
  },
  {
    project_id: 'proj-2',
    name: 'Project Beta',
    owner_login: 'testorg',
    project_number: 2,
    columns: [],
  },
];

const defaultProps = {
  isOpen: true,
  onClose: vi.fn(),
  projects,
  selectedProjectId: 'proj-1',
  isLoading: false,
  onSelectProject: vi.fn(),
};

describe('ProjectSelector', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockCreateProject.mutate = vi.fn();
    mockCreateProject.isPending = false;
  });

  it('renders nothing when closed', () => {
    const { container } = render(<ProjectSelector {...defaultProps} isOpen={false} />);
    expect(container.firstChild).toBeNull();
  });

  it('renders project list when open', () => {
    render(<ProjectSelector {...defaultProps} />);
    expect(screen.getByText('Project Alpha')).toBeInTheDocument();
    expect(screen.getByText('Project Beta')).toBeInTheDocument();
  });

  it('renders Projects header', () => {
    render(<ProjectSelector {...defaultProps} />);
    expect(screen.getByText('Projects')).toBeInTheDocument();
  });

  it('shows loading spinner when loading', () => {
    render(<ProjectSelector {...defaultProps} isLoading={true} projects={[]} />);
    expect(screen.queryByText('Project Alpha')).not.toBeInTheDocument();
  });

  it('shows empty state when no projects', () => {
    render(<ProjectSelector {...defaultProps} projects={[]} />);
    expect(screen.getByText('No projects available')).toBeInTheDocument();
  });

  it('calls onSelectProject and onClose when project clicked', () => {
    render(<ProjectSelector {...defaultProps} />);
    fireEvent.click(screen.getByText('Project Beta'));
    expect(defaultProps.onSelectProject).toHaveBeenCalledWith('proj-2');
    expect(defaultProps.onClose).toHaveBeenCalled();
  });

  it('displays check icon for selected project', () => {
    render(<ProjectSelector {...defaultProps} />);
    // The selected project should have a check icon (its button should have primary text)
    const selectedBtn = screen.getByText('Project Alpha').closest('button');
    expect(selectedBtn?.className).toContain('bg-primary');
  });

  it('shows New Project button', () => {
    render(<ProjectSelector {...defaultProps} />);
    expect(screen.getByText('New Project')).toBeInTheDocument();
  });

  it('opens new project form when New Project clicked', () => {
    render(<ProjectSelector {...defaultProps} />);
    fireEvent.click(screen.getByText('New Project'));
    expect(screen.getByText('Create New Project')).toBeInTheDocument();
    expect(screen.getByLabelText('Project title')).toBeInTheDocument();
    expect(screen.getByLabelText('Project owner')).toBeInTheDocument();
  });

  it('shows error when creating without title', () => {
    render(<ProjectSelector {...defaultProps} />);
    fireEvent.click(screen.getByText('New Project'));
    fireEvent.click(screen.getByText('Create'));
    expect(screen.getByText('Project title is required.')).toBeInTheDocument();
  });

  it('cancels new project form', () => {
    render(<ProjectSelector {...defaultProps} />);
    fireEvent.click(screen.getByText('New Project'));
    expect(screen.getByText('Create New Project')).toBeInTheDocument();
    fireEvent.click(screen.getByText('Cancel'));
    expect(screen.queryByText('Create New Project')).not.toBeInTheDocument();
  });

  it('calls createProject.mutate with title and owner', () => {
    render(<ProjectSelector {...defaultProps} />);
    fireEvent.click(screen.getByText('New Project'));
    const titleInput = screen.getByLabelText('Project title');
    fireEvent.change(titleInput, { target: { value: 'New Project Title' } });
    // Owner select should default to first available owner
    const ownerSelect = screen.getByLabelText('Project owner');
    fireEvent.change(ownerSelect, { target: { value: 'testuser' } });
    fireEvent.click(screen.getByText('Create'));
    expect(mockCreateProject.mutate).toHaveBeenCalledWith(
      { title: 'New Project Title', owner: 'testuser' },
      expect.any(Object),
    );
  });

  it('renders owner options from useOwners', () => {
    render(<ProjectSelector {...defaultProps} />);
    fireEvent.click(screen.getByText('New Project'));
    const select = screen.getByLabelText('Project owner');
    expect(select).toBeInTheDocument();
    expect(screen.getByText('testuser (User)')).toBeInTheDocument();
    expect(screen.getByText('testorg (Organization)')).toBeInTheDocument();
  });

  it('shows first letter of project names as avatars', () => {
    render(<ProjectSelector {...defaultProps} />);
    const avatars = screen.getAllByText('P');
    expect(avatars.length).toBe(2);
  });

  it('closes on Escape key', () => {
    render(<ProjectSelector {...defaultProps} />);
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(defaultProps.onClose).toHaveBeenCalled();
  });
});
