import { describe, it, expect } from 'vitest';
import { render, screen } from '@/test/test-utils';
import { expectNoA11yViolations } from '@/test/a11y-helpers';

import { PresetBadge } from './PresetBadge';

describe('PresetBadge', () => {
  it('renders known preset with correct label', () => {
    render(<PresetBadge presetId="spec-kit" />);
    expect(screen.getByText('Spec Kit')).toBeInTheDocument();
  });

  it('renders github preset', () => {
    render(<PresetBadge presetId="github" />);
    expect(screen.getByText('GitHub')).toBeInTheDocument();
  });

  it('renders unknown preset with presetId as label', () => {
    render(<PresetBadge presetId="custom-preset" />);
    expect(screen.getByText('custom-preset')).toBeInTheDocument();
  });

  it.each([
    ['github', 'GitHub'],
    ['spec-kit', 'Spec Kit'],
    ['default', 'Default'],
    ['app-builder', 'App Builder'],
  ])('renders %s preset with its label', (presetId, label) => {
    render(<PresetBadge presetId={presetId} />);
    expect(screen.getByText(label)).toBeInTheDocument();
  });

  it('applies custom className', () => {
    const { container } = render(<PresetBadge presetId="github" className="extra" />);
    expect(container.firstElementChild?.className).toContain('extra');
  });

  it('includes a lock icon', () => {
    const { container } = render(<PresetBadge presetId="github" />);
    const svg = container.querySelector('svg');
    expect(svg).toBeInTheDocument();
  });

  it('has no accessibility violations', async () => {
    const { container } = render(<PresetBadge presetId="default" />);
    await expectNoA11yViolations(container);
  });
});
