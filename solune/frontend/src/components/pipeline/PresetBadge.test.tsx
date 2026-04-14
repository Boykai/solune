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

  it('renders default preset with correct label', () => {
    render(<PresetBadge presetId="default" />);
    expect(screen.getByText('Default')).toBeInTheDocument();
  });

  it('renders app-builder preset with correct label', () => {
    render(<PresetBadge presetId="app-builder" />);
    expect(screen.getByText('App Builder')).toBeInTheDocument();
  });

  it('renders unknown preset with presetId as label', () => {
    render(<PresetBadge presetId="custom-preset" />);
    expect(screen.getByText('custom-preset')).toBeInTheDocument();
  });

  it('renders all known presets', () => {
    const presets = ['github', 'spec-kit', 'default', 'app-builder'];
    for (const presetId of presets) {
      const { unmount } = render(<PresetBadge presetId={presetId} />);
      unmount();
    }
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
