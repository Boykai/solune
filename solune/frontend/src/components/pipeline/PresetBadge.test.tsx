import { describe, it, expect } from 'vitest';
import { render, screen } from '@/test/test-utils';
import { expectNoA11yViolations } from '@/test/a11y-helpers';

import { PresetBadge } from './PresetBadge';

describe('PresetBadge', () => {
  it('renders known preset with correct label', () => {
    render(<PresetBadge presetId="spec-kit" />);
    expect(screen.getByText('Spec Kit')).toBeInTheDocument();
  });

  it('renders github-copilot preset', () => {
    render(<PresetBadge presetId="github-copilot" />);
    expect(screen.getByText('GitHub Copilot')).toBeInTheDocument();
  });

  it('renders unknown preset with presetId as label', () => {
    render(<PresetBadge presetId="custom-preset" />);
    expect(screen.getByText('custom-preset')).toBeInTheDocument();
  });

  it('renders all known presets', () => {
    const presets = ['spec-kit', 'github-copilot', 'easy', 'medium', 'hard', 'expert'];
    for (const presetId of presets) {
      const { unmount } = render(<PresetBadge presetId={presetId} />);
      unmount();
    }
  });

  it('applies custom className', () => {
    const { container } = render(<PresetBadge presetId="easy" className="extra" />);
    expect(container.firstElementChild?.className).toContain('extra');
  });

  it('includes a lock icon', () => {
    const { container } = render(<PresetBadge presetId="easy" />);
    const svg = container.querySelector('svg');
    expect(svg).toBeInTheDocument();
  });

  it('has no accessibility violations', async () => {
    const { container } = render(<PresetBadge presetId="medium" />);
    await expectNoA11yViolations(container);
  });
});
