import { describe, it, expect, vi, beforeEach } from 'vitest';
import userEvent from '@testing-library/user-event';

import { render, screen } from '@/test/test-utils';
import { ChoresToolbar } from '../ChoresToolbar';

function defaultProps() {
  return {
    search: '',
    onSearchChange: vi.fn(),
    statusFilter: 'all' as const,
    onStatusFilterChange: vi.fn(),
    scheduleFilter: 'all' as const,
    onScheduleFilterChange: vi.fn(),
    sortMode: 'attention' as const,
    onSortModeChange: vi.fn(),
  };
}

describe('ChoresToolbar', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the toolbar heading', () => {
    render(<ChoresToolbar {...defaultProps()} />);

    expect(screen.getByText('Filter active routines')).toBeInTheDocument();
  });

  it('renders the search input with correct aria-label', () => {
    render(<ChoresToolbar {...defaultProps()} />);

    const searchInput = screen.getByRole('textbox', { name: /search chores/i });
    expect(searchInput).toBeInTheDocument();
  });

  it('calls onSearchChange when typing in the search input', async () => {
    const user = userEvent.setup();
    const props = defaultProps();
    render(<ChoresToolbar {...props} />);

    await user.type(screen.getByRole('textbox', { name: /search chores/i }), 'cleanup');

    expect(props.onSearchChange).toHaveBeenCalled();
    expect(props.onSearchChange).toHaveBeenCalledWith('c');
  });

  it('renders status filter buttons', () => {
    render(<ChoresToolbar {...defaultProps()} />);

    expect(screen.getByRole('button', { name: /all states/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^active$/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^paused$/i })).toBeInTheDocument();
  });

  it('marks the active status filter as pressed', () => {
    render(<ChoresToolbar {...defaultProps()} statusFilter="active" />);

    expect(screen.getByRole('button', { name: /^active$/i })).toHaveAttribute(
      'aria-pressed',
      'true'
    );
    expect(screen.getByRole('button', { name: /all states/i })).toHaveAttribute(
      'aria-pressed',
      'false'
    );
  });

  it('calls onStatusFilterChange when a status button is clicked', async () => {
    const user = userEvent.setup();
    const props = defaultProps();
    render(<ChoresToolbar {...props} />);

    await user.click(screen.getByRole('button', { name: /^paused$/i }));

    expect(props.onStatusFilterChange).toHaveBeenCalledWith('paused');
  });

  it('renders the schedule filter dropdown', () => {
    render(<ChoresToolbar {...defaultProps()} />);

    const select = screen.getByRole('combobox', { name: /filter chores by schedule/i });
    expect(select).toBeInTheDocument();
    expect(select).toHaveValue('all');
  });

  it('calls onScheduleFilterChange when a schedule option is selected', async () => {
    const user = userEvent.setup();
    const props = defaultProps();
    render(<ChoresToolbar {...props} />);

    await user.selectOptions(
      screen.getByRole('combobox', { name: /filter chores by schedule/i }),
      'time'
    );

    expect(props.onScheduleFilterChange).toHaveBeenCalledWith('time');
  });

  it('renders the sort dropdown', () => {
    render(<ChoresToolbar {...defaultProps()} />);

    const select = screen.getByRole('combobox', { name: /sort chores/i });
    expect(select).toBeInTheDocument();
    expect(select).toHaveValue('attention');
  });

  it('calls onSortModeChange when a sort option is selected', async () => {
    const user = userEvent.setup();
    const props = defaultProps();
    render(<ChoresToolbar {...props} />);

    await user.selectOptions(
      screen.getByRole('combobox', { name: /sort chores/i }),
      'name'
    );

    expect(props.onSortModeChange).toHaveBeenCalledWith('name');
  });
});
