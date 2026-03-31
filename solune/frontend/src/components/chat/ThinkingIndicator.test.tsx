/**
 * Tests for ThinkingIndicator — phase-aware loading indicator for plan mode.
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@/test/test-utils';
import { expectNoA11yViolations } from '@/test/a11y-helpers';
import { ThinkingIndicator } from './ThinkingIndicator';

describe('ThinkingIndicator', () => {
  it('renders researching phase label', () => {
    render(<ThinkingIndicator phase="researching" />);
    expect(screen.getByText('Researching project context\u2026')).toBeInTheDocument();
  });

  it('renders planning phase label', () => {
    render(<ThinkingIndicator phase="planning" />);
    expect(screen.getByText('Drafting implementation plan\u2026')).toBeInTheDocument();
  });

  it('renders refining phase label', () => {
    render(<ThinkingIndicator phase="refining" />);
    expect(screen.getByText('Incorporating your feedback\u2026')).toBeInTheDocument();
  });

  it('renders detail text when provided', () => {
    render(<ThinkingIndicator phase="researching" detail="Scanning repo files…" />);
    expect(screen.getByText('Scanning repo files…')).toBeInTheDocument();
  });

  it('does not render detail when omitted', () => {
    render(<ThinkingIndicator phase="planning" />);
    expect(screen.queryByText(/Scanning/)).not.toBeInTheDocument();
  });

  it('has no accessibility violations', async () => {
    const { container } = render(
      <ThinkingIndicator phase="researching" detail="Reading project context…" />,
    );
    await expectNoA11yViolations(container);
  });
});
