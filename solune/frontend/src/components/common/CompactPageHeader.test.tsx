/**
 * Tests for the CompactPageHeader component.
 *
 * Covers: required props rendering, stats display, actions slot, badge,
 * className forwarding, and accessibility.
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@/test/test-utils';
import { CompactPageHeader } from './CompactPageHeader';
import { expectNoA11yViolations } from '@/test/a11y-helpers';

const defaultProps = {
  eyebrow: 'Catalog',
  title: 'Celestial Agents',
  description: 'Manage your agent constellation.',
};

describe('CompactPageHeader', () => {
  it('renders eyebrow, title, and description text', () => {
    render(<CompactPageHeader {...defaultProps} />);
    expect(screen.getByText('Catalog')).toBeInTheDocument();
    expect(screen.getByText('Celestial Agents')).toBeInTheDocument();
    expect(screen.getByText('Manage your agent constellation.')).toBeInTheDocument();
  });

  it('renders as a <section> element', () => {
    const { container } = render(<CompactPageHeader {...defaultProps} />);
    expect(container.querySelector('section')).toBeInTheDocument();
  });

  it('renders a badge when provided', () => {
    render(<CompactPageHeader {...defaultProps} badge="New" />);
    expect(screen.getByText('New')).toBeInTheDocument();
  });

  it('does not render a badge element when not provided', () => {
    const { container } = render(<CompactPageHeader {...defaultProps} />);
    const badgeSpans = container.querySelectorAll('span.rounded-full');
    const badges = Array.from(badgeSpans).filter((el) => el.textContent === 'New');
    expect(badges).toHaveLength(0);
  });

  it('renders stats as inline chips when provided', () => {
    const stats = [
      { label: 'Total Agents', value: '42' },
      { label: 'Active', value: '12' },
    ];
    render(<CompactPageHeader {...defaultProps} stats={stats} />);
    expect(screen.getByText('Total Agents')).toBeInTheDocument();
    expect(screen.getByText('42')).toBeInTheDocument();
    expect(screen.getByText('Active')).toBeInTheDocument();
    expect(screen.getByText('12')).toBeInTheDocument();
  });

  it('renders the actions slot', () => {
    render(
      <CompactPageHeader
        {...defaultProps}
        actions={<button data-testid="hero-action">Add Agent</button>}
      />
    );
    expect(screen.getByTestId('hero-action')).toBeInTheDocument();
    expect(screen.getByText('Add Agent')).toBeInTheDocument();
  });

  it('forwards custom className', () => {
    const { container } = render(
      <CompactPageHeader {...defaultProps} className="extra-header-class" />
    );
    const section = container.querySelector('section');
    expect(section?.className).toContain('extra-header-class');
  });

  it('applies section-aurora class on the section', () => {
    const { container } = render(<CompactPageHeader {...defaultProps} />);
    const section = container.querySelector('section');
    expect(section?.className).toContain('section-aurora');
  });

  it('has no accessibility violations', async () => {
    const { container } = render(<CompactPageHeader {...defaultProps} />);
    await expectNoA11yViolations(container);
  });
});
