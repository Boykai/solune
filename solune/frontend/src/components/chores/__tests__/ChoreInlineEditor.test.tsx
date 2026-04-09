import { describe, it, expect, vi, beforeEach } from 'vitest';
import userEvent from '@testing-library/user-event';

import { render, screen } from '@/test/test-utils';
import { ChoreInlineEditor } from '../ChoreInlineEditor';

vi.mock('@/hooks/useAuth', () => ({
  useAuth: () => ({
    user: { selected_project_id: 'proj-1', login: 'test-user' },
  }),
}));

vi.mock('@/components/activity/EntityHistoryPanel', () => ({
  EntityHistoryPanel: () => <div data-testid="entity-history-panel" />,
}));

function defaultProps() {
  return {
    choreId: 'chore-1',
    name: 'Weekly Cleanup',
    templateContent: '# Cleanup\n\n- [ ] Task 1',
    scheduleType: 'time' as const,
    scheduleValue: 7,
    onChange: vi.fn(),
  };
}

describe('ChoreInlineEditor', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders all editable fields with correct values', () => {
    render(<ChoreInlineEditor {...defaultProps()} />);

    expect(screen.getByLabelText(/name/i)).toHaveValue('Weekly Cleanup');
    expect(screen.getByLabelText(/template content/i)).toHaveValue('# Cleanup\n\n- [ ] Task 1');
    expect(screen.getByLabelText(/schedule type/i)).toHaveValue('time');
    expect(screen.getByLabelText(/schedule value/i)).toHaveValue(7);
  });

  it('calls onChange with updated name when the name input changes', async () => {
    const user = userEvent.setup();
    const props = defaultProps();
    render(<ChoreInlineEditor {...props} />);

    const nameInput = screen.getByLabelText(/name/i);
    await user.type(nameInput, 'X');

    expect(props.onChange).toHaveBeenCalledWith({ name: 'Weekly CleanupX' });
  });

  it('calls onChange with updated template_content when textarea changes', async () => {
    const user = userEvent.setup();
    const props = defaultProps();
    render(<ChoreInlineEditor {...props} />);

    const textarea = screen.getByLabelText(/template content/i);
    await user.type(textarea, '!');

    expect(props.onChange).toHaveBeenCalledWith({ template_content: '# Cleanup\n\n- [ ] Task 1!' });
  });

  it('calls onChange with updated schedule_type when select changes', async () => {
    const user = userEvent.setup();
    const props = defaultProps();
    render(<ChoreInlineEditor {...props} />);

    await user.selectOptions(screen.getByLabelText(/schedule type/i), 'count');

    expect(props.onChange).toHaveBeenCalledWith({ schedule_type: 'count' });
  });

  it('calls onChange with null schedule_value when value is cleared', async () => {
    const user = userEvent.setup();
    const props = defaultProps();
    render(<ChoreInlineEditor {...props} />);

    const valueInput = screen.getByLabelText(/schedule value/i);
    await user.clear(valueInput);

    expect(props.onChange).toHaveBeenCalledWith({ schedule_value: null });
  });

  it('disables all fields when disabled prop is true', () => {
    render(<ChoreInlineEditor {...defaultProps()} disabled />);

    expect(screen.getByLabelText(/name/i)).toBeDisabled();
    expect(screen.getByLabelText(/template content/i)).toBeDisabled();
    expect(screen.getByLabelText(/schedule type/i)).toBeDisabled();
    expect(screen.getByLabelText(/schedule value/i)).toBeDisabled();
  });

  it('disables schedule value when scheduleType is null', () => {
    render(<ChoreInlineEditor {...defaultProps()} scheduleType={null} scheduleValue={null} />);

    expect(screen.getByLabelText(/schedule value/i)).toBeDisabled();
  });

  it('renders the EntityHistoryPanel', () => {
    render(<ChoreInlineEditor {...defaultProps()} />);

    expect(screen.getByTestId('entity-history-panel')).toBeInTheDocument();
  });
});
