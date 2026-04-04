import { describe, expect, it, vi } from 'vitest';
import { fireEvent } from '@testing-library/react';
import { render, screen } from '@/test/test-utils';
import { BoardToolbar } from './BoardToolbar';
import type { BoardFilterState, BoardSortState, BoardGroupState } from '@/hooks/useBoardControls';

// ── Mocks ──

vi.mock('@/hooks/useMediaQuery', () => ({
  useMediaQuery: () => false, // Desktop by default
}));

// ── Helpers ──

const defaultFilters: BoardFilterState = {
  labels: [],
  assignees: [],
  milestones: [],
  priority: [],
  pipelineConfig: null,
};

const defaultSort: BoardSortState = {
  field: null,
  direction: 'desc',
};

const defaultGroup: BoardGroupState = {
  field: null,
};

const baseProps = {
  filters: defaultFilters,
  sort: defaultSort,
  group: defaultGroup,
  onFiltersChange: vi.fn(),
  onSortChange: vi.fn(),
  onGroupChange: vi.fn(),
  onClearAll: vi.fn(),
  availableLabels: ['bug', 'feature'],
  availableAssignees: ['alice', 'bob'],
  availableMilestones: ['v1.0'],
  hasActiveFilters: false,
  hasActiveSort: false,
  hasActiveGroup: false,
  hasActiveControls: false,
};

// ── Tests ──

describe('BoardToolbar', () => {
  it('renders Filter, Sort, and Group buttons', () => {
    render(<BoardToolbar {...baseProps} />);
    expect(screen.getByText('Filter')).toBeInTheDocument();
    expect(screen.getByText('Sort')).toBeInTheDocument();
    expect(screen.getByText('Group by')).toBeInTheDocument();
  });

  it('shows the search input when onSearchChange is provided', () => {
    render(<BoardToolbar {...baseProps} onSearchChange={vi.fn()} />);
    expect(screen.getByLabelText('Search issues')).toBeInTheDocument();
  });

  it('hides search input when onSearchChange is not provided', () => {
    render(<BoardToolbar {...baseProps} />);
    expect(screen.queryByLabelText('Search issues')).not.toBeInTheDocument();
  });

  it('calls onSearchChange when typing in search', () => {
    const onSearchChange = vi.fn();
    render(<BoardToolbar {...baseProps} onSearchChange={onSearchChange} />);
    const input = screen.getByLabelText('Search issues');
    fireEvent.change(input, { target: { value: 'test' } });
    expect(onSearchChange).toHaveBeenCalledWith('test');
  });

  it('shows Clear search button when searchQuery is present', () => {
    render(
      <BoardToolbar {...baseProps} searchQuery="hello" onSearchChange={vi.fn()} />
    );
    expect(screen.getByLabelText('Clear search')).toBeInTheDocument();
  });

  it('clears search when Clear search button is clicked', () => {
    const onSearchChange = vi.fn();
    render(
      <BoardToolbar {...baseProps} searchQuery="hello" onSearchChange={onSearchChange} />
    );
    fireEvent.click(screen.getByLabelText('Clear search'));
    expect(onSearchChange).toHaveBeenCalledWith('');
  });

  it('opens filter panel when Filter button is clicked', () => {
    render(<BoardToolbar {...baseProps} />);
    fireEvent.click(screen.getByText('Filter'));
    // Filter panel should show label checkboxes
    expect(screen.getByText('bug')).toBeInTheDocument();
    expect(screen.getByText('feature')).toBeInTheDocument();
  });

  it('opens sort panel when Sort button is clicked', () => {
    render(<BoardToolbar {...baseProps} />);
    fireEvent.click(screen.getByText('Sort'));
    expect(screen.getByText('Created Date')).toBeInTheDocument();
    expect(screen.getByText('Updated Date')).toBeInTheDocument();
  });

  it('closes filter panel when clicking Filter again (toggle)', () => {
    render(<BoardToolbar {...baseProps} />);
    fireEvent.click(screen.getByText('Filter'));
    expect(screen.getByText('bug')).toBeInTheDocument();

    fireEvent.click(screen.getByText('Filter'));
    expect(screen.queryByText('bug')).not.toBeInTheDocument();
  });

  it('only one panel is open at a time', () => {
    render(<BoardToolbar {...baseProps} />);
    // Open filter
    fireEvent.click(screen.getByText('Filter'));
    expect(screen.getByText('bug')).toBeInTheDocument();

    // Open sort — should close filter
    fireEvent.click(screen.getByText('Sort'));
    expect(screen.queryByText('bug')).not.toBeInTheDocument();
    expect(screen.getByText('Created Date')).toBeInTheDocument();
  });

  it('shows Clear button when hasActiveControls is true', () => {
    render(<BoardToolbar {...baseProps} hasActiveControls={true} />);
    // The main clear button has text "Clear" wrapped in a Tooltip
    const clearButtons = screen.getAllByText('Clear');
    expect(clearButtons.length).toBeGreaterThan(0);
  });

  it('hides Clear button when hasActiveControls is false', () => {
    render(<BoardToolbar {...baseProps} hasActiveControls={false} />);
    // No "Clear" button should be visible (other than potentially inside panels)
    expect(screen.queryByText('Clear')).not.toBeInTheDocument();
  });

  it('calls onClearAll when Clear button is clicked', () => {
    const onClearAll = vi.fn();
    render(<BoardToolbar {...baseProps} hasActiveControls={true} onClearAll={onClearAll} />);
    // Click the first "Clear" button (the toolbar-level one)
    fireEvent.click(screen.getAllByText('Clear')[0]);
    expect(onClearAll).toHaveBeenCalledOnce();
  });

  it('closes panel on Escape key', () => {
    render(<BoardToolbar {...baseProps} />);
    fireEvent.click(screen.getByText('Filter'));
    expect(screen.getByText('bug')).toBeInTheDocument();

    fireEvent.keyDown(document, { key: 'Escape' });
    expect(screen.queryByText('bug')).not.toBeInTheDocument();
  });

  it('shows indicator dot when hasActiveFilters is true', () => {
    const { container } = render(
      <BoardToolbar {...baseProps} hasActiveFilters={true} />
    );
    // The indicator dot is a span with specific classes
    const dots = container.querySelectorAll('.bg-primary.rounded-full');
    expect(dots.length).toBeGreaterThan(0);
  });

  it('renders available milestones in filter panel', () => {
    render(<BoardToolbar {...baseProps} />);
    fireEvent.click(screen.getByText('Filter'));
    expect(screen.getByText('v1.0')).toBeInTheDocument();
  });

  it('renders assignees in filter panel', () => {
    render(<BoardToolbar {...baseProps} />);
    fireEvent.click(screen.getByText('Filter'));
    expect(screen.getByText('alice')).toBeInTheDocument();
    expect(screen.getByText('bob')).toBeInTheDocument();
  });
});
