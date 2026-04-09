import { describe, it, expect, vi } from 'vitest';
import userEvent from '@testing-library/user-event';
import { render, screen } from '@/test/test-utils';
import { AgentIconCatalog } from '../AgentIconCatalog';
import { CELESTIAL_ICON_CATALOG } from '@/components/common/agentIcons';

vi.mock('@/components/common/ThemedAgentIcon', () => ({
  ThemedAgentIcon: () => <span data-testid="themed-icon" />,
}));

describe('AgentIconCatalog', () => {
  it('renders the Automatic option', () => {
    render(
      <AgentIconCatalog agentName="Test Agent" onSelect={vi.fn()} />,
    );
    expect(screen.getByText('Automatic')).toBeInTheDocument();
  });

  it('renders all catalog icons', () => {
    render(
      <AgentIconCatalog agentName="Test Agent" onSelect={vi.fn()} />,
    );
    for (const icon of CELESTIAL_ICON_CATALOG) {
      expect(screen.getByText(icon.label)).toBeInTheDocument();
    }
  });

  it('calls onSelect with null when Automatic is clicked', async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    render(
      <AgentIconCatalog agentName="Test Agent" onSelect={onSelect} />,
    );
    await user.click(screen.getByText('Automatic'));
    expect(onSelect).toHaveBeenCalledWith(null);
  });

  it('calls onSelect with icon id when a specific icon is clicked', async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    render(
      <AgentIconCatalog agentName="Test Agent" onSelect={onSelect} />,
    );
    const firstIcon = CELESTIAL_ICON_CATALOG[0];
    // Use getAllByText since the label appears in both the icon and label areas
    const elements = screen.getAllByText(firstIcon.label);
    await user.click(elements[0]);
    expect(onSelect).toHaveBeenCalledWith(firstIcon.id);
  });

  it('highlights the selected icon with primary ring', () => {
    const selectedIcon = CELESTIAL_ICON_CATALOG[0];
    const { container } = render(
      <AgentIconCatalog
        agentName="Test Agent"
        selectedIconName={selectedIcon.id}
        onSelect={vi.fn()}
      />,
    );
    const buttons = container.querySelectorAll('button');
    // First button is Automatic (should NOT have primary ring)
    expect(buttons[0].className).toContain('border-border/70');
    // Second button is the selected icon (should have primary ring)
    expect(buttons[1].className).toContain('ring-primary/20');
  });

  it('highlights Automatic when selectedIconName is null', () => {
    const { container } = render(
      <AgentIconCatalog
        agentName="Test Agent"
        selectedIconName={null}
        onSelect={vi.fn()}
      />,
    );
    const automaticButton = container.querySelectorAll('button')[0];
    expect(automaticButton.className).toContain('ring-primary/20');
  });
});
