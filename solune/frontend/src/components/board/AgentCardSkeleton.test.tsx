import { describe, it, expect } from 'vitest';
import { render } from '@/test/test-utils';
import { expectNoA11yViolations } from '@/test/a11y-helpers';

import { AgentCardSkeleton } from './AgentCardSkeleton';

describe('AgentCardSkeleton', () => {
  it('renders skeleton placeholders', () => {
    const { container } = render(<AgentCardSkeleton />);
    expect(container.querySelector('.rounded-lg')).toBeInTheDocument();
  });

  it('has no accessibility violations', async () => {
    const { container } = render(<AgentCardSkeleton />);
    await expectNoA11yViolations(container);
  });
});
