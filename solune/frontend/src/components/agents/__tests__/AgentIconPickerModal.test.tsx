import { describe, it, expect, vi, beforeEach } from 'vitest';
import userEvent from '@testing-library/user-event';
import { render, screen } from '@/test/test-utils';
import { AgentIconPickerModal } from '../AgentIconPickerModal';

vi.mock('../AgentIconCatalog', () => ({
  AgentIconCatalog: ({ onSelect }: { onSelect: (v: string | null) => void }) => (
    <div data-testid="icon-catalog">
      <button type="button" onClick={() => onSelect('sun-halo')}>
        Select Sun Halo
      </button>
    </div>
  ),
}));

vi.mock('@/hooks/useScrollLock', () => ({
  useScrollLock: vi.fn(),
}));

describe('AgentIconPickerModal', () => {
  const defaultProps = {
    isOpen: true,
    agentName: 'Test Agent',
    slug: 'test-agent',
    currentIconName: null as string | null,
    isSaving: false,
    onClose: vi.fn(),
    onSave: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders nothing when not open', () => {
    const { container } = render(
      <AgentIconPickerModal {...defaultProps} isOpen={false} />,
    );
    expect(container.firstChild).toBeNull();
  });

  it('renders dialog with agent name when open', () => {
    render(<AgentIconPickerModal {...defaultProps} />);
    expect(screen.getByRole('dialog', { name: /choose an icon for test agent/i })).toBeInTheDocument();
  });

  it('renders the catalog heading text', () => {
    render(<AgentIconPickerModal {...defaultProps} />);
    expect(screen.getByText('Celestial Icon Catalog')).toBeInTheDocument();
  });

  it('calls onClose when close button is clicked', async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    render(<AgentIconPickerModal {...defaultProps} onClose={onClose} />);
    await user.click(screen.getByLabelText('Close icon picker'));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('calls onClose when Cancel button is clicked', async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    render(<AgentIconPickerModal {...defaultProps} onClose={onClose} />);
    await user.click(screen.getByText('Cancel'));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('calls onSave when Save Icon button is clicked', async () => {
    const user = userEvent.setup();
    const onSave = vi.fn();
    render(<AgentIconPickerModal {...defaultProps} onSave={onSave} />);
    await user.click(screen.getByText('Save Icon'));
    expect(onSave).toHaveBeenCalledTimes(1);
  });

  it('disables Save Icon button when isSaving is true', () => {
    render(<AgentIconPickerModal {...defaultProps} isSaving={true} />);
    expect(screen.getByText('Saving…')).toBeInTheDocument();
    expect(screen.getByText('Saving…').closest('button')).toBeDisabled();
  });

  it('closes on Escape key press', async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    render(<AgentIconPickerModal {...defaultProps} onClose={onClose} />);
    await user.keyboard('{Escape}');
    expect(onClose).toHaveBeenCalled();
  });
});
