/**
 * Tests for the CompactPageHeader component.
 *
 * Covers: required props rendering, badge, stats chips, actions slot,
 * description line-clamp, className forwarding, mobile stats toggle,
 * and accessibility.
 */

import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@/test/test-utils';
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

  it('renders as a semantic <header> element', () => {
    const { container } = render(<CompactPageHeader {...defaultProps} />);
    expect(container.querySelector('header')).toBeInTheDocument();
  });

  it('renders an <h2> heading for the title', () => {
    render(<CompactPageHeader {...defaultProps} />);
    const heading = screen.getByRole('heading', { level: 2 });
    expect(heading).toHaveTextContent('Celestial Agents');
  });

  it('renders with minimal props (eyebrow + title + description only)', () => {
    render(<CompactPageHeader eyebrow="Test" title="Title" description="Desc" />);
    expect(screen.getByText('Test')).toBeInTheDocument();
    expect(screen.getByText('Title')).toBeInTheDocument();
    expect(screen.getByText('Desc')).toBeInTheDocument();
  });

  it('renders a badge when provided', () => {
    render(<CompactPageHeader {...defaultProps} badge="New" />);
    expect(screen.getByText('New')).toBeInTheDocument();
  });

  it('does not render a badge element when badge is undefined', () => {
    const { container } = render(<CompactPageHeader {...defaultProps} />);
    const badges = container.querySelectorAll('span.rounded-full');
    const badgeElements = Array.from(badges).filter((el) => el.textContent === 'New');
    expect(badgeElements).toHaveLength(0);
  });

  it('renders stats chips when provided', () => {
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

  it('does not render stats section when stats is empty', () => {
    render(<CompactPageHeader {...defaultProps} stats={[]} />);
    expect(screen.queryByRole('button', { name: /show stats/i })).not.toBeInTheDocument();
  });

  it('renders the actions slot', () => {
    render(
      <CompactPageHeader
        {...defaultProps}
        actions={<button data-testid="header-action">Add Agent</button>}
      />,
    );
    expect(screen.getByTestId('header-action')).toBeInTheDocument();
    expect(screen.getByText('Add Agent')).toBeInTheDocument();
  });

  it('applies line-clamp-1 class to description', () => {
    const { container } = render(<CompactPageHeader {...defaultProps} />);
    const desc = container.querySelector('p.line-clamp-1');
    expect(desc).toBeInTheDocument();
    expect(desc).toHaveTextContent('Manage your agent constellation.');
  });

  it('forwards custom className to root <header> element', () => {
    const { container } = render(
      <CompactPageHeader {...defaultProps} className="extra-class" />,
    );
    const header = container.querySelector('header');
    expect(header?.className).toContain('extra-class');
  });

  it('renders a mobile stats toggle button', () => {
    const stats = [{ label: 'Count', value: '5' }];
    render(<CompactPageHeader {...defaultProps} stats={stats} />);
    const toggleBtn = screen.getByRole('button', { name: /show stats/i });
    expect(toggleBtn).toBeInTheDocument();
  });

  it('toggles stats visibility on mobile when toggle is clicked', () => {
    const stats = [{ label: 'Count', value: '5' }];
    render(<CompactPageHeader {...defaultProps} stats={stats} />);
    const toggleBtn = screen.getByRole('button', { name: /show stats/i });

    // Initially mobile stats are hidden (button says "Show stats")
    expect(toggleBtn).toHaveAttribute('aria-expanded', 'false');

    // Click to show
    fireEvent.click(toggleBtn);
    expect(screen.getByRole('button', { name: /hide stats/i })).toHaveAttribute(
      'aria-expanded',
      'true',
    );

    // Click to hide again
    fireEvent.click(screen.getByRole('button', { name: /hide stats/i }));
    expect(screen.getByRole('button', { name: /show stats/i })).toHaveAttribute(
      'aria-expanded',
      'false',
    );
  });

  it('links the mobile toggle button to the stats container via aria-controls', () => {
    const stats = [{ label: 'Count', value: '5' }];
    const { container } = render(<CompactPageHeader {...defaultProps} stats={stats} />);
    const toggleBtn = screen.getByRole('button', { name: /show stats/i });
    const controlsId = toggleBtn.getAttribute('aria-controls');
    expect(controlsId).toBeTruthy();
    const statsContainer = container.querySelector(`#${CSS.escape(controlsId!)}`);
    expect(statsContainer).toBeInTheDocument();
    expect(statsContainer).toHaveTextContent('Count');
  });

  it('does not render actions zone when actions prop is omitted', () => {
    const { container } = render(<CompactPageHeader {...defaultProps} />);
    // The header should only contain eyebrow, title, and description areas — no action buttons
    const buttons = container.querySelectorAll('button');
    expect(buttons).toHaveLength(0);
  });

  it('description text appears only once in the header', () => {
    render(<CompactPageHeader {...defaultProps} />);
    // Unlike CelestialCatalogHero which duplicated description in an aside panel,
    // CompactPageHeader renders description exactly once
    const descriptions = screen.getAllByText('Manage your agent constellation.');
    expect(descriptions).toHaveLength(1);
  });

  it('renders each stat with both label and value text', () => {
    const stats = [
      { label: 'Columns', value: '4' },
      { label: 'Agents', value: '12' },
      { label: 'Active', value: '3' },
    ];
    render(<CompactPageHeader {...defaultProps} stats={stats} />);
    for (const stat of stats) {
      expect(screen.getByText(stat.label)).toBeInTheDocument();
      expect(screen.getByText(stat.value)).toBeInTheDocument();
    }
  });

  it('does not render a stats section when stats prop is omitted', () => {
    render(<CompactPageHeader {...defaultProps} />);
    expect(screen.queryByRole('button', { name: /stats/i })).not.toBeInTheDocument();
  });

  it('has no accessibility violations', async () => {
    const { container } = render(
      <CompactPageHeader
        {...defaultProps}
        badge="Beta"
        stats={[{ label: 'Items', value: '10' }]}
        actions={<button>Action</button>}
      />,
    );
    await expectNoA11yViolations(container);
  });
});
