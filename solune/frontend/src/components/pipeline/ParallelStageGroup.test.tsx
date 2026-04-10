/**
 * Tests for ParallelStageGroup component.
 *
 * Covers: children rendering, descriptive text, and custom className.
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@/test/test-utils';
import { ParallelStageGroup } from './ParallelStageGroup';

describe('ParallelStageGroup', () => {
  it('renders children', () => {
    render(
      <ParallelStageGroup>
        <div>Agent A</div>
        <div>Agent B</div>
      </ParallelStageGroup>,
    );
    expect(screen.getByText('Agent A')).toBeInTheDocument();
    expect(screen.getByText('Agent B')).toBeInTheDocument();
  });

  it('shows parallel execution description text', () => {
    render(
      <ParallelStageGroup>
        <div>Content</div>
      </ParallelStageGroup>,
    );
    expect(
      screen.getByText(
        'Agents in this stage are grouped. The pipeline completes this stage before moving on.',
      ),
    ).toBeInTheDocument();
  });

  it('applies custom className', () => {
    const { container } = render(
      <ParallelStageGroup className="my-custom-class">
        <div>Content</div>
      </ParallelStageGroup>,
    );
    const wrapper = container.firstChild as HTMLElement;
    expect(wrapper.className).toContain('my-custom-class');
  });
});
