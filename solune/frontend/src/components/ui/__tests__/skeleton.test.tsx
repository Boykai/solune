/**
 * Tests for Skeleton component.
 *
 * Covers: role/aria attributes, custom className, default pulse variant,
 * and shimmer variant.
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@/test/test-utils';
import { Skeleton } from '../skeleton';

describe('Skeleton', () => {
  it('renders with role=presentation', () => {
    render(<Skeleton />);
    expect(screen.getByRole('presentation', { hidden: true })).toBeInTheDocument();
  });

  it('has aria-hidden attribute', () => {
    render(<Skeleton />);
    const el = screen.getByRole('presentation', { hidden: true });
    expect(el).toHaveAttribute('aria-hidden', 'true');
  });

  it('applies custom className', () => {
    const { container } = render(<Skeleton className="w-20 h-4" />);
    const el = container.firstChild as HTMLElement;
    expect(el.className).toContain('w-20');
    expect(el.className).toContain('h-4');
  });

  it('applies default pulse variant', () => {
    const { container } = render(<Skeleton />);
    const el = container.firstChild as HTMLElement;
    expect(el.className).toContain('animate-pulse');
  });

  it('applies shimmer variant', () => {
    const { container } = render(<Skeleton variant="shimmer" />);
    const el = container.firstChild as HTMLElement;
    expect(el.className).toContain('celestial-shimmer');
    expect(el.className).not.toContain('animate-pulse');
  });
});
