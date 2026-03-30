import { describe, it, expect } from 'vitest';
import { render, screen } from '@/test/test-utils';
import { expectNoA11yViolations } from '@/test/a11y-helpers';

import { AgentAvatar } from '../AgentAvatar';

describe('AgentAvatar', () => {
  it('renders an SVG avatar with correct aria-label', () => {
    render(<AgentAvatar slug="reviewer" />);
    const svg = screen.getByRole('img', { name: /avatar for reviewer/i });
    expect(svg).toBeInTheDocument();
  });

  it('uses default medium size', () => {
    render(<AgentAvatar slug="reviewer" />);
    const svg = screen.getByRole('img');
    expect(svg).toHaveAttribute('width', '32');
    expect(svg).toHaveAttribute('height', '32');
  });

  it('respects sm size', () => {
    render(<AgentAvatar slug="reviewer" size="sm" />);
    const svg = screen.getByRole('img');
    expect(svg).toHaveAttribute('width', '24');
  });

  it('respects lg size', () => {
    render(<AgentAvatar slug="reviewer" size="lg" />);
    const svg = screen.getByRole('img');
    expect(svg).toHaveAttribute('width', '48');
  });

  it('produces deterministic avatar for same slug', () => {
    const { container: c1 } = render(<AgentAvatar slug="test-agent" />);
    const { container: c2 } = render(<AgentAvatar slug="test-agent" />);
    expect(c1.innerHTML).toBe(c2.innerHTML);
  });

  it('produces different avatars for different slugs', () => {
    const { container: c1 } = render(<AgentAvatar slug="alpha" />);
    const { container: c2 } = render(<AgentAvatar slug="omega" />);
    expect(c1.querySelector('svg')?.innerHTML).not.toBe(
      c2.querySelector('svg')?.innerHTML
    );
  });

  it('applies custom className', () => {
    render(<AgentAvatar slug="test" className="custom-class" />);
    const wrapper = screen.getByRole('img').parentElement;
    expect(wrapper?.className).toContain('custom-class');
  });

  it('has no accessibility violations', async () => {
    const { container } = render(<AgentAvatar slug="a11y-test" />);
    await expectNoA11yViolations(container);
  });
});
