import { describe, it, expect } from 'vitest';
import { render, screen } from '@/test/test-utils';
import { expectNoA11yViolations } from '@/test/a11y-helpers';

import { BoardColumnSkeleton } from './BoardColumnSkeleton';

describe('BoardColumnSkeleton', () => {
  it('renders with loading status', () => {
    render(<BoardColumnSkeleton />);
    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('indicates busy state for assistive technologies', () => {
    render(<BoardColumnSkeleton />);
    expect(screen.getByRole('status')).toHaveAttribute('aria-busy', 'true');
  });

  it('provides screen reader text', () => {
    render(<BoardColumnSkeleton />);
    expect(screen.getByText(/loading column/i)).toBeInTheDocument();
  });

  it('renders multiple issue card skeletons', () => {
    const { container } = render(<BoardColumnSkeleton />);
    const issueSkeletons = container.querySelectorAll('.rounded-\\[1\\.15rem\\]');
    expect(issueSkeletons.length).toBe(3);
  });

  it('has no accessibility violations', async () => {
    const { container } = render(<BoardColumnSkeleton />);
    await expectNoA11yViolations(container);
  });
});
