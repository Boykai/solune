import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@/test/test-utils';

let mockPathname = '/test';
vi.mock('react-router-dom', () => ({
  useLocation: () => ({ pathname: mockPathname }),
  Outlet: () => <div data-testid="outlet" />,
}));

import { PageTransition } from './PageTransition';

describe('PageTransition', () => {
  beforeEach(() => {
    mockPathname = '/test';
  });

  it('renders Outlet content', () => {
    render(<PageTransition />);
    expect(screen.getByTestId('outlet')).toBeInTheDocument();
  });

  it('has motion-safe:animate-page-enter class', () => {
    render(<PageTransition />);
    const wrapper = screen.getByTestId('outlet').parentElement!;
    expect(wrapper.className).toContain('motion-safe:animate-page-enter');
  });

  it('remounts wrapper when pathname changes', () => {
    mockPathname = '/page-a';
    const { rerender, container } = render(<PageTransition />);
    const firstWrapper = container.firstElementChild!;

    mockPathname = '/page-b';
    rerender(<PageTransition />);
    const secondWrapper = container.firstElementChild!;

    expect(firstWrapper).not.toBe(secondWrapper);
    expect(secondWrapper.className).toContain('motion-safe:animate-page-enter');
  });
});
