import { describe, it, expect } from 'vitest';
import { render } from '@/test/test-utils';
import { ChatMessageSkeleton } from './ChatMessageSkeleton';

describe('ChatMessageSkeleton', () => {
  it('renders without crashing', () => {
    const { container } = render(<ChatMessageSkeleton />);
    expect(container.firstChild).toBeTruthy();
  });

  it('renders skeleton placeholders', () => {
    const { container } = render(<ChatMessageSkeleton />);
    // The Skeleton component renders divs inside the wrapper
    const innerDivs = container.querySelectorAll('div div');
    // Should have multiple inner divs: avatar + text lines wrapper + individual lines
    expect(innerDivs.length).toBeGreaterThanOrEqual(3);
  });

  it('has a circular avatar skeleton', () => {
    const { container } = render(<ChatMessageSkeleton />);
    const roundedFull = container.querySelector('[class*="rounded-full"]');
    expect(roundedFull).toBeTruthy();
  });

  it('constrains max width', () => {
    const { container } = render(<ChatMessageSkeleton />);
    const outer = container.firstChild as HTMLElement;
    expect(outer?.className).toContain('max-w-');
  });
});
