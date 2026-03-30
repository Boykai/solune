import { describe, it, expect } from 'vitest';
import { render } from '@/test/test-utils';
import { expectNoA11yViolations } from '@/test/a11y-helpers';

import { IssueCardSkeleton } from './IssueCardSkeleton';

describe('IssueCardSkeleton', () => {
  it('renders skeleton placeholders', () => {
    const { container } = render(<IssueCardSkeleton />);
    expect(container.querySelector('.rounded-\\[1\\.15rem\\]')).toBeInTheDocument();
  });

  it('has no accessibility violations', async () => {
    const { container } = render(<IssueCardSkeleton />);
    await expectNoA11yViolations(container);
  });
});
